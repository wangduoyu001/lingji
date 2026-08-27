from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
import threading

import pytest

from src.automatic_memory.models import AuthorizationScope, SourceRecord
from src.automatic_memory.checkpoint import SnapshotJobRunner
from src.automatic_memory.snapshot import ConsistentSnapshot
from src.extraction.queue import SQLiteExtractionQueue
from src.automatic_memory.source_registry import SourceRegistry
from src.automatic_memory.scheduler import AutomaticMemoryScheduler, ReconciliationReport
from src.automatic_memory.watcher import AutomaticMemoryWatcher
from src.storage.state_db import StateDatabase


def registered(tmp_path: Path) -> tuple[StateDatabase, SourceRegistry, str]:
    db = StateDatabase(tmp_path / "state.db")
    registry = SourceRegistry(db)
    scope = AuthorizationScope(
        "grant-1", ("codex",), (str(tmp_path),), datetime.now(timezone.utc), None, True
    )
    return db, registry, registry.register(scope, "codex", str(tmp_path)).source_id


def test_reconciliation_admits_once_and_persists_report(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    calls: list[tuple[str, str]] = []

    def scan(scan_id: str, source_id: str, reason: str):
        calls.append((source_id, reason))
        return ReconciliationReport(1, 1, 0, (), True)

    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=scan)
    first = scheduler.reconcile(source_id, reason="event")
    second = scheduler.reconcile(source_id, reason="event")
    assert first.complete and second.complete
    assert calls == [(source_id, "event"), (source_id, "event")]
    assert len(scheduler.status()) == 2
    assert any(event["event_type"] == "automatic_memory_reconciliation" for event in db.recent_events(10))


def test_start_stop_pause_resume_and_restart_use_persisted_cron_jobs(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=lambda *args: None, poll_seconds=0.01)
    scheduler.start()
    names = {job["name"] for job in db.list_scheduler_jobs()}
    assert f"automatic_memory:{source_id}:reconciliation" in names
    assert f"automatic_memory:{source_id}:integrity" in names
    scheduler.pause()
    assert all(not job["enabled"] for job in db.list_scheduler_jobs())
    scheduler.resume()
    assert all(job["enabled"] for job in db.list_scheduler_jobs())
    scheduler.stop()
    restarted = AutomaticMemoryScheduler(db, registry, scan_runner=lambda *args: None, poll_seconds=0.01)
    restarted.start()
    # Startup reconciliation is intentionally persistent and may already have
    # admitted a scan before the assertion.
    assert all(item.source_id == source_id for item in restarted.status())
    restarted.stop()


def test_cleanup_retry_retries_cron_and_preserves_unrelated_error(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    release = threading.Event()
    stop_seen = threading.Event()

    def backend(_root, **_kwargs):
        while not release.is_set():
            if _kwargs["stop_event"].is_set():
                stop_seen.set()
            time.sleep(0.01)
        yield set()

    class RetryingCron:
        def __init__(self):
            self.state_db = db
            self.running = False
            self.stop_calls = 0
            self._thread = None

        def add_job(self, *_args, **_kwargs):
            return None

        def set_jobs_enabled(self, *_args, **_kwargs):
            return None

        def start(self, _runner):
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

        def _loop(self):
            while self.running:
                time.sleep(0.005)

        def stop(self):
            self.stop_calls += 1
            if self.stop_calls == 1:
                raise RuntimeError("cron cleanup failed")
            self.running = False
            if self._thread is not None:
                self._thread.join(timeout=1)

    watcher = AutomaticMemoryWatcher(
        source_provider=lambda source_id: next(
            item for item in registry.list_sources() if item.source_id == source_id
        ),
        on_change=lambda _source_id: None,
        watch_backend=backend,
        stop_timeout_seconds=0.01,
    )
    cron = RetryingCron()
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda *_args: ReconciliationReport(0, 0, 0, (), True),
        watcher=watcher,
        cron=cron,
        poll_seconds=0.01,
    )
    scheduler.start()
    assert source_id in watcher.running_sources()
    assert stop_seen.is_set() is False
    scheduler._source_cleanup_errors["other-source"] = "unrelated source error"

    with pytest.raises(RuntimeError, match="cron cleanup failed"):
        scheduler.stop()
    assert cron.stop_calls == 1
    assert cron.running is True
    assert "other-source" in scheduler.source_cleanup_errors

    release.set()
    deadline = time.monotonic() + 1.0
    while watcher.running_sources() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert watcher.running_sources() == ()

    scheduler.stop()
    assert cron.stop_calls == 2
    assert cron.running is False
    assert scheduler.source_cleanup_errors == {"other-source": "unrelated source error"}


