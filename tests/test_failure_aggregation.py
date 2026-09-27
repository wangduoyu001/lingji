"""失败聚合（审计 2.2）：同来源同原因只留一行持久失败，并给主人可行动的待办。"""
from __future__ import annotations

from pathlib import Path

from src.storage.state_db import StateDatabase
from src.work.capture_bridge import CaptureWorkBridge
from src.work.models import WorkItem
from src.work.projector import WorkProjector
from src.work.store import WorkStore, failure_key_for, normalize_failure_reason

ADAPTER_ERROR = "No approved extraction adapter for source type: codex_rollout; input schema is unsupported, unauthorized, or malformed"


def _scan_work(store: WorkStore, index: int, source_id: str = "codex-source") -> WorkItem:
    work = WorkItem(
        work_id=f"automatic-memory:scan-{index}",
        title=f"扫描 codex_rollout {index}",
        source_id=source_id,
        status="accepted",
        owner_approved=True,
    )
    return store.create_work(work)


def _file(relative_path: str, job_id: str, error: str = ADAPTER_ERROR, attempts: int = 1) -> dict[str, str]:
    return {"relative_path": relative_path, "job_id": job_id, "error": error, "attempts": attempts}


def _bridge(tmp_path: Path) -> tuple[CaptureWorkBridge, WorkStore]:
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    return CaptureWorkBridge(store), store


def test_same_source_same_reason_failure_5_times_keeps_one_aggregated_row(tmp_path: Path):
    bridge, store = _bridge(tmp_path)
    for index in range(5):
        work = _scan_work(store, index)
        bridge.record_failure(
            work.work_id,
            stage="extraction",
            reason="一个或多个来源文件提取失败，其他来源仍可继续",
            retryable=False,
            evidence={"scan_id": f"scan-{index}"},
            file_failures=[
                _file(f"sessions/day-{index}/a.jsonl", f"LJ-JOB-A{index}"),
                _file(f"sessions/day-{index}/b.jsonl", f"LJ-JOB-B{index}"),
            ],
        )

    records = store.list_failure_records()
    assert len(records) == 1, "同一来源同一原因指纹必须只保留一行持久失败"
    record = records[0]
    assert record["occurrence_count"] == 5
    assert record["source_id"] == "codex-source"
    assert record["stage"] == "extraction"
    assert record["first_seen_at"] and record["last_seen_at"]
    detail = record["detail"]
    assert len(detail["files"]) == 10, "证据文件名最多保留 10 个"
    assert "sessions/day-0/a.jsonl" in detail["files"]
    assert detail["file_count"] == 10
    assert "LJ-JOB-A0" in detail["job_ids"] and len(detail["job_ids"]) <= 10
    assert detail["raw_error"].startswith("No approved extraction adapter")
    assert len(detail["raw_error"]) <= 500
    assert detail["attempts_max"] == 1
    # 对账口径：聚合后的失败总数，而不是逐扫描逐文件的行数。
    assert store.count_failure_records() == 1
    assert WorkProjector(store).failures()["total"] == 1


def test_two_other_reasons_form_their_own_rows(tmp_path: Path):
    bridge, store = _bridge(tmp_path)
    work = _scan_work(store, 0)
    bridge.record_failure(
        work.work_id, stage="extraction", reason="提取失败", retryable=False,
        file_failures=[_file("a.jsonl", "J1", error=ADAPTER_ERROR)],
    )
    bridge.record_failure(
        work.work_id, stage="extraction", reason="提取失败", retryable=False,
        file_failures=[_file("b.jsonl", "J2", error="History Inbox file exceeds size limit")],
    )
    bridge.record_failure(
        work.work_id, stage="extraction", reason="提取失败", retryable=False,
        file_failures=[_file("c.jsonl", "J3", error="input is malformed and cannot be parsed")],
    )

    records = store.list_failure_records()
    assert len(records) == 3, "不同原因指纹必须各自成行"
    assert {record["detail"]["raw_error"] for record in records} == {
        ADAPTER_ERROR,
        "History Inbox file exceeds size limit",
        "input is malformed and cannot be parsed",
    }
    assert store.count_failure_records() == 3


def test_failure_fingerprint_ignores_paths_timestamps_and_numbers(tmp_path: Path):
    assert failure_key_for("src", "extraction", normalize_failure_reason("read failed: /var/log/x/2026-09-01T10:00:00Z/a.jsonl")) == (
        failure_key_for("src", "extraction", normalize_failure_reason("read failed: /var/log/x/2026-09-02T23:59:59+08:00/b.jsonl"))
    )
    assert failure_key_for("src", "extraction", normalize_failure_reason("LJ-JOB-ABC123 lease expired 3")) == (
        failure_key_for("src", "extraction", normalize_failure_reason("LJ-JOB-XYZ789 lease expired 9"))
    )
    assert failure_key_for("src", "extraction", normalize_failure_reason(ADAPTER_ERROR)) != (
        failure_key_for("src", "extraction", normalize_failure_reason("History Inbox file exceeds size limit"))
    )
    assert failure_key_for("src-a", "extraction", "same") != failure_key_for("src-b", "extraction", "same")
    assert failure_key_for("src", "snapshot", "same") != failure_key_for("src", "extraction", "same")


