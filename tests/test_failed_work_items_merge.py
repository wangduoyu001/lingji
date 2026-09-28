"""历史 failed work_items 的回溯归并（失败治理最后一公里）。

聚合上线之前，同一持久故障源每次扫描都会新写一行 failed work_item，主人的工作
履历因此整屏红字（生产库曾积压 1,297 行）。这里验证：启动迁移按来源归并、merged
行退出投影、迁移幂等、审计留痕，以及新失败不再逐扫描累积 failed 行。
"""
from __future__ import annotations

from pathlib import Path

from src.storage.state_db import StateDatabase
from src.work.capture_bridge import CaptureWorkBridge
from src.work.models import WorkItem
from src.work.projector import WorkProjector
from src.work.store import WorkStore


def _scan_work(store: WorkStore, scan_id: str, source_id: str, *, created_at: str | None = None, title: str | None = None) -> WorkItem:
    work = WorkItem(
        work_id=f"automatic-memory:scan-{scan_id}",
        title=title or f"扫描 codex_rollout",
        source_id=source_id,
        status="accepted",
        owner_approved=True,
        created_at=created_at or f"2026-09-01T00:00:{int(scan_id) % 60:02d}",
    )
    return store.create_work(work)


def _fail(store: WorkStore, work_id: str, *, occurred_at: str) -> None:
    store.apply_extraction_transition(
        work_id,
        "failed",
        summary="No approved extraction adapter for source type: codex_rollout",
        evidence={"stage": "extraction"},
        stage="extraction",
        retryable=False,
        occurred_at=occurred_at,
        skip_failure_record=True,
    )


def _statuses(store: WorkStore) -> dict[str, list[str]]:
    with store.state._connection() as connection:
        rows = connection.execute("SELECT status, work_id FROM work_items").fetchall()
    grouped: dict[str, list[str]] = {}
    for status, work_id in rows:
        grouped.setdefault(str(status), []).append(str(work_id))
    return grouped


def test_five_failed_two_completed_one_accepted_collapses_to_one_representative(tmp_path: Path):
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    for index in range(5):
        _scan_work(store, str(index), "src-a", created_at=f"2026-09-01T00:0{index}:00")
        _fail(store, f"automatic-memory:scan-{index}", occurred_at=f"2026-09-02T00:0{index}:00")
    good = WorkItem(work_id="automatic-memory:scan-good", title="扫描 ok", source_id="src-a", status="completed", owner_approved=True, created_at="2026-09-01T09:00:00")
    accepted = WorkItem(work_id="automatic-memory:scan-accepted", title="扫描 new", source_id="src-a", status="accepted", owner_approved=True, created_at="2026-09-01T10:00:00")
    store.create_work(good)
    store.create_work(accepted)

    statuses = _statuses(store)
    assert len(statuses.get("failed", [])) == 1, "5 条同源失败必须只剩 1 条聚合代表"
    assert len(statuses.get("merged", [])) == 4
    assert sorted(statuses.get("completed", [])) == ["automatic-memory:scan-good"], "completed 行永不参与归并"
    assert statuses.get("accepted") == ["automatic-memory:scan-accepted"], "accepted 行永不参与归并"

    representative = store.get_work(statuses["failed"][0])
    assert representative.created_at == "2026-09-01T00:00:00", "必须保留最早创建的一行作代表"
    assert "历史失败已聚合" in representative.title and "共 5 次扫描" in representative.title
    assert representative.updated_at == "2026-09-02T00:04:00", "代表行 updated_at 刷新为组内最新"


def test_two_sources_merge_into_separate_groups(tmp_path: Path):
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    for index in range(3):
        _scan_work(store, f"a{index}", "src-a", created_at=f"2026-09-01T00:0{index}:00")
        _fail(store, f"automatic-memory:scan-a{index}", occurred_at=f"2026-09-02T00:0{index}:00")
    for index in range(2):
        _scan_work(store, f"b{index}", "src-b", created_at=f"2026-09-03T00:0{index}:00", title="扫描 zcode_session")
        _fail(store, f"automatic-memory:scan-b{index}", occurred_at=f"2026-09-04T00:0{index}:00")

    statuses = _statuses(store)
    assert len(statuses.get("failed", [])) == 2, "两个来源各自保留一个聚合代表"
    assert len(statuses.get("merged", [])) == 3
    with store.state._connection() as connection:
        titles = dict(connection.execute("SELECT source_id, title FROM work_items WHERE status = 'failed'").fetchall())
    assert "共 3 次扫描" in titles["src-a"]
    assert "共 2 次扫描" in titles["src-b"]


