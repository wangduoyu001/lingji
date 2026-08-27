from __future__ import annotations

import json
import os
import stat
from dataclasses import replace
from pathlib import Path

import pytest

from src.automatic_memory.evaluation import AutomaticMemoryAcceptanceGate, EvaluationReport
from src.automatic_memory.quality_gate import (
    AcceptanceCleanupError,
    AcceptanceRoots,
    cleanup_failure_envelope,
    run_release_preflight,
    verify_acceptance_cleanup,
    QualityScaleBlockedError,
)
from src.automatic_memory.quality_evidence import (
    EvidenceState,
    ProtectedTreeSentinel,
    QualityEvidenceReadiness,
    QualityPublicationError,
    _open_anchored_directory,
    _open_publication_parent,
    finalize_quality_envelope,
    write_quality_json_atomic,
)
import src.automatic_memory.quality_evidence as evidence_module


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


def test_failed_functional_evidence_with_frozen_pass_remains_fail_closed() -> None:
    gate = SpyGate("PASS")
    result = finalize_quality_envelope(
        readiness=readiness(import_audit=EvidenceState.FAILED), production_pollution=0,
        evaluation_report=report(), acceptance_gate=gate,
    )
    assert result.evaluation_report is not None
    assert result.functional_status == result.phase_status == "FAIL"
    assert result.windows_status == "BLOCKED"


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


def test_sentinel_uses_anchored_child_directory_descriptors_and_never_reads_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    (root / "nested").mkdir(parents=True); outside.mkdir()
    (outside / "secret").write_text("secret", encoding="utf-8")
    (root / "nested" / "secret").write_text("safe", encoding="utf-8")
    calls: list[tuple[object, object]] = []
    real_open = evidence_module.os.open

    def recording_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        calls.append((path, kwargs.get("dir_fd")))
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(evidence_module.os, "open", recording_open)
    ProtectedTreeSentinel.capture((root,))
    assert any(dir_fd is not None for _path, dir_fd in calls)
    assert not any(str(outside) in str(path) for path, _dir_fd in calls)


def test_sentinel_rejects_same_size_content_race_after_first_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"; root.mkdir()
    target = root / "entry"; target.write_text("before", encoding="utf-8")
    real_fstat = evidence_module.os.fstat
    calls = 0

    def racing_fstat(fd: int):
        nonlocal calls
        calls += 1
        value = real_fstat(fd)
        if calls == 3:
            target.write_text("change", encoding="utf-8")
        return value

    monkeypatch.setattr(evidence_module.os, "fstat", racing_fstat)
    with pytest.raises(evidence_module.ProtectedTreeInvalidError):
        ProtectedTreeSentinel.capture((root,))


def test_finalizer_validates_report_before_gate_calls() -> None:
    gate = SpyGate()
    malformed = replace(report(), valid_fact_recall="bad")
    result = finalize_quality_envelope(
        readiness=readiness(), production_pollution=0,
        evaluation_report=malformed, acceptance_gate=gate,
    )
    assert not gate.calls
    assert result.evaluation_report is None
    assert "MALFORMED_EVALUATION_REPORT" in result.blocked_reasons


def test_atomic_writer_surfaces_directory_fsync_failure_after_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "output"; output_dir.mkdir()
    destination = output_dir / "report.json"; destination.write_text("old", encoding="utf-8")
    real_fsync = evidence_module.os.fsync
    calls = 0

    def failing_fsync(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected directory fsync failure")
        real_fsync(fd)

    monkeypatch.setattr(evidence_module.os, "fsync", failing_fsync)
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(destination, {"new": True}, protected_roots=())
    assert error.value.code == "DIRECTORY_FSYNC_FAILED_AFTER_REPLACE"
    assert json.loads(destination.read_text(encoding="utf-8")) == {"new": True}


def test_atomic_writer_wraps_arbitrary_serialization_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "output"; output_dir.mkdir()
    monkeypatch.setattr(evidence_module.json, "dumps", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("/Users/secret")))
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(output_dir / "report.json", {"answer": 1}, protected_roots=())
    assert error.value.code == "SERIALIZATION_FAILED"
    assert str(error.value) == "SERIALIZATION_FAILED"


def test_reason_allowlist_redacts_unknown_path_components() -> None:
    result = finalize_quality_envelope(
        readiness=readiness(mcp_parity=EvidenceState.NOT_MEASURED), production_pollution=0,
        evaluation_report=None, acceptance_gate=SpyGate(),
        blocked_reasons=("/Users/alice/secret", "x y", "WINDOWS_AFTER_MAC"),
    )
    assert result.blocked_reasons == ("UNTRUSTED_BLOCKED_REASON", "WINDOWS_AFTER_MAC")


