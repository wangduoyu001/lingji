"""Historical Task 4R1 takeover rejection coverage.

Old fixture-driven takeover and automatic-activation assertions remain
rejection coverage, not current product behavior.
"""
from __future__ import annotations

import pytest

from src.automatic_memory.quality_gate import QualityScaleBlockedError, ensure_4r2_ready_for_scale
from src.automatic_memory.quality_evidence import EvidenceState, QualityEvidenceReadiness
from src.automatic_memory.quality_gate import validate_selected_evidence


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
    import src.automatic_memory.quality_gate as quality_gate

    assert not hasattr(quality_gate, "build_prequery_identity_map")
    assert not hasattr(quality_gate, "select_gateway_evidence")


def test_takeover_adapter_projection_audit_rejects_mismatched_identity() -> None:
    from src.automatic_memory.quality_evidence import ExpectedImportedRow, ImportedEvidenceAudit

    class ReadModel:
        def list_ingestion_messages(self, *_args, **_kwargs):
            return {"items": [{"source_external_id": "wrong", "conversation_external_id": "wrong", "message_external_id": "m1", "source_id": "s", "conversation_id": "c", "message_id": "m", "role": "assistant", "sequence": 9, "occurred_at": "bad", "content_hash": "bad"}], "pagination": {"total": 1, "offset": 0, "limit": 200, "has_more": False}}

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
    assert _reset_readiness().functional_status == "NOT_EVALUATED"


def test_takeover_unreadable_or_missing_sentinel_is_not_pollution_zero() -> None:
    assert _reset_readiness().production_sentinel is EvidenceState.NOT_MEASURED