def test_adapter_missing_failure_creates_single_owner_pending_action(tmp_path: Path):
    bridge, store = _bridge(tmp_path)
    first = _scan_work(store, 0)
    bridge.record_failure(
        first.work_id, stage="extraction", reason="提取失败", retryable=False,
        file_failures=[_file("a.jsonl", "J1")],
    )

    record = store.list_failure_records()[0]
    assert record["requires_owner"] is True
    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0].actor == "owner"
    assert pending[0].action_id == f"failure-owner:{record['failure_key']}"
    assert "适配器" in pending[0].description and "停用" in pending[0].description
    assert pending[0].work_id == first.work_id

    second = _scan_work(store, 1)
    bridge.record_failure(
        second.work_id, stage="extraction", reason="提取失败", retryable=False,
        file_failures=[_file("a.jsonl", "J2")],
    )
    pending = store.list_pending()
    assert len(pending) == 1, "同 key 的主人待办不得重复创建"
    assert pending[0].work_id == second.work_id
    assert "已累计 2 次" in pending[0].description
    assert store.list_failure_records()[0]["occurrence_count"] == 2


def test_transient_retryable_failure_routes_to_system_without_owner_pending(tmp_path: Path):
    bridge, store = _bridge(tmp_path)
    work = _scan_work(store, 0)
    bridge.record_failure(
        work.work_id, stage="snapshot", reason="automatic-memory snapshot failed: disk busy", retryable=True,
    )

    record = store.list_failure_records()[0]
    assert record["requires_owner"] is False
    assert record["retryable"] is True
    assert store.list_pending() == []


def test_completed_extraction_resolves_stale_owner_failure_action(tmp_path: Path):
    bridge, store = _bridge(tmp_path)
    failed_work = _scan_work(store, 0)
    bridge.record_failure(
        failed_work.work_id, stage="extraction", reason="提取失败", retryable=False,
        file_failures=[_file("a.jsonl", "J1")],
    )
    assert len(store.list_pending()) == 1

    done_work = _scan_work(store, 1)
    bridge.complete_extraction(done_work.work_id, "处理完成", evidence={})

    assert store.list_pending() == [], "来源恢复后，过时的主人待办必须自动关闭"


def test_aggregated_failure_visible_from_every_failed_work_of_same_source(tmp_path: Path):
    bridge, store = _bridge(tmp_path)
    works = [_scan_work(store, index) for index in range(3)]
    for index, work in enumerate(works):
        bridge.record_failure(
            work.work_id, stage="extraction", reason="提取失败", retryable=False,
            file_failures=[_file(f"day-{index}.jsonl", f"J{index}")],
        )

    projector = WorkProjector(store)
    for work in works:
        fact = projector.fact(work.work_id)
        assert fact["failure"] is not None
        assert fact["failure"]["occurrence_count"] == 3
        assert fact["failure"]["detail"]["raw_error"].startswith("No approved extraction adapter")
    history = projector.history(limit=10)
    assert history["failure_total"] == 1


def test_legacy_unaggregated_failure_rows_merge_once_on_startup(tmp_path: Path):
    state_path = tmp_path / "state.db"
    store = WorkStore(StateDatabase(state_path))
    for index in range(4):
        _scan_work(store, index)
    with store.state._lock, store.state._connection() as connection:
        for index in range(4):
            connection.execute(
                "INSERT INTO work_failures(failure_id, work_id, stage, reason, retryable, created_at) VALUES (?, ?, ?, ?, 0, ?)",
                (
                    f"failure:automatic-memory:scan-{index}:extraction",
                    f"automatic-memory:scan-{index}",
                    "extraction",
                    "一个或多个来源文件提取失败，其他来源仍可继续",
                    f"2026-09-01T00:00:0{index}+00:00",
                ),
            )
    reopened = WorkStore(StateDatabase(state_path))

    records = reopened.list_failure_records()
    assert len(records) == 1, "旧版逐行失败必须在启动迁移时合并"
    assert records[0]["occurrence_count"] == 4
    assert records[0]["first_seen_at"] == "2026-09-01T00:00:00+00:00"
    assert records[0]["last_seen_at"] == "2026-09-01T00:00:03+00:00"
    assert reopened.get_failure("automatic-memory:scan-0").occurrence_count == 4
    assert reopened.count_failure_records() == 1


def test_new_failure_key_appends_one_idempotent_audit_event(tmp_path: Path):
    bridge, store = _bridge(tmp_path)
    for index in range(3):
        work = _scan_work(store, index)
        bridge.record_failure(
            work.work_id, stage="extraction", reason="提取失败", retryable=False,
            file_failures=[_file("a.jsonl", f"J{index}")],
        )
        other = _scan_work(store, 100 + index)
        bridge.record_failure(
            other.work_id, stage="extraction", reason="提取失败", retryable=False,
            file_failures=[_file("b.jsonl", "JX", error="History Inbox file exceeds size limit")],
        )

    events = [event for event in store.state.recent_events(limit=100) if event["event_type"] == "work.failure_aggregated"]
    assert len(events) == 2, "每个失败指纹只留一条审计事件"
    assert {event["entity_id"] for event in events} == {"codex-source"}
