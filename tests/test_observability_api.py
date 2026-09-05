"""Observability workbench projection tests (P0 batch)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.storage import StateDatabase

try:
    from src.control.api import create_control_app
    from src.control.service import LocalControlService
    from src.control.observability_api import explain_failure, project_item_status
except ModuleNotFoundError:
    create_control_app = None  # type: ignore[assignment]


def test_failure_explanations_are_owner_safe():
    result = explain_failure("unsupported Codex rollout: Codex rollout contains multiple distinct session_meta identities; no guessing")
    assert result["what"] == "同一个文件里混着多个不同的会话"
    assert "自动重试" in result["next"]
    assert "/" not in result["what"] and "session_meta" not in result["what"]
    empty = explain_failure("unsupported Codex rollout: Codex rollout contains no supported messages")
    assert empty["what"] == "文件里没有可读的聊天内容"
    unknown = explain_failure(None)
    assert unknown["what"] == "尚未获得"


def test_item_status_never_calls_queued_imported():
    assert project_item_status("queued", None)["label"] == "未处理"
    assert project_item_status("queued", "queued")["label"] == "处理中"
    merged = project_item_status("job:job-1:existing", "completed")
    assert merged["status"] == "merged"
    kept = project_item_status("job:job-2:new", "completed")
    assert kept["status"] == "kept"


def _fixture(tmp_path: Path):
    if create_control_app is None:
        pytest.fail("control api absent")
    from src.automatic_memory import AuthorizationScope, SourceRegistry

    storage = tmp_path / "storage"
    storage.mkdir()
    state = StateDatabase(storage / "lingji_state.db")
    registry = SourceRegistry(state)
    root = tmp_path / "authorized"
    root.mkdir()
    source = registry.register(
        AuthorizationScope("grant-obs", ("generic_ai_history",), (str(root),), datetime.now(timezone.utc), None, True),
        "generic_ai_history",
        str(root),
    )
    control = LocalControlService.__new__(LocalControlService)
    control.state_db = state
    control.settings = SimpleNamespace(storage_path=storage)
    app = create_control_app(SimpleNamespace(storage_path=storage), service=control, token="local-secret")
    headers = {"X-LingJi-Token": "local-secret"}
    return state, app, headers, registry, source


def test_tasks_steps_items_and_changes_are_projected(tmp_path: Path):
    state, app, headers, registry, source = _fixture(tmp_path)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    started = registry.start_scan(source.source_id)
    scan_id = started.scan_id
    state.acquire_automatic_memory_scan_lease(scan_id, "lease-obs")
    state.upsert_automatic_memory_scan_item_owned(
        scan_id, "lease-obs", source_id=source.source_id, relative_path="a.jsonl", sentinel="s1", status="job:j1:new",
    )
    state.upsert_automatic_memory_scan_item_owned(
        scan_id, "lease-obs", source_id=source.source_id, relative_path="b.jsonl", sentinel="s2", status="processed",
    )
    state.update_automatic_memory_scan_owned(
        scan_id, "lease-obs", lease_ttl_seconds=60,
        status="completed", total=3, progress=3, queued_count=2, reused_count=1,
        updated_at=now,
    )
    state.append_event("structured_ingestion_completed", "source", source.source_id, {"messages": 5})

    with TestClient(app) as client:
        denied = client.get("/api/observability/tasks")
        assert denied.status_code == 401

        tasks = client.get("/api/observability/tasks", headers=headers).json()
        assert tasks["items"][0]["scan_id"] == scan_id
        assert tasks["items"][0]["total"] == 3

        steps = client.get(f"/api/observability/tasks/{scan_id}/steps", headers=headers).json()
        by_step = {s["step"]: s for s in steps["steps"]}
        assert len(steps["steps"]) == 9
        assert by_step["fetch"]["count"] == 3
        assert by_step["dedupe"]["count"] == 1
        assert by_step["fetch"]["plain"], "every step carries a plain-language explanation"
        for step in steps["steps"]:
            if step["count"] is None:
                assert step["label"] and "尚未获得" not in step["label"]

        items = client.get(f"/api/observability/tasks/{scan_id}/items", headers=headers).json()
        by_name = {i["name"]: i for i in items["items"]}
        assert by_name["a.jsonl"]["status"] == "pending"  # queued job absent → 未处理
        assert by_name["b.jsonl"]["status"] == "kept"

        state.connection if False else None
        changes = client.get("/api/observability/changes", headers=headers).json()
        assert any(c["action"] == "内容导入完成" for c in changes["items"])

        feed = client.get("/api/observability/feed", headers=headers).json()
        assert feed["items"] == [], "no extraction jobs yet in this fixture"

        missing = client.get("/api/observability/tasks/scan-nope/steps", headers=headers)
        assert missing.status_code == 404


def test_failed_job_projects_owner_safe_reason(tmp_path: Path):
    state, app, headers, registry, source = _fixture(tmp_path)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    started = registry.start_scan(source.source_id)
    scan_id = started.scan_id
    state.acquire_automatic_memory_scan_lease(scan_id, "lease-f")
    from src.extraction.queue import SQLiteExtractionQueue

    SQLiteExtractionQueue(storage if False else state.path)
    payload = {"scan_id": scan_id, "relative_path": "2026/08/10/rollout-bad.jsonl", "raw_id": "x", "sha256": "y"}
    with TestClient(app) as client:
        # 直接插一个失败 job（模拟真实失败事实）
        import sqlite3 as _s

        with state._connection() as conn:
            conn.execute(
                "INSERT INTO extraction_jobs (job_id, source_type, adapter_name, adapter_version, input_path, payload_json, idempotency_key, status, priority, attempts, max_attempts, next_run_at, last_error, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("LJ-JOB-FAIL1", "automatic_memory_snapshot", "x", "1", "/private/raw/x", json.dumps(payload), "idem-1", "failed", 100, 1, 1, now, "unsupported Codex rollout: Codex rollout contains multiple distinct session_meta identities; no guessing", now, now),
            )
        items = client.get(f"/api/observability/tasks/{scan_id}/items", headers=headers).json()
        row = items["items"][0]
        assert row["name"] == "rollout-bad.jsonl", row
        assert row["status"] == "failed"
        assert row["failure"]["what"] == "同一个文件里混着多个不同的会话"
        assert "session_meta" not in json.dumps(row, ensure_ascii=False) and "category" not in row.get("failure", {})
        feed = client.get("/api/observability/feed", headers=headers).json()
        assert feed["items"][0]["status"] == "failed"
        assert "/private" not in json.dumps(feed, ensure_ascii=False)
