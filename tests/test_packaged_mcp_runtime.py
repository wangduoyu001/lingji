from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from run_packaged_control_api import (
    _ensure_mcp_token,
    _install_mcp_state,
    configure_packaged_environment,
    mcp_state_path,
    mcp_token_path,
    packaged_runtime_contract,
)


@pytest.fixture
def runtime_tmp_path(tmp_path: Path):
    if os.name != "nt":
        yield tmp_path
        return
    parent = Path.cwd() / "output" / "test-mcp-runtime"
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_packaged_contract_adds_backward_compatible_managed_mcp(runtime_tmp_path: Path) -> None:
    root = runtime_tmp_path / "LingJi" / "acceptance"
    contract = packaged_runtime_contract(root, workspace="acceptance")

    assert contract["schema_version"] == 2
    assert contract["mode"] == "packaged_sidecar"
    assert contract["workspace"] == "acceptance"
    assert contract["mcp"] == {
        "managed": True,
        "host": "127.0.0.1",
        "port": 8767,
        "url": "http://127.0.0.1:8767/mcp",
        "transport": "streamable-http",
        "authentication": "bearer_token",
        "token_file": str(mcp_token_path(root)),
        "state_file": str(mcp_state_path(root)),
        "loopback_only": True,
        "automatic_core_memory_write": False,
    }


def test_packaged_environment_configures_loopback_mcp_without_changing_control_api(
    runtime_tmp_path: Path,
) -> None:
    environ: dict[str, str] = {}
    values = configure_packaged_environment(
        runtime_tmp_path / "LingJi" / "production",
        workspace="production",
        environ=environ,
    )

    assert values["CONTROL_API_HOST"] == "127.0.0.1"
    assert values["CONTROL_API_PORT"] == "8766"
    assert values["MCP_HOST"] == "127.0.0.1"
    assert values["MCP_PORT"] == "8767"
    assert values["MCP_TRANSPORT"] == "streamable-http"


def test_packaged_mcp_token_is_generated_once_and_kept_outside_install_dir(
    runtime_tmp_path: Path,
) -> None:
    root = runtime_tmp_path / "LingJi" / "production"
    configure_packaged_environment(root, workspace="production", environ={})

    first = _ensure_mcp_token(root.resolve())
    second = _ensure_mcp_token(root.resolve())

    assert first == second
    assert len(first) >= 32
    assert mcp_token_path(root).read_text(encoding="utf-8").strip() == first
    assert mcp_token_path(root).is_relative_to(root.resolve())


def test_packaged_mcp_state_records_parent_and_authenticated_loopback_identity(
    runtime_tmp_path: Path,
) -> None:
    root = runtime_tmp_path / "LingJi" / "acceptance"
    configure_packaged_environment(root, workspace="acceptance", environ={})

    _install_mcp_state(root.resolve(), parent_pid=4321, workspace="acceptance")
    payload = json.loads(mcp_state_path(root).read_text(encoding="utf-8"))

    assert payload["mode"] == "packaged_mcp_http"
    assert payload["workspace"] == "acceptance"
    assert payload["parent_pid"] == 4321
    assert payload["host"] == "127.0.0.1"
    assert payload["port"] == 8767
    assert payload["url"] == "http://127.0.0.1:8767/mcp"
    assert payload["authenticated"] is True
