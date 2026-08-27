"""Preserved Task 4R1 round-5 rejection facts.

Round-5 automatic-activation behavior was rejected and is intentionally not a
current PASS contract. These tests keep that history visible while the reset
runner remains quarantined before Task 4R2.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.automatic_memory.quality_gate import run_quality_gate, temporary_acceptance_roots
from src.automatic_memory.evidence_identity import build_identity_registry, select_context_evidence
from src.automatic_memory.quality_evidence import EvidenceState, ImportedEvidenceAudit

CORPUS = Path(__file__).parent / "fixtures" / "automatic_memory_corpus.jsonl"
QUESTIONS = Path(__file__).parent / "fixtures" / "automatic_memory_questions.jsonl"


def test_round5_rejected_activation_is_not_current_truth(tmp_path: Path) -> None:
    with temporary_acceptance_roots(base_directory=tmp_path) as roots:
        envelope = run_quality_gate(CORPUS, QUESTIONS, output_path=roots.output_root / "quality.json", acceptance_roots=roots)
        assert envelope.functional_status == envelope.phase_status == "NOT_EVALUATED"
        assert envelope.evaluation_report is None


def test_round5_report_keeps_unmeasured_4r2_fields_explicit(tmp_path: Path) -> None:
    with temporary_acceptance_roots(base_directory=tmp_path) as roots:
        run_quality_gate(CORPUS, QUESTIONS, output_path=roots.output_root / "quality.json", acceptance_roots=roots)
        payload = json.loads((roots.output_root / "quality.json").read_text(encoding="utf-8"))
        assert payload["mcp_parity"]["status"] == "NOT_MEASURED"
        assert payload["semantic_degradation"]["status"] == "NOT_MEASURED"
        assert payload["phase_status"] == "NOT_EVALUATED"


def test_round5_expectation_blind_selection_and_unknown_identity_fail_closed() -> None:
    identity = build_identity_registry(
        corpus=(),
        persisted_messages=[],
        promotion_bindings={},
        message_links=[],
    )
    pack = {"sections": [{"kind": "retrieved_memory", "memory_id": "unknown"}]}
    try:
        select_context_evidence(pack, identity)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown selected identity must fail closed")


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
        assert payload["production_pollution"] is None
        assert payload["quality_evidence_readiness"]["production_sentinel"] == "not_measured"


def test_round5_readiness_states_are_explicit_enum_values() -> None:
    assert EvidenceState.NOT_MEASURED.value == "not_measured"
