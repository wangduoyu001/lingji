from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

import pytest

from src.assistant_hub import AiMemoryConnectorService, ConnectorError


def test_explicit_empty_environment_does_not_inherit_machine_codex_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_codex_home = tmp_path / "owner-codex"
    owner_config = owner_codex_home / "config.toml"
    owner_config.parent.mkdir(parents=True)
    owner_original = 'model = "owner-model"\n'
    owner_config.write_text(owner_original, encoding="utf-8")

    isolated_home = tmp_path / "isolated-home"
    storage = tmp_path / "storage"
    monkeypatch.setenv("CODEX_HOME", str(owner_codex_home))

    service = AiMemoryConnectorService(storage_path=storage, home=isolated_home, env={})
    service.apply("codex", "CONNECT_CODEX_TO_LINGJI")

    isolated_config = isolated_home / ".codex" / "config.toml"
    assert isolated_config.is_file()
    assert "lingji-memory" in isolated_config.read_text(encoding="utf-8")
    assert owner_config.read_text(encoding="utf-8") == owner_original
    assert service.env == {}


def test_codex_preview_apply_and_rollback_preserve_existing_config(tmp_path: Path) -> None:
    home = tmp_path / "home"
    storage = tmp_path / "storage"
    config = home / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('model = "gpt-5"\napproval_policy = "on-request"\n', encoding="utf-8")
    service = AiMemoryConnectorService(storage_path=storage, home=home, env={})

    preview = service.preview("codex")
    assert preview["supported"] is True
    assert preview["conflict"] is False
    assert "<本机令牌已隐藏>" in preview["preview"]
    assert "Bearer " not in preview["preview"].replace("Bearer <本机令牌已隐藏>", "")

    result = service.apply("codex", "CONNECT_CODEX_TO_LINGJI")
    assert result["state"] == "configured"
    updated = config.read_text(encoding="utf-8")
    parsed = tomllib.loads(updated)
    assert parsed["model"] == "gpt-5"
    assert parsed["approval_policy"] == "on-request"
    assert parsed["mcp_servers"]["lingji-memory"]["url"] == "http://127.0.0.1:8767/mcp"
    assert parsed["mcp_servers"]["lingji-memory"]["enabled"] is True
    assert "Authorization" in parsed["mcp_servers"]["lingji-memory"]["http_headers"]
    backups = list((storage / "assistant_hub" / "connector_backups" / "codex").glob("*.bak"))
    assert len(backups) == 1

    rolled_back = service.rollback("codex", "DISCONNECT_CODEX_FROM_LINGJI")
    assert rolled_back["state"] == "disconnected"
    restored = config.read_text(encoding="utf-8")
    assert 'model = "gpt-5"' in restored
    assert 'approval_policy = "on-request"' in restored
    assert "lingji-memory" not in restored


def test_codex_refuses_external_same_name_configuration(tmp_path: Path) -> None:
    home = tmp_path / "home"
    config = home / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[mcp_servers.lingji-memory]\nurl = "http://example.invalid/mcp"\n',
        encoding="utf-8",
    )
    service = AiMemoryConnectorService(storage_path=tmp_path / "storage", home=home, env={})

    preview = service.preview("codex")
    assert preview["conflict"] is True
    with pytest.raises(ConnectorError) as error:
        service.apply("codex", "CONNECT_CODEX_TO_LINGJI")
    assert error.value.code == "CONFIG_CONFLICT"
    assert "example.invalid" in config.read_text(encoding="utf-8")


def test_apply_requires_exact_confirmation(tmp_path: Path) -> None:
    service = AiMemoryConnectorService(
        storage_path=tmp_path / "storage",
        home=tmp_path / "home",
        env={},
    )
    with pytest.raises(ConnectorError) as error:
        service.apply("codex", "yes")
    assert error.value.code == "CONFIRMATION_REQUIRED"
    assert error.value.status_code == 403


def test_workbuddy_returns_copy_only_authenticated_http_config(tmp_path: Path) -> None:
    service = AiMemoryConnectorService(
        storage_path=tmp_path / "storage",
        home=tmp_path / "home",
        env={},
    )
    preview = service.preview("workbuddy")
    assert preview["mode"] == "copy_configuration"
    assert "<本机令牌已隐藏>" in preview["preview"]
    assert "copy_payload" not in preview

    result = service.apply("workbuddy", "COPY_WORKBUDDY_LINGJI_CONFIG")
    payload = json.loads(result["copy_payload"])
    connector = payload["mcpServers"]["lingji-memory"]
    assert connector["type"] == "http"
    assert connector["url"] == "http://127.0.0.1:8767/mcp"
    assert connector["headers"]["Authorization"].startswith("Bearer ")
    assert result["state"] == "manual_action_required"


