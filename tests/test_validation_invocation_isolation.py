from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
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
    output_hint: str = "isolation-test",
    output_root: Path | str | None = None,
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
        str(output_root or validation_root),
        "--output-hint",
        output_hint,
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


def _start_held_validation(validation_root: Path, *, clock: str) -> subprocess.Popen[str]:
    powershell = Path(_powershell())
    environment = os.environ.copy()
    environment["LINGJI_VALIDATE_TEST_CLOCK"] = clock
    environment["PATH"] = str(powershell.parent) + os.pathsep + environment.get("PATH", "")
    return subprocess.Popen(
        [
            sys.executable,
            str(VALIDATION_LAUNCHER),
            "--mode",
            "focused",
            "--area",
            "docs",
            "--python-command",
            sys.executable,
            "--output-root",
            str(validation_root),
            "--output-hint",
            "held-parent",
            "--hold-for-test",
        ],
        cwd=REPO_ROOT,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _run_directories(validation_root: Path) -> list[Path]:
    return sorted(path for path in validation_root.iterdir() if path.is_dir())


def _read_until(process: subprocess.Popen[str], needle: str) -> str:
    assert process.stdout is not None
    while True:
        line = process.stdout.readline()
        assert line, "held validation exited before reaching its barrier"
        if needle in line:
            return line


def _owner_marker(path: Path, *, state: str, invocation_id: str, ended_at: str | None = None) -> None:
    marker = {
        "schema_version": 1,
        "invocation_id": invocation_id,
        "state": state,
        "process_id": 2147483647,
        "process_started_at": "2000-01-01T00:00:00+00:00",
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


@pytest.mark.parametrize(
    ("parent_clock", "child_clock"),
    [("20260830-100000", "20260830-100000"), ("20260830-100000", "20260830-100001")],
)
def test_live_parent_survives_nested_entry_only_without_sleep(
    tmp_path: Path, parent_clock: str, child_clock: str
) -> None:
    validation_root = tmp_path / "validation"
    parent = _start_held_validation(validation_root, clock=parent_clock)
    try:
        _read_until(parent, "LINGJI_VALIDATE_TEST_BARRIER_ENTERED")
        parent_directories = _run_directories(validation_root)
        assert len(parent_directories) == 1
        parent_directory = parent_directories[0]
        parent_marker = json.loads((parent_directory / ".owner.json").read_text(encoding="utf-8"))
        assert parent_marker["state"] == "running"

        child = _run_validation(validation_root, clock=child_clock, mode="release", entry_only=True)
        assert child.returncode != 0
        assert "BLOCKED_4R2_REQUIRED" in child.stdout + child.stderr
        (parent_directory / "parent-final-write.txt").write_text("parent final write", encoding="utf-8")
        assert parent_directory.exists()
        assert (parent_directory / "parent-final-write.txt").read_text(encoding="utf-8") == "parent final write"

        directories = _run_directories(validation_root)
        assert len(directories) == 2
        invocation_ids = [json.loads((directory / ".owner.json").read_text(encoding="utf-8"))["invocation_id"] for directory in directories]
        assert len(set(invocation_ids)) == 2

        assert parent.stdin is not None
        parent.stdin.write("\n")
        parent.stdin.flush()
        parent.stdin.close()
        assert parent.wait(timeout=20) == 0
        assert (parent_directory / "summary.json").is_file()
        assert (parent_directory / "summary.md").is_file()
        assert any(parent_directory.joinpath("logs").glob("*.log"))
    finally:
        if parent.poll() is None:
            if parent.stdin is not None:
                parent.stdin.write("\n")
                parent.stdin.flush()
                parent.stdin.close()
            parent.wait(timeout=20)


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
    valid_id = uuid.uuid4().hex
    valid_directory = validation_root / f"old-completed-{valid_id}-focused"
    _owner_marker(
        valid_directory,
        state="completed",
        invocation_id=valid_id,
        ended_at="2000-01-01T00:00:00+00:00",
    )
    (valid_directory / "outside-path.txt").write_text(str(outside_root / "keep.txt"), encoding="utf-8")
    (validation_root / "unresolved-file").write_text("keep unresolved", encoding="utf-8")
    dangling = validation_root / "dangling-link"
    dangling.symlink_to(tmp_path / "does-not-exist", target_is_directory=True)
    link_target = tmp_path / "linked-directory"
    link_target.mkdir()
    (link_target / "keep.txt").write_text("linked evidence", encoding="utf-8")
    (validation_root / "linked-directory").symlink_to(link_target, target_is_directory=True)

    result = _run_validation(f"{validation_root}{os.sep}", clock="20260830-100000")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (validation_root / "live-parent").is_dir()
    assert (validation_root / "live-child").is_dir()
    assert not valid_directory.exists()
    assert (validation_root / "unresolved-file").is_file()
    assert dangling.is_symlink()
    assert (validation_root / "linked-directory").is_symlink()
    assert (link_target / "keep.txt").read_text(encoding="utf-8") == "linked evidence"
    assert (outside_root / "keep.txt").read_text(encoding="utf-8") == "outside evidence"


def _start_active_process() -> tuple[subprocess.Popen[str], dict[str, str]]:
    powershell = Path(_powershell())
    command = (
        "$process = Get-Process -Id $PID; "
        "[ordered]@{process_id=[int]$PID; process_started_at=$process.StartTime.ToUniversalTime().ToString('o')} "
        "| ConvertTo-Json -Compress; [Console]::Out.Flush(); [Console]::ReadLine() | Out-Null"
    )
    process = subprocess.Popen(
        [str(powershell), "-NoProfile", "-Command", command],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    line = process.stdout.readline()
    assert line
    return process, json.loads(line)


def test_active_pid_and_pid_reuse_are_retained_fail_closed(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"
    process, identity = _start_active_process()
    try:
        active_id = uuid.uuid4().hex
        active = validation_root / f"active-{active_id}-focused"
        _owner_marker(
            active,
            state="completed",
            invocation_id=active_id,
            ended_at="2000-01-01T00:00:00+00:00",
        )
        active_marker = json.loads((active / ".owner.json").read_text(encoding="utf-8"))
        active_marker["process_id"] = int(identity["process_id"])
        active_marker["process_started_at"] = identity["process_started_at"]
        (active / ".owner.json").write_text(json.dumps(active_marker), encoding="utf-8")

        reused_id = uuid.uuid4().hex
        reused = validation_root / f"reused-{reused_id}-focused"
        _owner_marker(
            reused,
            state="completed",
            invocation_id=reused_id,
            ended_at="2000-01-01T00:00:00+00:00",
        )
        reused_marker = json.loads((reused / ".owner.json").read_text(encoding="utf-8"))
        reused_marker["process_id"] = int(identity["process_id"])
        reused_marker["process_started_at"] = "2000-01-01T00:00:00+00:00"
        (reused / ".owner.json").write_text(json.dumps(reused_marker), encoding="utf-8")

        result = _run_validation(validation_root, clock="20260830-100000")

        assert result.returncode == 0, result.stdout + result.stderr
        assert active.is_dir()
        assert reused.is_dir()
    finally:
        assert process.stdin is not None
        process.stdin.write("\n")
        process.stdin.flush()
        process.stdin.close()
        process.wait(timeout=20)


def test_per_run_root_reparse_swap_never_writes_outside(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("untouched", encoding="utf-8")
    parent = _start_held_validation(validation_root, clock="20260830-100000")
    try:
        _read_until(parent, "LINGJI_VALIDATE_TEST_BARRIER_ENTERED")
        parent_directory = _run_directories(validation_root)[0]
        moved_directory = tmp_path / "moved-parent"
        parent_directory.rename(moved_directory)
        parent_directory.symlink_to(outside, target_is_directory=True)

        assert parent.stdin is not None
        parent.stdin.write("\n")
        parent.stdin.flush()
        parent.stdin.close()
        assert parent.wait(timeout=20) != 0
        assert sentinel.read_text(encoding="utf-8") == "untouched"
        assert parent_directory.is_symlink()
        assert not (outside / "logs").exists()
    finally:
        if parent.poll() is None:
            if parent.stdin is not None:
                parent.stdin.write("\n")
                parent.stdin.flush()
                parent.stdin.close()
            parent.wait(timeout=20)


@pytest.mark.parametrize("pointer_name", ["latest-summary.json", "latest-summary.md"])
def test_latest_summary_symlink_never_writes_outside_validation_root(tmp_path: Path, pointer_name: str) -> None:
    validation_root = tmp_path / "validation"
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / pointer_name
    sentinel.write_text("outside sentinel", encoding="utf-8")
    validation_root.mkdir()
    (validation_root / pointer_name).symlink_to(sentinel)

    result = _run_validation(validation_root, clock="20260830-100000")

    assert result.returncode != 0
    assert sentinel.read_text(encoding="utf-8") == "outside sentinel"
    assert (validation_root / pointer_name).is_symlink()


def test_selected_validation_root_symlink_fails_closed(tmp_path: Path) -> None:
    real_root = tmp_path / "real-validation"
    real_root.mkdir()
    linked_root = tmp_path / "linked-validation"
    linked_root.symlink_to(real_root, target_is_directory=True)
    sentinel = tmp_path / "outside-sentinel.txt"
    sentinel.write_text("untouched", encoding="utf-8")

    result = _run_validation(linked_root, clock="20260830-100000")

    assert result.returncode != 0
    assert list(real_root.iterdir()) == []
    assert sentinel.read_text(encoding="utf-8") == "untouched"

def test_malformed_foreign_and_nonpositive_owner_markers_are_retained(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"
    malformed = validation_root / "malformed-marker"
    malformed.mkdir(parents=True)
    (malformed / ".owner.json").write_text(
        json.dumps({"state": "completed", "process_id": 2147483647, "ended_at": "2000-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    nonpositive = validation_root / "nonpositive-marker"
    _owner_marker(nonpositive, state="completed", invocation_id=uuid.uuid4().hex, ended_at="2000-01-01T00:00:00+00:00")
    (nonpositive / ".owner.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "invocation_id": json.loads((nonpositive / ".owner.json").read_text(encoding="utf-8"))["invocation_id"],
                "process_id": 0,
                "process_started_at": "2000-01-01T00:00:00+00:00",
                "state": "completed",
                "started_at": "2000-01-01T00:00:00+00:00",
                "ended_at": "2000-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    foreign_id = uuid.uuid4().hex
    foreign = validation_root / f"foreign-{uuid.uuid4().hex}-focused"
    _owner_marker(foreign, state="completed", invocation_id=foreign_id, ended_at="2000-01-01T00:00:00+00:00")
    typed_id = uuid.uuid4().hex
    typed = validation_root / f"typed-{typed_id}-focused"
    _owner_marker(typed, state="completed", invocation_id=typed_id, ended_at="2000-01-01T00:00:00+00:00")
    typed_marker = json.loads((typed / ".owner.json").read_text(encoding="utf-8"))
    typed_marker["process_id"] = str(typed_marker["process_id"])
    (typed / ".owner.json").write_text(json.dumps(typed_marker), encoding="utf-8")
    oversized_id = uuid.uuid4().hex
    oversized = validation_root / f"oversized-{oversized_id}-focused"
    _owner_marker(oversized, state="completed", invocation_id=oversized_id, ended_at="2000-01-01T00:00:00+00:00")
    (oversized / ".owner.json").write_text("{" + ("x" * 5000) + "}", encoding="utf-8")

    result = _run_validation(validation_root, clock="20260830-100000")

    assert result.returncode == 0, result.stdout + result.stderr
    assert malformed.is_dir()
    assert nonpositive.is_dir()
    assert foreign.is_dir()
    assert typed.is_dir()
    assert oversized.is_dir()