@pytest.mark.parametrize("field", [
    "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
    "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
])
@pytest.mark.parametrize("state", [EvidenceState.NOT_MEASURED, EvidenceState.INVALID])
def test_every_functional_unavailable_state_is_not_evaluated(field: str, state: EvidenceState) -> None:
    gate = SpyGate()
    pollution = None if field == "production_sentinel" else 0
    result = finalize_quality_envelope(
        readiness=readiness(**{field: state}), production_pollution=pollution,
        evaluation_report=report(), acceptance_gate=gate,
    )
    assert not gate.calls
    assert result.evaluation_report is None
    assert (result.functional_status, result.phase_status, result.windows_status) == (
        "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED"
    )


@pytest.mark.parametrize("field", [
    "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
    "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
])
def test_measured_failed_functional_state_uses_frozen_fail(field: str) -> None:
    gate = SpyGate("FAIL")
    pollution = 1 if field == "production_sentinel" else 0
    result = finalize_quality_envelope(
        readiness=readiness(**{field: EvidenceState.FAILED}), production_pollution=pollution,
        evaluation_report=replace(report(), production_pollution=pollution), acceptance_gate=gate,
    )
    assert len(gate.calls) == 2
    assert result.functional_status == result.phase_status == "FAIL"


@pytest.mark.parametrize("field", ["scale", "owner_review", "reboot_recovery", "mac_release"])
@pytest.mark.parametrize("state,phase", [
    (EvidenceState.NOT_MEASURED, "BLOCKED"), (EvidenceState.INVALID, "BLOCKED"),
    (EvidenceState.FAILED, "FAIL"), (EvidenceState.READY, "PASS"),
])
def test_mac_release_state_controls_phase_after_functional_pass(field: str, state: EvidenceState, phase: str) -> None:
    values = {"windows_release": EvidenceState.NOT_MEASURED, field: state}
    result = finalize_quality_envelope(
        readiness=readiness(**values), production_pollution=0,
        evaluation_report=report(), acceptance_gate=SpyGate(),
    )
    assert result.functional_status == "PASS"
    assert result.phase_status == phase


@pytest.mark.parametrize("state,expected", [
    (EvidenceState.NOT_MEASURED, "BLOCKED"), (EvidenceState.INVALID, "BLOCKED"),
    (EvidenceState.FAILED, "FAIL"), (EvidenceState.READY, "PASS"),
])
def test_windows_state_is_evaluated_only_after_mac_pass(state: EvidenceState, expected: str) -> None:
    result = finalize_quality_envelope(
        readiness=readiness(windows_release=state), production_pollution=0,
        evaluation_report=report(), acceptance_gate=SpyGate(),
    )
    assert result.phase_status == "PASS"
    assert result.windows_status == expected


def test_windows_is_blocked_before_mac_pass() -> None:
    result = finalize_quality_envelope(
        readiness=readiness(scale=EvidenceState.NOT_MEASURED, windows_release=EvidenceState.READY),
        production_pollution=0, evaluation_report=report(), acceptance_gate=SpyGate(),
    )
    assert result.phase_status == "BLOCKED"
    assert result.windows_status == "BLOCKED"
    assert "WINDOWS_AFTER_MAC" in result.blocked_reasons


class SequenceGate:
    def __init__(self, *verdicts: str) -> None:
        self.verdicts = list(verdicts)
        self.calls = 0

    def evaluate(self, _report: EvaluationReport) -> str:
        self.calls += 1
        return self.verdicts.pop(0)


@pytest.mark.parametrize("verdicts", [("MALFORMED", "PASS"), ("PASS", "MALFORMED"), ("BLOCKED", "PASS")])
def test_malformed_or_blocked_gate_verdict_fails_closed(verdicts: tuple[str, str]) -> None:
    gate = SequenceGate(*verdicts)
    result = finalize_quality_envelope(
        readiness=readiness(), production_pollution=0,
        evaluation_report=report(), acceptance_gate=gate,
    )
    assert result.evaluation_report is None
    assert result.functional_status == "NOT_EVALUATED"


