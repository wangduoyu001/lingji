from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
import time

import pytest

from fastapi.testclient import TestClient

from src.automatic_memory import AuthorizationScope, SourceRegistry
from src.automatic_memory.watcher import AutomaticMemoryWatcher
from src.auto_review.promotion import AutoMemoryPromotionService
from src.automatic_memory.runtime import AutomaticMemoryRuntime
from src.control.api import create_control_app
from src.storage import StateDatabase


class _Watcher:
    def __init__(self) -> None:
        self.started = False
        self.paused = False

    def running_sources(self):
        return ("source-1",) if self.started else ()


class _Scheduler:
    def __init__(self) -> None:
        self.running = False
        self.paused = False
        self.watcher = _Watcher()
        self.calls: list[str] = []

    def start(self) -> None:
        self.calls.append("scheduler.start")
        self.running = True
        self.watcher.started = True

    def stop(self) -> None:
        self.calls.append("scheduler.stop")
        self.running = False
        self.watcher.started = False

    def pause(self) -> None:
        self.calls.append("scheduler.pause")
        self.paused = True

    def resume(self) -> None:
        self.calls.append("scheduler.resume")
        self.paused = False

    def reconcile(self, source_id: str, *, reason: str = "manual"):
        self.calls.append(f"scheduler.reconcile:{source_id}:{reason}")
        return {"source_id": source_id, "reason": reason, "complete": True}


class _Worker:
    def __init__(self) -> None:
        self.running = False
        self.calls: list[str] = []

    def start(self) -> None:
        self.calls.append("worker.start")
        self.running = True

    def stop(self) -> None:
        self.calls.append("worker.stop")
        self.running = False

    def status(self):
        return {"running": self.running, "queue": {"queued": 0}}


class _PartiallyStartingScheduler(_Scheduler):
    def start(self) -> None:
        self.calls.append("scheduler.start")
        self.running = True
        raise RuntimeError("scheduler start failed after acquiring resources")


class _RetryingStopScheduler(_Scheduler):
    def __init__(self) -> None:
        super().__init__()
        self.stop_attempts = 0

    def stop(self) -> None:
        self.stop_attempts += 1
        self.calls.append("scheduler.stop")
        if self.stop_attempts == 1:
            self.running = True
            raise RuntimeError("scheduler stop timed out")
        self.running = False
        self.watcher.started = False


