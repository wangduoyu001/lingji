from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import asdict
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.storage import StateDatabase
from src.automatic_memory import AuthorizationScope, AutomaticMemoryRuntime
from src.automatic_memory.source_registry import SourceRegistry
from src.extraction.bootstrap import build_extraction_pipeline
from src.control.automatic_memory_api import project_scan_dto

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
    class Runtime:
        def scan_now(self, source_id):
            return asdict(control.automatic_memory_registry.start_scan(source_id))

    control.state_db = StateDatabase(database_path)
    control.automatic_memory_registry = None
    control.runtime = None
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
        control.runtime = Runtime()

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
        assert scan["work_id"] == f"automatic-memory:{scan_id}"

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


def test_user_home_drives_authorize_and_runtime_scan_when_process_home_differs(tmp_path: Path, monkeypatch):
    effective_home = tmp_path / "configured-home"
    host_home = tmp_path / "host-home"
    source_root = effective_home / ".codex" / "sessions"
    source_path = source_root / "2026" / "08" / "29" / "rollout-user-home.jsonl"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("\n".join(json.dumps(row) for row in [
        {"type": "session_meta", "payload": {"id": "user-home-session"}},
        {"type": "event_msg", "id": "user-home-u", "payload": {"type": "user_message", "message": "configured home"}, "timestamp": "2026-08-29T00:00:00Z"},
    ]) + "\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(host_home))
    settings = SimpleNamespace(
        storage_path=tmp_path / "storage", state_db_path=tmp_path / "storage" / "lingji_state.db",
        memory_db_path=tmp_path / "storage" / "lingji_memory.db", vault_path=tmp_path / "vault",
        user_home=effective_home, runtime_settings_file="runtime_settings.json", extraction_max_attempts=1, extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30, scheduler_poll_seconds=0.02,
        automatic_memory_debounce_seconds=1, automatic_memory_reconciliation_seconds=60,
        automatic_memory_integrity_seconds=3600, extraction_poll_seconds=0.02,
        extraction_batch_size=2, embedding_enabled=False, semantic_enabled=False,
    )
    settings.storage_path.mkdir(parents=True)
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    pipeline = build_extraction_pipeline(settings)
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    control = LocalControlService.__new__(LocalControlService)
    control.settings = settings
    control.state_db = state
    control.automatic_memory_registry = registry
    control.runtime = runtime
    app = create_control_app(settings, service=control, token="local-secret")
    headers = {"X-LingJi-Token": "local-secret"}
    authorization = {
        "grant_id": "grant-user-home", "source_kinds": ["codex_rollout"],
        "roots": [str(source_root)], "granted_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None, "owner_confirmed": True, "kind": "codex_rollout", "root": str(source_root),
    }
    runtime.start()
    try:
        with TestClient(app) as client:
            authorized = client.post("/api/automatic-memory/authorize", headers=headers, json=authorization)
            assert authorized.status_code == 200, authorized.text
            source_id = authorized.json()["source_id"]
            denied = client.post("/api/automatic-memory/authorize", headers=headers, json={
                **authorization, "grant_id": "grant-host-home", "roots": [str(host_home / ".codex" / "sessions")],
                "root": str(host_home / ".codex" / "sessions"),
            })
            assert denied.status_code == 403
            scan = client.post("/api/automatic-memory/scan", headers=headers, json={"source_id": source_id})
            assert scan.status_code == 200, scan.text
            deadline = time.time() + 8
            jobs = []
            while time.time() < deadline:
                jobs = pipeline.queue.list_page(source_type="automatic_memory_snapshot", limit=10)
                if jobs and jobs[0]["status"] in {"completed", "failed"}:
                    break
                time.sleep(0.03)
            assert jobs and jobs[0]["status"] == "completed", jobs
    finally:
        runtime.stop()


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


def test_scan_list_summary_and_detail_share_nullable_count_evidence_shape(tmp_path: Path):
    """Every scan endpoint must project the same persisted count evidence."""
    root = tmp_path / "source"
    root.mkdir()
    settings = SimpleNamespace(storage_path=tmp_path / "storage")
    settings.storage_path.mkdir()
    control = LocalControlService.__new__(LocalControlService)
    database_path = settings.storage_path / "lingji_state.db"
    control.state_db = StateDatabase(database_path)
    app = create_control_app(settings, service=control, token="local-secret")
    headers = {"X-LingJi-Token": "local-secret"}
    now = datetime.now(timezone.utc).replace(microsecond=0)
    source = control.automatic_memory_registry.register(
        AuthorizationScope(
            "grant-api-counts", ("chatgpt_export",), (str(root),), now, None, True
        ),
        "chatgpt_export",
        str(root),
    )
    scan = control.automatic_memory_registry.start_scan(source.source_id)
    completed = control.automatic_memory_registry.complete_scan_if_authorized(
        scan.scan_id, progress=0, total=0, queued_count=0, reused_count=0
    )
    assert completed is not None

    with TestClient(app) as client:
        listed = client.get("/api/automatic-memory/scans", headers=headers)
        summary = client.get("/api/automatic-memory/summary", headers=headers)
        detail = client.get(
            f"/api/automatic-memory/scans/{scan.scan_id}", headers=headers
        )
    assert listed.status_code == summary.status_code == detail.status_code == 200
    list_item = listed.json()[0]
    summary_item = summary.json()["latest"]
    detail_item = detail.json()
    for payload in (list_item, summary_item, detail_item):
        assert payload["queued"] == 0
        assert payload["reused"] == 0
        assert payload["counts_present"] == ["queued", "reused"]
        assert payload["work_id"] == f"automatic-memory:{scan.scan_id}"
    assert list_item["updated_at"] == summary_item["updated_at"] == detail_item["updated_at"]

    unmeasured = control.automatic_memory_registry.start_scan(source.source_id)
    with TestClient(app) as client:
        paused = client.post(
            "/api/automatic-memory/pause",
            headers=headers,
            json={"scan_id": unmeasured.scan_id},
        )
        listed = client.get("/api/automatic-memory/scans", headers=headers)
        summary = client.get("/api/automatic-memory/summary", headers=headers)
        detail = client.get(
            f"/api/automatic-memory/scans/{unmeasured.scan_id}", headers=headers
        )
    assert paused.status_code == 200
    listed_by_id = {item["scan_id"]: item for item in listed.json()}
    assert unmeasured.scan_id in listed_by_id
    assert summary.json()["latest"]["scan_id"] == unmeasured.scan_id
    for payload in (paused.json(), listed_by_id[unmeasured.scan_id], summary.json()["latest"], detail.json()):
        assert payload["queued"] is None
        assert payload["reused"] is None
        assert payload["counts_present"] == []
        assert payload["work_id"] == f"automatic-memory:{unmeasured.scan_id}"


def test_scan_projector_does_not_promote_legacy_zero_without_presence_marker():
    """Compatibility rows with model-default zero remain unmeasured."""
    projected = project_scan_dto(
        {"scan_id": "legacy", "queued": 0, "reused": 0, "status": "completed"}
    )
    assert projected["queued"] is None
    assert projected["reused"] is None
    assert projected["counts_present"] == []


@pytest.mark.parametrize(
    ("status", "expected_action"),
    [
        ("unsupported", "official support"),
        ("expired", "re-authorize"),
    ],
)
def test_authenticated_scan_action_reports_real_early_exit_next_action(
    tmp_path: Path, status: str, expected_action: str
):
    """The production runtime, not a fake route double, owns early exits."""
    root = tmp_path / "source"
    root.mkdir()
    storage = tmp_path / "storage"
    storage.mkdir()
    settings = SimpleNamespace(
        storage_path=storage,
        state_db_path=storage / "lingji_state.db",
        memory_db_path=storage / "lingji_memory.db",
        vault_path=tmp_path / "vault",
        runtime_settings_file="runtime_settings.json",
        extraction_poll_seconds=0.05,
        extraction_batch_size=1,
        extraction_max_attempts=1,
        extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30,
        scheduler_poll_seconds=0.05,
        automatic_memory_debounce_seconds=1,
        automatic_memory_reconciliation_seconds=60,
        automatic_memory_integrity_seconds=3600,
        embedding_enabled=False,
        semantic_enabled=False,
    )
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            f"grant-{status}", ("generic_ai_history",), (str(root),),
            datetime.now(timezone.utc), None, True,
        ),
        "generic_ai_history",
        str(root),
    )
    registry.set_status(source.source_id, status, reason="test early exit")
    runtime = AutomaticMemoryRuntime(
        state_db=state,
        pipeline=build_extraction_pipeline(settings),
        settings=settings,
        registry=registry,
    )
    control = LocalControlService.__new__(LocalControlService)
    control.settings = settings
    control.state_db = state
    control.automatic_memory_registry = registry
    control.runtime = runtime
    app = create_control_app(settings, service=control, token="secret")
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/automatic-memory/scan",
                headers={"X-LingJi-Token": "secret"},
                json={"source_id": source.source_id},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["complete"] is False
        assert payload["queued"] is None and payload["reused"] is None
        assert payload["counts_present"] == []
        assert payload["next_action"] and expected_action in payload["next_action"]
    finally:
        runtime.stop()


