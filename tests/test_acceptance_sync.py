from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_acceptance_sync.py"
SPEC = importlib.util.spec_from_file_location("check_acceptance_sync", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def validate(paths):
    return MODULE.validate_changed_paths(paths)


def test_docs_only_change_does_not_require_acceptance_contract() -> None:
    valid, product_changes, acceptance_changes, contracts = validate(
        ["docs/PROJECT_STATUS.md"]
    )

    assert valid is True
    assert product_changes == []
    assert acceptance_changes == []
    assert contracts == []


def test_product_change_without_acceptance_contract_fails() -> None:
    valid, product_changes, acceptance_changes, contracts = validate(
        ["src/control/api.py", "tests/test_control_api.py"]
    )

    assert valid is False
    assert product_changes == ["src/control/api.py"]
    assert acceptance_changes == []
    assert contracts == []


def test_product_change_with_legacy_acceptance_log_passes() -> None:
    valid, product_changes, acceptance_changes, contracts = validate(
        [
            "desktop/lingji-control/src/App.tsx",
            "docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md",
        ]
    )

    assert valid is True
    assert product_changes == ["desktop/lingji-control/src/App.tsx"]
    assert acceptance_changes == ["docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md"]
    assert contracts == ["docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md"]


def test_product_change_with_isolated_acceptance_entry_passes() -> None:
    valid, product_changes, acceptance_changes, contracts = validate(
        [
            "src/assistant_hub/executable_resolution.py",
            "docs/ACCEPTANCE/changes/2026-08-02-pr73-launchable-codex-command.md",
        ]
    )

    assert valid is True
    assert product_changes == ["src/assistant_hub/executable_resolution.py"]
    assert acceptance_changes == [
        "docs/ACCEPTANCE/changes/2026-08-02-pr73-launchable-codex-command.md"
    ]
    assert contracts == acceptance_changes


def test_undated_or_non_markdown_change_entry_does_not_pass() -> None:
    for path in [
        "docs/ACCEPTANCE/changes/pr73.md",
        "docs/ACCEPTANCE/changes/2026-08-02-pr73.txt",
        "docs/ACCEPTANCE/changes/README.md",
    ]:
        valid, _, acceptance_changes, contracts = validate(
            ["src/mcp_server.py", path]
        )
        assert valid is False
        assert acceptance_changes == [path]
        assert contracts == []


def test_other_acceptance_file_does_not_replace_change_contract() -> None:
    valid, _, acceptance_changes, contracts = validate(
        [
            "src/mcp_server.py",
            "docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md",
        ]
    )

    assert valid is False
    assert acceptance_changes == [
        "docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md"
    ]
    assert contracts == []


def test_workflow_and_dependency_changes_require_acceptance_contract() -> None:
    valid, product_changes, _, contracts = validate(
        [".github/workflows/tests.yml", "requirements-mcp.txt"]
    )

    assert valid is False
    assert product_changes == [
        ".github/workflows/tests.yml",
        "requirements-mcp.txt",
    ]
    assert contracts == []


def test_windows_paths_are_normalized() -> None:
    valid, product_changes, acceptance_changes, contracts = validate(
        [
            r"desktop\lingji-control\src-tauri\src\main.rs",
            r"docs\ACCEPTANCE\changes\2026-08-02-pr73-windows.md",
        ]
    )

    assert valid is True
    assert product_changes == [
        "desktop/lingji-control/src-tauri/src/main.rs"
    ]
    assert acceptance_changes == [
        "docs/ACCEPTANCE/changes/2026-08-02-pr73-windows.md"
    ]
    assert contracts == acceptance_changes


def test_test_only_change_does_not_force_acceptance_update() -> None:
    valid, product_changes, acceptance_changes, contracts = validate(
        ["tests/test_memory.py"]
    )

    assert valid is True
    assert product_changes == []
    assert acceptance_changes == []
    assert contracts == []
