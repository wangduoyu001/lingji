from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.control.api import create_control_app


class ControlStub:
    def obsidian_status(self):
        return {
            "state": "configuration_required",
            "enabled": True,
            "available": False,
            "cli_path_display": "",
            "vault_path_display": "…/test/vault",
            "issues": [{"code": "OBSIDIAN_CLI_NOT_FOUND", "message": "Obsidian CLI 尚未配置"}],
        }

    def validate_obsidian_settings(self, values):
        return {**self.obsidian_status(), "persisted": False, "validated_values": sorted(values)}



def test_obsidian_routes_require_token_and_return_stable_contract():
    app = create_control_app(SimpleNamespace(), service=ControlStub(), token="secret")
    client = TestClient(app)

    assert client.get("/api/obsidian/status").status_code == 401

    headers = {"X-LingJi-Token": "secret"}
    response = client.get("/api/obsidian/status", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "configuration_required"
    assert payload["issues"][0]["code"] == "OBSIDIAN_CLI_NOT_FOUND"
    assert "cli_path" not in payload
    assert "vault_path" not in payload

    validated = client.post(
        "/api/obsidian/validate",
        headers=headers,
        json={"values": {"obsidian_cli_enabled": False}},
    )
    assert validated.status_code == 200
    assert validated.json()["persisted"] is False

    refreshed = client.post("/api/obsidian/refresh", headers=headers, json={})
    assert refreshed.status_code == 200