def test_gate_exception_fails_closed_without_partial_report() -> None:
    class RaisingGate:
        def evaluate(self, _report: EvaluationReport) -> str:
            raise RuntimeError("private path")
    result = finalize_quality_envelope(
        readiness=readiness(), production_pollution=0,
        evaluation_report=report(), acceptance_gate=RaisingGate(),
    )
    assert result.evaluation_report is None
    assert result.blocked_reasons == ("GATE_EXCEPTION",)


def test_sentinel_rejects_empty_duplicate_and_overlapping_roots(tmp_path: Path) -> None:
    root = tmp_path / "root"; root.mkdir()
    with pytest.raises(evidence_module.ProtectedTreeUnavailableError):
        ProtectedTreeSentinel.capture(())
    with pytest.raises(evidence_module.ProtectedTreeUnavailableError):
        ProtectedTreeSentinel.capture((root, root))
    with pytest.raises(evidence_module.ProtectedTreeUnavailableError):
        ProtectedTreeSentinel.capture((root, root / "nested"))


def test_sentinel_root_contract_is_order_independent_and_mismatch_invalid(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir(); second.mkdir()
    left = ProtectedTreeSentinel.capture((first, second))
    right = ProtectedTreeSentinel.capture((second, first))
    assert left.root_contract == right.root_contract
    other = ProtectedTreeSentinel.capture((first,))
    with pytest.raises(evidence_module.ProtectedTreeInvalidError):
        left.diff(other)


def test_atomic_writer_rejects_target_and_parent_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"; outside.mkdir()
    real_parent = tmp_path / "real"; real_parent.mkdir()
    (real_parent / "existing").symlink_to(outside / "missing")
    with pytest.raises(QualityPublicationError) as target_error:
        write_quality_json_atomic(real_parent / "existing", {}, protected_roots=())
    assert target_error.value.code == "OUTPUT_SYMLINK"
    link_parent = tmp_path / "link"; link_parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(QualityPublicationError) as parent_error:
        write_quality_json_atomic(link_parent / "report.json", {}, protected_roots=())
    assert parent_error.value.code in {"PARENT_UNAVAILABLE", "PARENT_SYMLINK"}


@pytest.mark.parametrize("replacement", ["symlink", "directory"])
def test_child_directory_replacement_is_rejected_before_reading_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str,
) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    (root / "nested").mkdir(parents=True); outside.mkdir()
    (outside / "secret").write_text("SECRET_OUTSIDE", encoding="utf-8")
    (root / "nested" / "safe").write_text("safe", encoding="utf-8")
    real_open = evidence_module.os.open
    swapped = False
    reads: list[bytes] = []

    def swap_before_child_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal swapped
        if not swapped and path == "nested" and kwargs.get("dir_fd") is not None:
            swapped = True
            old = root / "nested-old"
            os.rename(root / "nested", old)
            if replacement == "symlink":
                (root / "nested").symlink_to(outside, target_is_directory=True)
            else:
                (root / "nested").mkdir()
                (root / "nested" / "secret").write_text("SECRET_OUTSIDE", encoding="utf-8")
        return real_open(path, flags, *args, **kwargs)

    real_read = evidence_module.os.read
    def recording_read(fd: int, size: int) -> bytes:
        chunk = real_read(fd, size)
        reads.append(chunk)
        return chunk

    monkeypatch.setattr(evidence_module.os, "open", swap_before_child_open)
    monkeypatch.setattr(evidence_module.os, "read", recording_read)
    with pytest.raises(evidence_module.ProtectedTreeInvalidError):
        ProtectedTreeSentinel.capture((root,))
    assert b"SECRET_OUTSIDE" not in b"".join(reads)


def test_root_path_replacement_is_detected_at_completion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir(); outside.mkdir(); (outside / "secret").write_text("outside", encoding="utf-8")
    real_scandir = evidence_module.os.scandir
    replaced = False

    def replacing_scandir(path: object):
        nonlocal replaced
        if not replaced and isinstance(path, int):
            replaced = True
            old = tmp_path / "root-old"
            os.rename(root, old)
            root.symlink_to(outside, target_is_directory=True)
        return real_scandir(path)

    monkeypatch.setattr(evidence_module.os, "scandir", replacing_scandir)
    with pytest.raises(evidence_module.ProtectedTreeInvalidError) as error:
        ProtectedTreeSentinel.capture((root,))
    assert error.value.code == "ROOT_RACE"


class EvilReason:
    def __str__(self) -> str:
        raise RuntimeError("/Users/private")


class EvilReasons:
    def __iter__(self):
        raise RuntimeError("token=/Users/private")