def _runtime(tmp_path: Path):
    state = StateDatabase(tmp_path / "lingji_state.db")
    queue = type("Queue", (), {"path": state.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()
    scheduler = _Scheduler()
    scheduler.state_db = state
    worker = _Worker()
    runtime = AutomaticMemoryRuntime(
        state_db=state,
        queue=queue,
        pipeline=pipeline,
        scheduler=scheduler,
        worker=worker,
    )
    return runtime, scheduler, worker


def test_start_stop_are_idempotent_and_worker_precedes_scheduler(tmp_path: Path):
    runtime, scheduler, worker = _runtime(tmp_path)

    runtime.start()
    runtime.start()
    assert worker.calls == ["worker.start"]
    assert scheduler.calls == ["scheduler.start"]
    assert runtime.status()["state"] == "running"
    assert runtime.status()["authorized_watcher_count"] == 1

    runtime.stop()
    runtime.stop()
    assert worker.calls == ["worker.start", "worker.stop"]
    assert scheduler.calls == ["scheduler.start", "scheduler.stop"]
    assert runtime.status()["state"] == "stopped"


def test_status_does_not_fabricate_scheduler_heartbeat(tmp_path: Path):
    runtime, _scheduler, _worker = _runtime(tmp_path)

    status = runtime.status()

    assert status["scheduler_heartbeat_age"] is None
    assert "unavailable" in status["scheduler_heartbeat_reason"]
    assert status["last_global_error"] is None


def test_scan_pause_resume_delegate_to_existing_scheduler(tmp_path: Path):
    runtime, scheduler, _worker = _runtime(tmp_path)

    assert runtime.scan_now("source-1")["source_id"] == "source-1"
    assert runtime.pause()["state"] == "stopped"
    assert runtime.resume()["state"] == "stopped"
    assert scheduler.calls == [
        "scheduler.reconcile:source-1:manual",
        "scheduler.pause",
        "scheduler.resume",
    ]


def test_runtime_uses_canonical_state_and_queue_path(tmp_path: Path):
    runtime, _scheduler, _worker = _runtime(tmp_path)
    assert Path(runtime.state_db.path).resolve() == Path(runtime.queue.path).resolve()
    assert Path(runtime.pipeline.queue.path).resolve() == Path(runtime.state_db.path).resolve()


@pytest.mark.parametrize("mismatched", ["registry", "scheduler"])
def test_runtime_rejects_mismatched_registry_or_scheduler_state_db(
    tmp_path: Path, mismatched: str
):
    canonical = StateDatabase(tmp_path / "a.db")
    other = StateDatabase(tmp_path / "b.db")
    queue = type("Queue", (), {"path": canonical.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()
    registry = SourceRegistry(other if mismatched == "registry" else canonical)
    scheduler = _Scheduler()
    scheduler.state_db = other if mismatched == "scheduler" else canonical

    with pytest.raises(ValueError, match="one canonical state database"):
        AutomaticMemoryRuntime(
            state_db=canonical,
            queue=queue,
            pipeline=pipeline,
            registry=registry,
            scheduler=scheduler,
            worker=_Worker(),
        )


def test_start_failure_retries_cleanup_for_partially_started_scheduler(tmp_path: Path):
    state = StateDatabase(tmp_path / "lingji_state.db")
    queue = type("Queue", (), {"path": state.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()
    scheduler = _PartiallyStartingScheduler()
    scheduler.state_db = state
    worker = _Worker()
    runtime = AutomaticMemoryRuntime(
        state_db=state, queue=queue, pipeline=pipeline, scheduler=scheduler, worker=worker
    )

    try:
        runtime.start()
    except RuntimeError as exc:
        assert "scheduler start failed" in str(exc)
    else:
        raise AssertionError("start should fail")

    assert scheduler.calls == ["scheduler.start", "scheduler.stop"]
    assert worker.calls == ["worker.start", "worker.stop"]


def test_stop_error_keeps_cleanup_pending_and_allows_retry(tmp_path: Path):
    runtime, _scheduler, worker = _runtime(tmp_path)
    state = runtime.state_db
    scheduler = _RetryingStopScheduler()
    scheduler.state_db = state
    runtime.scheduler = scheduler
    runtime.start()

    with pytest.raises(RuntimeError, match="scheduler stop timed out"):
        runtime.stop()
    first = runtime.status()
    assert first["state"] == "degraded"
    assert first["cleanup_pending"] is True
    assert first["running"] is True
    assert "scheduler stop timed out" in first["cleanup_error"]
    assert "scheduler stop timed out" in first["last_global_error"]

    runtime.stop()
    second = runtime.status()
    assert second["state"] == "stopped"
    assert second["cleanup_pending"] is False
    assert second["running"] is False
    assert scheduler.calls == ["scheduler.start", "scheduler.stop", "scheduler.stop"]


def test_never_started_pause_remains_stopped(tmp_path: Path):
    runtime, _scheduler, _worker = _runtime(tmp_path)
    result = runtime.pause()
    assert result["state"] == "stopped"
    assert result["paused"] is True


def test_running_scheduler_attaches_newly_authorized_source(tmp_path: Path):
    from src.automatic_memory.scheduler import AutomaticMemoryScheduler

    state = StateDatabase(tmp_path / "lingji_state.db")
    registry = SourceRegistry(state)
    queue = type("Queue", (), {"path": state.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()
    settings = type(
        "Settings",
        (),
        {
            "storage_path": tmp_path,
            "scheduler_poll_seconds": 0.02,
            "automatic_memory_debounce_seconds": 1,
            "automatic_memory_reconciliation_seconds": 60,
            "automatic_memory_integrity_seconds": 3600,
            "extraction_poll_seconds": 0.2,
            "extraction_batch_size": 1,
        },
    )()
    scheduler = AutomaticMemoryScheduler(
        state, registry, scan_runner=lambda *_args: None, poll_seconds=0.02
    )
    runtime = AutomaticMemoryRuntime(
        state_db=state,
        queue=queue,
        pipeline=pipeline,
        settings=settings,
        registry=registry,
        scheduler=scheduler,
        worker=_Worker(),
    )
    runtime.start()
    source = registry.register(
        AuthorizationScope(
            "grant-live",
            ("generic_ai_history",),
            (str(tmp_path),),
            datetime.now(timezone.utc),
            None,
            True,
        ),
        "generic_ai_history",
        str(tmp_path),
    )

    deadline = time.monotonic() + 1.0
    while source.source_id not in scheduler.watcher.running_sources() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert source.source_id in scheduler.watcher.running_sources()
    names = {row["name"] for row in state.list_scheduler_jobs()}
    assert f"automatic_memory:{source.source_id}:reconciliation" in names
    assert f"automatic_memory:{source.source_id}:integrity" in names
    runtime.stop()


def test_watcher_reports_surviving_thread_after_bounded_stop(tmp_path: Path):
    release = __import__("threading").Event()
    source = {
        "source_id": "source-1",
        "root": str(tmp_path),
        "status": "authorized",
    }

    def backend(_root, **_kwargs):
        while not release.is_set():
            time.sleep(0.02)
        yield set()

    watcher = AutomaticMemoryWatcher(
        source_provider=lambda _source_id: source,
        on_change=lambda _source_id: None,
        watch_backend=backend,
    )
    watcher.start("source-1", debounce_seconds=1)
    result = watcher.stop(timeout_seconds=0.01)
    assert result["stopped"] is False
    assert result["surviving_threads"] == ["lingji-memory-watch-source-1"]
    assert watcher.running_sources() == ("source-1",)

    release.set()
    watcher.stop(timeout_seconds=1)
    assert watcher.running_sources() == ()


def test_revoke_linearizes_quickly_and_runtime_reports_survivor_until_retry(
    tmp_path: Path,
):
    from src.automatic_memory.scheduler import AutomaticMemoryScheduler

    release = threading.Event()

    def backend(_root, **_kwargs):
        while not release.is_set():
            time.sleep(0.01)
        yield set()

    state = StateDatabase(tmp_path / "lingji_state.db")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            "grant-revoke",
            ("generic_ai_history",),
            (str(tmp_path),),
            datetime.now(timezone.utc),
            None,
            True,
        ),
        "generic_ai_history",
        str(tmp_path),
    )
    watcher = AutomaticMemoryWatcher(
        source_provider=lambda source_id: next(
            item for item in registry.list_sources() if item.source_id == source_id
        ),
        on_change=lambda _source_id: None,
        watch_backend=backend,
    )
    scheduler = AutomaticMemoryScheduler(
        state,
        registry,
        scan_runner=lambda *_args: None,
        watcher=watcher,
        poll_seconds=0.02,
    )
    queue = type("Queue", (), {"path": state.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()
    runtime = AutomaticMemoryRuntime(
        state_db=state,
        queue=queue,
        pipeline=pipeline,
        registry=registry,
        scheduler=scheduler,
        worker=_Worker(),
    )
    runtime.start()
    deadline = time.monotonic() + 1.0
    while source.source_id not in watcher.running_sources() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert source.source_id in watcher.running_sources()

    def broken_observer(_source):
        raise RuntimeError("observer failed")

    registry.add_lifecycle_listener(broken_observer)
    started = time.monotonic()
    registry.revoke(source.source_id)
    elapsed = time.monotonic() - started
    assert elapsed < 0.5
    assert source.source_id not in {
        row["name"].split(":")[1]
        for row in state.list_scheduler_jobs()
        if row["name"].startswith(f"automatic_memory:{source.source_id}:")
        and row["enabled"]
    }
    assert source.source_id in watcher.running_sources()
    status = runtime.status()
    assert status["state"] == "degraded"
    assert status["cleanup_pending"] is True
    assert source.source_id in status["source_cleanup_errors"]

    release.set()
    runtime.stop()
    assert watcher.running_sources() == ()
    assert runtime.status()["state"] == "stopped"


def test_late_watcher_exit_clears_scheduler_cleanup_error_on_second_stop(
    tmp_path: Path,
):
    """A survivor must remain degraded until a later stop observes its exit."""
    from src.automatic_memory.scheduler import AutomaticMemoryScheduler

    release = threading.Event()
    state = StateDatabase(tmp_path / "lingji_state.db")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            "grant-late-stop",
            ("generic_ai_history",),
            (str(tmp_path),),
            datetime.now(timezone.utc),
            None,
            True,
        ),
        "generic_ai_history",
        str(tmp_path),
    )

    def backend(_root, **_kwargs):
        while not release.is_set():
            time.sleep(0.01)
        yield set()

    watcher = AutomaticMemoryWatcher(
        source_provider=lambda source_id: next(
            item for item in registry.list_sources() if item.source_id == source_id
        ),
        on_change=lambda _source_id: None,
        watch_backend=backend,
        stop_timeout_seconds=0.01,
    )
    scheduler = AutomaticMemoryScheduler(
        state,
        registry,
        scan_runner=lambda *_args: None,
        watcher=watcher,
        poll_seconds=0.02,
    )
    queue = type("Queue", (), {"path": state.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()
    runtime = AutomaticMemoryRuntime(
        state_db=state,
        queue=queue,
        pipeline=pipeline,
        registry=registry,
        scheduler=scheduler,
        worker=_Worker(),
    )
    runtime.start()
    deadline = time.monotonic() + 1.0
    while source.source_id not in watcher.running_sources() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert source.source_id in watcher.running_sources()

    registry.revoke(source.source_id)
    assert registry.list_sources()[0].status == "revoked"

    with pytest.raises(RuntimeError, match="watcher threads survived stop"):
        runtime.stop()
    degraded = runtime.status()
    assert degraded["state"] == "degraded"
    assert degraded["cleanup_pending"] is True
    assert source.source_id in watcher.running_sources()

    release.set()
    deadline = time.monotonic() + 1.0
    while watcher.running_sources() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert watcher.running_sources() == ()

    retry_errors: list[BaseException] = []

    def retry_stop() -> None:
        try:
            runtime.stop()
        except BaseException as exc:  # pragma: no cover - failure evidence
            retry_errors.append(exc)

    retries = [threading.Thread(target=retry_stop) for _ in range(2)]
    for thread in retries:
        thread.start()
    for thread in retries:
        thread.join(timeout=1.0)
        assert not thread.is_alive()
    assert retry_errors == []

    stopped = runtime.status()
    assert stopped["state"] == "stopped"
    assert stopped["cleanup_pending"] is False
    assert stopped["cleanup_error"] is None
    assert stopped["source_cleanup_errors"] == {}
    assert stopped["running"] is False


def test_runtime_status_route_is_authenticated_and_truthful(tmp_path: Path):
    state = StateDatabase(tmp_path / "lingji_state.db")
    runtime = type(
        "Runtime",
        (),
        {"status": lambda self: {"state": "running", "scheduler_heartbeat_age": None}},
    )()
    control = type(
        "Control",
        (),
        {
            "state_db": state,
            "automatic_memory_registry": SourceRegistry(state),
            "runtime": runtime,
        },
    )()
    app = create_control_app(object(), service=control, token="token")
    client = TestClient(app)

    assert client.get("/api/automatic-memory/runtime").status_code == 401
    response = client.get(
        "/api/automatic-memory/runtime", headers={"X-LingJi-Token": "token"}
    )
    assert response.status_code == 200
    assert response.json() == {"state": "running", "scheduler_heartbeat_age": None}


def test_background_lifecycle_never_enters_quarantined_promotion_seams(
    tmp_path: Path, monkeypatch
):
    calls: list[str] = []

    def forbidden(name):
        def fail(*_args, **_kwargs):
            calls.append(name)
            raise AssertionError(f"background promotion seam called: {name}")

        return fail

    for name in (
        "evaluate",
        "promote",
        "submit",
        "reconcile_incomplete_projections",
        "rebuild_derived_projections",
    ):
        if hasattr(AutoMemoryPromotionService, name):
            monkeypatch.setattr(AutoMemoryPromotionService, name, forbidden(name))

    state = StateDatabase(tmp_path / "lingji_state.db")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            "grant-1",
            ("generic_ai_history",),
            (str(tmp_path),),
            datetime.now(timezone.utc),
            None,
            True,
        ),
        "generic_ai_history",
        str(tmp_path),
    )
    from src.extraction.queue import SQLiteExtractionQueue

    queue = SQLiteExtractionQueue(state.path)
    pipeline = type("Pipeline", (), {"queue": queue})()
    settings = type(
        "Settings",
        (),
        {
            "storage_path": tmp_path,
            "scheduler_poll_seconds": 0.01,
            "automatic_memory_debounce_seconds": 1,
            "automatic_memory_reconciliation_seconds": 1,
            "automatic_memory_integrity_seconds": 1,
            "extraction_poll_seconds": 0.2,
            "extraction_batch_size": 1,
        },
    )()
    runtime = AutomaticMemoryRuntime(
        state_db=state,
        queue=queue,
        pipeline=pipeline,
        settings=settings,
        registry=registry,
        worker=_Worker(),
    )
    runtime.start()
    deadline = time.monotonic() + 1.0
    while not state.list_scheduler_jobs() and time.monotonic() < deadline:
        time.sleep(0.01)
    runtime.scan_now(source.source_id)
    runtime.stop()
    runtime.start()
    runtime.stop()

    assert calls == []
