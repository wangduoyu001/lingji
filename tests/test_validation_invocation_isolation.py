from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_SCRIPT = REPO_ROOT / "scripts" / "validate.ps1"
VALIDATION_LAUNCHER = REPO_ROOT / "scripts" / "run_powershell_validation.py"
PRIVATE_PWSH = Path("/tmp/LingJiToolchain/powershell-7.6.5/pwsh")


def _powershell() -> str:
    candidates = [PRIVATE_PWSH, *(Path(path) for path in (shutil.which(name) for name in ("pwsh", "powershell", "powershell.exe")) if path)]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    pytest.skip("a real PowerShell host is required for validation isolation tests")


def _run_validation(
    validation_root: Path,
    *,
    clock: str,
    mode: str = "focused",
    entry_only: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["LINGJI_VALIDATE_TEST_CLOCK"] = clock
    powershell = Path(_powershell())
    environment["PATH"] = str(powershell.parent) + os.pathsep + environment.get("PATH", "")
    command = [
        sys.executable,
        str(VALIDATION_LAUNCHER),
        "--mode",
        mode,
        "--area",
        "docs",
        "--python-command",
        sys.executable,
        "--output-root",
        str(validation_root),
        "--output-hint",
        "isolation-test",
    ]
    if entry_only:
        hook = validation_root / "entry-only-hook.txt"
        command.extend(("--hook", str(hook), "--entry-only"))
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_directories(validation_root: Path) -> list[Path]:
    return sorted(path for path in validation_root.iterdir() if path.is_dir())


def _owner_marker(path: Path, *, state: str, invocation_id: str, ended_at: str | None = None) -> None:
    marker = {
        "invocation_id": invocation_id,
        "state": state,
        "process_id": 0,
        "started_at": "2000-01-01T00:00:00+00:00",
    }
    if ended_at is not None:
        marker["ended_at"] = ended_at
    path.mkdir(parents=True)
    (path / ".owner.json").write_text(json.dumps(marker), encoding="utf-8")


def test_same_second_nested_invocations_keep_each_owned_evidence_and_parent_final_write(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"

    parent = _run_validation(validation_root, clock="20260830-100000")
    assert parent.returncode == 0, parent.stdout + parent.stderr
    parent_directories = _run_directories(validation_root)
    assert len(parent_directories) == 1
    parent_directory = parent_directories[0]
    (parent_directory / "parent-final-write.txt").write_text("parent remains", encoding="utf-8")

    child = _run_validation(validation_root, clock="20260830-100000", mode="release", entry_only=True)
    assert child.returncode != 0
    assert "BLOCKED_4R2_REQUIRED" in child.stdout + child.stderr

    directories = _run_directories(validation_root)
    assert len(directories) == 2
    assert parent_directory.exists()
    assert (parent_directory / "parent-final-write.txt").read_text(encoding="utf-8") == "parent remains"
    invocation_ids = []
    for directory in directories:
        marker = json.loads((directory / ".owner.json").read_text(encoding="utf-8"))
        invocation_ids.append(marker["invocation_id"])
        assert (directory / "summary.json").is_file()
        assert (directory / "summary.md").is_file()
        assert any(directory.joinpath("logs").glob("*.log"))
    assert len(set(invocation_ids)) == 2


def test_different_second_nested_invocations_keep_authoritative_per_run_summaries(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"

    first = _run_validation(validation_root, clock="20260830-100000")
    second = _run_validation(validation_root, clock="20260830-100001")

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    directories = _run_directories(validation_root)
    assert len(directories) == 2
    for directory in directories:
        assert (directory / "summary.json").is_file()
        assert (directory / "summary.md").is_file()
        assert any(directory.joinpath("logs").glob("*.log"))
    summaries = [json.loads((directory / "summary.json").read_text(encoding="utf-8")) for directory in directories]
    assert {summary["mode"] for summary in summaries} == {"focused"}
    assert {summary["overall"] for summary in summaries} == {"PASS"}


def test_stale_cleanup_only_removes_old_completed_runs_inside_validation_root(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"
    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    (outside_root / "keep.txt").write_text("outside evidence", encoding="utf-8")

    _owner_marker(
        validation_root / "live-parent",
        state="running",
        invocation_id="live-parent",
    )
    _owner_marker(
        validation_root / "live-child",
        state="running",
        invocation_id="live-child",
    )
    _owner_marker(
        validation_root / "old-completed",
        state="completed",
        invocation_id="old-completed",
        ended_at="2000-01-01T00:00:00+00:00",
    )
    (validation_root / "old-completed" / "outside-path.txt").write_text(str(outside_root / "keep.txt"), encoding="utf-8")
    (validation_root / "unresolved-file").write_text("keep unresolved", encoding="utf-8")
    dangling = validation_root / "dangling-link"
    dangling.symlink_to(tmp_path / "does-not-exist", target_is_directory=True)
    link_target = tmp_path / "linked-directory"
    link_target.mkdir()
    (link_target / "keep.txt").write_text("linked evidence", encoding="utf-8")
    (validation_root / "linked-directory").symlink_to(link_target, target_is_directory=True)

    result = _run_validation(validation_root, clock="20260830-100000")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (validation_root / "live-parent").is_dir()
    assert (validation_root / "live-child").is_dir()
    assert not (validation_root / "old-completed").exists()
    assert (validation_root / "unresolved-file").is_file()
    assert dangling.is_symlink()
    assert (validation_root / "linked-directory").is_symlink()
    assert (link_target / "keep.txt").read_text(encoding="utf-8") == "linked evidence"
    assert (outside_root / "keep.txt").read_text(encoding="utf-8") == "outside evidence"
