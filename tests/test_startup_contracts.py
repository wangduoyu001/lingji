"""Behavior-oriented startup contracts for LingJi entry points.

These tests deliberately inspect syntax and configuration behavior instead of
comparing complete source files, comments, whitespace or snapshots.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from src.config import Settings


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = (
    "main.py",
    "run_service.py",
    "run_control_api.py",
    "run_mcp_server.py",
    "run_extraction_worker.py",
)
WINDOWS_ABSOLUTE = re.compile(r"[A-Za-z]:[\\/]")
MACHINE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]Users[\\/]|D:[\\/]codex[\\/])", re.IGNORECASE)


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8-sig")


def _tree(relative_path: str) -> ast.Module:
    return ast.parse(_source(relative_path), filename=relative_path)


def _is_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    compare = node.test
    if len(compare.ops) != 1 or not isinstance(compare.ops[0], ast.Eq):
        return False
    values = [compare.left, *compare.comparators]
    has_name = any(isinstance(value, ast.Name) and value.id == "__name__" for value in values)
    has_main = any(isinstance(value, ast.Constant) and value.value == "__main__" for value in values)
    return has_name and has_main


def _attribute_chain(node: ast.AST) -> str:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _top_level_calls(tree: ast.Module) -> set[str]:
    calls: set[str] = set()
    for statement in tree.body:
        if _is_main_guard(statement):
            continue
        for node in ast.walk(statement):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(node, ast.Call):
                name = _attribute_chain(node.func)
                if name:
                    calls.add(name)
    return calls


def test_all_startup_entrypoints_have_main_guards():
    for relative_path in ENTRYPOINTS:
        assert any(_is_main_guard(node) for node in _tree(relative_path).body), relative_path


def test_import_phase_does_not_start_services():
    forbidden_suffixes = (".start", ".run_forever", ".serve", ".run_until_complete")
    for relative_path in ENTRYPOINTS:
        calls = _top_level_calls(_tree(relative_path))
        offenders = sorted(
            call
            for call in calls
            if call == "main" or call.endswith(forbidden_suffixes)
        )
        assert offenders == [], f"{relative_path} starts runtime work during import: {offenders}"


def test_startup_entrypoints_do_not_contain_machine_specific_paths():
    for relative_path in ENTRYPOINTS:
        source = _source(relative_path)
        assert MACHINE_PATH.search(source) is None, relative_path


def test_port_contract_is_owned_by_settings():
    settings = Settings(_env_file=None)
    assert settings.compatibility_api_port == 8765
    assert settings.control_api_port == 8766
    assert settings.mcp_port == 8767
    assert len(
        {
            settings.compatibility_api_port,
            settings.control_api_port,
            settings.mcp_port,
        }
    ) == 3


def test_control_api_passes_settings_host_and_port_to_uvicorn():
    tree = _tree("run_control_api.py")
    uvicorn_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _attribute_chain(node.func) == "uvicorn.run"
    ]
    assert len(uvicorn_calls) == 1
    keywords = {keyword.arg: _attribute_chain(keyword.value) for keyword in uvicorn_calls[0].keywords}
    assert keywords["host"] == "settings.control_api_host"
    assert keywords["port"] == "settings.control_api_port"


def test_mcp_entrypoint_resolves_runtime_from_settings():
    tree = _tree("run_mcp_server.py")
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _attribute_chain(node.func) == "resolve_mcp_runtime_config"
    ]
    assert len(calls) == 1
    assert calls[0].args
    assert _attribute_chain(calls[0].args[0]) == "settings"


def test_startup_files_do_not_hardcode_service_ports():
    allowed_config_file = ROOT / "src/config.py"
    assert allowed_config_file.is_file()
    for relative_path in ENTRYPOINTS:
        source = _source(relative_path)
        for port in (8765, 8766, 8767):
            assert str(port) not in source, f"{relative_path} hardcodes port {port}"


def test_no_startup_file_embeds_an_absolute_windows_path():
    for relative_path in ENTRYPOINTS:
        source = _source(relative_path)
        assert WINDOWS_ABSOLUTE.search(source) is None, relative_path
