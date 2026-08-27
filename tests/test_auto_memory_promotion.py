from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path

import pytest

from src.auto_review import (
    AutoMemoryPromotionService,
    PromotionStatus,
    ReviewCandidate,
)
from src.retrieval.memory_db import MemoryDatabase
from src.sources import SourceReadModel
from src.storage.state_db import StateDatabase


def make_candidate(**overrides):
    content = "The owner prefers short answers."
    title = "The owner prefers short answers"
    structured = {"preference": "short answers"}
    authentic_hash = hashlib.sha256(
        json.dumps({"title": title, "content": content, "structured": structured}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    values = {
        "memory_id": "candidate-1",
        "title": title,
        "content": content,
        "memory_type": "preference",
        "content_hash": authentic_hash,
        "source_refs": ("msg-1",),
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
    source = SourceReadModel(memory)
    source_row = source.upsert_source({"source_type": "chat", "external_id": "chat-1"})
    conversation = source.upsert_conversation({"source_id": source_row["source_id"], "external_id": "conv-1"})
    source.upsert_message({"message_id": "msg-1", "source_id": source_row["source_id"], "conversation_id": conversation["conversation_id"], "external_id": "msg-ext-1", "role": "user", "sequence": 1, "content": "source evidence"})
    return AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source), state, memory


@pytest.mark.parametrize(
    ("overrides", "status", "reason"),
    [
        ({"confidence": 0.899}, PromotionStatus.PENDING_OWNER_REVIEW, "confidence_below_threshold"),
        ({"confidence": 0.90}, PromotionStatus.PENDING_OWNER_REVIEW, "automatic_activation_quarantined"),
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


def test_authoritative_current_project_source_requires_owner_approval(harness):
    service, _state, _memory = harness
    candidate = make_candidate(
        authority="project_authority",
        source_kind="current_project_document",
        metadata={"current_authoritative": True},
    )
    result = service.evaluate(candidate)
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    assert result["reason_codes"] == ["automatic_activation_quarantined"]


def test_projection_contains_provenance_and_is_idempotent(harness):
    service, state, memory = harness
    pending = service.evaluate(make_candidate())
    first = service.approve(
        pending["candidate_id"],
        expected_content_hash=pending["content_hash"],
        owner_confirmed=True,
    )
    second = service.approve(
        pending["candidate_id"],
        expected_content_hash=pending["content_hash"],
        owner_confirmed=True,
    )
    assert first["status"] == PromotionStatus.ACTIVE.value
    assert second["decision_id"] == first["decision_id"]
    assert len(memory.list_documents()) == 1
    events = state.recent_events(100)
    decisions = [e for e in events if e["event_type"] == "memory_promotion_decision"]
    assert len(decisions) == 1
    projection = memory.fetch_memory(first["candidate_id"])
    assert projection["relationships"]["evidence_refs"][0]["kind"] == "message"
    assert projection["relationships"]["evidence_refs"][0]["value"] == "msg-1"
    assert projection["relationships"]["policy_version"] == "memory-promotion-1"


def test_eligible_automatic_evaluation_is_quarantined_until_owner_approval(harness):
    service, state, memory = harness
    candidate = make_candidate()

    first = service.evaluate(candidate)
    second = service.evaluate(candidate)

    assert first["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    assert first["reason_codes"] == ["automatic_activation_quarantined"]
    assert second["status"] == first["status"]
    assert "automatic_activation_quarantined" in second["reason_codes"]
    assert second["decision_id"] == first["decision_id"]
    assert memory.fetch_memory(candidate.memory_id) is None
    assert service.evidence_store.memory_links(candidate.memory_id) == []
    event_types = {row["event_type"] for row in state.recent_events(100)}
    assert "memory_promotion_preparing" not in event_types
    assert "memory_projection_activated" not in event_types
    assert "memory_projection_rolled_back" not in event_types
    assert "memory_projection_repair_required" not in event_types
    assert event_types <= {"memory_candidate_recorded", "memory_promotion_decision"}

    approved = service.approve(
        first["candidate_id"],
        expected_content_hash=first["content_hash"],
        owner_confirmed=True,
    )
    assert approved["status"] == PromotionStatus.ACTIVE.value
    assert memory.fetch_memory(candidate.memory_id)["memory_tier"] == "derived"


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
        service.approve(pending["candidate_id"], expected_content_hash=pending["content_hash"], owner_confirmed=False)
    with pytest.raises(ValueError, match="hash"):
        service.approve(pending["candidate_id"], expected_content_hash="stale", owner_confirmed=True)
    approved = service.approve(pending["candidate_id"], expected_content_hash=pending["content_hash"], owner_confirmed=True)
    assert approved["status"] == PromotionStatus.ACTIVE.value
    assert memory.fetch_memory(candidate.memory_id)["memory_tier"] == "derived"


def test_rejection_requires_confirmation_and_retains_evidence(harness):
    service, state, memory = harness
    pending = service.evaluate(make_candidate(authority="ai_inference", source_kind="summary"))
    rejected = service.reject(
        pending["candidate_id"], expected_content_hash=pending["content_hash"], owner_confirmed=True, reason="not stable"
    )
    assert rejected["status"] == PromotionStatus.REJECTED.value
    assert memory.fetch_memory("candidate-1") is None
    assert any(e["event_type"] == "memory_promotion_owner_rejected" for e in state.recent_events(100))
    assert service.candidate("candidate-1")["content"] == "The owner prefers short answers."


def test_projection_failure_is_truthful_pending_error_and_keeps_candidate(tmp_path: Path):
    state = StateDatabase(tmp_path / "state.db")
    state.append_event("evidence_recorded", "message", "msg-1", {})
    memory = MemoryDatabase(tmp_path / "memory.db")
    source = SourceReadModel(memory)
    source_row = source.upsert_source({"source_type": "chat", "external_id": "chat-1"})
    conversation = source.upsert_conversation({"source_id": source_row["source_id"], "external_id": "conv-1"})
    source.upsert_message({"message_id": "msg-1", "source_id": source_row["source_id"], "conversation_id": conversation["conversation_id"], "external_id": "msg-ext-1", "role": "user", "sequence": 1, "content": "source evidence"})

    def broken(_entry):
        raise OSError("index unavailable")

    service = AutoMemoryPromotionService(state_db=state, projection_writer=broken, evidence_store=source, memory_db=memory)
    pending = service.evaluate(make_candidate())
    result = service.approve(
        pending["candidate_id"],
        expected_content_hash=pending["content_hash"],
        owner_confirmed=True,
    )
    assert result["status"] == PromotionStatus.ERROR.value
    assert result["reason_codes"] == ["projection_persist_failed"]
    assert result["mutation_performed"] is False
    assert service.candidate("candidate-1") is not None


def test_restricted_and_security_categories_never_auto_activate(harness):
    service, _state, _memory = harness
    for flag in ("secret", "permission", "legal", "financial", "security", "irreversible"):
        result = service.evaluate(make_candidate(risk_flags=(flag,)))
        assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value


@pytest.mark.parametrize("memory_type", [
    "identity", "credentials", "secrets", "permission", "medical", "legal",
    "financial", "security", "destructive", "irreversible", "privacy", "restricted", "core",
])
def test_high_risk_memory_type_requires_owner(harness, memory_type):
    service, _state, _memory = harness
    result = service.evaluate(make_candidate(memory_type=memory_type))
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value


@pytest.mark.parametrize("confidence", [True, False, "0.90", float("nan"), float("inf"), float("-inf")])
def test_confidence_is_finite_numeric_and_fail_closed(harness, confidence):
    service, _state, _memory = harness
    result = service.evaluate(make_candidate(confidence=confidence))
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    assert "confidence_below_threshold" in result["reason_codes"]


def test_unverifiable_evidence_reference_stays_pending(harness):
    service, _state, _memory = harness
    result = service.evaluate(make_candidate(source_refs=("missing-evidence-id",)))
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    assert "evidence_reference_unverifiable" in result["reason_codes"]


def test_candidate_owned_evidence_reference_cannot_self_validate(harness):
    service, state, _memory = harness
    state.append_event("evidence_recorded", "message", "candidate-1", {"content": "candidate-owned"})
    result = service.evaluate(make_candidate(source_refs=("candidate-1",)))
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    assert "evidence_reference_unverifiable" in result["reason_codes"]


def test_supplied_mismatched_content_hash_is_rejected(harness):
    service, _state, _memory = harness
    with pytest.raises(ValueError, match="content hash"):
        service.evaluate(make_candidate(content_hash="forged"))


def test_failed_owner_approval_does_not_bypass_quarantine_on_retry(tmp_path: Path):
    state = StateDatabase(tmp_path / "state.db")
    state.append_event("evidence_recorded", "message", "msg-1", {})
    memory = MemoryDatabase(tmp_path / "memory.db")
    source = SourceReadModel(memory)
    source_row = source.upsert_source({"source_type": "chat", "external_id": "chat-1"})
    conversation = source.upsert_conversation({"source_id": source_row["source_id"], "external_id": "conv-1"})
    source.upsert_message({"message_id": "msg-1", "source_id": source_row["source_id"], "conversation_id": conversation["conversation_id"], "external_id": "msg-ext-1", "role": "user", "sequence": 1, "content": "source evidence"})
    calls = {"count": 0}

    def flaky(**_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("index unavailable")
        return {"memory_id": "candidate-1"}

    service = AutoMemoryPromotionService(state_db=state, projection_writer=flaky, evidence_store=source, memory_db=memory)
    candidate = make_candidate()
    pending = service.evaluate(candidate)
    first = service.approve(
        pending["candidate_id"],
        expected_content_hash=pending["content_hash"],
        owner_confirmed=True,
    )
    second = service.evaluate(candidate)
    third = service.evaluate(candidate)
    assert first["status"] == PromotionStatus.ERROR.value
    assert second["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    assert third["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    assert calls["count"] == 1
    events = state.recent_events(100)
    assert len([e for e in events if e["event_type"] == "memory_promotion_decision"]) == 1
    assert len([e for e in events if e["event_type"] == "memory_promotion_projection_error"]) == 1


def test_derived_projection_rebuild_replays_state_events(harness):
    service, _state, memory = harness
    pending = service.evaluate(make_candidate())
    first = service.approve(
        pending["candidate_id"],
        expected_content_hash=pending["content_hash"],
        owner_confirmed=True,
    )
    memory.rebuild_from_index([], Path("."))
    assert memory.fetch_memory(first["candidate_id"]) is None
    rebuilt = service.rebuild_derived_projections()
    assert rebuilt["rebuilt"] == 1
    assert memory.fetch_memory(first["candidate_id"])["memory_tier"] == "derived"
    assert service.rebuild_derived_projections()["rebuilt"] == 0