def test_scheduler_start_waits_for_inflight_stop_cleanup(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    release = threading.Event()
    stop_seen = threading.Event()
    backend_calls = 0

    def backend(_root, **kwargs):
        nonlocal backend_calls
        backend_calls += 1
        if backend_calls > 1:
            while not kwargs["stop_event"].wait(0.01):
                yield set()
            return
        while not release.is_set():
            if kwargs["stop_event"].is_set():
                stop_seen.set()
            time.sleep(0.01)
        yield set()

    watcher = AutomaticMemoryWatcher(
        source_provider=lambda source_id: next(
            item for item in registry.list_sources() if item.source_id == source_id
        ),
        on_change=lambda _source_id: None,
        watch_backend=backend,
        stop_timeout_seconds=0.2,
    )
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda *_args: ReconciliationReport(0, 0, 0, (), True),
        watcher=watcher,
        poll_seconds=0.01,
    )
    scheduler.start()
    stop_thread = threading.Thread(target=scheduler.stop)
    stop_thread.start()
    assert stop_seen.wait(1)

    start_returned = threading.Event()

    def restart():
        scheduler.start()
        start_returned.set()

    start_thread = threading.Thread(target=restart)
    start_thread.start()
    assert not start_returned.wait(0.05)

    release.set()
    stop_thread.join(timeout=2)
    start_thread.join(timeout=2)
    assert not stop_thread.is_alive()
    assert not start_thread.is_alive()
    assert scheduler._running is True
    assert scheduler.cron.running is True
    deadline = time.monotonic() + 1.0
    while watcher.running_sources() != (source_id,) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert watcher.running_sources() == (source_id,)

    scheduler.stop()


def test_scheduler_stop_after_start_is_serialized_and_idempotent(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda *_args: ReconciliationReport(0, 0, 0, (), True),
        poll_seconds=0.01,
    )
    started = threading.Event()
    start_thread = threading.Thread(target=lambda: (scheduler.start(), started.set()))
    start_thread.start()
    assert started.wait(1)
    start_thread.join(timeout=1)

    stop_thread = threading.Thread(target=scheduler.stop)
    stop_thread.start()
    stop_thread.join(timeout=2)
    assert not stop_thread.is_alive()
    assert scheduler._running is False
    assert scheduler.watcher.running_sources() == ()
    scheduler.stop()


def test_restart_marks_incremental_job_due_and_reuses_running_scan(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    first_scan = registry.start_scan(source_id)
    calls: list[str] = []

    def scan(scan_id: str, current_id: str, reason: str):
        calls.append(scan_id)
        return ReconciliationReport(0, 0, 0, (), True)

    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=scan, poll_seconds=0.01)
    scheduler.start()
    scheduler.stop()
    assert calls
    assert calls[0] == first_scan.scan_id
    job = next(item for item in db.list_scheduler_jobs() if item["name"].endswith(":reconciliation"))
    assert job["last_finished_at"] is not None


