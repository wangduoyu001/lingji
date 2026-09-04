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
from src.control.automatic_memory_api import project_scan_dto, project_scan_processing, project_scan_item

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


def test_scan_detail_merges_safe_manifest_and_queue_items_with_pagination(tmp_path: Path):
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
            "grant-scan-items",
            ("chatgpt_export",),
            (str(root),),
            datetime.now(timezone.utc),
            None,
            True,
        ),
        "chatgpt_export",
        str(root),
    )
    scan = registry.start_scan(source.source_id)
    state.acquire_automatic_memory_scan_lease(scan.scan_id, "lease-scan-items")
    state.upsert_automatic_memory_scan_item_owned(
        scan.scan_id,
        "lease-scan-items",
        source_id=source.source_id,
        relative_path="alpha.txt",
        sentinel="alpha-sentinel",
    )
    state.upsert_automatic_memory_scan_item_owned(
        scan.scan_id,
        "lease-scan-items",
        source_id=source.source_id,
        relative_path="../secret.txt",
        sentinel="secret-sentinel",
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
    app = create_control_app(settings, service=control, token="local-secret")
    headers = {"X-LingJi-Token": "local-secret"}

    completed_job = runtime.queue.enqueue_authorized_snapshot(
        scan_id=scan.scan_id,
        lease_id="lease-scan-items",
        source_id=source.source_id,
        relative_path="alpha.txt",
        raw_id="raw-alpha",
        sha256="a" * 64,
        input_path=root / "alpha.txt",
    )
    completed_claim = runtime.queue.claim(
        "worker-1",
        job_id=completed_job["job_id"],
        allowed_source_types={"automatic_memory_snapshot"},
    )
    runtime.queue.complete(
        completed_job["job_id"],
        {
            "structured_read_model": {
                "sources": 7,
                "conversations": 8,
                "messages": 9,
            }
        },
        worker_id="worker-1",
        lease_token=completed_claim["lease_token"],
    )

    queued_job = runtime.queue.enqueue_authorized_snapshot(
        scan_id=scan.scan_id,
        lease_id="lease-scan-items",
        source_id=source.source_id,
        relative_path="beta.txt",
        raw_id="raw-beta",
        sha256="b" * 64,
        input_path=root / "beta.txt",
    )
    failed_job = runtime.queue.enqueue_authorized_snapshot(
        scan_id=scan.scan_id,
        lease_id="lease-scan-items",
        source_id=source.source_id,
        relative_path="gamma.txt",
        raw_id="raw-gamma",
        sha256="c" * 64,
        input_path=root / "gamma.txt",
    )
    failed_claim = runtime.queue.claim(
        "worker-2",
        job_id=failed_job["job_id"],
        allowed_source_types={"automatic_memory_snapshot"},
    )
    runtime.queue.fail(
        failed_job["job_id"],
        "boom /private/token",
        worker_id="worker-2",
        lease_token=failed_claim["lease_token"],
        retry_delay_seconds=0,
    )

    with TestClient(app) as client:
        default_response = client.get(
            f"/api/automatic-memory/scans/{scan.scan_id}", headers=headers
        )
        paged_response = client.get(
            f"/api/automatic-memory/scans/{scan.scan_id}",
            headers=headers,
            params={"limit": 2, "offset": 1},
        )
        max_response = client.get(
            f"/api/automatic-memory/scans/{scan.scan_id}",
            headers=headers,
            params={"limit": 100},
        )
        scan_action = client.post(
            "/api/automatic-memory/scan",
            headers=headers,
            json={"source_id": source.source_id},
        )
        listed = client.get("/api/automatic-memory/scans", headers=headers)
        summary = client.get("/api/automatic-memory/summary", headers=headers)
        bad_limit = client.get(
            f"/api/automatic-memory/scans/{scan.scan_id}",
            headers=headers,
            params={"limit": 0},
        )
        bad_offset = client.get(
            f"/api/automatic-memory/scans/{scan.scan_id}",
            headers=headers,
            params={"offset": -1},
        )

    assert default_response.status_code == paged_response.status_code == max_response.status_code == 200
    default_payload = default_response.json()
    paged_payload = paged_response.json()
    max_payload = max_response.json()
    expected_item_keys = {
        "item_id",
        "name",
        "source",
        "stage",
        "result",
        "reason",
        "updated_at",
        "retryable",
        "imported_sources",
        "imported_conversations",
        "imported_messages",
    }

    assert "items" in default_payload
    assert "items_pagination" in default_payload
    assert default_payload["items_pagination"] == {
        "limit": 20,
        "offset": 0,
        "total": 4,
        "has_more": False,
    }
    assert [item["name"] for item in default_payload["items"]] == [
        "alpha.txt",
        "beta.txt",
        "gamma.txt",
        "无法安全显示名称",
    ]
    assert all(set(item) == expected_item_keys for item in default_payload["items"])
    assert default_payload["items"][0]["stage"] == "completed"
    assert default_payload["items"][0]["result"] == "imported"
    assert default_payload["items"][0]["source"] == "ChatGPT导出记录"
    assert default_payload["items"][0]["imported_sources"] == 7
    assert default_payload["items"][0]["imported_conversations"] == 8
    assert default_payload["items"][0]["imported_messages"] == 9
    assert default_payload["items"][1]["stage"] == "queued"
    assert default_payload["items"][1]["result"] == "waiting"
    assert default_payload["items"][2]["stage"] == "completed"
    assert default_payload["items"][2]["result"] == "failed"
    assert default_payload["items"][2]["retryable"] is True
    assert default_payload["items"][3]["name"] == "无法安全显示名称"
    assert default_payload["items"][3]["result"] == "recorded"
    assert default_payload["items"][3]["reason"] == "已记录到扫描清单"

    assert paged_payload["items_pagination"] == {
        "limit": 2,
        "offset": 1,
        "total": 4,
        "has_more": True,
    }
    assert [item["name"] for item in paged_payload["items"]] == [
        "beta.txt",
        "gamma.txt",
    ]
    assert all(set(item) == expected_item_keys for item in paged_payload["items"])
    assert max_payload["items_pagination"] == {
        "limit": 100,
        "offset": 0,
        "total": 4,
        "has_more": False,
    }
    assert len(max_payload["items"]) == 4
    assert "items" not in listed.json()[0]
    assert "items" not in summary.json()["latest"]
    assert "items" not in scan_action.json()
    assert bad_limit.status_code == 422
    assert bad_offset.status_code == 422


def test_scan_detail_exact_queue_query_enumerates_more_than_200_rows(tmp_path: Path):
    root = tmp_path / "source"
    root.mkdir()
    storage = tmp_path / "storage"
    storage.mkdir()
    state = StateDatabase(storage / "lingji_state.db")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope("grant-fallback", ("generic_ai_history",), (str(root),), datetime.now(timezone.utc), None, True),
        "generic_ai_history", str(root),
    )
    scan = registry.start_scan(source.source_id)
    queue = build_extraction_pipeline(SimpleNamespace(
        storage_path=storage, state_db_path=storage / "lingji_state.db",
        memory_db_path=storage / "lingji_memory.db", vault_path=tmp_path / "vault",
        runtime_settings_file="runtime_settings.json",
        extraction_max_attempts=1, extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30,
        embedding_enabled=False, semantic_enabled=False,
    )).queue
    for index in range(205):
        queue.enqueue(
            "automatic_memory_snapshot",
            payload={"scan_id": scan.scan_id, "source_id": source.source_id, "relative_path": f"item-{index:03d}.json"},
        )

    control = LocalControlService.__new__(LocalControlService)
    control.state_db = state
    control.automatic_memory_registry = registry
    control.runtime = SimpleNamespace(queue=queue)
    app = create_control_app(SimpleNamespace(storage_path=storage), service=control, token="secret")
    with TestClient(app) as client:
        response = client.get(
            f"/api/automatic-memory/scans/{scan.scan_id}",
            headers={"X-LingJi-Token": "secret"},
            params={"limit": 100},
        )
    assert response.status_code == 200
    assert response.json()["items_pagination"]["total"] == 205


