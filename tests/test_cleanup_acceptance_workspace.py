from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "ACCEPTANCE"
    / "tools"
    / "cleanup_acceptance_workspace.py"
)
SPEC = importlib.util.spec_from_file_location("cleanup_acceptance_workspace", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
cleanup_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup_module)
CleanupError = cleanup_module.CleanupError
cleanup_workspace = cleanup_module.cleanup_workspace
initialize_workspace = cleanup_module.initialize_workspace


def test_initialize_and_itemized_cleanup(tmp_path: Path) -> None:
    root = tmp_path / "acceptance"
    target = root / "TASK-1"

    initialized = initialize_workspace(target, root, "TASK-1")
    assert initialized.executed is True
    assert (target / ".lingji-acceptance-workspace.json").is_file()

    nested = target / "logs" / "nested"
    nested.mkdir(parents=True)
    (nested / "result.log").write_text("ok", encoding="utf-8")
    (target / "artifact.zip").write_bytes(b"artifact")

    preview = cleanup_workspace(target, root, "TASK-1", execute=False)
    assert preview.executed is False
    assert preview.files == 3
    assert target.exists()

    result = cleanup_workspace(target, root, "TASK-1", execute=True)
    assert result.executed is True
    assert result.files == 3
    assert not target.exists()


def test_cleanup_refuses_target_outside_allowed_root(tmp_path: Path) -> None:
    root = tmp_path / "acceptance"
    outside = tmp_path / "outside" / "TASK-1"
    outside.mkdir(parents=True)

    with pytest.raises(CleanupError, match="direct child"):
        cleanup_workspace(outside, root, "TASK-1", execute=False, allow_unmarked_legacy=True)


def test_cleanup_refuses_task_id_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "acceptance"
    target = root / "TASK-1"
    initialize_workspace(target, root, "TASK-1")

    with pytest.raises(CleanupError, match="task_id"):
        cleanup_workspace(target, root, "TASK-2", execute=False)


def test_cleanup_refuses_symlink_inside_workspace(tmp_path: Path) -> None:
    root = tmp_path / "acceptance"
    target = root / "TASK-1"
    initialize_workspace(target, root, "TASK-1")
    external = tmp_path / "external.txt"
    external.write_text("owner", encoding="utf-8")
    link = target / "owner-link"
    try:
        link.symlink_to(external)
    except OSError:
        pytest.skip("symlink creation is not available in this environment")

    with pytest.raises(CleanupError, match="symlink or junction"):
        cleanup_workspace(target, root, "TASK-1", execute=True)
    assert external.read_text(encoding="utf-8") == "owner"


def test_registered_legacy_cleanup_is_allowed_only_for_known_entries(tmp_path: Path) -> None:
    root = tmp_path / "acceptance"
    target = root / "PR60-MEMORY-TRIAL-1c514877"
    (target / "logs").mkdir(parents=True)
    (target / "logs" / "old.log").write_text("old", encoding="utf-8")

    preview = cleanup_workspace(
        target,
        root,
        "PR60-MEMORY-QUALITY-TRIAL-1C514877",
        execute=False,
        allow_unmarked_legacy=True,
    )
    assert preview.files == 1

    (target / "unexpected-owner-data").mkdir()
    with pytest.raises(CleanupError, match="unexpected entries"):
        cleanup_workspace(
            target,
            root,
            "PR60-MEMORY-QUALITY-TRIAL-1C514877",
            execute=True,
            allow_unmarked_legacy=True,
        )
