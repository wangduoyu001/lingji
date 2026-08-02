from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.assistant_hub import AiMemoryConnectorService


def _service(tmp_path: Path, runner):
    return AiMemoryConnectorService(
        storage_path=tmp_path / "storage",
        home=tmp_path / "home",
        env={"PATH": "C:/Tools"},
        runner=runner,
    )


def test_codex_access_denied_is_not_reported_as_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.assistant_hub.connectors.shutil.which",
        lambda name, path=None: "C:/Tools/codex.exe" if name == "codex" else None,
    )
    monkeypatch.setattr(
        "src.assistant_hub.governed.shutil.which",
        lambda name, path=None: "C:/Tools/codex.exe" if name == "codex" else None,
    )

    def denied(command, timeout):
        raise PermissionError(13, "Access is denied", command[0])

    service = _service(tmp_path, denied)
    monkeypatch.setattr(service, "_runtime_ready", lambda: True)
    service.apply("codex", "CONNECT_CODEX_TO_LINGJI")

    tested = service.test("codex")
    assert tested["ok"] is False
    assert tested["state"] == "blocked"
    assert tested["code"] == "CLIENT_ACCESS_DENIED"
    assert "Access is denied" in tested["message"]

    status = service.status()["connectors"][0]
    assert status["status_state"] == "client_launch_blocked"
    assert status["readiness"]["configuration"]["state"] == "configured"
    assert status["readiness"]["client"]["state"] == "launch_blocked"
    assert status["readiness"]["real_connection"]["state"] == "blocked"
    assert status["readiness"]["real_connection"]["verified"] is False


def test_codex_readiness_becomes_verified_only_after_command_lists_mcp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.assistant_hub.connectors.shutil.which",
        lambda name, path=None: "C:/Tools/codex.exe" if name == "codex" else None,
    )
    monkeypatch.setattr(
        "src.assistant_hub.governed.shutil.which",
        lambda name, path=None: "C:/Tools/codex.exe" if name == "codex" else None,
    )

    def runner(command, timeout):
        return subprocess.CompletedProcess(
            command,
            0,
            "lingji-memory http://127.0.0.1:8767/mcp",
            "",
        )

    service = _service(tmp_path, runner)
    monkeypatch.setattr(service, "_runtime_ready", lambda: True)
    service.apply("codex", "CONNECT_CODEX_TO_LINGJI")

    before = service.status()["connectors"][0]
    assert before["readiness"]["client"]["state"] == "available"
    assert before["readiness"]["real_connection"]["state"] == "not_verified"
    assert before["status_state"] == "verification_required"

    tested = service.test("codex")
    assert tested["code"] == "VERIFIED"
    assert tested["ok"] is True

    after = service.status()["connectors"][0]
    assert after["status_state"] == "ready"
    assert after["readiness"]["real_connection"]["state"] == "verified"
    assert after["readiness"]["real_connection"]["method"] == "codex mcp list"


def test_codex_command_without_registration_is_failed_not_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.assistant_hub.connectors.shutil.which",
        lambda name, path=None: "C:/Tools/codex.exe" if name == "codex" else None,
    )
    monkeypatch.setattr(
        "src.assistant_hub.governed.shutil.which",
        lambda name, path=None: "C:/Tools/codex.exe" if name == "codex" else None,
    )

    def runner(command, timeout):
        return subprocess.CompletedProcess(command, 0, "other-server", "")

    service = _service(tmp_path, runner)
    monkeypatch.setattr(service, "_runtime_ready", lambda: True)
    service.apply("codex", "CONNECT_CODEX_TO_LINGJI")

    tested = service.test("codex")
    assert tested["ok"] is False
    assert tested["code"] == "MCP_REGISTRATION_NOT_VISIBLE"

    status = service.status()["connectors"][0]
    assert status["status_state"] == "verification_failed"
    assert status["readiness"]["real_connection"]["state"] == "failed"