def test_hostile_reason_item_and_iterator_are_redacted_without_stringification() -> None:
    for reasons in ((EvilReason(),), EvilReasons()):
        result = finalize_quality_envelope(
            readiness=readiness(mcp_parity=EvidenceState.NOT_MEASURED), production_pollution=0,
            evaluation_report=None, acceptance_gate=SpyGate(), blocked_reasons=reasons,
        )
        assert result.blocked_reasons == ("UNTRUSTED_BLOCKED_REASON",)


def test_anchored_directory_close_failure_is_typed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"; root.mkdir()
    real_close = evidence_module.os.close
    failed = False

    def close_once(fd: int) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("injected close")
        real_close(fd)

    monkeypatch.setattr(evidence_module.os, "close", close_once)
    with pytest.raises(evidence_module.ProtectedTreeInvalidError) as error:
        ProtectedTreeSentinel.capture((root,))
    assert error.value.code == "FD_CLOSE_FAILED"


def test_atomic_writer_failure_at_file_fsync_leaves_no_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "output"; output_dir.mkdir()
    destination = output_dir / "report.json"; destination.write_text("old", encoding="utf-8")
    monkeypatch.setattr(evidence_module.os, "fsync", lambda _fd: (_ for _ in ()).throw(OSError("fsync")))
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(destination, {"new": True}, protected_roots=())
    assert error.value.code == "WRITE_FAILED"
    assert destination.read_text(encoding="utf-8") == "old"
    assert not list(output_dir.glob("*.tmp"))


def test_atomic_writer_parent_replacement_cannot_publish_outside(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent, outside = tmp_path / "parent", tmp_path / "outside"
    parent.mkdir(); outside.mkdir()
    real_open = evidence_module.os.open
    swapped = False

    def replace_parent(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal swapped
        if not swapped and path == "parent" and kwargs.get("dir_fd") is not None:
            swapped = True
            old = tmp_path / "parent-old"
            os.rename(parent, old)
            parent.symlink_to(outside, target_is_directory=True)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(evidence_module.os, "open", replace_parent)
    with pytest.raises(QualityPublicationError):
        write_quality_json_atomic(parent / "report.json", {"new": True}, protected_roots=())
    assert not (outside / "report.json").exists()


def test_initial_root_identity_failure_is_typed_and_path_redacted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(evidence_module.os, "fstat", lambda _fd: (_ for _ in ()).throw(OSError("/private/root")))
    with pytest.raises(evidence_module.ProtectedTreeInvalidError) as error:
        ProtectedTreeSentinel.capture((root,))
    assert error.value.code == "ROOT_FSTAT_FAILED"
    assert str(error.value) == "ROOT_FSTAT_FAILED"


def test_final_root_identity_failure_is_typed_and_path_redacted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"
    root.mkdir()
    real_fstat = evidence_module.os.fstat
    calls = 0

    def failing_final_fstat(fd: int):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise OSError("/private/root-final")
        return real_fstat(fd)

    monkeypatch.setattr(evidence_module.os, "fstat", failing_final_fstat)
    with pytest.raises(evidence_module.ProtectedTreeInvalidError) as error:
        ProtectedTreeSentinel.capture((root,))
    assert error.value.code == "ROOT_FSTAT_FAILED"
    assert str(error.value) == "ROOT_FSTAT_FAILED"


def test_hostile_report_string_subclass_is_rejected_without_stringification() -> None:
    class HostileString(str):
        def strip(self):
            raise RuntimeError("/private/report")

    malformed = replace(report(), blocked_reasons=(HostileString("BLOCKED"),))
    result = finalize_quality_envelope(
        readiness=readiness(), production_pollution=0,
        evaluation_report=malformed, acceptance_gate=SpyGate(),
    )
    assert result.evaluation_report is None
    assert (result.functional_status, result.phase_status, result.windows_status) == (
        "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED",
    )
    assert result.blocked_reasons == ("MALFORMED_EVALUATION_REPORT",)


def test_malformed_report_tuple_member_is_rejected_without_truthiness() -> None:
    class HostileValue:
        def __bool__(self):
            raise RuntimeError("/private/report")

    malformed = replace(report(), blocked_reasons=(HostileValue(),))
    result = finalize_quality_envelope(
        readiness=readiness(), production_pollution=0,
        evaluation_report=malformed, acceptance_gate=SpyGate(),
    )
    assert result.evaluation_report is None
    assert result.blocked_reasons == ("MALFORMED_EVALUATION_REPORT",)


def test_report_validation_exception_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        evidence_module, "_valid_evaluation_report",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("/private/validation")),
    )
    result = finalize_quality_envelope(
        readiness=readiness(), production_pollution=0,
        evaluation_report=report(), acceptance_gate=SpyGate(),
    )
    assert result.evaluation_report is None
    assert (result.functional_status, result.phase_status, result.windows_status) == (
        "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED",
    )
    assert result.blocked_reasons == ("MALFORMED_EVALUATION_REPORT",)


