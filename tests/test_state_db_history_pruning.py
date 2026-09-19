"""滚动保留检查留痕：防止 15 分钟一次的自动检查把记录表撑爆。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.storage import StateDatabase

try:
    from src.automatic_memory import AuthorizationScope, SourceRegistry
except ModuleNotFoundError:  # pragma: no cover
    SourceRegistry = None


def _seed(tmp_path: Path, completed: int = 25):
    state = StateDatabase(tmp_path / "lingji_state.db")
    source_id = "src-prune"
    now = "2026-09-12T00:00:00+00:00"
    with state._connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO automatic_memory_sources (source_id, grant_id, kind, root, status, capability, policy_version, created_at) VALUES (?, 'grant-prune', 'generic_ai_history', '/tmp/prune-root', 'authorized', 'full', 'v1', ?)",
            (source_id, now),
        )
        # 1 个运行中的扫描（永不清理）
        conn.execute(
            "INSERT INTO automatic_memory_scans (scan_id, source_id, status, progress, updated_at) VALUES ('scan-running', ?, 'running', 0, ?)",
            (source_id, now),
        )
        conn.execute(
            "INSERT INTO automatic_memory_scan_items (scan_id, source_id, relative_path, sentinel, status, updated_at) VALUES ('scan-running', ?, 'r.jsonl', 'sr', 'processed', ?)",
            (source_id, now),
        )
        for index in range(completed):
            scan_id = f"scan-{index:03d}"
            conn.execute(
                "INSERT INTO automatic_memory_scans (scan_id, source_id, status, progress, total, updated_at) VALUES (?, ?, 'completed', 1, 1, ?)",
                (scan_id, source_id, f"2026-09-11T00:{index:02d}:00+00:00"),
            )
            conn.execute(
                "INSERT INTO automatic_memory_scan_items (scan_id, source_id, relative_path, sentinel, status, updated_at) VALUES (?, ?, ?, ?, 'processed', ?)",
                (scan_id, source_id, f"f-{index}.jsonl", f"s-{index}", now),
            )
        for index in range(2100):
            conn.execute(
                "INSERT INTO events (event_type, entity_type, entity_id, payload_json, created_at) VALUES ('structured_ingestion_completed', 'source', ?, ?, ?)",
                (source_id, '{"i":' + str(index) + "}", now),
            )
        conn.execute("COMMIT")
    return state, {"source_id": source_id}, "scan-running"


def test_prune_keeps_recent_scans_and_running_scan(tmp_path: Path):
    if SourceRegistry is None:
        raise AssertionError("SourceRegistry absent")
    state, _source, running_scan = _seed(tmp_path, completed=25)
    result = state.prune_automatic_memory_history(keep_scans_per_source=20, keep_events=2000)
    assert result["scans"] == 5
    remaining = [
        row for row in state.list_automatic_memory_scans()
        if row["status"] == "completed"
    ]
    assert len(remaining) == 20
    # 运行中的扫描永不清理
    ids = {row["scan_id"] for row in state.list_automatic_memory_scans()}
    assert running_scan in ids
    # 被裁剪扫描的条目一并删除（保留的是最近 20 次的条目）
    kept_scan_ids = {row["scan_id"] for row in remaining}
    for scan_id in kept_scan_ids:
        assert state.list_automatic_memory_scan_items(scan_id) is not None


def test_prune_caps_event_table(tmp_path: Path):
    if SourceRegistry is None:
        raise AssertionError("SourceRegistry absent")
    state, _source, _running = _seed(tmp_path, completed=3)
    result = state.prune_automatic_memory_history(keep_scans_per_source=20, keep_events=2000)
    assert result["events"] >= 100
    with state._connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert count <= 2000


def test_prune_is_idempotent(tmp_path: Path):
    if SourceRegistry is None:
        raise AssertionError("SourceRegistry absent")
    state, _source, _running = _seed(tmp_path, completed=10)
    first = state.prune_automatic_memory_history(keep_scans_per_source=20, keep_events=2000)
    second = state.prune_automatic_memory_history(keep_scans_per_source=20, keep_events=2000)
    assert first["scans"] == 0
    assert second["scans"] == 0
    assert second["events"] == 0


def test_prune_retires_only_old_successful_scan_work(tmp_path):
    from src.work.store import WorkStore
    from src.work.models import WorkItem, ExecutionEvent, PendingAction
    state = StateDatabase(tmp_path / 'state.db')
    work = WorkStore(state)
    for index in range(205):
        ident = f'automatic-memory:retired-{index:03}'
        work.create_work(WorkItem(work_id=ident, title='旧扫描', status='completed'))
        work.append_event(ExecutionEvent(work_id=ident, event_type='scan.completed'))
    for ident, status in [('automatic-memory:failed', 'failed'), ('automatic-memory:running', 'running'), ('owner-task', 'completed')]:
        work.create_work(WorkItem(work_id=ident, title='保留', status=status))
    work.add_pending_action(PendingAction(work_id='automatic-memory:retired-000', description='待主人处理'))
    state.prune_automatic_memory_history()
    with state._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM work_items WHERE work_id LIKE 'automatic-memory:retired-%'").fetchone()[0] == 201
        assert connection.execute('SELECT COUNT(*) FROM execution_events').fetchone()[0] == 201
    for ident in ['automatic-memory:failed', 'automatic-memory:running', 'owner-task', 'automatic-memory:retired-000']:
        assert work.get_work(ident) is not None
