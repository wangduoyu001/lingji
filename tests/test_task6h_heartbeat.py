from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.automatic_memory.runtime import AutomaticMemoryRuntime
from src.automatic_memory.scheduler import AutomaticMemoryScheduler
from src.automatic_memory.source_registry import SourceRegistry
from src.storage import StateDatabase
from src.work.models import WorkItem


class _Worker:
    running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def status(self):
        return {"running": self.running, "queue": {"queued": 0}}


def _runtime(tmp_path: Path, *, heartbeat_seconds: float = 0.1):
    state = StateDatabase(tmp_path / "lingji_state.db")
    queue = type("Queue", (), {"path": state.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()
    registry = SourceRegistry(state)
    scheduler = AutomaticMemoryScheduler(
        state,
        registry,
        scan_runner=lambda *_args: None,
        poll_seconds=60.0,
        heartbeat_seconds=heartbeat_seconds,
    )
    runtime = AutomaticMemoryRuntime(
        state_db=state,
        queue=queue,
        pipeline=pipeline,
        registry=registry,
        scheduler=scheduler,
        worker=_Worker(),
    )
    return runtime, state, scheduler


def _wait_for_heartbeat(runtime: AutomaticMemoryRuntime, timeout: float = 2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = runtime.status()
        if status.get("scheduler_heartbeat_at"):
            return status
        time.sleep(0.01)
    raise AssertionError("scheduler heartbeat was not persisted")


def test_idle_runtime_persists_instance_bound_heartbeat_and_refreshes_without_reconciliation(
    tmp_path: Path,
):
    runtime, state, scheduler = _runtime(tmp_path)
    runtime.start()
    try:
        first = _wait_for_heartbeat(runtime)
        assert first["state"] == "running"
        assert first["scheduler_heartbeat_age"] <= 1.0
        assert first["scheduler_heartbeat_instance"] == scheduler.instance_id
        assert first["scheduler_heartbeat_generation"] == scheduler.generation
        time.sleep(0.2)
        second = runtime.status()
        assert second["scheduler_heartbeat_at"] != first["scheduler_heartbeat_at"]
        assert second["scheduler_heartbeat_age"] <= 1.0
        assert len(state.list_automatic_memory_scans()) == 0
        assert len(state.recent_events(limit=100)) == 0
    finally:
        runtime.stop()


def test_pause_continues_heartbeat_and_stop_marks_instance_stopped(tmp_path: Path):
    runtime, state, scheduler = _runtime(tmp_path)
    runtime.start()
    paused = runtime.pause()
    assert paused["state"] == "paused"
    paused_at = paused["scheduler_heartbeat_at"]
    time.sleep(0.2)
    assert runtime.status()["scheduler_heartbeat_at"] != paused_at
    runtime.stop()
    stopped = runtime.status()
    assert stopped["state"] == "stopped"
    assert stopped["scheduler_heartbeat_state"] == "stopped"
    assert stopped["scheduler_heartbeat_instance"] == scheduler.instance_id
    with sqlite3.connect(state.path) as connection:
        row = connection.execute(
            "SELECT state FROM automatic_memory_heartbeats WHERE instance_id = ?",
            (scheduler.instance_id,),
        ).fetchone()
    assert row == ("stopped",)


def test_new_runtime_uses_new_instance_and_old_running_heartbeat_is_not_reused(
    tmp_path: Path,
):
    first, state, first_scheduler = _runtime(tmp_path)
    first.start()
    _wait_for_heartbeat(first)
    first.stop()
    second, _state, second_scheduler = _runtime(tmp_path)
    assert second_scheduler.instance_id != first_scheduler.instance_id
    second.start()
    try:
        current = _wait_for_heartbeat(second)
        assert current["scheduler_heartbeat_instance"] == second_scheduler.instance_id
        assert current["scheduler_heartbeat_instance"] != first_scheduler.instance_id
        assert state.list_automatic_memory_heartbeats(instance_id=first_scheduler.instance_id)[0]["state"] == "stopped"
    finally:
        second.stop()


def test_active_scan_refreshes_work_fact_without_event_growth(tmp_path: Path):
    runtime, state, scheduler = _runtime(tmp_path)
    work_id = "automatic-memory:scan-active"
    runtime.work_store.create_work(WorkItem(work_id=work_id, title="active scan", status="running"))
    state.upsert_automatic_memory_heartbeat(
        scheduler.instance_id, 0, "running", heartbeat_at=datetime.now(timezone.utc).isoformat()
    )
    with state._lock, state._connection() as connection:
        connection.execute(
            "INSERT INTO automatic_memory_scans(scan_id, source_id, status, updated_at) VALUES (?, ?, 'running', ?)",
            ("scan-active", "source-active", datetime.now(timezone.utc).isoformat()),
        )
    before = len(runtime.work_store.list_events(work_id))
    runtime._touch_active_scan_work()
    after = runtime.work_store.get_work(work_id)
    assert after is not None and after.updated_at
    assert len(runtime.work_store.list_events(work_id)) == before


def test_clock_jump_is_degraded_and_db_write_failure_is_fail_closed_then_recovers(
    tmp_path: Path,
):
    runtime, state, scheduler = _runtime(tmp_path)
    runtime.start()
    try:
        _wait_for_heartbeat(runtime)
        future = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        state.upsert_automatic_memory_heartbeat(
            scheduler.instance_id,
            scheduler.generation,
            "running",
            heartbeat_at=future,
        )
        assert runtime.status()["state"] == "degraded"
        original = state.upsert_automatic_memory_heartbeat
        state.upsert_automatic_memory_heartbeat = lambda *args, **kwargs: (_ for _ in ()).throw(sqlite3.OperationalError("locked"))
        time.sleep(0.15)
        failed = runtime.status()
        assert failed["state"] == "degraded"
        assert "heartbeat" in (failed["scheduler_heartbeat_reason"] or "")
        state.upsert_automatic_memory_heartbeat = original
        time.sleep(0.15)
        assert runtime.status()["scheduler_heartbeat_state"] == "running"
    finally:
        state.upsert_automatic_memory_heartbeat = original if "original" in locals() else state.upsert_automatic_memory_heartbeat
        runtime.stop()


def test_heartbeat_cadence_does_not_run_reconciliation_at_heartbeat_frequency(
    tmp_path: Path,
):
    runtime, state, scheduler = _runtime(tmp_path, heartbeat_seconds=0.05)
    calls = 0
    original = state.claim_due_scheduler_jobs

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    state.claim_due_scheduler_jobs = counted
    runtime.start()
    try:
        time.sleep(0.25)
        assert calls <= 2
    finally:
        runtime.stop()


def test_active_work_heartbeat_failure_is_persisted_degraded_and_recovers(
    tmp_path: Path,
):
    runtime, _state, scheduler = _runtime(tmp_path)
    runtime.start()
    try:
        _wait_for_heartbeat(runtime)
        failures = 0

        def failing_touch():
            nonlocal failures
            failures += 1
            raise OSError("work fact database locked")

        scheduler.heartbeat_work_callback = failing_touch
        scheduler._heartbeat_tick()
        failed = runtime.status()
        assert failed["state"] == "degraded"
        assert "active work heartbeat" in (failed["scheduler_heartbeat_reason"] or "")
        assert "locked" in (failed["scheduler_heartbeat_last_error"] or "")
        assert failures == 1

        scheduler.heartbeat_work_callback = lambda: None
        scheduler._heartbeat_tick()
        recovered = runtime.status()
        assert recovered["state"] == "running"
        assert recovered["scheduler_heartbeat_state"] == "running"
        assert recovered["scheduler_heartbeat_last_error"] is None
    finally:
        runtime.stop()


def test_active_work_heartbeat_failure_isolated_per_source(tmp_path: Path):
    runtime, state, scheduler = _runtime(tmp_path)
    runtime.work_store.create_work(WorkItem(work_id="automatic-memory:scan-a", title="a", status="running"))
    runtime.work_store.create_work(WorkItem(work_id="automatic-memory:scan-b", title="b", status="running"))
    now = datetime.now(timezone.utc).isoformat()
    with state._lock, state._connection() as connection:
        for scan_id, source_id in (("scan-a", "source-a"), ("scan-b", "source-b")):
            connection.execute(
                "INSERT INTO automatic_memory_scans(scan_id, source_id, status, updated_at) VALUES (?, ?, 'running', ?)",
                (scan_id, source_id, now),
            )
    original = runtime.work_store.touch_work

    def isolated_touch(work_id: str, *, updated_at: str | None = None):
        if work_id.endswith("scan-a"):
            raise OSError("source-a locked")
        return original(work_id, updated_at=updated_at)

    runtime.work_store.touch_work = isolated_touch
    runtime.start()
    try:
        scheduler._heartbeat_tick()
        assert runtime.status()["state"] == "degraded"
        assert runtime.work_store.get_work("automatic-memory:scan-b").updated_at
    finally:
        runtime.work_store.touch_work = original
        runtime.stop()