def test_migration_is_idempotent_across_reopen(tmp_path: Path):
    state_path = tmp_path / "state.db"
    store = WorkStore(StateDatabase(state_path))
    for index in range(4):
        _scan_work(store, str(index), "src-a", created_at=f"2026-09-01T00:0{index}:00")
        _fail(store, f"automatic-memory:scan-{index}", occurred_at=f"2026-09-02T00:0{index}:00")
    first_snapshot = _statuses(store)
    representative_title = store.get_work(first_snapshot["failed"][0]).title

    reopened = WorkStore(StateDatabase(state_path))
    assert _statuses(reopened) == first_snapshot, "重开数据库不得再次改动归并结果"
    assert reopened.get_work(first_snapshot["failed"][0]).title == representative_title

    # 再跑一遍迁移主体本身也必须是无操作。
    with reopened.state._lock, reopened.state._connection() as connection:
        WorkStore._merge_legacy_failed_work_items(connection)
    assert _statuses(reopened) == first_snapshot


def _merge_audits(store: WorkStore) -> list[dict]:
    import json

    details: list[dict] = []
    for event in store.state.recent_events(limit=100):
        if event["event_type"] != "work.failed_items_merged":
            continue
        payload = event["payload_json"]
        details.append(json.loads(payload) if isinstance(payload, str) else payload)
    return details


def test_migration_merge_writes_audit_events_with_row_counts(tmp_path: Path):
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    with store.state._lock, store.state._connection() as connection:
        for index in range(3):
            connection.execute(
                "INSERT INTO work_items(work_id, title, source_id, status, owner_approved, created_at, updated_at) VALUES (?, ?, ?, 'failed', 1, ?, ?)",
                (f"automatic-memory:scan-{index}", "扫描 codex_rollout", "src-a", f"2026-09-01T00:0{index}:00", f"2026-09-02T00:0{index}:00"),
            )

    reopened = WorkStore(StateDatabase(tmp_path / "state.db"))
    audits = _merge_audits(reopened)
    assert len(audits) == 1, "批量历史积压在启动迁移时归并，每来源留一条审计"
    detail = audits[0]
    assert detail["source_id"] == "src-a"
    assert detail["before_failed_rows"] == 3 and detail["after_failed_rows"] == 1
    assert detail["merged_rows"] == 2 and detail["represented_scans"] == 3
    assert detail["representative_work_id"] == "automatic-memory:scan-0"


def test_runtime_convergence_writes_incremental_audit_events(tmp_path: Path):
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    for index in range(3):
        _scan_work(store, str(index), "src-a", created_at=f"2026-09-01T00:0{index}:00")
        _fail(store, f"automatic-memory:scan-{index}", occurred_at=f"2026-09-02T00:0{index}:00")

    audits = _merge_audits(store)
    audits.sort(key=lambda item: item["represented_scans"])
    assert len(audits) == 2, "第 2、3 次失败各触发一轮真实归并，各留一条审计"
    assert all(item["before_failed_rows"] == 2 and item["after_failed_rows"] == 1 for item in audits)
    assert [item["represented_scans"] for item in audits] == [2, 3], "聚合计数随新失败单调增长"


def test_history_hides_merged_rows_and_representative_carries_aggregate_title(tmp_path: Path):
    bridge = CaptureWorkBridge(WorkStore(StateDatabase(tmp_path / "state.db")))
    store = bridge.store
    for index in range(5):
        _scan_work(store, str(index), "src-a", created_at=f"2026-09-01T00:0{index}:00")
        bridge.record_failure(
            f"automatic-memory:scan-{index}",
            stage="extraction",
            reason="一个或多个来源文件提取失败，其他来源仍可继续",
            retryable=False,
            file_failures=[{"relative_path": f"day-{index}.jsonl", "job_id": f"J{index}", "error": "No approved extraction adapter"}],
        )

    projector = WorkProjector(store)
    history = projector.history(limit=20)
    failed_items = [item for item in history["items"] if item["work"]["status"] == "failed"]
    assert len(failed_items) == 1, "履历不得逐条展示被合并的失败"
    assert history["total"] == 1, "分页总数必须与过滤后的可见条目一致"
    assert history["failure_total"] == 1
    representative = failed_items[0]["work"]
    assert "历史失败已聚合" in representative["title"] and "共 5 次扫描" in representative["title"]
    assert all(item["work"]["status"] != "merged" for item in history["items"])


