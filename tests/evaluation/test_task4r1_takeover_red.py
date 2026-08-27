"""Historical Task 4R1 takeover rejection coverage.

Old fixture-driven takeover and automatic-activation assertions remain
rejection coverage, not current product behavior.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.auto_review.models import ReviewCandidate
from src.auto_review.promotion import AutoMemoryPromotionService, PromotionStatus
from src.automatic_memory import quality_evidence, quality_gate
from src.automatic_memory.quality_gate import QualityScaleBlockedError, ensure_4r2_ready_for_scale
from src.automatic_memory.quality_evidence import EvidenceState, QualityEvidenceReadiness
from src.automatic_memory.quality_evidence import ExpectedImportedRow, ImportedEvidenceAudit, ProtectedTreeSentinel
from src.automatic_memory.quality_gate import validate_selected_evidence
from src.retrieval.memory_db import MemoryDatabase
from src.sources.read_model import SourceReadModel
from src.storage.state_db import StateDatabase


def _reset_readiness() -> QualityEvidenceReadiness:
    fields = (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
        "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
    )
    return QualityEvidenceReadiness(**{field: EvidenceState.NOT_MEASURED for field in fields})


def test_round5_takeover_cannot_authorize_scale() -> None:
    try:
        ensure_4r2_ready_for_scale(_reset_readiness())
    except QualityScaleBlockedError as error:
        assert str(error) == "BLOCKED_4R2_REQUIRED"
    else:
        raise AssertionError("scale must remain blocked until 4R2")


def test_rejected_runner_apis_are_not_reintroduced() -> None:
    assert not hasattr(quality_gate, "build_prequery_identity_map")
    assert not hasattr(quality_gate, "select_gateway_evidence")


def test_takeover_adapter_projection_audit_rejects_mismatched_identity() -> None:
    class ReadModel:
        def list_ingestion_messages(self, *_args, **_kwargs):
            return {"items": [{
                "source_external_id": "wrong", "conversation_external_id": "wrong", "message_external_id": "m1",
                "source_id": "s", "conversation_id": "c", "message_id": "m", "role": "assistant", "sequence": 9,
                "occurred_at": "bad", "content_hash": "bad",
            }], "pagination": {"total": 1, "offset": 0, "limit": 200, "has_more": False}}

    expected = (ExpectedImportedRow("source", "conversation", "m1", 0, 0, "user", "h1", "2026-01-01T00:00:00+00:00"),)
    audit = ImportedEvidenceAudit.from_read_model(ReadModel(), ingestion_batch_id="batch", expected_rows=expected)
    assert audit.ready is False


def test_takeover_selector_rejects_unknown_or_duplicate_evidence() -> None:
    with pytest.raises(ValueError):
        validate_selected_evidence(recalled=("unknown",), citations=(), expected=(), forbidden=(), expected_citations=())
    with pytest.raises(ValueError):
        validate_selected_evidence(recalled=("fact", "fact"), citations=(), expected=("fact",), forbidden=(), expected_citations=())


def test_takeover_ambiguous_or_unresolved_provenance_stays_owner_review(tmp_path) -> None:
    from src.auto_review.models import ReviewCandidate
    from src.auto_review.promotion import AutoMemoryPromotionService, PromotionStatus
    from src.retrieval.memory_db import MemoryDatabase
    from src.sources.read_model import SourceReadModel
    from src.storage.state_db import StateDatabase

    memory = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(memory)
    service = AutoMemoryPromotionService(state_db=StateDatabase(tmp_path / "state.db"), memory_db=memory, evidence_store=read_model)
    candidate = ReviewCandidate(memory_id="rejected", title="t", content="c", memory_type="preference", source_refs=("missing",), confidence=.99, authority="direct_user", source_kind="user_chat", extractor_version="test")
    result = service.evaluate(candidate)
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value


def test_takeover_malformed_gateway_evidence_fails_closed() -> None:
    with pytest.raises(ValueError):
        validate_selected_evidence(recalled=("fact",), citations=("citation",), expected=(), forbidden=(), expected_citations=())


def test_takeover_invalid_readiness_cannot_be_evaluated() -> None:
    readiness = quality_evidence.QualityEvidenceReadiness(
        import_audit=EvidenceState.READY, promotion_provenance=EvidenceState.READY,
        gateway_selection=EvidenceState.READY, production_sentinel=EvidenceState.READY,
        mcp_parity=EvidenceState.NOT_MEASURED, qdrant_degradation=EvidenceState.NOT_MEASURED,
        corruption_isolation=EvidenceState.NOT_MEASURED, context_baseline=EvidenceState.NOT_MEASURED,
        scale=EvidenceState.NOT_MEASURED, owner_review=EvidenceState.NOT_MEASURED,
        reboot_recovery=EvidenceState.NOT_MEASURED, mac_release=EvidenceState.NOT_MEASURED,
        windows_release=EvidenceState.NOT_MEASURED,
    )
    assert readiness.functional_status == "NOT_EVALUATED"
    assert readiness.should_run_acceptance_gate is False
    assert not hasattr(readiness, "evaluate")


def test_takeover_unreadable_or_missing_sentinel_is_not_pollution_zero() -> None:
    assert _reset_readiness().production_sentinel is EvidenceState.NOT_MEASURED


def _source_model(tmp_path: Path):
    memory = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(memory)
    source = read_model.stable_id("source", "source")
    conversation = read_model.stable_id("conversation", source, "conversation")
    read_model.upsert_bundle({
        "source": {"source_id": source, "source_type": "generic", "display_name": "S", "external_id": "source-ext"},
        "conversations": [{"conversation_id": conversation, "external_id": "conversation-ext", "title": "C", "messages": [
            {"external_id": "message-ext", "role": "user", "sequence": 0, "content": "owner evidence"},
        ]}],
    })
    return memory, read_model


def _candidate(refs: tuple[str, ...], memory_id: str = "candidate") -> ReviewCandidate:
    title, content, structured = "Remember", "owner evidence", {"x": 1}
    digest = hashlib.sha256(json.dumps(
        {"title": title, "content": content, "structured": structured}, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    return ReviewCandidate(
        memory_id=memory_id, title=title, content=content, memory_type="preference", content_hash=digest,
        source_refs=refs, confidence=.99, authority="direct_user", source_kind="user_chat",
        extractor_version="round5", structured_content=structured,
    )


def test_takeover_promotion_resolves_generic_refs_and_rejects_ambiguous_or_unresolved(tmp_path: Path) -> None:
    memory, read_model = _source_model(tmp_path)
    service = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "state.db"), memory_db=memory, evidence_store=read_model,
    )
    active_candidate = _candidate(("message-ext",))
    active = service.evaluate(active_candidate)
    assert active["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    active = service.approve(
        "candidate", expected_content_hash=active_candidate.content_hash, owner_confirmed=True,
    )
    assert active["status"] == PromotionStatus.ACTIVE.value
    assert read_model.memory_links(active["candidate_id"])
    unresolved = service.evaluate(_candidate(("missing-ref",), "candidate-2"))
    assert unresolved["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value


def test_takeover_promotion_fails_closed_for_ambiguous_conversation_ref(tmp_path: Path) -> None:
    memory = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(memory)
    source = read_model.stable_id("source", "s")
    conversation = read_model.stable_id("conversation", source, "c")
    read_model.upsert_bundle({
        "source": {"source_id": source, "source_type": "generic", "display_name": "S"},
        "conversations": [{"conversation_id": conversation, "external_id": "ambiguous-conversation", "title": "C", "messages": [
            {"external_id": "m1", "role": "user", "sequence": 0, "content": "one"},
            {"external_id": "m2", "role": "user", "sequence": 1, "content": "two"},
        ]}],
    })
    service = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "state.db"), memory_db=memory, evidence_store=read_model,
    )
    result = service.evaluate(_candidate(("ambiguous-conversation",)))
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value


def test_takeover_projection_failure_rolls_back_partial_links(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    memory, read_model = _source_model(tmp_path)
    source = read_model.stable_id("source", "source")
    conversation = read_model.stable_id("conversation", source, "conversation")
    read_model.upsert_bundle({
        "source": {"source_id": source, "source_type": "generic", "display_name": "S", "external_id": "source-ext"},
        "conversations": [{"conversation_id": conversation, "external_id": "conversation-ext", "title": "C", "messages": [
            {"external_id": "message-ext", "role": "user", "sequence": 0, "content": "owner evidence"},
            {"external_id": "message-ext-2", "role": "user", "sequence": 1, "content": "second evidence"},
        ]}],
    })
    original = read_model.link_message_memory_batch

    def fail_after_first(messages, memory_id, **kwargs):
        refs = tuple(messages)
        original(refs[:1], memory_id, **kwargs)
        raise OSError("link failed")

    monkeypatch.setattr(read_model, "link_message_memory_batch", fail_after_first)
    candidate = _candidate(("message-ext", "message-ext-2"))
    service = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "state.db"), memory_db=memory, evidence_store=read_model,
    )
    result = service.evaluate(candidate)
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    result = service.approve(
        candidate.memory_id, expected_content_hash=candidate.content_hash, owner_confirmed=True,
    )
    assert result["status"] == PromotionStatus.ERROR.value
    assert read_model.memory_links(candidate.memory_id) == []
    assert memory.fetch_memory(candidate.memory_id) is None


def test_takeover_sentinel_fails_closed_on_unreadable_descendant(tmp_path: Path) -> None:
    root = tmp_path / "protected"
    root.mkdir()
    child = root / "data"
    child.write_text("x", encoding="utf-8")
    child.chmod(0)
    try:
        with pytest.raises(ValueError):
            ProtectedTreeSentinel.capture((root,))
    finally:
        child.chmod(0o600)