def test_atomic_writer_wraps_fdopen_exception_and_cleans_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    destination = output_dir / "report.json"
    destination.write_text("old", encoding="utf-8")
    monkeypatch.setattr(evidence_module.os, "fdopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("/private/fd")))
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(destination, {"new": True}, protected_roots=())
    assert error.value.code == "WRITE_FAILED"
    assert str(error.value) == "WRITE_FAILED"
    assert destination.read_text(encoding="utf-8") == "old"
    assert not list(output_dir.glob("*.tmp"))


@pytest.mark.parametrize("opener,expected", [
    (_open_anchored_directory, "FD_CLOSE_FAILED"),
    (_open_publication_parent, "FD_CLOSE_FAILED"),
])
def test_anchored_helper_does_not_retry_descriptor_after_close_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, opener, expected: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    real_close = evidence_module.os.close
    calls: dict[int, int] = {}
    raised = False

    def close_after_real_close(fd: int) -> None:
        nonlocal raised
        calls[fd] = calls.get(fd, 0) + 1
        if not raised:
            raised = True
            real_close(fd)
            raise OSError("/private/close")
        real_close(fd)

    monkeypatch.setattr(evidence_module.os, "close", close_after_real_close)
    with pytest.raises((evidence_module.ProtectedTreeInvalidError, QualityPublicationError)) as error:
        opener(root)
    assert error.value.code == expected
    assert max(calls.values()) == 1


class _FailingWriterStream:
    def __init__(self, fd: int, stage: str) -> None:
        self.fd = fd
        self.stage = stage

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        evidence_module.os.close(self.fd)
        if self.stage == "close":
            raise RuntimeError("/private/stream-close")
        return False

    def write(self, _payload: bytes) -> int:
        if self.stage == "write":
            raise RuntimeError("/private/stream-write")
        return 1

    def flush(self) -> None:
        if self.stage == "flush":
            raise RuntimeError("/private/stream-flush")

    def fileno(self) -> int:
        return self.fd


@pytest.mark.parametrize("stage", ["write", "flush", "close"])
def test_atomic_writer_wraps_each_stream_stage_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    destination = output_dir / "report.json"
    destination.write_text("old", encoding="utf-8")
    monkeypatch.setattr(evidence_module.os, "fdopen", lambda fd, *_args, **_kwargs: _FailingWriterStream(fd, stage))
    monkeypatch.setattr(evidence_module.os, "fsync", lambda _fd: None)
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(destination, {"new": True}, protected_roots=())
    assert error.value.code == "WRITE_FAILED"
    assert str(error.value) == "WRITE_FAILED"
    assert destination.read_text(encoding="utf-8") == "old"
    assert not list(output_dir.glob("*.tmp"))


def test_atomic_writer_wraps_replace_exception_and_preserves_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    destination = output_dir / "report.json"
    destination.write_text("old", encoding="utf-8")
    monkeypatch.setattr(evidence_module.os, "replace", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("/private/replace")))
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(destination, {"new": True}, protected_roots=())
    assert error.value.code == "REPLACE_FAILED"
    assert str(error.value) == "REPLACE_FAILED"
    assert destination.read_text(encoding="utf-8") == "old"
    assert not list(output_dir.glob("*.tmp"))


def test_atomic_writer_cleanup_failure_is_stable_after_real_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    destination = output_dir / "report.json"
    destination.write_text("old", encoding="utf-8")
    real_replace = evidence_module.os.replace
    real_unlink = evidence_module.os.unlink
    monkeypatch.setattr(evidence_module.os, "replace", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("replace")))

    def unlink_then_raise(path: object, *args: object, **kwargs: object) -> None:
        real_unlink(path, *args, **kwargs)
        raise OSError("/private/cleanup")

    monkeypatch.setattr(evidence_module.os, "unlink", unlink_then_raise)
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(destination, {"new": True}, protected_roots=())
    assert error.value.code == "TEMP_CLEANUP_FAILED"
    assert str(error.value) == "TEMP_CLEANUP_FAILED"
    assert destination.read_text(encoding="utf-8") == "old"
    assert not list(output_dir.glob("*.tmp"))


