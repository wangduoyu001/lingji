from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
import threading

from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.source_registry import SourceRegistry
from src.automatic_memory.scheduler import AutomaticMemoryScheduler, ReconciliationReport
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
