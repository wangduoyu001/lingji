from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_acceptance_sync.py"
SPEC = importlib.util.spec_from_file_location("check_acceptance_sync", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_docs_only_change_does_not_require_acceptance_log() -> None:
    valid, product_changes, acceptance_changes = MODULE.validate_changed_paths(
        ["docs/PROJECT_STATUS.md"]
    )

    assert valid is True
    assert product_changes == []
    assert acceptance_changes == []


def test_product_change_without_acceptance_log_fails() -> None:
    valid, product_changes, acceptance_changes = MODULE.validate_changed_paths(
        ["src/control/api.py", "tests/test_control_api.py"]
    )

    assert valid is False
    assert product_changes == ["src/control/api.py"]
    assert acceptance_changes == []


def test_product_change_with_acceptance_log_passes() -> None:
    valid, product_changes, acceptance_changes = MODULE.validate_changed_paths(
        [
            "desktop/lingji-control/src/App.tsx",
            "docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md",
        ]
    )

    assert valid is True
    assert product_changes == ["desktop/lingji-control/src/App.tsx"]
    assert acceptance_changes == ["docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md"]


def test_other_acceptance_file_does_not_replace_change_log() -> None:
    valid, _, acceptance_changes = MODULE.validate_changed_paths(
        [
            "src/mcp_server.py",
            "docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md",
        ]
    )

    assert valid is False
    assert acceptance_changes == [
        "docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md"
    ]


def test_workflow_and_dependency_changes_require_acceptance_log() -> None:
    valid, product_changes, _ = MODULE.validate_changed_paths(
        [".github/workflows/tests.yml", "requirements-mcp.txt"]
    )

    assert valid is False
    assert product_changes == [
        ".github/workflows/tests.yml",
        "requirements-mcp.txt",
    ]


def test_windows_paths_are_normalized() -> None:
    valid, product_changes, acceptance_changes = MODULE.validate_changed_paths(
        [
            r"desktop\lingji-control\src-tauri\src\main.rs",
            r"docs\ACCEPTANCE\CHANGE_ACCEPTANCE_LOG.md",
        ]
    )

    assert valid is True
    assert product_changes == [
        "desktop/lingji-control/src-tauri/src/main.rs"
    ]
    assert acceptance_changes == [
        "docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md"
    ]


def test_test_only_change_does_not_force_acceptance_update() -> None:
    valid, product_changes, acceptance_changes = MODULE.validate_changed_paths(
        ["tests/test_memory.py"]
    )

    assert valid is True
    assert product_changes == []
    assert acceptance_changes == []