def test_atomic_writer_parent_close_failure_is_stable_after_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    destination = output_dir / "report.json"
    destination.write_text("old", encoding="utf-8")
    real_fsync = evidence_module.os.fsync
    real_close = evidence_module.os.close
    parent_fd: int | None = None
    fsync_calls = 0
    raised = False

    def record_parent_fsync(fd: int) -> None:
        nonlocal parent_fd, fsync_calls
        fsync_calls += 1
        real_fsync(fd)
        if fsync_calls == 2:
            parent_fd = fd

    def close_parent_after_real_close(fd: int) -> None:
        nonlocal raised
        if parent_fd is not None and fd == parent_fd and not raised:
            raised = True
            real_close(fd)
            raise OSError("/private/parent-close")
        real_close(fd)

    monkeypatch.setattr(evidence_module.os, "fsync", record_parent_fsync)
    monkeypatch.setattr(evidence_module.os, "close", close_parent_after_real_close)
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(destination, {"new": True}, protected_roots=())
    assert error.value.code == "FD_CLOSE_FAILED"
    assert str(error.value) == "FD_CLOSE_FAILED"
    assert json.loads(destination.read_text(encoding="utf-8")) == {"new": True}
    assert not list(output_dir.glob("*.tmp"))


@pytest.mark.parametrize("replacement", ["symlink", "directory"])
def test_root_replacement_before_final_anchored_open_is_root_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str,
) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir(); outside.mkdir()
    (outside / "secret").write_text("outside", encoding="utf-8")
    real_open_anchored = evidence_module._open_anchored_directory
    calls = 0

    def replace_before_final_open(path: Path) -> int:
        nonlocal calls
        calls += 1
        if calls == 2:
            old = tmp_path / "root-old"
            os.rename(root, old)
            if replacement == "symlink":
                root.symlink_to(outside, target_is_directory=True)
            else:
                root.mkdir()
                (root / "secret").write_text("outside", encoding="utf-8")
        return real_open_anchored(path)

    monkeypatch.setattr(evidence_module, "_open_anchored_directory", replace_before_final_open)
    with pytest.raises(evidence_module.ProtectedTreeInvalidError) as error:
        ProtectedTreeSentinel.capture((root,))
    assert error.value.code == "ROOT_RACE"


def test_snapshot_after_final_observation_is_deferred_to_next_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    replacement = tmp_path / "replacement"
    root.mkdir(); replacement.mkdir()
    (root / "entry").write_text("before", encoding="utf-8")
    real_fstat = evidence_module.os.fstat
    calls = 0

    def replace_after_final_observation(fd: int):
        nonlocal calls
        calls += 1
        value = real_fstat(fd)
        if calls == 7:
            old = tmp_path / "root-old"
            os.rename(root, old)
            os.rename(replacement, root)
        return value

    monkeypatch.setattr(evidence_module.os, "fstat", replace_after_final_observation)
    first = ProtectedTreeSentinel.capture((root,))
    assert first.entries
    second = ProtectedTreeSentinel.capture((root,))
    assert first.diff(second)


