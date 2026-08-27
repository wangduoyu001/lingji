from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time

from fastapi.testclient import TestClient

from src.automatic_memory import AuthorizationScope, SourceRegistry
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


def _runtime(tmp_path: Path):
    state = StateDatabase(tmp_path / "lingji_state.db")
    queue = type("Queue", (), {"path": state.path})()
    pipeline = type("Pipeline", (), {"queue": queue})()
    scheduler = _Scheduler()
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
    assert runtime.pause()["state"] == "paused"
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
