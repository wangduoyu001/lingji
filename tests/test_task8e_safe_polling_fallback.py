from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.scheduler import AutomaticMemoryScheduler, ReconciliationReport
from src.automatic_memory.source_registry import SourceRegistry
from src.automatic_memory.runtime import AutomaticMemoryRuntime
from src.control.automatic_memory_api import register_automatic_memory_routes
from src.storage.state_db import StateDatabase


class RecordingWatcher:
    def __init__(self) -> None:
        self.start_calls: list[str] = []
        self.stop_calls = 0

    def start(self, source_id: str, **_kwargs) -> None:
        self.start_calls.append(source_id)

    def stop(self) -> dict[str, object]:
        self.stop_calls += 1
        return {"stopped": True, "surviving_threads": []}

    def stop_source(self, source_id: str, **_kwargs) -> dict[str, object]:
        del source_id
        self.stop_calls += 1
        return {"stopped": True, "surviving_threads": []}

    def running_sources(self) -> tuple[str, ...]:
        return ()

    def pause(self) -> None:
        return None

    def resume(self) -> None:
        return None


class RecordingCron:
    def __init__(self) -> None:
        self.state_db = None
        self.jobs: list[dict[str, object]] = []
        self.runner = None
        self.running = False

    def add_job(self, name: str, interval_hours: float, **kwargs) -> None:
        self.jobs.append({"name": name, "interval_hours": interval_hours, **kwargs})

    def set_jobs_enabled(self, *_args, **_kwargs) -> None:
        return None

    def configure_heartbeat(self, *_args, **_kwargs) -> None:
        return None

    def start(self, runner) -> None:
        self.runner = runner
        self.running = True

    def stop(self) -> None:
        self.running = False


def registered(tmp_path: Path) -> tuple[StateDatabase, SourceRegistry, str]:
    db = StateDatabase(tmp_path / "state.db")
    registry = SourceRegistry(db)
    source = registry.register(
        AuthorizationScope(
            "grant-safe-polling",
            ("codex",),
            (str(tmp_path),),
            datetime.now(timezone.utc),
            None,
            True,
        ),
        "codex",
        str(tmp_path),
    )
    return db, registry, source.source_id


def test_fallback_does_not_start_event_watcher_but_keeps_startup_and_daily_jobs(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    watcher = RecordingWatcher()
    cron = RecordingCron()
    cron.state_db = db
    calls: list[str] = []
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda _scan_id, _source_id, reason: (
            calls.append(reason) or ReconciliationReport(0, 0, 0, (), True)
        ),
        watcher=watcher,
        cron=cron,
        event_watcher_enabled=False,
    )

    scheduler.start()
    try:
        assert watcher.start_calls == []
        names = {str(job["name"]) for job in cron.jobs}
        assert f"automatic_memory:{source_id}:reconciliation" in names
        assert f"automatic_memory:{source_id}:integrity" in names
        assert next(job for job in cron.jobs if str(job["name"]).endswith(":reconciliation"))["run_on_start"] is True
        cron.runner(f"automatic_memory:{source_id}:reconciliation")
        cron.runner(f"automatic_memory:{source_id}:integrity")
        assert calls == ["reconciliation", "integrity"]
    finally:
        scheduler.stop()


def test_fallback_manual_scan_and_revoke_stop_admission(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    watcher = RecordingWatcher()
    calls: list[str] = []
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda _scan_id, _source_id, reason: (
            calls.append(reason) or ReconciliationReport(0, 0, 0, (), True)
        ),
        watcher=watcher,
        cron=RecordingCron(),
        event_watcher_enabled=False,
    )
    scheduler.start()
    try:
        manual = scheduler.reconcile(source_id, reason="manual")
        assert manual.complete
        assert calls == ["manual"]
        registry.revoke(source_id)
        after_revoke = scheduler.reconcile(source_id, reason="reconciliation")
        assert after_revoke.complete is False
        assert calls == ["manual"]
        assert watcher.start_calls == []
    finally:
        scheduler.stop()


def test_fallback_status_names_periodic_reconciliation_mode(tmp_path: Path):
    db, registry, _source_id = registered(tmp_path)
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda *_args: ReconciliationReport(0, 0, 0, (), True),
        event_watcher_enabled=False,
    )
    assert scheduler.event_watcher_enabled is False
    assert scheduler.automation_mode == "periodic_reconciliation"
    assert scheduler.next_reconciliation_seconds == 900.0


def test_event_watcher_default_is_platform_specific_and_explicit_override_wins():
    assert AutomaticMemoryScheduler.resolve_event_watcher_enabled(None, platform_name="darwin") is False
    assert AutomaticMemoryScheduler.resolve_event_watcher_enabled(None, platform_name="win32") is True
    assert AutomaticMemoryScheduler.resolve_event_watcher_enabled(None, platform_name="linux") is True
    assert AutomaticMemoryScheduler.resolve_event_watcher_enabled(True, platform_name="darwin") is True
    assert AutomaticMemoryScheduler.resolve_event_watcher_enabled(False, platform_name="win32") is False