def test_reconciliation_runs_after_event_silence(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    calls: list[str] = []

    def scan(scan_id: str, current_id: str, reason: str):
        calls.append(reason)
        return ReconciliationReport(0, 0, 0, (), True)

    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=scan,
        poll_seconds=0.01,
        reconciliation_seconds=0.1,
    )
    scheduler.start()
    deadline = time.monotonic() + 1.0
    while len(calls) < 2 and time.monotonic() < deadline:
        time.sleep(0.02)
    scheduler.stop()
    assert calls[0] == "reconciliation"
    assert len(calls) >= 2


def test_daily_integrity_job_runs_without_event(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    calls: list[str] = []

    def scan(scan_id: str, current_id: str, reason: str):
        calls.append(reason)
        return ReconciliationReport(0, 0, 0, (), True)

    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=scan,
        poll_seconds=0.01,
        reconciliation_seconds=60,
        integrity_seconds=0.1,
    )
    scheduler.start()
    deadline = time.monotonic() + 1.0
    while "integrity" not in calls and time.monotonic() < deadline:
        time.sleep(0.02)
    scheduler.stop()
    assert "integrity" in calls


def test_same_source_reconciliation_is_single_flight(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    def scan(scan_id: str, current_id: str, reason: str):
        calls.append(scan_id)
        entered.set()
        assert release.wait(1)
        return ReconciliationReport(1, 1, 0, (), True)

    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=scan)
    results: list[ReconciliationReport] = []
    first = threading.Thread(target=lambda: results.append(scheduler.reconcile(source_id, reason="event")))
    second = threading.Thread(target=lambda: results.append(scheduler.reconcile(source_id, reason="reconciliation")))
    first.start()
    assert entered.wait(1)
    second.start()
    time.sleep(0.05)
    assert len(calls) == 1
    release.set()
    first.join()
    second.join()
    assert len(calls) == 1
    assert results == [results[0], results[0]]


def test_incomplete_report_fails_persisted_scan(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda *args: ReconciliationReport(2, 1, 0, ("one file failed",), False),
    )
    report = scheduler.reconcile(source_id)
    assert not report.complete
    assert scheduler.status()[0].status == "failed"
    assert scheduler.status()[0].last_error == "one file failed"


def test_revoke_disables_jobs_and_stops_source_watcher(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=lambda *args: None, poll_seconds=0.01)
    scheduler.start()
    registry.revoke(source_id)
    scheduler.reconcile(source_id, reason="reconciliation")
    assert all(not job["enabled"] for job in db.list_scheduler_jobs())
    assert source_id not in scheduler.watcher.running_sources()
    scheduler.resume()
    assert all(not job["enabled"] for job in db.list_scheduler_jobs())
    scheduler.stop()


def test_revoke_during_runner_cannot_resurrect_cancelled_scan(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    entered = threading.Event()
    release = threading.Event()

    def scan(scan_id: str, current_id: str, reason: str):
        entered.set()
        assert release.wait(1)
        return ReconciliationReport(1, 1, 0, (), True)

    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=scan)
    result: list[ReconciliationReport] = []
    worker = threading.Thread(target=lambda: result.append(scheduler.reconcile(source_id)))
    worker.start()
    assert entered.wait(1)
    registry.revoke(source_id)
    release.set()
    worker.join()
    assert result and not result[0].complete
    assert scheduler.status()[0].status == "cancelled"