def test_production_shape_1297_failed_rows_collapse_to_one_per_source(tmp_path: Path):
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    with store.state._lock, store.state._connection() as connection:
        for index in range(975):
            connection.execute(
                "INSERT INTO work_items(work_id, title, source_id, status, owner_approved, created_at, updated_at) VALUES (?, ?, ?, 'failed', 1, ?, ?)",
                (f"automatic-memory:scan-p975-{index}", "扫描 codex_rollout", "src-449d", f"2026-09-{(index % 27) + 1:02d}T00:00:00", f"2026-09-20T00:00:00"),
            )
        for index in range(322):
            connection.execute(
                "INSERT INTO work_items(work_id, title, source_id, status, owner_approved, created_at, updated_at) VALUES (?, ?, ?, 'failed', 1, ?, ?)",
                (f"automatic-memory:scan-p322-{index}", "扫描 codex_rollout", "src-5b53", f"2026-09-{(index % 27) + 1:02d}T00:00:00", f"2026-09-21T00:00:00"),
            )
        for index in range(72):
            connection.execute(
                "INSERT INTO work_items(work_id, title, source_id, status, owner_approved, created_at, updated_at) VALUES (?, ?, ?, 'accepted', 1, ?, ?)",
                (f"automatic-memory:scan-acc-{index}", "扫描 codex_rollout", f"src-acc-{index}", "2026-09-25T00:00:00", "2026-09-25T00:00:00"),
            )
        for index in range(317):
            connection.execute(
                "INSERT INTO work_items(work_id, title, source_id, status, owner_approved, created_at, updated_at) VALUES (?, ?, ?, 'completed', 1, ?, ?)",
                (f"automatic-memory:scan-done-{index}", "扫描 codex_rollout", f"src-done-{index}", "2026-09-26T00:00:00", "2026-09-26T00:00:00"),
            )

    reopened = WorkStore(StateDatabase(tmp_path / "state.db"))
    with reopened.state._connection() as connection:
        failed = connection.execute("SELECT source_id, COUNT(*) FROM work_items WHERE status='failed' GROUP BY source_id").fetchall()
        merged = connection.execute("SELECT COUNT(*) FROM work_items WHERE status='merged'").fetchone()[0]
    assert dict(failed) == {"src-449d": 1, "src-5b53": 1}, "生产形态必须每源收敛为 1 条"
    assert merged == 1295
    assert reopened.count_work() == 2 + 72 + 317, "履历总数只含代表行与 completed/accepted 行"

    projector = WorkProjector(reopened)
    history = projector.history(limit=100)
    assert sum(1 for item in history["items"] if item["work"]["status"] == "failed") <= 2


def test_new_failed_scan_after_merge_does_not_grow_failed_rows(tmp_path: Path):
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    for index in range(3):
        _scan_work(store, str(index), "src-a", created_at=f"2026-09-01T00:0{index}:00")
        _fail(store, f"automatic-memory:scan-{index}", occurred_at=f"2026-09-02T00:0{index}:00")
    statuses = _statuses(store)
    assert len(statuses.get("failed", [])) == 1

    # 迁移收敛之后，持久故障源再来一次失败扫描：不得产生第二条 failed 履历行。
    _scan_work(store, "99", "src-a", created_at="2026-09-05T00:00:00")
    _fail(store, "automatic-memory:scan-99", occurred_at="2026-09-05T12:00:00")
    statuses = _statuses(store)
    assert len(statuses.get("failed", [])) == 1, "新失败只更新聚合代表，不新增 failed 行"
    assert len(statuses.get("merged", [])) == 3
    representative = store.get_work(statuses["failed"][0])
    assert "共 4 次扫描" in representative.title, "代表行标题计数必须随新失败增长"
    assert representative.updated_at == "2026-09-05T12:00:00"