def test_successful_sentinel_and_writer_return_to_descriptor_baseline(tmp_path: Path) -> None:
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (nested / "entry").write_text("content", encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    baseline = len(os.listdir("/dev/fd"))
    ProtectedTreeSentinel.capture((root,))
    write_quality_json_atomic(output / "report.json", {"ok": True}, protected_roots=())
    assert len(os.listdir("/dev/fd")) <= baseline


def test_admission_identity_rejects_real_root_replacement_before_first_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, replacement = tmp_path / "root", tmp_path / "replacement"
    root.mkdir(); replacement.mkdir()
    (replacement / "secret").write_text("REPLACEMENT_SECRET", encoding="utf-8")
    real_open = evidence_module._open_anchored_directory
    reads: list[bytes] = []
    swapped = False

    def replace_before_first_open(path: Path) -> int:
        nonlocal swapped
        if not swapped:
            swapped = True
            old = tmp_path / "root-old"
            os.rename(root, old)
            os.rename(replacement, root)
        return real_open(path)

    real_read = evidence_module.os.read
    monkeypatch.setattr(evidence_module, "_open_anchored_directory", replace_before_first_open)
    monkeypatch.setattr(evidence_module.os, "read", lambda fd, size: (lambda chunk: (reads.append(chunk), chunk)[1])(real_read(fd, size)))
    with pytest.raises(evidence_module.ProtectedTreeInvalidError) as error:
        ProtectedTreeSentinel.capture((root,))
    assert error.value.code == "ROOT_RACE"
    assert b"REPLACEMENT_SECRET" not in b"".join(reads)


def test_admission_identity_is_bound_to_each_sorted_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first, second, replacement = tmp_path / "first", tmp_path / "second", tmp_path / "replacement"
    first.mkdir(); second.mkdir(); replacement.mkdir()
    (replacement / "secret").write_text("REPLACEMENT_SECRET", encoding="utf-8")
    real_open = evidence_module._open_anchored_directory
    swapped = False

    def replace_second_before_open(path: Path) -> int:
        nonlocal swapped
        if path == second and not swapped:
            swapped = True
            old = tmp_path / "second-old"
            os.rename(second, old)
            os.rename(replacement, second)
        return real_open(path)

    monkeypatch.setattr(evidence_module, "_open_anchored_directory", replace_second_before_open)
    with pytest.raises(evidence_module.ProtectedTreeInvalidError) as error:
        ProtectedTreeSentinel.capture((second, first))
    assert error.value.code == "ROOT_RACE"


class _HostileReadiness(QualityEvidenceReadiness):
    def __getattribute__(self, name: str):
        if name == "import_audit":
            raise RuntimeError("/private/readiness")
        return super().__getattribute__(name)


def test_hostile_readiness_subclass_is_rejected_before_field_access() -> None:
    hostile = _HostileReadiness(**{field: EvidenceState.READY for field in (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
        "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
    )})
    gate = SpyGate()
    result = finalize_quality_envelope(
        readiness=hostile, production_pollution=0,
        evaluation_report=report(), acceptance_gate=gate,
    )
    assert not gate.calls
    assert result.evaluation_report is None
    assert (result.functional_status, result.phase_status, result.windows_status) == (
        "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED",
    )
    assert result.blocked_reasons == ("INVALID_EVIDENCE",)


class _HostileVerdict:
    def __eq__(self, _other):
        raise RuntimeError("/private/verdict")


@pytest.mark.parametrize("verdicts,expected_calls", [
    (("PASS", _HostileVerdict()), 2),
    ((_HostileVerdict(), "PASS"), 1),
])
def test_hostile_gate_verdict_is_rejected_at_the_individual_call(
    verdicts: tuple[object, object], expected_calls: int,
) -> None:
    class Gate:
        def __init__(self) -> None:
            self.calls = 0

        def evaluate(self, _report: EvaluationReport):
            value = verdicts[self.calls]
            self.calls += 1
            return value

    gate = Gate()
    result = finalize_quality_envelope(
        readiness=readiness(), production_pollution=0,
        evaluation_report=report(), acceptance_gate=gate,
    )
    assert gate.calls == expected_calls
    assert result.evaluation_report is None
    assert (result.functional_status, result.phase_status, result.windows_status) == (
        "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED",
    )
    assert result.blocked_reasons == ("MALFORMED_GATE_RESULT",)


def test_parent_directory_fsync_runtime_error_is_stable_after_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"; output_dir.mkdir()
    destination = output_dir / "report.json"; destination.write_text("old", encoding="utf-8")
    calls = 0

    def fail_parent_fsync(_fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("/private/fsync")

    monkeypatch.setattr(evidence_module.os, "fsync", fail_parent_fsync)
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(destination, {"new": True}, protected_roots=())
    assert error.value.code == "DIRECTORY_FSYNC_FAILED_AFTER_REPLACE"
    assert str(error.value) == "DIRECTORY_FSYNC_FAILED_AFTER_REPLACE"
    assert json.loads(destination.read_text(encoding="utf-8")) == {"new": True}


def test_cleanup_runtime_error_is_stable_and_reports_actual_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "output"; output_dir.mkdir()
    destination = output_dir / "report.json"; destination.write_text("old", encoding="utf-8")
    real_unlink = evidence_module.os.unlink
    monkeypatch.setattr(evidence_module.os, "replace", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("replace")))

    def unlink_then_runtime(path: object, *args: object, **kwargs: object) -> None:
        real_unlink(path, *args, **kwargs)
        raise RuntimeError("/private/cleanup")

    monkeypatch.setattr(evidence_module.os, "unlink", unlink_then_runtime)
    with pytest.raises(QualityPublicationError) as error:
        write_quality_json_atomic(destination, {"new": True}, protected_roots=())
    assert error.value.code == "TEMP_CLEANUP_FAILED"
    assert str(error.value) == "TEMP_CLEANUP_FAILED"
    assert destination.read_text(encoding="utf-8") == "old"
    assert not list(output_dir.glob("*.tmp"))


def test_acceptance_admission_checks_mode_bits_and_real_directory_access(tmp_path: Path) -> None:
    root = tmp_path / "lingji-task4r-mode"
    root.mkdir()
    storage, vault, output, marker = (root / name for name in ("storage", "vault", "output", ".lease"))
    storage.mkdir(); vault.mkdir(); output.mkdir(); marker.write_text("lease", encoding="utf-8")
    roots = AcceptanceRoots(root, storage, vault, output, marker, tmp_path, "lease")
    roots.validate_temporary_isolation()
    for target in (root, storage, vault, output):
        target.chmod(0)
        try:
            with pytest.raises(ValueError):
                roots.validate_temporary_isolation()
        finally:
            target.chmod(0o755)
    marker.chmod(0)
    try:
        with pytest.raises(ValueError):
            roots.validate_temporary_isolation()
    finally:
        marker.chmod(0o644)


def test_cleanup_inventory_detects_dangling_symlink(tmp_path: Path) -> None:
    root = tmp_path / "lingji-task4r-residue"
    root.mkdir()
    storage = root / "storage"
    storage.symlink_to(tmp_path / "missing-target", target_is_directory=True)
    roots = AcceptanceRoots(root, storage, root / "vault", root / "output", root / ".lease")
    with pytest.raises(AcceptanceCleanupError) as error:
        verify_acceptance_cleanup(roots)
    assert error.value.code == "TEMP_CLEANUP_INCOMPLETE"


@pytest.mark.parametrize("verdict", ["PASS", "BOGUS", None])
def test_measured_functional_failure_cannot_be_downgraded_by_gate(verdict: object) -> None:
    class Gate:
        def evaluate(self, _report: EvaluationReport) -> object:
            if verdict == "RAISE":
                raise RuntimeError("private gate detail")
            return verdict

    result = finalize_quality_envelope(
        readiness=readiness(import_audit=EvidenceState.FAILED), production_pollution=0,
        evaluation_report=report(), acceptance_gate=Gate(),
    )
    assert result.functional_status == result.phase_status == "FAIL"
    assert result.windows_status == "BLOCKED"
    assert result.evaluation_report is not None
    expected_reason = "CONTRADICTORY_FUNCTIONAL_EVIDENCE" if verdict == "PASS" else "MALFORMED_GATE_RESULT"
    assert expected_reason in result.blocked_reasons


def test_measured_functional_failure_and_gate_exception_remain_fail() -> None:
    class Gate:
        def evaluate(self, _report: EvaluationReport) -> str:
            raise RuntimeError("private gate detail")

    result = finalize_quality_envelope(
        readiness=readiness(import_audit=EvidenceState.FAILED), production_pollution=0,
        evaluation_report=report(), acceptance_gate=Gate(),
    )
    assert result.functional_status == result.phase_status == "FAIL"
    assert result.evaluation_report is not None
    assert "GATE_EXCEPTION" in result.blocked_reasons


def test_release_preflight_blocks_before_scale_callbacks_and_orders_success() -> None:
    calls: list[str] = []
    with pytest.raises(QualityScaleBlockedError):
        run_release_preflight(
            readiness(scale=EvidenceState.NOT_MEASURED),
            prepare_scale_environment=lambda: calls.append("env"),
            run_scale_command=lambda: calls.append("command"),
        )
    assert calls == []
    run_release_preflight(
        readiness(), prepare_scale_environment=lambda: calls.append("env"),
        run_scale_command=lambda: calls.append("command"),
    )
    assert calls == ["env", "command"]


def test_release_validation_entry_calls_python_preflight_before_scale() -> None:
    text = Path("scripts/validate.ps1").read_text(encoding="utf-8")
    release = text.split("function Invoke-ReleaseValidation", 1)[1].split("$scopeText", 1)[0]
    assert "scripts/automatic_memory_quality_gate.py" in release
    assert "--check-4r2" in release
    assert "LINGJI_RUN_100K" not in release


def test_cleanup_failure_unknown_code_is_stable_and_redacted() -> None:
    secret = "/private/path/token=do-not-leak"
    result = cleanup_failure_envelope(None, AcceptanceCleanupError(secret))
    assert result.blocked_reasons == ("UNTRUSTED_BLOCKED_REASON",)
    assert secret not in repr(result)
