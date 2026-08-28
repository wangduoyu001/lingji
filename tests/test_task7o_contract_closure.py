from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.automatic_memory.quality_evidence import EvidenceState
from src.automatic_memory.scale_benchmark import readiness_from_envelope


def test_canonical_functional_evidence_rejects_real_failed_runner_payload(tmp_path: Path):
    from src.automatic_memory.quality_evidence import CanonicalFunctionalEvidence

    payload = {"functional_status": "FAIL", "phase_status": "FAIL"}
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(payload)


def test_scale_loader_rejects_real_failed_runner_artifact(tmp_path: Path):
    from src.automatic_memory import quality_gate as runner

    with runner.temporary_acceptance_roots(base_directory=tmp_path) as roots:
        runner.run_quality_gate(
            Path("tests/evaluation/fixtures/automatic_memory_corpus.jsonl"),
            Path("tests/evaluation/fixtures/automatic_memory_questions.jsonl"),
            output_path=roots.output_root / "quality.json", acceptance_roots=roots,
        )
        with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
            readiness_from_envelope(roots.output_root / "quality.json")


def test_canonical_functional_evidence_round_trips_complete_artifact():
    from src.automatic_memory.quality_evidence import CanonicalFunctionalEvidence

    artifact = CanonicalFunctionalEvidence.complete_for_test()
    restored = CanonicalFunctionalEvidence.from_mapping(artifact.to_mapping())
    assert restored == artifact


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(extra_field=1),
    lambda p: p["mcp_parity"].update(attempts=True),
    lambda p: p["mcp_parity"].update(strict_rate=float("nan")),
])
def test_canonical_artifact_rejects_unknown_bool_and_nan(mutation):
    from src.automatic_memory.quality_evidence import CanonicalFunctionalEvidence

    payload = CanonicalFunctionalEvidence.complete_for_test().to_mapping()
    mutation(payload)
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(payload)


def test_quarantined_activation_is_not_measured_as_zero_of_ninety_three():
    from src.automatic_memory.quality_promotion import activation_measurement

    result = activation_measurement(
        [{"category": "low-risk-user", "expected_status": "pending_owner_review", "status": "pending_owner_review"}]
    )
    assert result == {"status": "not_applicable", "correct": None, "total": None, "accuracy": None}


def test_promotion_audit_finds_orphan_link_and_rejected_audit():
    from src.automatic_memory.quality_promotion import validate_promotion_measurement

    with pytest.raises(ValueError, match="missing|extra|orphan|non-active"):
        validate_promotion_measurement({
            "outcomes": [
                {"category": "low-risk-user", "status": "pending_owner_review", "memory_id": "m-pending"},
                {"category": "low-risk-user", "status": "rejected", "memory_id": "m-rejected"},
            ],
            "projection_ids": [],
            "audit_ids": ["m-pending"],
            "memory_link_keys": [("msg", "m-pending")],
        })


def test_runner_uses_nullable_mcp_and_baseline_contract(tmp_path: Path):
    from src.automatic_memory import quality_gate as runner

    with runner.temporary_acceptance_roots(base_directory=tmp_path) as roots:
        envelope = runner.run_quality_gate(
            Path("tests/evaluation/fixtures/automatic_memory_corpus.jsonl"),
            Path("tests/evaluation/fixtures/automatic_memory_questions.jsonl"),
            output_path=roots.output_root / "quality.json",
            acceptance_roots=roots,
        )
    assert envelope.readiness.mcp_parity is EvidenceState.FAILED
    assert envelope.readiness.context_baseline is EvidenceState.NOT_MEASURED
    assert envelope.evaluation_report is None