def test_scan_detail_real_second_scan_projects_reused_content(tmp_path: Path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "history.json").write_text(
        json.dumps({"schema": "lingji.history.inbox", "schema_version": "1", "conversations": []}),
        encoding="utf-8",
    )
    storage = tmp_path / "storage"
    storage.mkdir()
    settings = SimpleNamespace(
        storage_path=storage, state_db_path=storage / "lingji_state.db",
        memory_db_path=storage / "lingji_memory.db", vault_path=tmp_path / "vault",
        runtime_settings_file="runtime_settings.json", extraction_max_attempts=1,
        extraction_lease_heartbeat_seconds=2, extraction_stale_after_seconds=30,
        extraction_poll_seconds=0.05, extraction_batch_size=1,
        embedding_enabled=False, semantic_enabled=False,
    )
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope("grant-real-reuse", ("generic_ai_history",), (str(root),), datetime.now(timezone.utc), None, True),
        "generic_ai_history", str(root),
    )
    runtime = AutomaticMemoryRuntime(
        state_db=state, pipeline=build_extraction_pipeline(settings), settings=settings, registry=registry,
    )
    first = runtime.scan_now(source.source_id)
    first_job = runtime.queue.list_page(source_type="automatic_memory_snapshot", limit=1)[0]
    claim = runtime.queue.claim("reuse-test", job_id=first_job["job_id"], allowed_source_types={"automatic_memory_snapshot"})
    runtime.queue.complete(first_job["job_id"], {"structured_read_model": {"sources": 0, "conversations": 0, "messages": 0}}, worker_id="reuse-test", lease_token=claim["lease_token"])
    second = runtime.scan_now(source.source_id)
    control = LocalControlService.__new__(LocalControlService)
    control.settings = settings
    control.state_db = state
    control.automatic_memory_registry = registry
    control.runtime = runtime
    app = create_control_app(settings, service=control, token="secret")
    second_scan_id = second["scan_id"]
    with TestClient(app) as client:
        response = client.get(
            f"/api/automatic-memory/scans/{second_scan_id}",
            headers={"X-LingJi-Token": "secret"},
        )
    assert first["scan_id"] != second["scan_id"]
    assert response.status_code == 200
    assert response.json()["items"][0]["result"] == "reused"


