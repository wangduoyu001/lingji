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
    control.settings = SimpleNamespace(storage_path=storage, runtime_settings_file="runtime_settings.json")
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


def test_knowledge_routes_project_distilled_entries(tmp_path: Path):
    """路由级：知识要点列表/详情/空库守卫（回归 distillation 接线）。"""
    import sqlite3

    state, app, headers, registry, source = _fixture(tmp_path)
    memory_db = tmp_path / "storage" / "lingji_memory.db"
    control_settings = getattr(app.state, "lingji_control", None)

    with TestClient(app) as client:
        # 空库/缺库：200 + 空列表（不 500）
        missing = client.get("/api/observability/knowledge", headers=headers)
        assert missing.status_code == 200
        assert missing.json()["items"] == []
        assert missing.json()["stats"]["total"] == 0

    # 播种最小记忆库：一段对话 + 已提炼条目 + 一条消息
    with sqlite3.connect(str(memory_db)) as conn:
        conn.execute(
            "CREATE TABLE conversation_records (conversation_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, title TEXT NOT NULL, started_at TEXT, message_count INTEGER NOT NULL DEFAULT 0)"
        )
        conn.execute(
            "CREATE TABLE message_records (message_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL, author TEXT, content TEXT NOT NULL, content_hash TEXT NOT NULL, occurred_at TEXT, sequence INTEGER NOT NULL DEFAULT 0)"
        )
        conn.execute("INSERT INTO conversation_records VALUES ('LJ-CONV-K1', 'src', '对话 K1', '2026-09-01T00:00:00+00:00', 1)")
        conn.execute(
            "INSERT INTO message_records VALUES ('LJ-MSG-K1', 'LJ-CONV-K1', 'user', '主人', '讨论了本地模型方案', 'h1', '2026-09-01T00:00:00+00:00', 0)"
        )
        conn.execute(
            """
            CREATE TABLE distilled_knowledge (
                conversation_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, title TEXT NOT NULL,
                summary TEXT NOT NULL, key_points_json TEXT NOT NULL, category TEXT NOT NULL,
                model TEXT NOT NULL, messages_digest TEXT NOT NULL, message_count INTEGER NOT NULL DEFAULT 0,
                revision INTEGER NOT NULL DEFAULT 1, occurred_at TEXT, status TEXT NOT NULL DEFAULT 'ready',
                last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO distilled_knowledge (conversation_id, source_id, title, summary, key_points_json, category, model, messages_digest, message_count, revision, occurred_at, status, created_at, updated_at) VALUES ('LJ-CONV-K1', 'src', '对话 K1', '确定了本地模型方案', '[\"使用本地模型\"]', '决策', 'test-chat', 'dig', 1, 1, '2026-09-01T00:00:00+00:00', 'ready', '2026-09-01T00:00:00+00:00', '2026-09-01T00:00:00+00:00')"
        )
        conn.commit()

    # 告诉 distiller 记忆库在哪（与真实 settings 契约一致）
    from src.automatic_memory.distillation import KnowledgeDistiller

    original_init = KnowledgeDistiller.__init__

    def _patched_init(self, settings, **kwargs):
        settings = SimpleNamespace(
            storage_path=getattr(settings, "storage_path", ""),
            ollama_base_url=getattr(settings, "ollama_base_url", "http://127.0.0.1:11434"),
            distill_model=getattr(settings, "distill_model", ""),
            memory_db_path=str(memory_db),
        )
        original_init(self, settings, **kwargs)

    KnowledgeDistiller.__init__ = _patched_init
    try:
        with TestClient(app) as client:
            listing = client.get("/api/observability/knowledge?limit=10", headers=headers)
            assert listing.status_code == 200, listing.text
            body = listing.json()
            assert body["stats"]["ready"] == 1
            assert body["items"][0]["summary"] == "确定了本地模型方案"
            assert body["items"][0]["key_points"] == ["使用本地模型"]

            searched = client.get("/api/observability/knowledge?q=本地模型", headers=headers).json()
            assert len(searched["items"]) == 1
            empty_search = client.get("/api/observability/knowledge?q=不存在xyz", headers=headers).json()
            assert empty_search["items"] == []

            detail = client.get("/api/observability/knowledge/LJ-CONV-K1", headers=headers)
            assert detail.status_code == 200, detail.text
            detail_body = detail.json()
            assert detail_body["entry"]["category"] == "决策"
            assert detail_body["messages"][0]["content"] == "讨论了本地模型方案"

            updated_order = client.get("/api/observability/knowledge?order=updated", headers=headers).json()
            assert updated_order["items"][0]["conversation_id"] == "LJ-CONV-K1"
    finally:
        KnowledgeDistiller.__init__ = original_init


def test_knowledge_progress_fields_and_model_switch(tmp_path: Path):
    """进度/模型列表字段 + 主人切换提炼模型的端点。"""
    state, app, headers, registry, source = _fixture(tmp_path)
    with TestClient(app) as client:
        listing = client.get("/api/observability/knowledge", headers=headers).json()
        assert "progress" in listing and listing["progress"]["active"] is False
        assert isinstance(listing["models"], list)
        assert "distill_model" in listing

        rejected = client.post("/api/observability/knowledge/model", headers=headers, json={"model": "not-installed:x"})
        assert rejected.status_code == 400

        reset = client.post("/api/observability/knowledge/model", headers=headers, json={"model": ""})
        assert reset.status_code == 200
        assert reset.json()["distill_model"] == ""


def test_recall_guard_drops_degenerate_perfect_scores_and_below_floor():
    """WorkBuddy 2026-09-16 复检：无关中文查询回填 1.0 分给不相关内容。

    护栏契约：满分(>=0.999)只有查询词与命中内容互为子串（真重复）才保留；
    低于分数下限的弱相关一律丢弃（bge-m3：相关 >=0.55，无关噪声 <=0.44）。
    """
    from src.control.observability_api import _plausible_recall_hits

    hits = [
        {"score": 1.0, "content": "什么情况"},
        {"score": 1.0, "content": "登陆了啊"},
        {"score": 1.0, "content": "桃园结义是三国故事"},
        {"score": 0.839, "content": "本机能跑comfyui吗"},
        {"score": 0.5, "content": "弱相关内容"},
    ]
    kept = _plausible_recall_hits("桃园结义", hits)
    assert [h["content"] for h in kept] == ["桃园结义是三国故事", "本机能跑comfyui吗"], "degenerate perfect scores must not pose as real hits; below-floor must drop"

    dup = _plausible_recall_hits("什么情况", [{"score": 1.0, "content": "什么情况"}])
    assert len(dup) == 1, "a true duplicate (query equals content) must stay"

    empty = _plausible_recall_hits("桃园结义", [{"score": 0.44, "content": "无关内容"}])
    assert empty == [], "below-floor noise must return an empty result set"
