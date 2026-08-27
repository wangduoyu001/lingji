"""Composition boundary for the packaged automatic-memory runtime.

This module deliberately contains orchestration only.  Discovery, adapter
selection and snapshot-job consumption remain owned by the existing
components (and are completed by the later automatic-memory tasks).
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from src.storage import StateDatabase

from .checkpoint import SnapshotJobRunner
from .scheduler import AutomaticMemoryScheduler
from .snapshot import ConsistentSnapshot
from .source_registry import SourceRegistry


class AutomaticMemoryRuntime:
    """Own one worker and one automatic-memory scheduler in one process.

    ``state_db`` and ``queue`` are injected so the packaged entry point can
    prove that every component points at the canonical state file.  Multiple
    SQLite connections to that file are expected; a second logical file is
    rejected.
    """

    HEARTBEAT_UNAVAILABLE_REASON = (
        "unavailable: existing scheduler exposes no trustworthy idle heartbeat"
    )

    def __init__(
        self,
        *,
        state_db: StateDatabase,
        queue: Any | None = None,
        pipeline: Any | None = None,
        settings: Any | None = None,
        registry: SourceRegistry | None = None,
        snapshot: ConsistentSnapshot | None = None,
        runner: SnapshotJobRunner | None = None,
        scheduler: Any | None = None,
        worker: Any | None = None,
        path_provider: Callable[[Any, Any], Any] | None = None,
    ) -> None:
        self.state_db = state_db
        if pipeline is None and settings is not None:
            # Import lazily: extraction adapters import automatic_memory models
            # during bootstrap, so a module-level import would create a cycle.
            from src.extraction.bootstrap import build_extraction_pipeline

            pipeline = build_extraction_pipeline(settings)
        self.pipeline = pipeline
        if self.pipeline is None:
            raise TypeError("pipeline or settings is required")
        pipeline_queue = getattr(self.pipeline, "queue", None)
        self.queue = pipeline_queue if queue is None else queue
        if self.queue is None:
            raise TypeError("queue or pipeline.queue is required")
        if pipeline_queue is not None and self.queue is not pipeline_queue:
            raise ValueError("runtime and extraction pipeline must share one queue wrapper")
        self._validate_canonical_state_path()
        self.registry = registry or SourceRegistry(state_db)
        self.snapshot = snapshot
        self.runner = runner
        if scheduler is None:
            self.snapshot = snapshot or ConsistentSnapshot(
                self.registry,
                Path(getattr(settings, "storage_path", Path(state_db.path).parent)) / "raw",
            )
            self.runner = runner or SnapshotJobRunner(
                self.snapshot,
                self.queue,
                self.state_db,
                # File enumeration is intentionally not part of Task 2.
                # Task 3 supplies the authorized path policy.
                path_provider=path_provider or (lambda _scan, _source: ()),
            )
            scheduler = AutomaticMemoryScheduler(
                self.state_db,
                self.registry,
                scan_runner=self.runner.run,
                poll_seconds=float(getattr(settings, "scheduler_poll_seconds", 60.0)),
                debounce_seconds=float(
                    getattr(settings, "automatic_memory_debounce_seconds", 5.0)
                ),
                reconciliation_seconds=float(
                    getattr(settings, "automatic_memory_reconciliation_seconds", 900.0)
                ),
                integrity_seconds=float(
                    getattr(settings, "automatic_memory_integrity_seconds", 86400.0)
                ),
            )
        self.scheduler = scheduler
        if worker is None:
            from src.extraction.worker import ExtractionWorker

            worker = ExtractionWorker(
                self.pipeline,
                poll_seconds=float(getattr(settings, "extraction_poll_seconds", 5.0)),
                batch_size=int(getattr(settings, "extraction_batch_size", 5)),
            )
        self.worker = worker
        self._lock = RLock()
        self._started = False
        self._paused = False

    def _validate_canonical_state_path(self) -> None:
        state_path = Path(self.state_db.path).expanduser().resolve(strict=False)
        queue_path = Path(self.queue.path).expanduser().resolve(strict=False)
        pipeline_queue = getattr(self.pipeline, "queue", None)
        pipeline_path = (
            Path(pipeline_queue.path).expanduser().resolve(strict=False)
            if pipeline_queue is not None
            else queue_path
        )
        if state_path != queue_path or state_path != pipeline_path:
            raise ValueError(
                "automatic-memory runtime requires one canonical state database and queue path"
            )

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._paused = False
            self.worker.start()
            try:
                # Scheduler owns watcher and CronScheduler; do not start either
                # child directly here.
                self.scheduler.start()
            except BaseException:
                self.worker.stop()
                raise
            self._started = True

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                # Keep stop idempotent but release a scheduler that may have
                # been supplied already running by an embedding test/host.
                return
        # Stop admission first.  CronScheduler.stop waits for in-flight
        # reconciliation before the extraction consumer is stopped.
        try:
            self.scheduler.stop()
        finally:
            self.worker.stop()
            with self._lock:
                self._started = False

    def status(self) -> dict[str, object]:
        worker_status: dict[str, Any] = {}
        try:
            value = self.worker.status()
            if isinstance(value, dict):
                worker_status = dict(value)
        except Exception:
            worker_status = {}
        scheduler_running = bool(
            getattr(self.scheduler, "running", getattr(getattr(self.scheduler, "cron", None), "running", False))
        )
        worker_running = worker_status.get("running")
        if worker_running is None:
            worker_running = getattr(self.worker, "running", None)
        with self._lock:
            started = self._started
            paused = self._paused
        if paused:
            state = "paused"
        elif not started:
            state = "stopped"
        elif scheduler_running and worker_running is True:
            state = "running"
        else:
            state = "degraded"
        watcher = getattr(self.scheduler, "watcher", None)
        try:
            sources = tuple(watcher.running_sources()) if watcher is not None else ()
        except Exception:
            sources = None
        return {
            "state": state,
            "running": started,
            "paused": paused,
            "scheduler_state": "running" if scheduler_running else "stopped",
            "scheduler_heartbeat_age": None,
            "scheduler_heartbeat_reason": self.HEARTBEAT_UNAVAILABLE_REASON,
            "worker_state": worker_running,
            "worker": worker_status,
            "authorized_watcher_count": len(sources) if sources is not None else None,
            "watcher_sources": list(sources) if sources is not None else None,
            "last_global_error": self._last_global_error(),
        }

    def scan_now(self, source_id: str) -> dict[str, object]:
        result = self.scheduler.reconcile(source_id, reason="manual")
        if is_dataclass(result):
            return asdict(result)
        if isinstance(result, dict):
            return dict(result)
        return {"source_id": source_id, "result": result}

    def pause(self) -> dict[str, object]:
        self.scheduler.pause()
        with self._lock:
            self._paused = True
        return self.status()

    def resume(self) -> dict[str, object]:
        self.scheduler.resume()
        with self._lock:
            self._paused = False
        return self.status()

    def _last_global_error(self) -> str | None:
        try:
            for row in self.state_db.list_automatic_memory_scans():
                error = row.get("last_error")
                if error:
                    return str(error)[:2000]
            for row in self.state_db.recent_events(limit=100):
                event_type = str(row.get("event_type") or "")
                if "failed" not in event_type and "error" not in event_type:
                    continue
                payload = row.get("payload_json")
                if isinstance(payload, str) and payload:
                    return payload[:2000]
                if payload:
                    return str(payload)[:2000]
        except Exception:
            return None
        return None
