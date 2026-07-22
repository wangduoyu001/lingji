from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.control.settings_api import register_settings_governance_routes


class _Control:
    def __init__(self):
        self.previewed = None
        self.committed = None

    def preview_settings(self, values):
        self.previewed = dict(values)
        return {
            "changes": [{"key": "storage_auto_cleanup_enabled"}],
            "normalized_values": dict(values),
            "change_count": 1,
            "high_risk_changes": [{"key": "storage_auto_cleanup_enabled"}],
            "requires_confirmation": True,
            "confirmation_phrase": "CONFIRM_HIGH_RISK_SETTINGS",
            "errors": [],
            "warnings": [],
            "can_commit": True,
        }

    def commit_settings(self, values, *, confirmation, actor):
        self.committed = {
            "values": dict(values),
            "confirmation": confirmation,
            "actor": actor,
        }
        if confirmation != "CONFIRM_HIGH_RISK_SETTINGS":
            raise PermissionError("High-risk settings require explicit impact confirmation")
        return {"values": dict(values), "definitions": {}, "groups": []}


def app_and_control():
    app = FastAPI()
    control = _Control()
    register_settings_governance_routes(app, control, token="local-token")
    return TestClient(app), control


def test_settings_preview_requires_existing_control_token():
    client, _ = app_and_control()

    response = client.post(
        "/api/settings/preview",
        json={"values": {"storage_auto_cleanup_enabled": True}},
    )

    assert response.status_code == 401


def test_settings_preview_returns_impact_contract():
    client, control = app_and_control()

    response = client.post(
        "/api/settings/preview",
        headers={"X-LingJi-Token": "local-token"},
        json={"values": {"storage_auto_cleanup_enabled": True}},
    )

    assert response.status_code == 200
    assert response.json()["requires_confirmation"] is True
    assert control.previewed == {"storage_auto_cleanup_enabled": True}


def test_high_risk_commit_is_rejected_without_confirmation():
    client, _ = app_and_control()

    response = client.post(
        "/api/settings/commit",
        headers={"X-LingJi-Token": "local-token"},
        json={"values": {"storage_auto_cleanup_enabled": True}},
    )

    assert response.status_code == 403


def test_confirmed_commit_records_local_ui_actor():
    client, control = app_and_control()

    response = client.post(
        "/api/settings/commit",
        headers={"X-LingJi-Token": "local-token"},
        json={
            "values": {"storage_auto_cleanup_enabled": True},
            "confirmation": "CONFIRM_HIGH_RISK_SETTINGS",
        },
    )

    assert response.status_code == 200
    assert control.committed == {
        "values": {"storage_auto_cleanup_enabled": True},
        "confirmation": "CONFIRM_HIGH_RISK_SETTINGS",
        "actor": "local_ui",
    }
