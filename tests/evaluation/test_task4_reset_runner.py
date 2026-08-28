"""Task 4R reset Task 6 runner contracts.

These tests deliberately exercise the public reset runner boundary rather than
its implementation details.  They are the first RED tests for the thin-runner
reset and remain expectation-blind to the frozen evaluator fixtures.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

import src.automatic_memory.quality_gate as runner
from src.automatic_memory.evaluation import EvaluationReport
from src.automatic_memory.quality_evidence import EvidenceState, QualityEvidenceReadiness


def _readiness(**changes: EvidenceState) -> QualityEvidenceReadiness:
    values = {field: EvidenceState.READY for field in (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
        "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
    )}
    values.update(changes)
    return QualityEvidenceReadiness(**values)


def _report() -> EvaluationReport:
    return EvaluationReport(
        answered_questions=100,
        imported_messages=100,
        expected_messages=100,
        ordered_role_matches=100,
        expected_ordered_roles=100,
        valid_fact_hits=90,
        valid_fact_total=100,
        citation_hits=95,
        citation_total=100,
        automatic_activation_correct=95,
        automatic_activation_total=100,
        valid_fact_recall=90.0,
        citation_accuracy=95.0,
        automatic_activation_accuracy=95.0,
        protected_false_promotions=0,
        stale_current_leaks=0,
        duplicate_records=0,
        baseline_context_chars=1000,
        rendered_context_chars=100,
        context_reduction=90.0,
        mcp_successes=95,
        mcp_attempts=100,
        mcp_success_rate=95.0,
        production_pollution=0,
        owner_review_success=None,
        reboot_recovery=None,
        blocked_reasons=(),
    )


class SpyGate:
    def __init__(self, verdict: str = "PASS") -> None:
        self.verdict = verdict
        self.calls: list[EvaluationReport] = []

    def evaluate(self, report: EvaluationReport) -> str:
        self.calls.append(report)
        return self.verdict


def test_unavailable_evidence_never_enters_evaluation_report() -> None:
    gate = SpyGate()
    result = runner.finalize_quality_envelope(
        readiness=_readiness(context_baseline=EvidenceState.NOT_MEASURED),
        production_pollution=0,
        evaluation_report=_report(),
        acceptance_gate=gate,
    )
    assert not gate.calls
    assert result.evaluation_report is None
    assert result.functional_status == result.phase_status == result.windows_status == "NOT_EVALUATED"


def test_measured_failure_remains_fail_instead_of_becoming_blocked() -> None:
    gate = SpyGate("FAIL")
    result = runner.finalize_quality_envelope(
        readiness=_readiness(import_audit=EvidenceState.FAILED),
        production_pollution=0,
        evaluation_report=replace(_report(), imported_messages=99),
        acceptance_gate=gate,
    )
    assert result.functional_status == "FAIL"
    assert result.phase_status == "FAIL"


def test_measured_failure_cannot_be_overridden_by_a_spurious_gate_pass() -> None:
    result = runner.finalize_quality_envelope(
        readiness=_readiness(import_audit=EvidenceState.FAILED),
        production_pollution=0,
        evaluation_report=replace(_report(), imported_messages=99),
        acceptance_gate=SpyGate("PASS"),
    )
    assert result.functional_status == result.phase_status == "FAIL"


def test_measured_failure_survives_gate_exception() -> None:
    class RaisingGate(SpyGate):
        def evaluate(self, report: EvaluationReport) -> str:
            raise RuntimeError("gate unavailable")

    result = runner.finalize_quality_envelope(
        readiness=_readiness(import_audit=EvidenceState.FAILED),
        production_pollution=0,
        evaluation_report=_report(),
        acceptance_gate=RaisingGate(),
    )
    assert result.functional_status == result.phase_status == "FAIL"


def test_unmeasured_fields_do_not_enter_raw_machine_report(tmp_path: Path) -> None:
    with runner.temporary_acceptance_roots(base_directory=tmp_path) as roots:
        runner.run_quality_gate(
            Path(__file__).parent / "fixtures" / "automatic_memory_corpus.jsonl",
            Path(__file__).parent / "fixtures" / "automatic_memory_questions.jsonl",
            output_path=roots.output_root / "quality.json",
            acceptance_roots=roots,
        )
        payload = json.loads((roots.output_root / "quality.json").read_text(encoding="utf-8"))
        assert "raw_evaluation_report" not in payload
        assert "mcp_successes" not in payload
        assert "baseline_context_chars" not in payload


def test_runner_restores_readiness_enums_before_finalizing_envelope(tmp_path: Path) -> None:
    with runner.temporary_acceptance_roots(base_directory=tmp_path) as roots:
        envelope = runner.run_quality_gate(
            Path(__file__).parent / "fixtures" / "automatic_memory_corpus.jsonl",
            Path(__file__).parent / "fixtures" / "automatic_memory_questions.jsonl",
            output_path=roots.output_root / "quality.json",
            acceptance_roots=roots,
        )
    assert envelope.readiness.mcp_parity is EvidenceState.READY
    assert envelope.readiness.context_baseline is EvidenceState.READY
    assert envelope.blocked_reasons != ("INVALID_EVIDENCE",)


def test_acceptance_factory_rejects_tampered_lease_and_cleans_setup_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with runner.temporary_acceptance_roots(base_directory=tmp_path) as roots:
        roots.lease_marker.write_text("tampered", encoding="utf-8")
        with pytest.raises(ValueError):
            roots.validate_temporary_isolation()

    original = runner.AcceptanceRoots.validate_temporary_isolation
    created: list[Path] = []

    def fail_once(self):
        created.append(self.root)
        raise ValueError("setup failure")

    monkeypatch.setattr(runner.AcceptanceRoots, "validate_temporary_isolation", fail_once)
    with pytest.raises(ValueError):
        with runner.temporary_acceptance_roots(base_directory=tmp_path):
            pass
    assert created and not created[0].exists()
    monkeypatch.setattr(runner.AcceptanceRoots, "validate_temporary_isolation", original)


def test_acceptance_roots_reject_hand_made_root_outside_os_temp(tmp_path: Path) -> None:
    root = tmp_path / "lingji-task4r-manual-probe"
    storage, vault, output = root / "storage", root / "vault", root / "output"
    storage.mkdir(parents=True)
    vault.mkdir()
    output.mkdir()
    lease = root / ".lease"
    lease.write_text("x", encoding="utf-8")
    forged = runner.AcceptanceRoots(root, storage, vault, output, lease)
    with pytest.raises(ValueError):
        forged.validate_temporary_isolation()


def test_acceptance_cleanup_failure_replaces_pre_cleanup_verdict() -> None:
    cleanup_error = getattr(runner, "AcceptanceCleanupError", None)
    assert cleanup_error is not None
    envelope = runner.cleanup_failure_envelope(_report(), cleanup_error("TEMP_CLEANUP_FAILED"))
    assert envelope.functional_status == envelope.phase_status == envelope.windows_status == "NOT_EVALUATED"
    assert envelope.evaluation_report is None
    assert "TEMP_CLEANUP_FAILED" in envelope.blocked_reasons


def test_runner_requires_isolated_acceptance_roots_and_publishes_only_after_cleanup(tmp_path: Path) -> None:
    roots_factory = getattr(runner, "temporary_acceptance_roots", None)
    assert roots_factory is not None
    output = tmp_path / "published.json"
    with roots_factory(base_directory=tmp_path) as roots:
        assert roots.root.parent == tmp_path
        assert roots.storage_root.is_relative_to(roots.root)
        assert roots.vault_root.is_relative_to(roots.root)
        assert roots.output_root.is_relative_to(roots.root)
        local_output = roots.output_root / "quality.json"
        envelope = runner.run_quality_gate(
            Path(__file__).parent / "fixtures" / "automatic_memory_corpus.jsonl",
            Path(__file__).parent / "fixtures" / "automatic_memory_questions.jsonl",
            output_path=local_output,
            acceptance_roots=roots,
        )
        assert envelope.phase_status == "FAIL"
        assert local_output.exists()
    assert not roots.root.exists()
    runner.publish_quality_envelope(envelope, repository_output_path=output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["phase_status"] == "FAIL"


def test_release_guard_blocks_scale_before_any_100k_marker() -> None:
    guard = getattr(runner, "ensure_4r2_ready_for_scale", None)
    assert guard is not None
    guard(_readiness(scale=EvidenceState.NOT_MEASURED))


def test_public_cli_uses_private_temporary_factory_not_arbitrary_roots() -> None:
    source = Path("scripts/automatic_memory_quality_gate.py").read_text(encoding="utf-8")
    assert "temporary_acceptance_roots" in source
    assert "settings.vault_path" not in source
    assert "settings.storage_path" not in source


def test_release_preflight_is_executable_and_prevents_scale_invocation() -> None:
    result = subprocess.run(
        ["./.venv/bin/python", "scripts/automatic_memory_quality_gate.py", "--check-4r2"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "BLOCKED_4R2_REQUIRED" in result.stderr


@pytest.mark.parametrize("stage", [
    "admission", "root", "sentinel", "fixture", "import", "gateway",
    "promotion", "audit", "scoring", "evaluator", "publication_pre",
])
def test_runner_stage_exception_publishes_fresh_not_evaluated_envelope(
    tmp_path: Path, stage: str,
) -> None:
    fixtures = Path(__file__).parent / "fixtures"

    def fail_at(current: str) -> None:
        if current == stage:
            raise RuntimeError("secret/path/fixture payload must not escape")

    with runner.temporary_acceptance_roots(base_directory=tmp_path) as roots:
        result = runner.run_quality_gate(
            fixtures / "automatic_memory_corpus.jsonl",
            fixtures / "automatic_memory_questions.jsonl",
            output_path=roots.output_root / "quality.json",
            acceptance_roots=roots,
            stage_hook=fail_at,
        )
        payload = json.loads((roots.output_root / "quality.json").read_text(encoding="utf-8"))
        assert result.evaluation_report is None
        assert result.functional_status == result.phase_status == result.windows_status == "NOT_EVALUATED"
        assert result.blocked_reasons == (f"RUNNER_{stage.upper()}_FAILED",)
        assert payload["evaluation_report"] is None
        assert payload["blocked_reasons"] == [f"RUNNER_{stage.upper()}_FAILED"]
        assert payload["cleanup_inventory"]["root_exists"] is True
        assert "secret" not in json.dumps(payload)
        assert str(fixtures) not in json.dumps(payload)


def test_runner_failure_envelope_replaces_stale_pass_atomically(tmp_path: Path) -> None:
    destination = tmp_path / "automatic-memory-quality.json"
    destination.write_text(json.dumps({"functional_status": "PASS"}), encoding="utf-8")
    envelope = runner.runner_failure_envelope("gateway")
    runner.publish_quality_envelope(envelope, repository_output_path=destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["functional_status"] == "NOT_EVALUATED"
    assert payload["evaluation_report"] is None
    assert payload["blocked_reasons"] == ["RUNNER_GATEWAY_FAILED"]
