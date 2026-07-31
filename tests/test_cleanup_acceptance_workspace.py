from __future__ import annotations

from pathlib import Path

import pytest

from scripts.cleanup_acceptance_workspace import CleanupError, cleanup, validate_target


def test_refuses_acceptance_root_itself(tmp_path: Path) -> None:
    with pytest.raises(CleanupError):
        validate_target(tmp_path, tmp_path, "PR60-MEMORY-QUALITY-TRIAL-D69874AF")


def test_refuses_target_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = tmp_path / "other" / "PR60-MEMORY-TRIAL-1c514877"
    with pytest.raises(CleanupError):
        validate_target(root, target, "PR60-MEMORY-QUALITY-TRIAL-D69874AF")


def test_refuses_non_allowlisted_target(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = root / "Production"
    with pytest.raises(CleanupError):
        validate_target(root, target, "PR60-MEMORY-QUALITY-TRIAL-D69874AF")


def test_dry_run_reports_without_deleting(tmp_path: Path) -> None:
    root = tmp_path / "LingJiAcceptance"
    target = root / "PR60-MEMORY-TRIAL-1c514877"
    (target / "logs").mkdir(parents=True)
    (target / "logs" / "run.log").write_text("ok", encoding="utf-8")

    resolved_root, resolved_target = validate_target(
        root, target, "PR60-MEMORY-QUALITY-TRIAL-D69874AF"
    )
    result = cleanup(resolved_root, resolved_target, execute=False)

    assert result.existed is True
    assert result.executed is False
    assert target.exists()
    assert "PR60-MEMORY-TRIAL-1c514877/logs/run.log" in result.remaining


def test_execute_removes_only_allowlisted_target(tmp_path: Path) -> None:
    root = tmp_path / "LingJiAcceptance"
    target = root / "PR60-MEMORY-TRIAL-1c514877"
    protected = root / "unrelated-owner-data"
    (target / "artifact").mkdir(parents=True)
    (target / "artifact" / "build.zip").write_bytes(b"zip")
    protected.mkdir(parents=True)
    (protected / "keep.txt").write_text("keep", encoding="utf-8")

    resolved_root, resolved_target = validate_target(
        root, target, "PR60-MEMORY-QUALITY-TRIAL-D69874AF"
    )
    result = cleanup(resolved_root, resolved_target, execute=True)

    assert result.executed is True
    assert result.remaining == []
    assert not target.exists()
    assert (protected / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_current_target_requires_matching_task_identity(tmp_path: Path) -> None:
    root = tmp_path / "LingJiAcceptance"
    target = root / "PR60-MEMORY-TRIAL-d69874af"
    with pytest.raises(CleanupError):
        validate_target(root, target, "PR60-MEMORY-QUALITY-TRIAL-1C514877")