def test_failed_scan_is_retried_on_next_trigger(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    calls = 0

    def scan(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ReconciliationReport(2, 1, 0, ("temporary failure",), False)
        return ReconciliationReport(2, 2, 0, (), True)

    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=scan)
    assert not scheduler.reconcile(source_id).complete
    assert scheduler.reconcile(source_id).complete
    assert calls == 2
    assert scheduler.status()[0].status == "completed"


def test_none_runner_result_is_a_failed_scan(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=lambda *args: None)
    report = scheduler.reconcile(source_id)
    assert not report.complete
    assert "report" in report.errors[0]
    assert scheduler.status()[0].status == "failed"


def test_direct_revoke_stops_only_that_source_immediately(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    second_id = registry.register(
        AuthorizationScope(
            "grant-2", ("codex",), (str(tmp_path),), datetime.now(timezone.utc), None, True
        ),
        "codex",
        str(tmp_path),
    ).source_id
    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=lambda *args: ReconciliationReport(0, 0, 0, (), True), poll_seconds=0.01)
    scheduler.start()
    assert source_id in scheduler.watcher.running_sources()
    assert second_id in scheduler.watcher.running_sources()
    registry.revoke(source_id)
    assert source_id not in scheduler.watcher.running_sources()
    assert second_id in scheduler.watcher.running_sources()
    jobs = {job["name"]: job for job in db.list_scheduler_jobs()}
    assert not any(source_id in name and job["enabled"] for name, job in jobs.items())
    assert any(second_id in name and job["enabled"] for name, job in jobs.items())
    scheduler.stop()


def test_direct_unsupported_stops_source_and_disables_jobs(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=lambda *args: ReconciliationReport(0, 0, 0, (), True), poll_seconds=0.01)
    scheduler.start()
    registry.set_status(source_id, "unsupported", reason="no official export")
    assert source_id not in scheduler.watcher.running_sources()
    assert all(not job["enabled"] for job in db.list_scheduler_jobs())
    scheduler.stop()


def test_two_scheduler_instances_single_flight_one_active_scan(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    def scan(scan_id: str, current_id: str, reason: str):
        calls.append(scan_id)
        entered.set()
        assert release.wait(1)
        return ReconciliationReport(1, 1, 0, (), True)

    first_scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=scan)
    second_scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=scan)
    first_result: list[ReconciliationReport] = []
    second_result: list[ReconciliationReport] = []
    first = threading.Thread(target=lambda: first_result.append(first_scheduler.reconcile(source_id)))
    second = threading.Thread(target=lambda: second_result.append(second_scheduler.reconcile(source_id)))
    first.start()
    assert entered.wait(1)
    second.start()
    time.sleep(0.05)
    assert len(calls) == 1
    release.set()
    first.join()
    second.join()
    assert first_result[0].complete
    assert not second_result[0].complete


def test_degraded_source_mid_run_finishes_as_failed_not_running(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    entered = threading.Event()
    release = threading.Event()

    def scan(*args):
        entered.set()
        assert release.wait(1)
        return ReconciliationReport(1, 1, 0, (), True)

    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=scan)
    result: list[ReconciliationReport] = []
    worker = threading.Thread(target=lambda: result.append(scheduler.reconcile(source_id)))
    worker.start()
    assert entered.wait(1)
    registry.set_status(source_id, "degraded", reason="source temporarily unavailable")
    release.set()
    worker.join()
    assert result and not result[0].complete
    assert scheduler.status()[0].status == "failed"
    assert scheduler.status()[0].last_error


def test_late_listener_from_previous_lifecycle_cannot_disable_restarted_scheduler(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda *args: ReconciliationReport(0, 0, 0, (), True),
        poll_seconds=0.01,
    )
    scheduler.start()
    old_listener = registry._lifecycle_listeners[0]
    scheduler.stop()
    scheduler.start()
    old_listener(SourceRecord(
        source_id,
        "codex",
        str(tmp_path),
        "revoked",
        "metadata_discovery",
        "v1",
    ))
    jobs = {job["name"]: job for job in db.list_scheduler_jobs()}
    assert all(job["enabled"] for job in jobs.values())
    scheduler.stop()


def test_scheduler_invokes_real_snapshot_runner_without_binding_source_to_crash_at(
    tmp_path: Path,
):
    db, registry, source_id = registered(tmp_path)
    captured = tmp_path / "captured.txt"
    captured.write_text("snapshot evidence", encoding="utf-8")
    snapshot = ConsistentSnapshot(registry, tmp_path / "raw")
    queue = SQLiteExtractionQueue(tmp_path / "state.db")
    runner = SnapshotJobRunner(
        snapshot,
        queue,
        db,
        path_provider=lambda scan, source: [captured],
    )
    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=runner.run)

    report = scheduler.reconcile(source_id)

    assert report.complete
    assert scheduler.status()[0].status == "completed"
    assert queue.count(source_type="automatic_memory_snapshot") == 1


