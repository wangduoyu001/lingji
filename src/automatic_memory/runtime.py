"""Composition boundary for the packaged automatic-memory runtime.

This module deliberately contains orchestration only.  Discovery, adapter
selection and snapshot-job consumption remain owned by the existing
components (and are completed by the later automatic-memory tasks).
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Callable

from src.storage import StateDatabase

from .checkpoint import SnapshotJobRunner
from .scheduler import AutomaticMemoryScheduler
from .snapshot import ConsistentSnapshot
from .source_registry import SourceRegistry
from .models import SourceRecord
from .path_policy import enumerate_authorized_files
from src.work.capture_bridge import CaptureWorkBridge
from src.work.models import ExecutionEvent, WorkItem
from src.work.projector import WorkProjector
from src.work.store import WorkStore


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
                path_provider=path_provider or self._authorized_paths,
            )
            scheduler = AutomaticMemoryScheduler(
                self.state_db,
                self.registry,
                scan_runner=self._run_scan,
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
                event_watcher_enabled=bool(
                    getattr(settings, "automatic_memory_event_watcher_enabled", False)
                ),
                heartbeat_seconds=float(
                    getattr(settings, "automatic_memory_heartbeat_seconds", 5.0)
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
        self._validate_canonical_state_path()
        self._lock = RLock()
        self._started = False
        self._paused = False
        self._cleanup_pending = False
        self._cleanup_errors: list[str] = []
        self._scan_reports: dict[str, Any] = {}
        self.work_store = WorkStore(state_db)
        self.work_projector = WorkProjector(self.work_store)
        self.work_bridge = CaptureWorkBridge(self.work_store)
        if hasattr(self.scheduler, "heartbeat_work_callback"):
            self.scheduler.heartbeat_work_callback = self._touch_active_scan_work
        if hasattr(self.registry, "add_lifecycle_listener"):
            # Project StateDB authorization transitions into the existing
            # structured read/index rows before current retrieval can observe
            # them. This is a read-model projection, not a second authority.
            self.registry.add_lifecycle_listener(self._on_source_lifecycle_projection)
        if hasattr(self.pipeline, "add_lifecycle_callback"):
            self.pipeline.add_lifecycle_callback(self._on_extraction_lifecycle)

    def _on_source_lifecycle_projection(self, source: Any) -> None:
        sink = getattr(self.pipeline, "structured_sink", None)
        read_model = getattr(sink, "read_model", None)
        project = getattr(read_model, "sync_automatic_source_lifecycle", None)
        if not callable(project):
            return
        source_id = str(getattr(source, "source_id", "") or "")
        status = str(getattr(source, "status", "") or "")
        if not source_id or not status:
            return
        project(source_id, status)

    def _validate_canonical_state_path(self) -> None:
        def verified_path(value: Any, label: str) -> Path:
            raw = getattr(value, "path", None)
            if raw is None:
                raise ValueError(
                    f"automatic-memory runtime cannot verify {label} canonical state path"
                )
            try:
                return Path(raw).expanduser().resolve(strict=False)
            except (TypeError, ValueError, OSError) as exc:
                raise ValueError(
                    f"automatic-memory runtime cannot verify {label} canonical state path"
                ) from exc

        state_path = verified_path(self.state_db, "state_db")
        queue_path = verified_path(self.queue, "queue")
        pipeline_queue = getattr(self.pipeline, "queue", None)
        if pipeline_queue is None:
            raise ValueError(
                "automatic-memory runtime cannot verify pipeline.queue canonical state path"
            )
        pipeline_path = verified_path(pipeline_queue, "pipeline.queue")
        registry_db = getattr(self.registry, "state_db", None)
        scheduler_db = getattr(self.scheduler, "state_db", None)
        if registry_db is None:
            raise ValueError(
                "automatic-memory runtime cannot verify registry canonical state path"
            )
        if scheduler_db is None:
            raise ValueError(
                "automatic-memory runtime cannot verify scheduler canonical state path"
            )
        registry_path = verified_path(registry_db, "registry")
        scheduler_path = verified_path(scheduler_db, "scheduler")
        if len({state_path, queue_path, pipeline_path, registry_path, scheduler_path}) != 1:
            raise ValueError(
                "automatic-memory runtime requires one canonical state database and queue path"
            )

    def _reconcile_snapshot_cleanup(self) -> str | None:
        snapshot = self.snapshot or getattr(self.runner, "snapshot", None)
        reconcile = getattr(snapshot, "reconcile_temporary_snapshots", None)
        if not callable(reconcile):
            return None
        try:
            result = reconcile()
        except Exception:
            return "snapshot temporary cleanup failed: snapshot_reconcile_failed"
        errors = tuple(
            str(error) for error in (result.get("errors") or ()) if str(error)
        ) if isinstance(result, dict) else ("snapshot_reconcile_failed",)
        if not errors:
            return None
        return "snapshot temporary cleanup failed: " + ",".join(dict.fromkeys(errors))

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._paused = False
            try:
                self.worker.start()
                # Scheduler owns watcher and CronScheduler; do not start either
                # child directly here.
                self.scheduler.start()
                # ``list_sources`` also materializes expired grants in StateDB;
                # project those states on every restart before serving queries.
                for source in self.registry.list_sources():
                    self._on_source_lifecycle_projection(source)
                snapshot_error = self._reconcile_snapshot_cleanup()
                self._cleanup_errors = [snapshot_error] if snapshot_error else []
                self._cleanup_pending = bool(snapshot_error)
            except BaseException as start_error:
                errors = [f"start failed: {start_error}"]
                for component in (self.scheduler, self.worker):
                    try:
                        result = component.stop()
                        if self._component_alive(component, result):
                            errors.append(
                                f"{component.__class__.__name__} remained alive after start cleanup"
                            )
                    except BaseException as cleanup_error:
                        errors.append(f"cleanup failed: {cleanup_error}")
                self._cleanup_errors = errors
                self._cleanup_pending = any(
                    self._component_alive(component)
                    for component in (self.scheduler, self.worker)
                ) or len(errors) > 1
                self._started = self._cleanup_pending
                raise
            self._started = True
            self._cleanup_pending = False
            self._cleanup_errors = []

    def stop(self) -> None:
        with self._lock:
            if not self._started and not self._cleanup_pending:
                # Keep stop idempotent but release a scheduler that may have
                # been supplied already running by an embedding test/host.
                snapshot_error = self._reconcile_snapshot_cleanup()
                if snapshot_error:
                    self._cleanup_errors = [snapshot_error]
                    self._cleanup_pending = True
                return
        # Stop admission first.  CronScheduler.stop waits for in-flight
        # reconciliation before the extraction consumer is stopped.
        errors: list[str] = []
        for component in (self.scheduler, self.worker):
            try:
                result = component.stop()
                if self._component_alive(component, result):
                    errors.append(
                        f"{component.__class__.__name__} remained alive after stop"
                    )
            except BaseException as exc:
                errors.append(f"{component.__class__.__name__} stop failed: {exc}")
        snapshot_error = self._reconcile_snapshot_cleanup()
        if snapshot_error:
            errors.append(snapshot_error)
        with self._lock:
            self._cleanup_errors = errors
            self._cleanup_pending = bool(errors)
            self._started = bool(errors)
        if errors:
            raise RuntimeError("; ".join(errors))

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
            cleanup_pending = self._cleanup_pending
            cleanup_error = "; ".join(self._cleanup_errors) if self._cleanup_errors else None
        source_cleanup_errors = getattr(self.scheduler, "source_cleanup_errors", {}) or {}
        source_cleanup_errors = dict(source_cleanup_errors)
        if source_cleanup_errors:
            cleanup_pending = True
            source_error = "; ".join(
                f"{source_id}: {error}"
                for source_id, error in sorted(source_cleanup_errors.items())
            )
            cleanup_error = "; ".join(
                value for value in (cleanup_error, source_error) if value
            )
        transient_cleanup = worker_status.get("transient_cleanup")
        transient_errors = (
            transient_cleanup.get("errors")
            if isinstance(transient_cleanup, dict)
            else None
        )
        if transient_errors:
            cleanup_pending = True
            details = "; ".join(
                str(item.get("reason") or "cleanup_failed")
                for item in transient_errors
                if isinstance(item, dict)
            )
            cleanup_error = "; ".join(
                value for value in (cleanup_error, f"automatic-memory transient cleanup: {details}") if value
            )
        if not started and not cleanup_pending:
            state = "stopped"
        elif cleanup_pending:
            state = "degraded"
        elif paused:
            state = "paused"
        elif scheduler_running and worker_running is True:
            state = "running"
        else:
            state = "degraded"
        heartbeat = None
        heartbeat_reason = self.HEARTBEAT_UNAVAILABLE_REASON
        heartbeat_age = None
        heartbeat_state = None
        heartbeat_instance = None
        heartbeat_generation = None
        heartbeat_last_error = None
        heartbeat_reader = getattr(self.scheduler, "heartbeat_status", None)
        if callable(heartbeat_reader):
            heartbeat = heartbeat_reader()
            if heartbeat is not None:
                heartbeat_state = heartbeat.get("state")
                heartbeat_instance = heartbeat.get("instance_id")
                heartbeat_generation = heartbeat.get("generation")
                heartbeat_last_error = heartbeat.get("last_error")
                heartbeat_reason = heartbeat.get("reason") or heartbeat_last_error
                timestamp = heartbeat.get("heartbeat_at")
                try:
                    parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    heartbeat_age = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
                    if heartbeat_age < 0:
                        heartbeat_reason = "clock jump detected: heartbeat is in the future"
                        state = "degraded"
                    elif heartbeat_age > 10 and heartbeat_state in {"running", "paused"}:
                        heartbeat_reason = f"heartbeat stale: age={heartbeat_age:.3f}s"
                        state = "degraded"
                except (TypeError, ValueError, OverflowError):
                    heartbeat_age = None
                    heartbeat_reason = "heartbeat timestamp unavailable"
                    state = "degraded" if started else state
                if heartbeat_state == "degraded":
                    state = "degraded"
        watcher_enabled = bool(getattr(self.scheduler, "event_watcher_enabled", True))
        watcher = getattr(self.scheduler, "watcher", None)
        if not watcher_enabled:
            sources = ()
        else:
            try:
                sources = tuple(watcher.running_sources()) if watcher is not None else ()
            except Exception:
                sources = None
        return {
            "state": state,
            "running": bool(started or cleanup_pending or scheduler_running or worker_running),
            "paused": paused,
            "cleanup_pending": cleanup_pending,
            "cleanup_error": cleanup_error,
            "source_cleanup_errors": source_cleanup_errors,
            "scheduler_state": "running" if scheduler_running else "stopped",
            "scheduler_heartbeat_at": heartbeat.get("heartbeat_at") if heartbeat else None,
            "scheduler_heartbeat_age": heartbeat_age,
            "scheduler_heartbeat_reason": heartbeat_reason,
            "scheduler_heartbeat_instance": heartbeat_instance,
            "scheduler_heartbeat_generation": heartbeat_generation,
            "scheduler_heartbeat_state": heartbeat_state,
            "scheduler_heartbeat_last_error": heartbeat_last_error,
            "worker_state": worker_running,
            "worker": worker_status,
            "authorized_watcher_count": len(sources) if sources is not None else None,
            "watcher_sources": list(sources) if sources is not None else None,
            "automation_mode": str(
                getattr(self.scheduler, "automation_mode", "event_watcher")
            ),
            "event_watcher_enabled": watcher_enabled,
            "next_reconciliation_seconds": float(
                getattr(self.scheduler, "next_reconciliation_seconds", 900.0)
            ),
            "last_global_error": self._last_global_error() or cleanup_error,
        }

    def _touch_active_scan_work(self) -> None:
        """Refresh active scan Work Facts without appending event rows."""
        failures: list[str] = []
        for scan in self.state_db.list_automatic_memory_scans():
            if scan.get("status") == "running":
                try:
                    self.work_store.touch_work(f"automatic-memory:{scan['scan_id']}")
                except Exception as exc:
                    failures.append(f"{scan.get('source_id') or scan.get('scan_id')}: {exc}")
        if failures:
            raise RuntimeError("; ".join(failures)[:2000])

    def scan_now(self, source_id: str) -> dict[str, object]:
        result = self.scheduler.reconcile(source_id, reason="manual")
        if is_dataclass(result):
            value = asdict(result)
            value["source_id"] = source_id
            return value
        if isinstance(result, dict):
            value = dict(result)
            value.setdefault("source_id", source_id)
            scan_id = value.get("scan_id")
            if scan_id is not None:
                value.setdefault("work_id", f"automatic-memory:{scan_id}")
            return value
        return {"source_id": source_id, "result": result}

    def _authorized_paths(self, _scan: Any, source: Any) -> tuple[Path, ...]:
        if isinstance(source, SourceRecord):
            record = source
        else:
            record = SourceRecord(
                source_id=str(source["source_id"]), kind=str(source["kind"]), root=str(source["root"]),
                status=str(source["status"]), capability=str(source.get("capability") or "metadata_discovery"),
                policy_version=str(source.get("policy_version") or "automatic-memory-source-v1"),
            )
        return enumerate_authorized_files(record)

    def _run_scan(self, scan_id: str, source_id: str, reason: str = "scheduled") -> Any:
        work_id = f"automatic-memory:{scan_id}"
        source = next((item for item in self.registry.list_sources() if item.source_id == source_id), None)
        title = f"扫描 {source.kind if source else source_id}"
        work = self.work_store.get_work(work_id)
        if work is None:
            work = self.work_store.create_work(WorkItem(work_id=work_id, title=title, source_id=source_id, status="accepted", owner_approved=True))
            self.work_store.append_event(ExecutionEvent(work_id=work_id, event_id=f"scan:{scan_id}:started", event_type="scan.started", detail={"scan_id": scan_id, "source_id": source_id, "reason": reason}))
        try:
            result = self.runner.run(scan_id)
            self._scan_reports[scan_id] = result
            status = getattr(result, "status", None) or (result.get("status") if isinstance(result, dict) else None)
            self.work_store.append_event(ExecutionEvent(work_id=work_id, event_id=f"scan:{scan_id}:{status or 'progress'}", event_type="scan.completed" if status == "completed" else "scan.progress", detail={"scan_id": scan_id, "status": status, "progress": getattr(result, "progress", None)}))
            last_error = getattr(result, "last_error", None)
            cleanup_failed = isinstance(last_error, str) and last_error.startswith(
                "snapshot temporary cleanup failed:"
            )
            if status == "failed" or cleanup_failed:
                self.work_bridge.record_failure(work_id, stage="snapshot", reason=str(last_error or "automatic-memory snapshot failed"), retryable=True, evidence={"scan_id": scan_id})
            else:
                self._maybe_finalize_scan_work(scan_id, result)
            return result
        except Exception as exc:
            self.work_bridge.record_failure(work_id, stage="snapshot", reason=str(exc)[:2000], retryable=True, evidence={"scan_id": scan_id})
            raise

    def _on_extraction_lifecycle(self, phase: str, job: Any, result: Any, error: str | None) -> None:
        if str(job.get("source_type") or "") != "automatic_memory_snapshot":
            return
        payload = job.get("payload") if isinstance(job, dict) else None
        if not isinstance(payload, dict) or not payload.get("scan_id"):
            return
        scan_id = str(payload["scan_id"])
        work_id = f"automatic-memory:{scan_id}"
        self.work_store.append_event(ExecutionEvent(work_id=work_id, event_id=f"extraction:{job.get('job_id')}:{phase}", event_type=f"extraction.{phase}", detail={"job_id": job.get("job_id"), "error": error, "source_type": payload.get("source_type")}))
        self._maybe_finalize_scan_work(scan_id)

    def _maybe_finalize_scan_work(self, scan_id: str, report: Any | None = None) -> None:
        work_id = f"automatic-memory:{scan_id}"
        if self.work_store.get_work(work_id) is None:
            return
        report = report or self._scan_reports.get(scan_id)
        scan = self.state_db.get_automatic_memory_scan(scan_id)
        if scan is None or scan.get("status") not in {"completed", "failed", "cancelled"}:
            # A paused/resumable scan may already have terminal extraction
            # jobs from its first checkpoint.  Do not turn those jobs into a
            # terminal Work Fact until the durable scan itself completes.
            return
        cleanup_error = scan.get("last_error")
        if isinstance(cleanup_error, str) and cleanup_error.startswith(
            "snapshot temporary cleanup failed:"
        ):
            self.work_bridge.record_failure(
                work_id,
                stage="snapshot",
                reason=cleanup_error,
                retryable=True,
                evidence={"scan_id": scan_id},
            )
            self._scan_reports.pop(scan_id, None)
            return
        jobs = [item for item in self.queue.list_page(source_type="automatic_memory_snapshot", limit=200) if str((item.get("payload") or {}).get("scan_id") or "") == scan_id]
        if any(item.get("status") not in {"completed", "failed", "cancelled"} for item in jobs):
            return
        if any(item.get("status") in {"failed", "cancelled"} for item in jobs):
            self.work_bridge.record_failure(work_id, stage="extraction", reason="一个或多个来源文件提取失败，其他来源仍可继续", retryable=False, evidence={"scan_id": scan_id, "failed_jobs": [item.get("job_id") for item in jobs if item.get("status") in {"failed", "cancelled"}]})
            self._scan_reports.pop(scan_id, None)
            return
        queued = int(getattr(report, "queued", 0) or 0)
        reused = int(getattr(report, "reused", 0) or 0)
        reported_total = getattr(report, "total", None) if report is not None else None
        if reported_total is None and report is not None:
            reported_total = getattr(report, "discovered", None)
        if reported_total is None:
            total = queued + reused if report is not None else len(jobs)
        else:
            total = max(int(reported_total or 0), len(jobs))
        if not jobs and reused == 0 and queued == 0 and report is None:
            return
        summary = f"扫描完成，已检查 {total} 个来源文件（新增 {queued}，复用 {reused}）"
        self.work_bridge.complete_extraction(work_id, summary, evidence={"scan_id": scan_id, "jobs": len(jobs), "queued": queued, "reused": reused, "next_actor": "system"})
        self._scan_reports.pop(scan_id, None)

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

    @staticmethod
    def _component_alive(component: Any, result: Any | None = None) -> bool:
        if isinstance(result, dict):
            if result.get("thread_alive") is True or result.get("running") is True:
                return True
            if result.get("stopped") is False:
                return True
        running = getattr(component, "running", None)
        if running is True:
            return True
        try:
            status = component.status()
        except Exception:
            status = None
        if isinstance(status, dict):
            if status.get("thread_alive") is True or status.get("running") is True:
                return True
            worker_stop = status.get("stop_outcome")
            if isinstance(worker_stop, dict) and worker_stop.get("thread_alive") is True:
                return True
        watcher = getattr(component, "watcher", None)
        try:
            if watcher is not None and watcher.running_sources():
                return True
        except Exception:
            return True
        return False
