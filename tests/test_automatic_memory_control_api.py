from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.storage import StateDatabase

try:
    from src.control.api import create_control_app
    from src.control.service import LocalControlService
except ModuleNotFoundError:  # RED until Task 1 route module is wired.
    create_control_app = None  # type: ignore[assignment]
    LocalControlService = None  # type: ignore[assignment]


def test_automatic_memory_routes_require_existing_local_control_token(tmp_path: Path):
    """Catches automatic-memory endpoints accidentally bypassing 8766 auth."""
    if create_control_app is None or LocalControlService is None:
        pytest.fail("automatic-memory control API production modules are absent")

    settings = SimpleNamespace(storage_path=tmp_path / "storage")
    settings.storage_path.mkdir()
    control = LocalControlService.__new__(LocalControlService)
    control.state_db = StateDatabase(settings.storage_path / "lingji_state.db")
    app = create_control_app(settings, service=control, token="local-secret")
    with TestClient(app) as client:
        response = client.get("/api/automatic-memory/sources")
        assert response.status_code == 401


def test_automatic_memory_authorize_scan_pause_retry_and_reopen(tmp_path: Path):
    """Catches routes that fabricate completed/zero state or skip persistence."""
    if create_control_app is None or LocalControlService is None:
        pytest.fail("automatic-memory control API production modules are absent")

    root = tmp_path / "chatgpt-export"
    root.mkdir()
    settings = SimpleNamespace(storage_path=tmp_path / "storage")
    settings.storage_path.mkdir()
    database_path = settings.storage_path / "lingji_state.db"
    control = LocalControlService.__new__(LocalControlService)
    control.state_db = StateDatabase(database_path)
    app = create_control_app(settings, service=control, token="local-secret")
    headers = {"X-LingJi-Token": "local-secret"}
    authorization = {
        "grant_id": "grant-cn-owner-2",
        "source_kinds": ["chatgpt_export"],
        "roots": [str(root)],
        "granted_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "expires_at": None,
        "owner_confirmed": True,
        "kind": "chatgpt_export",
        "root": str(root),
    }

    with TestClient(app) as client:
        response = client.post(
            "/api/automatic-memory/authorize", headers=headers, json=authorization
        )
        assert response.status_code == 200
        source = response.json()
        assert source["status"] == "authorized"
        assert source["root"] == str(root)
        source_id = source["source_id"]

        denied = client.post(
            "/api/automatic-memory/authorize",
            headers=headers,
            json={**authorization, "root": str(root / "child")},
        )
        assert denied.status_code == 403

        scan_response = client.post(
            "/api/automatic-memory/scan",
            headers=headers,
            json={"source_id": source_id},
        )
        assert scan_response.status_code == 200
        scan = scan_response.json()
        assert scan["status"] == "running"
        assert scan["progress"] == 0
        assert scan["total"] is None
        scan_id = scan["scan_id"]

        paused = client.post(
            "/api/automatic-memory/pause",
            headers=headers,
            json={"scan_id": scan_id},
        )
        assert paused.status_code == 200
        assert paused.json()["status"] == "paused"
        assert paused.json()["recovery_token"]

        retried = client.post(
            "/api/automatic-memory/retry",
            headers=headers,
            json={"scan_id": scan_id},
        )
        assert retried.status_code == 200
        assert retried.json()["status"] == "running"
        assert retried.json()["progress"] == 0
        assert retried.json()["total"] is None

        listed = client.get("/api/automatic-memory/sources", headers=headers)
        assert listed.status_code == 200
        assert listed.json()[0]["source_id"] == source_id
        fetched = client.get(
            f"/api/automatic-memory/scans/{scan_id}", headers=headers
        )
        assert fetched.status_code == 200
        assert fetched.json()["scan_id"] == scan_id

        revoked = client.post(
            "/api/automatic-memory/revoke",
            headers=headers,
            json={"source_id": source_id},
        )
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "revoked"
        retry_denied = client.post(
            "/api/automatic-memory/retry",
            headers=headers,
            json={"scan_id": scan_id},
        )
        assert retry_denied.status_code == 403
        start_denied = client.post(
            "/api/automatic-memory/scan",
            headers=headers,
            json={"source_id": source_id},
        )
        assert start_denied.status_code == 403

    reopened_control = LocalControlService.__new__(LocalControlService)
    reopened_control.state_db = StateDatabase(database_path)
    reopened_app = create_control_app(
        settings, service=reopened_control, token="local-secret"
    )
    with TestClient(reopened_app) as client:
        persisted = client.get(
            f"/api/automatic-memory/scans/{scan_id}", headers=headers
        )
        assert persisted.status_code == 200
        assert persisted.json()["status"] == "cancelled"


def test_automatic_memory_discovery_scan_summary_and_runtime_actions_are_secured(tmp_path: Path):
    settings = SimpleNamespace(storage_path=tmp_path / "storage", vault_path=tmp_path / "vault", generic_history_dir=tmp_path / "history")
    settings.storage_path.mkdir()
    settings.generic_history_dir.mkdir()
    control = LocalControlService.__new__(LocalControlService)
    control.settings = settings
    control.state_db = StateDatabase(settings.storage_path / "lingji_state.db")
    app = create_control_app(settings, service=control, token="local-secret")
    with TestClient(app) as client:
        assert client.get("/api/automatic-memory/discovered").status_code == 401
        headers = {"X-LingJi-Token": "local-secret"}
        discovered = client.get("/api/automatic-memory/discovered", headers=headers)
        assert discovered.status_code == 200
        assert any(item["kind"] == "generic_ai_history" for item in discovered.json())
        scans = client.get("/api/automatic-memory/scans", headers=headers)
        assert scans.status_code == 200
        summary = client.get("/api/automatic-memory/summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["total"] == 0
