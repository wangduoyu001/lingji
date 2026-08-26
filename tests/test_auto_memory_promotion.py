from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.auto_review import (
    AutoMemoryPromotionService,
    PromotionStatus,
    ReviewCandidate,
)
from src.retrieval.memory_db import MemoryDatabase
from src.storage.state_db import StateDatabase


def make_candidate(**overrides):
    values = {
        "memory_id": "candidate-1",
        "title": "The owner prefers short answers",
        "content": "The owner prefers short answers.",
        "memory_type": "preference",
        "content_hash": "hash-1",
        "source_refs": ("chat:1:message:2",),
        "confidence": 0.90,
        "authority": "direct_user",
        "source_kind": "user_chat",
        "extractor_version": "extractor-1",
        "structured_content": {"preference": "short answers"},
        "risk_flags": (),
    }
    values.update(overrides)
    return ReviewCandidate(**values)


@pytest.fixture
def harness(tmp_path: Path):
    state = StateDatabase(tmp_path / "state.db")
    memory = MemoryDatabase(tmp_path / "memory.db")
    return AutoMemoryPromotionService(state_db=state, memory_db=memory), state, memory


@pytest.mark.parametrize(
    ("overrides", "status", "reason"),
    [
        ({"confidence": 0.899}, PromotionStatus.PENDING_OWNER_REVIEW, "confidence_below_threshold"),
        ({"confidence": 0.90}, PromotionStatus.ACTIVE, "auto_activation_eligible"),
        ({"authority": "ai_inference", "source_kind": "summary"}, PromotionStatus.PENDING_OWNER_REVIEW, "direct_user_or_authoritative_source_required"),
        ({"source_refs": ()}, PromotionStatus.PENDING_OWNER_REVIEW, "evidence_required"),
        ({"metadata": {"has_conflict": True}}, PromotionStatus.PENDING_OWNER_REVIEW, "unresolved_conflict"),
        ({"metadata": {"duplicate_ambiguity": True}}, PromotionStatus.PENDING_OWNER_REVIEW, "duplicate_ambiguity"),
        ({"memory_type": "core"}, PromotionStatus.PENDING_OWNER_REVIEW, "core_memory_requires_owner"),
        ({"metadata": {"risk_flags": ["identity"]}}, PromotionStatus.PENDING_OWNER_REVIEW, "identity_requires_owner"),
        ({"risk_flags": ("credentials",)}, PromotionStatus.PENDING_OWNER_REVIEW, "credentials_requires_owner"),
        ({"risk_flags": ("medical",)}, PromotionStatus.PENDING_OWNER_REVIEW, "medical_requires_owner"),
        ({"risk_flags": ("destructive",)}, PromotionStatus.PENDING_OWNER_REVIEW, "destructive_requires_owner"),
    ],
)
def test_policy_matrix(harness, overrides, status, reason):
    service, _state, _memory = harness
    result = service.evaluate(make_candidate(**overrides))
    assert result["status"] == status.value
    assert reason in result["reason_codes"]


def test_authoritative_current_project_source_can_activate(harness):
    service, _state, _memory = harness
    candidate = make_candidate(
        authority="project_authority",
        source_kind="current_project_document",
        metadata={"current_authoritative": True},
    )
    assert service.evaluate(candidate)["status"] == PromotionStatus.ACTIVE.value


def test_projection_contains_provenance_and_is_idempotent(harness):
    service, state, memory = harness
    first = service.evaluate(make_candidate())
    second = service.evaluate(make_candidate())
    assert first["status"] == PromotionStatus.ACTIVE.value
    assert second["decision_id"] == first["decision_id"]
    assert len(memory.list_documents()) == 1
    events = state.recent_events(100)
    decisions = [e for e in events if e["event_type"] == "memory_promotion_decision"]
    assert len(decisions) == 1
    projection = memory.fetch_memory(first["candidate_id"])
    assert projection["relationships"]["evidence_refs"] == ["chat:1:message:2"]
    assert projection["relationships"]["policy_version"] == "memory-promotion-1"


def test_policy_or_extractor_version_creates_new_decision_preserving_audit(harness):
    service, state, _memory = harness
    first = service.evaluate(make_candidate())
    second = service.evaluate(replace(make_candidate(), extractor_version="extractor-2"))
    assert first["decision_id"] != second["decision_id"]
    decisions = [e for e in state.recent_events(100) if e["event_type"] == "memory_promotion_decision"]
    assert len(decisions) == 2
    assert {d["payload_json"] for d in decisions}


def test_owner_approval_requires_confirmation_and_expected_hash(harness):
    service, _state, memory = harness
    candidate = make_candidate(memory_type="core")
    pending = service.evaluate(candidate)
    with pytest.raises(PermissionError):
        service.approve(pending["candidate_id"], expected_content_hash="hash-1", owner_confirmed=False)
    with pytest.raises(ValueError, match="hash"):
        service.approve(pending["candidate_id"], expected_content_hash="stale", owner_confirmed=True)
    approved = service.approve(pending["candidate_id"], expected_content_hash="hash-1", owner_confirmed=True)
    assert approved["status"] == PromotionStatus.ACTIVE.value
    assert memory.fetch_memory(candidate.memory_id)["memory_tier"] == "derived"


def test_rejection_requires_confirmation_and_retains_evidence(harness):
    service, state, memory = harness
    pending = service.evaluate(make_candidate(authority="ai_inference", source_kind="summary"))
    rejected = service.reject(
        pending["candidate_id"], expected_content_hash="hash-1", owner_confirmed=True, reason="not stable"
    )
    assert rejected["status"] == PromotionStatus.REJECTED.value
    assert memory.fetch_memory("candidate-1") is None
    assert any(e["event_type"] == "memory_promotion_owner_rejected" for e in state.recent_events(100))
    assert service.candidate("candidate-1")["content"] == "The owner prefers short answers."


def test_projection_failure_is_truthful_pending_error_and_keeps_candidate(tmp_path: Path):
    state = StateDatabase(tmp_path / "state.db")

    def broken(_entry):
        raise OSError("index unavailable")

    service = AutoMemoryPromotionService(state_db=state, projection_writer=broken)
    result = service.evaluate(make_candidate())
    assert result["status"] == PromotionStatus.ERROR.value
    assert result["reason_codes"] == ["projection_persist_failed"]
    assert result["mutation_performed"] is False
    assert service.candidate("candidate-1") is not None


def test_restricted_and_security_categories_never_auto_activate(harness):
    service, _state, _memory = harness
    for flag in ("secret", "permission", "legal", "financial", "security", "irreversible"):
        result = service.evaluate(make_candidate(risk_flags=(flag,)))
        assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value

