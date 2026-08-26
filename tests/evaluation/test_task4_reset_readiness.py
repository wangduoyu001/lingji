from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.automatic_memory.evaluation import AutomaticMemoryAcceptanceGate, EvaluationReport
from src.automatic_memory.quality_evidence import (
    EvidenceState,
    ProtectedTreeSentinel,
    QualityEvidenceReadiness,
    QualityPublicationError,
    finalize_quality_envelope,
    write_quality_json_atomic,
)


def readiness(**changes: EvidenceState) -> QualityEvidenceReadiness:
    values = {field: EvidenceState.READY for field in (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
        "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
    )}
    values.update(changes)
    return QualityEvidenceReadiness(**values)


def report() -> EvaluationReport:
    return EvaluationReport(
        answered_questions=100, imported_messages=100, expected_messages=100,
        ordered_role_matches=100, expected_ordered_roles=100,
        valid_fact_hits=90, valid_fact_total=100, citation_hits=95, citation_total=100,
        automatic_activation_correct=95, automatic_activation_total=100,
        valid_fact_recall=90.0, citation_accuracy=95.0,
        automatic_activation_accuracy=95.0, protected_false_promotions=0,
        stale_current_leaks=0, duplicate_records=0, baseline_context_chars=1000,
        rendered_context_chars=100, context_reduction=90.0, mcp_successes=95,
        mcp_attempts=100, mcp_success_rate=95.0, production_pollution=0,
        owner_review_success=100.0, reboot_recovery=100.0, blocked_reasons=(),
    )


class SpyGate:
    def __init__(self, verdict: str = "PASS") -> None:
        self.calls: list[EvaluationReport] = []
        self.verdict = verdict

    def evaluate(self, value: EvaluationReport) -> str:
        self.calls.append(value)
        return self.verdict


@pytest.mark.parametrize("field", [
    "import_audit", "promotion_provenance", "gateway_selection", "mcp_parity",
    "qdrant_degradation", "corruption_isolation", "context_baseline",
])
def test_unmeasured_functional_evidence_never_reaches_gate(field: str) -> None:
    gate = SpyGate()
    result = finalize_quality_envelope(
        readiness=readiness(**{field: EvidenceState.NOT_MEASURED}),
        production_pollution=None,
        evaluation_report=None,
        acceptance_gate=gate,
    )
    assert not gate.calls
    assert result.evaluation_report is None
    assert result.functional_status == result.phase_status == result.windows_status == "NOT_EVALUATED"


def test_complete_ready_evidence_calls_frozen_gate_twice_and_blocks_unmeasured_release() -> None:
    gate = SpyGate()
    result = finalize_quality_envelope(
        readiness=readiness(scale=EvidenceState.NOT_MEASURED, owner_review=EvidenceState.NOT_MEASURED,
                            reboot_recovery=EvidenceState.NOT_MEASURED, mac_release=EvidenceState.NOT_MEASURED,
                            windows_release=EvidenceState.NOT_MEASURED),
        production_pollution=0,
        evaluation_report=report(),
        acceptance_gate=gate,
    )
    assert len(gate.calls) == 2
    assert gate.calls[0].owner_review_success == 100.0
    assert gate.calls[0].reboot_recovery == 100.0
    assert gate.calls[0].blocked_reasons == ()
    assert result.functional_status == "PASS"
    assert result.phase_status == "BLOCKED"
    assert "SCALE_NOT_MEASURED" in result.blocked_reasons


def test_failed_functional_evidence_with_frozen_pass_is_contradictory() -> None:
    gate = SpyGate("PASS")
    result = finalize_quality_envelope(
        readiness=readiness(import_audit=EvidenceState.FAILED), production_pollution=0,
        evaluation_report=report(), acceptance_gate=gate,
    )
    assert result.evaluation_report is None
    assert result.functional_status == "NOT_EVALUATED"


def test_sentinel_requires_strict_count_consistency() -> None:
    gate = SpyGate()
    result = finalize_quality_envelope(
        readiness=readiness(production_sentinel=EvidenceState.READY), production_pollution=1,
        evaluation_report=report(), acceptance_gate=gate,
    )
    assert not gate.calls
    assert result.production_pollution is None


def test_protected_tree_contract_and_nested_mutation(tmp_path: Path) -> None:
    root = tmp_path / "protected"
    root.mkdir()
    (root / "nested").mkdir()
    (root / "nested" / "entry.txt").write_text("before", encoding="utf-8")
    before = ProtectedTreeSentinel.capture((root,))
    (root / "nested" / "entry.txt").write_text("after!", encoding="utf-8")
    after = ProtectedTreeSentinel.capture((root,))
    changes = before.diff(after)
    assert len(changes) == 1
    assert changes[0].path != str(root)


def test_atomic_writer_requires_existing_parent_and_protects_roots(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    destination = output_dir / "report.json"
    write_quality_json_atomic(destination, {"answer": 1}, protected_roots=())
    assert json.loads(destination.read_text(encoding="utf-8")) == {"answer": 1}
    with pytest.raises(QualityPublicationError):
        write_quality_json_atomic(tmp_path / "missing" / "report.json", {}, protected_roots=())
    protected = tmp_path / "protected"
    protected.mkdir()
    with pytest.raises(QualityPublicationError):
        write_quality_json_atomic(protected / "report.json", {}, protected_roots=(protected,))
