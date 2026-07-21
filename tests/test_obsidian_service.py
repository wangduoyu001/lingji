from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.obsidian import (
    DISCOVERY_RUNTIME_SETTINGS,
    OBSIDIAN_CLI_NOT_FOUND,
    ObsidianCliClient,
    ObsidianService,
    display_path,
)


class RuntimeSettingsStub:
    def __init__(self, values):
        self.values = dict(values)

    def snapshot(self):
        return {"values": dict(self.values)}


class ClientStub:
    def __init__(self, config):
        self.config = config

    def get_version(self):
        return "1.9.0"


def service(tmp_path: Path, values: dict, *, client_factory=ClientStub):
    vault = tmp_path / "private" / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    settings = SimpleNamespace(vault_path=vault)
    return ObsidianService(
        settings,
        runtime_settings=RuntimeSettingsStub(values),
        environ={"PATH": ""},
        platform="win32",
        client_factory=client_factory,
    )


def test_runtime_cli_path_has_priority_and_status_is_sanitized(tmp_path):
    cli = tmp_path / "private" / "Obsidian" / "Obsidian.com"
    cli.parent.mkdir(parents=True)
    cli.write_text("stub", encoding="utf-8")
    obsidian = service(
        tmp_path,
        {
            "obsidian_cli_enabled": True,
            "obsidian_cli_path": str(cli),
            "obsidian_vault_name": "工作知识库",
            "obsidian_cli_timeout_seconds": 22,
            "obsidian_cli_dry_run": False,
        },
    )

    status = obsidian.status()

    assert status["state"] == "healthy"
    assert status["version"] == "1.9.0"
    assert status["cli_discovery_source"] == DISCOVERY_RUNTIME_SETTINGS
    assert status["vault_discovery_source"] == "workspace"
    assert status["timeout_seconds"] == 22
    assert status["vault_name"] == "工作知识库"
    assert str(tmp_path) not in status["cli_path_display"]
    assert str(tmp_path) not in status["vault_path_display"]
    assert "cli_path" not in status
    assert "vault_path" not in status


def test_missing_cli_is_configuration_required(tmp_path):
    status = service(tmp_path, {"obsidian_cli_enabled": True}).status()

    assert status["state"] == "configuration_required"
    assert status["available"] is False
    assert status["issues"][0]["code"] == OBSIDIAN_CLI_NOT_FOUND


def test_disabled_status_does_not_claim_failure(tmp_path):
    status = service(tmp_path, {"obsidian_cli_enabled": False}).status()

    assert status["state"] == "disabled"
    assert status["issues"] == []
    assert status["capabilities"]["read"] is False
    assert status["capabilities"]["write"] is False


def test_validate_configuration_is_non_persistent_and_rejects_foreign_keys(tmp_path):
    obsidian = service(tmp_path, {"obsidian_cli_enabled": False})

    result = obsidian.validate_configuration({"obsidian_cli_enabled": False})
    assert result["persisted"] is False
    assert result["state"] == "disabled"

    with pytest.raises(KeyError):
        obsidian.validate_configuration({"storage_max_gb": 1})


def test_display_path_supports_windows_and_posix_without_full_parent():
    assert display_path(r"D:\Users\owner\Vault") == "…/owner/Vault"
    assert display_path("/home/owner/Vault") == "…/owner/Vault"


def test_client_path_contract_blocks_escape_and_absolute_paths():
    assert ObsidianCliClient.validate_path("Projects/LingJi.md") is True
    assert ObsidianCliClient.validate_path("../outside.md") is False
    assert ObsidianCliClient.validate_path(r"C:\outside.md") is False
    assert ObsidianCliClient.validate_path("/outside.md") is False
