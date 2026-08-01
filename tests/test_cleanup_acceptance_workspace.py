from __future__ import annotations

from pathlib import Path

import pytest

from scripts.cleanup_acceptance_workspace import CleanupError, cleanup, validate_target


def test_refuses_cleanup_root_itself(tmp_path: Path) -> None:
    root = tmp_path / "LingJiAcceptance"
    with pytest.raises(CleanupError, match="root itself"):
        validate_target(root, root, "PR60-MEMORY-QUALITY-TRIAL-D69874AF")


def test_refuses_target_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "LingJiAcceptance"
    target = tmp_path / "other" / "PR60-MEMORY-TRIAL-1c514877"
    with pytest.raises(CleanupError, match="outside"):
        validate_target(root, target, "PR60-MEMORY-QUALITY-TRIAL-D69874AF")


def test_refuses_non_authorized_target(tmp_path: Path) -> None:
    root = tmp_path / "LingJiAcceptance"
    target = root / "Production"
    with pytest.raises(CleanupError, match="not authorized"):
        validate_target(root, target, "PR60-MEMORY-QUALITY-TRIAL-D69874AF")


def test_refuses_unsupported_task_id(tmp_path: Path) -> None:
    root = tmp_path / "LingJiValidation"
    target = root / "PR60-CODE-a90a18a6"
    with pytest.raises(CleanupError, match="unsupported cleanup task id"):
        validate_target(root, target, "PR60-UNKNOWN-A90A18A6")


def test_refuses_wrong_root_family(tmp_path: Path) -> None:
    root = tmp_path / "LingJiAcceptance"
    target = root / "PR60-CODE-a90a18a6"
    with pytest.raises(CleanupError, match="LingJiValidation"):
        validate_target(root, target, "PR60-CODE-RELEASE-VALIDATION-A90A18A6")


def test_code_release_validation_target_is_authorized(tmp_path: Path) -> None:
    root = tmp_path / "LingJiValidation"
    target = root / "PR60-CODE-a90a18a6"

    resolved_root, resolved_target = validate_target(
        root,
        target,
        "PR60-CODE-RELEASE-VALIDATION-A90A18A6",
    )

    assert resolved_root == root.resolve()
    assert resolved_target == target.resolve()


def test_code_release_validation_requires_matching_identity(tmp_path: Path) -> None:
    root = tmp_path / "LingJiValidation"
    target = root / "PR60-CODE-a90a18a6"
    with pytest.raises(CleanupError, match="not authorized"):
        validate_target(
            root,
            target,
            "PR60-CODE-RELEASE-VALIDATION-FFFFFFFF",
        )


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


def test_execute_removes_only_authorized_validation_target(tmp_path: Path) -> None:
    root = tmp_path / "LingJiValidation"
    target = root / "PR60-CODE-a90a18a6"
    protected = root / "unrelated-owner-data"
    (target / "artifact").mkdir(parents=True)
    (target / "artifact" / "build.zip").write_bytes(b"zip")
    protected.mkdir(parents=True)
    (protected / "keep.txt").write_text("keep", encoding="utf-8")

    resolved_root, resolved_target = validate_target(
        root,
        target,
        "PR60-CODE-RELEASE-VALIDATION-A90A18A6",
    )
    result = cleanup(resolved_root, resolved_target, execute=True)

    assert result.executed is True
    assert result.remaining == []
    assert not target.exists()
    assert (protected / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_memory_target_requires_matching_task_identity(tmp_path: Path) -> None:
    root = tmp_path / "LingJiAcceptance"
    target = root / "PR60-MEMORY-TRIAL-d69874af"
    with pytest.raises(CleanupError, match="not authorized"):
        validate_target(root, target, "PR60-MEMORY-QUALITY-TRIAL-1C514877")