def test_scan_item_projection_uses_owner_source_labels_and_canonical_safe_names():
    queue_item = {
        "updated_at": "2026-09-04T00:00:02+00:00",
        "status": "completed",
        "payload": {
            "source_id": "source-a",
            "source_type": "chatgpt_export",
            "relative_path": "a//b.json",
            "sha256": "a" * 64,
        },
        "result": {"structured_read_model": {"sources": 1}},
    }
    for path in ("a//b.json", "a/./b.json", "line\nb.json", "nul\x00b.json"):
        item = project_scan_item(
            "scan-a",
            path,
            source_id="source-a",
            source_kind="chatgpt_export",
            queue_item={**queue_item, "payload": {**queue_item["payload"], "relative_path": path}},
        )
        assert item["name"] == "无法安全显示名称"
    item = project_scan_item(
        "scan-a",
        "history.json",
        source_id="source-a",
        source_kind="chatgpt_export",
        queue_item={**queue_item, "payload": {**queue_item["payload"], "relative_path": "history.json"}},
    )
    assert item["source"] == "ChatGPT导出记录"
    assert "source-a" not in item.values()


def test_scan_item_projection_prefers_newest_duplicate_and_reuse_is_completed():
    old = {
        "updated_at": "2026-09-04T00:00:01+00:00",
        "status": "failed",
        "payload": {"source_id": "source-a", "source_type": "generic_ai_history", "relative_path": "same.json", "sha256": "a" * 64},
    }
    new = {
        "updated_at": "2026-09-04T00:00:02+00:00",
        "status": "queued",
        "payload": {"source_id": "source-a", "source_type": "generic_ai_history", "relative_path": "same.json", "sha256": "b" * 64},
    }
    assert project_scan_item("scan-a", "same.json", source_id="source-a", source_kind="generic_ai_history", queue_item=new)["result"] == "waiting"
    reused = project_scan_item(
        "scan-b", "same.json", source_id="source-a", source_kind="generic_ai_history",
        queue_item=old, reused=True,
    )
    assert reused["stage"] == "completed"
    assert reused["result"] == "reused"
    assert reused["reason"] == "命中复用，未重复导入"


