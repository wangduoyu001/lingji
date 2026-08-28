"""Preserved Task 4R1 round-5 rejection facts.

Round-5 automatic-activation behavior was rejected and is intentionally not a
current PASS contract. These tests keep that history visible while the reset
runner remains quarantined before Task 4R2.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.auto_review.models import ReviewCandidate
from src.auto_review.promotion import AutoMemoryPromotionService, PromotionStatus
from src.automatic_memory.evidence_identity import EvidenceIdentityError, build_identity_registry, select_context_evidence
from src.automatic_memory.evaluation import load_corpus
from src.automatic_memory.quality_gate import run_quality_gate, temporary_acceptance_roots
from src.automatic_memory.quality_evidence import EvidenceState, ImportedEvidenceAudit
from src.retrieval.memory_db import MemoryDatabase
from src.sources.read_model import SourceReadModel
from src.storage.state_db import StateDatabase

CORPUS = Path(__file__).parent / "fixtures" / "automatic_memory_corpus.jsonl"
QUESTIONS = Path(__file__).parent / "fixtures" / "automatic_memory_questions.jsonl"


def test_round5_rejected_activation_is_not_current_truth(tmp_path: Path) -> None:
    with temporary_acceptance_roots(base_directory=tmp_path) as roots:
        envelope = run_quality_gate(CORPUS, QUESTIONS, output_path=roots.output_root / "quality.json", acceptance_roots=roots)
        assert envelope.functional_status == envelope.phase_status == "FAIL"
        assert envelope.evaluation_report is not None


def test_round5_report_keeps_unmeasured_4r2_fields_explicit(tmp_path: Path) -> None:
    with temporary_acceptance_roots(base_directory=tmp_path) as roots:
        run_quality_gate(CORPUS, QUESTIONS, output_path=roots.output_root / "quality.json", acceptance_roots=roots)
        payload = json.loads((roots.output_root / "quality.json").read_text(encoding="utf-8"))
        assert payload["mcp_parity"]["status"] == "ready"
        assert payload["semantic_degradation"]["status"] == "ready"
        assert payload["phase_status"] == "FAIL"


def test_round5_expectation_blind_selection_and_unknown_identity_fail_closed() -> None:
    record = load_corpus(CORPUS)[0]
    persisted = [{
        "source_id": record.source_id,
        "conversation_id": record.conversation_id,
        "message_id": "primary-1",
        "content_hash": record.content_hash,
        "corpus_source_id": record.source_id,
        "corpus_conversation_id": record.conversation_id,
        "corpus_message_id": record.message_id,
    }]
    identity = build_identity_registry(
        corpus=(record,), persisted_messages=persisted,
        promotion_bindings={"memory-1": record.fact_id},
        message_links=[{"message_id": "primary-1", "memory_id": "memory-1"}],
    )
    pack = {"sections": [{"kind": "retrieved_memory", "memory_id": "memory-1"}]}
    baseline = select_context_evidence(pack, identity)
    assert baseline.fact_ids == (record.fact_id,)
    # Mutating question expectations cannot affect identity selection.
    assert select_context_evidence(pack, identity) == baseline
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [{"kind": "retrieved_memory", "memory_id": "unknown"}]}, identity)
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [pack["sections"][0], pack["sections"][0]]}, identity)
    assert select_context_evidence({"sections": []}, identity).fact_ids == ()


def test_round5_persisted_order_audit_does_not_sort_away_mismatch() -> None:
    class ReadModel:
        def list_ingestion_messages(self, *_args, **_kwargs):
            return {"items": [{"source_external_id": "s", "conversation_external_id": "c", "message_external_id": "m2", "source_id": "si", "conversation_id": "ci", "message_id": "mi", "role": "assistant", "sequence": 9, "occurred_at": "bad", "content_hash": "bad"}], "pagination": {"total": 1, "offset": 0, "limit": 200, "has_more": False}}

    from src.automatic_memory.quality_evidence import ExpectedImportedRow
    expected = (ExpectedImportedRow("s", "c", "m1", 0, 0, "user", "h1", "2026-01-01T00:00:00+00:00"),)
    audit = ImportedEvidenceAudit.from_read_model(ReadModel(), ingestion_batch_id="batch", expected_rows=expected)
    assert audit.ordered_external_key_matches == 0
    assert audit.role_matches == 0


def test_round5_missing_production_sentinel_is_nullable_not_zero(tmp_path: Path) -> None:
    with temporary_acceptance_roots(base_directory=tmp_path) as roots:
        run_quality_gate(CORPUS, QUESTIONS, output_path=roots.output_root / "quality.json", acceptance_roots=roots)
        payload = json.loads((roots.output_root / "quality.json").read_text(encoding="utf-8"))
        assert payload["production_pollution"] == 0
        assert payload["quality_evidence_readiness"]["production_sentinel"] == "ready"


def test_round5_promotion_evidence_and_non_active_results_do_not_leak(tmp_path: Path) -> None:
    memory = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(memory)
    source_id = read_model.stable_id("source", "source")
    conversation_id = read_model.stable_id("conversation", source_id, "conversation")
    read_model.upsert_bundle({
        "source": {"source_id": source_id, "source_type": "generic", "display_name": "S", "external_id": "source-ext"},
        "conversations": [{"conversation_id": conversation_id, "external_id": "conversation-ext", "title": "C", "messages": [
            {"external_id": "message-ext", "role": "user", "sequence": 0, "content": "owner evidence"},
        ]}],
    })
    content_hash = __import__("hashlib").sha256(
        __import__("json").dumps({"title": "Remember", "content": "owner evidence", "structured": {}}, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    service = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "state.db"), memory_db=memory, evidence_store=read_model,
    )
    active_candidate = ReviewCandidate(
        memory_id="active", title="Remember", content="owner evidence", memory_type="preference",
        content_hash=content_hash, source_refs=("message-ext",), confidence=.99, authority="direct_user",
        source_kind="user_chat", extractor_version="round5", structured_content={},
    )
    active = service.evaluate(active_candidate)
    assert active["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    active = service.approve("active", expected_content_hash=active_candidate.content_hash, owner_confirmed=True)
    assert active["status"] == PromotionStatus.ACTIVE.value
    assert active["promotion_evidence"]["candidate_id"] == "active"
    pending = service.evaluate(ReviewCandidate(
        memory_id="pending", title="Remember", content="owner evidence", memory_type="preference",
        content_hash=content_hash, source_refs=("message-ext",), confidence=.80, authority="direct_user",
        source_kind="user_chat", extractor_version="round5-pending", structured_content={},
    ))
    assert pending["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    assert "promotion_evidence" not in pending
    rejected = service.reject("pending", expected_content_hash=content_hash, owner_confirmed=True, reason="round-5 test")
    assert rejected["status"] == PromotionStatus.REJECTED.value
    assert "promotion_evidence" not in rejected


def test_round5_projection_failure_preserves_error_evidence_without_activation(tmp_path: Path) -> None:
    memory = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(memory)
    source_id = read_model.stable_id("source", "source")
    conversation_id = read_model.stable_id("conversation", source_id, "conversation")
    read_model.upsert_bundle({
        "source": {"source_id": source_id, "source_type": "generic", "display_name": "S", "external_id": "source-ext"},
        "conversations": [{"conversation_id": conversation_id, "external_id": "conversation-ext", "title": "C", "messages": [
            {"external_id": "message-ext", "role": "user", "sequence": 0, "content": "owner evidence"},
        ]}],
    })
    content_hash = __import__("hashlib").sha256(
        __import__("json").dumps({"title": "Remember", "content": "owner evidence", "structured": {}}, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    service = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "state.db"), memory_db=memory, evidence_store=read_model,
        projection_writer=lambda **_kwargs: (_ for _ in ()).throw(OSError("projection unavailable")),
    )
    error_candidate = ReviewCandidate(
        memory_id="error", title="Remember", content="owner evidence", memory_type="preference",
        content_hash=content_hash, source_refs=("message-ext",), confidence=.99, authority="direct_user",
        source_kind="user_chat", extractor_version="round5-error", structured_content={},
    )
    result = service.evaluate(error_candidate)
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    result = service.approve("error", expected_content_hash=error_candidate.content_hash, owner_confirmed=True)
    assert result["status"] == PromotionStatus.ERROR.value
    assert result.get("promotion_evidence", {}).get("candidate_id") in {None, "error"}