def test_claude_uses_only_official_cli_commands_and_records_management(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def runner(command, timeout):
        commands.append(list(command))
        if command[1:4] == ["mcp", "get", "lingji-memory"]:
            return subprocess.CompletedProcess(command, 1, "", "not found")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(
        "src.assistant_hub.connectors.shutil.which",
        lambda name, path=None: "C:/Tools/claude.exe" if name == "claude" else None,
    )
    service = AiMemoryConnectorService(
        storage_path=tmp_path / "storage",
        home=tmp_path / "home",
        env={"PATH": "C:/Tools"},
        runner=runner,
    )

    preview = service.preview("claude_code")
    assert preview["supported"] is True
    assert "claude.exe mcp add" in preview["preview"]
    assert "<本机令牌已隐藏>" in preview["preview"]

    result = service.apply("claude_code", "CONNECT_CLAUDE_TO_LINGJI")
    assert result["state"] == "configured"
    assert commands[0][1:] == ["mcp", "get", "lingji-memory"]
    add = commands[1]
    assert add[1:5] == ["mcp", "add", "--transport", "http"]
    assert "--scope" in add and "user" in add
    assert "--header" in add
    assert add[-2:] == ["lingji-memory", "http://127.0.0.1:8767/mcp"]
    assert service.status()["connectors"][1]["managed_by_lingji"] is True


def test_unsupported_connector_is_rejected(tmp_path: Path) -> None:
    service = AiMemoryConnectorService(
        storage_path=tmp_path / "storage",
        home=tmp_path / "home",
        env={},
    )
    with pytest.raises(ConnectorError) as error:
        service.preview("random-ai")
    assert error.value.code == "UNSUPPORTED_CONNECTOR"
    assert error.value.status_code == 404


def test_codex_config_without_command_is_blocked_not_connected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.assistant_hub.connectors.shutil.which", lambda name, path=None: None)
    monkeypatch.setattr("src.assistant_hub.governed.shutil.which", lambda name, path=None: None)
    service = AiMemoryConnectorService(
        storage_path=tmp_path / "storage",
        home=tmp_path / "home",
        env={},
    )
    monkeypatch.setattr(service, "_runtime_ready", lambda: True)
    service.apply("codex", "CONNECT_CODEX_TO_LINGJI")

    result = service.test("codex")
    assert result["ok"] is False
    assert result["state"] == "blocked"
    assert "找不到 codex 命令" in result["message"]

    status = service.status()["connectors"][0]
    assert status["configuration_state"] == "configured"
    assert status["status_state"] == "blocked"
    assert status["client_available"] is False
    assert status["live_test"] is False
    assert "配置文件已写入" in status["blocking_reason"]


def test_codex_is_ready_only_after_real_cli_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def runner(command, timeout):
        return subprocess.CompletedProcess(command, 0, "lingji-memory http://127.0.0.1:8767/mcp", "")

    monkeypatch.setattr(
        "src.assistant_hub.connectors.shutil.which",
        lambda name, path=None: "C:/Tools/codex.exe" if name == "codex" else None,
    )
    monkeypatch.setattr(
        "src.assistant_hub.governed.shutil.which",
        lambda name, path=None: "C:/Tools/codex.exe" if name == "codex" else None,
    )
    service = AiMemoryConnectorService(
        storage_path=tmp_path / "storage",
        home=tmp_path / "home",
        env={"PATH": "C:/Tools"},
        runner=runner,
    )
    monkeypatch.setattr(service, "_runtime_ready", lambda: True)
    service.apply("codex", "CONNECT_CODEX_TO_LINGJI")

    before = service.status()["connectors"][0]
    assert before["status_state"] == "verification_required"
    assert before["live_test"] is not True

    tested = service.test("codex")
    assert tested["ok"] is True

    after = service.status()["connectors"][0]
    assert after["status_state"] == "ready"
    assert after["live_test"] is True
    assert after["client_available"] is True