def test_authenticated_scan_action_reports_paused_and_lease_contention(
    tmp_path: Path,
):
    """Paused and contended actions retain formal scheduler semantics."""
    root = tmp_path / "source"
    root.mkdir()
    storage = tmp_path / "storage"
    storage.mkdir()
    settings = SimpleNamespace(
        storage_path=storage,
        state_db_path=storage / "lingji_state.db",
        memory_db_path=storage / "lingji_memory.db",
        vault_path=tmp_path / "vault",
        runtime_settings_file="runtime_settings.json",
        extraction_poll_seconds=0.05,
        extraction_batch_size=1,
        extraction_max_attempts=1,
        extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30,
        scheduler_poll_seconds=0.05,
        automatic_memory_debounce_seconds=1,
        automatic_memory_reconciliation_seconds=60,
        automatic_memory_integrity_seconds=3600,
        embedding_enabled=False,
        semantic_enabled=False,
    )
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            "grant-paused-lease", ("generic_ai_history",), (str(root),),
            datetime.now(timezone.utc), None, True,
        ),
        "generic_ai_history",
        str(root),
    )
    runtime = AutomaticMemoryRuntime(
        state_db=state,
        pipeline=build_extraction_pipeline(settings),
        settings=settings,
        registry=registry,
    )
    control = LocalControlService.__new__(LocalControlService)
    control.settings = settings
    control.state_db = state
    control.automatic_memory_registry = registry
    control.runtime = runtime
    app = create_control_app(settings, service=control, token="secret")
    headers = {"X-LingJi-Token": "secret"}
    try:
        runtime.scheduler.pause()
        with TestClient(app) as client:
            paused = client.post(
                "/api/automatic-memory/scan",
                headers=headers,
                json={"source_id": source.source_id},
            )
        assert paused.status_code == 200
        assert paused.json()["queued"] is None
        assert paused.json()["reused"] is None
        assert paused.json()["next_action"] and "resume" in paused.json()["next_action"]

        runtime.scheduler.resume()
        scan = registry.start_scan(source.source_id)
        assert state.claim_automatic_memory_scheduler_scan(
            scan.scan_id, "api-existing-lease", "api-existing-owner", ttl_seconds=300
        )
        with TestClient(app) as client:
            contended = client.post(
                "/api/automatic-memory/scan",
                headers=headers,
                json={"source_id": source.source_id},
            )
        assert contended.status_code == 200
        assert contended.json()["queued"] is None
        assert contended.json()["reused"] is None
        assert contended.json()["next_action"] and "existing" in contended.json()["next_action"]
    finally:
        runtime.stop()