@pytest.mark.parametrize("historical_status", ["failed", "cancelled", "queued", "processing"])
def test_scan_item_projection_does_not_infer_reuse_from_historical_status(historical_status):
    item = project_scan_item(
        "scan-a", "history.json", source_id="source-a", source_kind="generic_ai_history",
        manifest_item={"source_id": "source-a", "status": historical_status, "updated_at": "2026-09-04T00:00:00+00:00"},
    )
    assert item["result"] != "reused"
    assert item["result"] in {"failed", "cancelled", "waiting", "processing"}


@pytest.mark.parametrize(
    ("scan", "jobs", "expected"),
    [
        (
            {"status": "completed", "total": 2, "queued_count": 2, "reused_count": 0},
            [{"status": "running"}, {"status": "queued"}],
            {"processing_status": "processing", "processing_completed": 0, "processing_failed": 0, "processing_pending": 2},
        ),
        (
            {"status": "completed", "total": 2, "queued_count": 2, "reused_count": 0},
            [{"status": "completed"}, {"status": "completed"}],
            {"processing_status": "imported", "processing_completed": 2, "processing_failed": 0, "processing_pending": 0},
        ),
        (
            {"status": "completed", "total": 2, "queued_count": 2, "reused_count": 0},
            [{"status": "completed"}, {"status": "failed"}],
            {"processing_status": "partial_failure", "processing_completed": 1, "processing_failed": 1, "processing_pending": 0},
        ),
        (
            {"status": "completed", "total": 1, "queued_count": 1, "reused_count": 0},
            [{"status": "cancelled"}],
            {"processing_status": "failed", "processing_completed": 0, "processing_failed": 1, "processing_pending": 0},
        ),
        (
            {"status": "completed", "total": 0, "queued_count": 0, "reused_count": 0},
            [],
            {"processing_status": "empty", "processing_completed": 0, "processing_failed": 0, "processing_pending": 0},
        ),
        (
            {"status": "completed", "total": 3, "queued_count": 0, "reused_count": 0},
            [],
            {"processing_status": "unsupported_format", "processing_completed": 0, "processing_failed": 0, "processing_pending": 0},
        ),
    ],
)
def test_scan_processing_projection_uses_extraction_terminal_facts(scan, jobs, expected):
    projected = project_scan_processing(scan, jobs)
    for key, value in expected.items():
        assert projected[key] == value
    assert projected["processing_total"] == len(jobs)
    assert projected["processing_counts_present"] == [
        "processing_total", "processing_completed", "processing_failed", "processing_pending"
    ]


def test_scan_processing_projection_never_calls_queued_or_reused_imported():
    projected = project_scan_processing(
        {"status": "completed", "total": 4, "queued_count": 2, "reused_count": 2},
        None,
    )
    assert projected["processing_status"] == "scan_completed"
    assert projected["processing_completed"] is None
    assert projected["processing_counts_present"] == []


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
