from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.scheduler import AutomaticMemoryScheduler, ReconciliationReport
from src.automatic_memory.source_registry import SourceRegistry
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