def test_scheduler_snapshot_runner_reacquires_paused_scan(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    captured = tmp_path / "paused-captured.txt"
    captured.write_text("paused evidence", encoding="utf-8")
    scan = registry.start_scan(source_id)
    assert registry.pause_scan(scan.scan_id).status == "paused"
    snapshot = ConsistentSnapshot(registry, tmp_path / "raw")
    queue = SQLiteExtractionQueue(tmp_path / "state.db")
    runner = SnapshotJobRunner(
        snapshot,
        queue,
        db,
        path_provider=lambda scan, source: [captured],
    )
    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=runner.run)

    report = scheduler.reconcile(source_id)

    assert report.complete
    assert db.get_automatic_memory_scan(scan.scan_id)["status"] == "completed"
    assert queue.count(source_type="automatic_memory_snapshot") == 1


def test_generic_report_runner_cannot_complete_paused_scan(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    scan = registry.start_scan(source_id)
    assert registry.pause_scan(scan.scan_id).status == "paused"
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda *args: ReconciliationReport(1, 1, 0, (), True),
    )

    report = scheduler.reconcile(source_id)

    assert not report.complete
    assert db.get_automatic_memory_scan(scan.scan_id)["status"] == "paused"


@pytest.mark.parametrize("transition", ["unsupported", "degraded", "expired", "revoke"])
def test_source_terminalization_clears_scheduler_lease_and_recovery_is_not_blocked(
    tmp_path: Path, transition: str
):
    db, registry, source_id = registered(tmp_path)
    scan = registry.start_scan(source_id)
    claimed = db.claim_automatic_memory_scheduler_scan(
        scan.scan_id, "scheduler-lease", "test-owner", ttl_seconds=300
    )
    assert claimed is not None

    if transition == "revoke":
        registry.revoke(source_id)
        expected_status = "cancelled"
    else:
        registry.set_status(source_id, transition, reason="test lifecycle transition")
        expected_status = "failed"

    row = db.get_automatic_memory_scan(scan.scan_id)
    assert row is not None
    assert row["status"] == expected_status
    assert row["scheduler_lease_id"] is None
    assert row["scheduler_lease_owner"] is None
    assert row["scheduler_lease_heartbeat_at"] is None
    assert row["scheduler_lease_expires_at"] is None

    if transition != "revoke":
        registry.set_status(source_id, "authorized")
        calls: list[str] = []
        scheduler = AutomaticMemoryScheduler(
            db,
            registry,
            scan_runner=lambda scan_id: calls.append(scan_id)
            or ReconciliationReport(0, 0, 0, (), True),
        )
        report = scheduler.reconcile(source_id)
        assert report.complete
        assert calls == [scan.scan_id]


def test_one_source_failure_isolated_and_recorded(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    other_scope = AuthorizationScope(
        "grant-2", ("codex",), (str(tmp_path),), datetime.now(timezone.utc), None, True
    )
    other_id = registry.register(other_scope, "codex", str(tmp_path)).source_id

    def scan(scan_id: str, current_id: str, reason: str):
        if current_id == source_id:
            raise RuntimeError("fixture failure")
        return ReconciliationReport(1, 1, 0, (), True)

    scheduler = AutomaticMemoryScheduler(db, registry, scan_runner=scan)
    failed = scheduler.reconcile(source_id)
    succeeded = scheduler.reconcile(other_id)
    assert not failed.complete and failed.errors == ("fixture failure",)
    assert succeeded.complete
    assert any(
        "fixture failure" in (json.loads(event["payload_json"]).get("error") or "")
        for event in db.recent_events(20)
    )