def test_fallback_stays_quiet_for_two_reconciliation_periods_and_discovers_on_schedule(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    watcher = RecordingWatcher()
    calls: list[tuple[str, int]] = []

    def scan(_scan_id: str, _source_id: str, reason: str):
        calls.append((reason, 0))
        return ReconciliationReport(0, 0, 0, (), True)

    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=scan,
        watcher=watcher,
        event_watcher_enabled=False,
        poll_seconds=0.02,
        reconciliation_seconds=1,
        integrity_seconds=3600,
    )
    scheduler.start()
    try:
        time.sleep(2.25)
    finally:
        scheduler.stop()
    assert len([reason for reason, _incremental in calls if reason == "reconciliation"]) >= 3
    assert all(reason != "event" and incremental == 0 for reason, incremental in calls)
    assert watcher.start_calls == []


def test_fallback_pause_resume_restart_preserve_reconciliation_without_starting_watcher(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    watcher = RecordingWatcher()
    calls: list[str] = []
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda _scan_id, _source_id, reason: (
            calls.append(reason) or ReconciliationReport(0, 0, 0, (), True)
        ),
        watcher=watcher,
        event_watcher_enabled=False,
        poll_seconds=0.02,
        reconciliation_seconds=1,
        integrity_seconds=3600,
    )
    scheduler.start()
    time.sleep(0.1)
    scheduler.pause()
    paused_count = len(calls)
    time.sleep(1.1)
    assert len(calls) == paused_count
    scheduler.resume()
    time.sleep(1.1)
    scheduler.stop()
    first_run_count = len(calls)
    restarted = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda _scan_id, _source_id, reason: (
            calls.append(reason) or ReconciliationReport(0, 0, 0, (), True)
        ),
        watcher=watcher,
        event_watcher_enabled=False,
        poll_seconds=0.02,
        reconciliation_seconds=1,
        integrity_seconds=3600,
    )
    restarted.start()
    time.sleep(1.1)
    restarted.stop()
    assert len(calls) > first_run_count
    assert all(reason != "event" for reason in calls)
    assert watcher.start_calls == []


def test_api_runtime_and_summary_report_the_same_periodic_interval(tmp_path: Path):
    db, registry, source_id = registered(tmp_path)
    queue = type("Queue", (), {"path": db.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()
    scheduler = AutomaticMemoryScheduler(
        db,
        registry,
        scan_runner=lambda *_args: ReconciliationReport(0, 0, 0, (), True),
        event_watcher_enabled=False,
    )
    worker = type("Worker", (), {"status": lambda _self: {"running": False}})()
    runtime = AutomaticMemoryRuntime(
        state_db=db,
        queue=queue,
        pipeline=pipeline,
        registry=registry,
        scheduler=scheduler,
        worker=worker,
    )
    app = FastAPI()
    control = type("Control", (), {"state_db": db, "runtime": runtime, "automatic_memory_registry": registry})()
    register_automatic_memory_routes(app, control, [])
    with TestClient(app) as client:
        runtime_payload = client.get("/api/automatic-memory/runtime").json()
        summary_payload = client.get("/api/automatic-memory/summary").json()
    assert runtime_payload["automation_mode"] == "periodic_reconciliation"
    assert runtime_payload["event_watcher_enabled"] is False
    assert runtime_payload["next_reconciliation_seconds"] == 900.0
    assert "15 minutes" in summary_payload["next_action"]


def test_runtime_composition_uses_injected_platform_and_explicit_override(tmp_path: Path):
    db, registry, _source_id = registered(tmp_path)
    queue = type("Queue", (), {"path": db.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()

    windows_runtime = AutomaticMemoryRuntime(
        state_db=db,
        queue=queue,
        pipeline=pipeline,
        registry=registry,
        worker=object(),
        platform_provider=lambda: "win32",
    )
    assert windows_runtime.scheduler.event_watcher_enabled is True

    mac_runtime = AutomaticMemoryRuntime(
        state_db=db,
        queue=queue,
        pipeline=pipeline,
        registry=registry,
        worker=object(),
        platform_provider=lambda: "darwin",
    )
    assert mac_runtime.scheduler.event_watcher_enabled is False

    override_settings = type("Settings", (), {"automatic_memory_event_watcher_enabled": False})()
    overridden_windows_runtime = AutomaticMemoryRuntime(
        state_db=db,
        queue=queue,
        pipeline=pipeline,
        settings=override_settings,
        registry=registry,
        worker=object(),
        platform_provider=lambda: "win32",
    )
    assert overridden_windows_runtime.scheduler.event_watcher_enabled is False
