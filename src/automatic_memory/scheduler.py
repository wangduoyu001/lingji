from __future__ import annotations

import inspect
import threading
from datetime import datetime, timezone
from concurrent.futures import Future
from dataclasses import dataclass, replace
from typing import Any, Callable
from uuid import uuid4

from src.scheduler.cron import CronScheduler
from src.storage.state_db import StateDatabase

from .models import ScanRun
from .policy import resolve_event_watcher_enabled
from .source_registry import SourceRegistry
from .watcher import AutomaticMemoryWatcher


@dataclass(frozen=True)
class ReconciliationReport:
    discovered: int
    queued: int
    unchanged: int
    errors: tuple[str, ...]
    complete: bool
    reused: int = 0
    # Durable identity of the scan admitted by this reconciliation call.  The
    # optional fields preserve compatibility with existing runner callbacks and
    # reports while allowing callers to bind evidence to this exact scan.
    scan_id: str | None = None
    work_id: str | None = None
    # A report produced by an actual completed scanner has measured counts;
    # a ScanRun without persisted evidence must remain unmeasured even when
    # internal arithmetic uses zero.
    counts_measured: bool = True


class AutomaticMemoryScheduler:
    """Own automatic-memory lifecycle on top of the existing CronScheduler."""

    JOB_PREFIX = "automatic_memory:"
    RECONCILIATION_SECONDS = 900.0
    INTEGRITY_SECONDS = 86400.0

    @staticmethod
    def resolve_event_watcher_enabled(
        configured: bool | None, *, platform_name: str | None = None
    ) -> bool:
        return resolve_event_watcher_enabled(configured, platform_name=platform_name)

    def __init__(
        self,
        state_db: StateDatabase,
        source_registry: SourceRegistry,
        *,
        scan_runner: Callable[..., Any],
        watcher: AutomaticMemoryWatcher | None = None,
        cron: CronScheduler | None = None,
        poll_seconds: float = 60.0,
        debounce_seconds: float = 5.0,
        reconciliation_seconds: float = RECONCILIATION_SECONDS,
        integrity_seconds: float = INTEGRITY_SECONDS,
        heartbeat_seconds: float = 5.0,
        heartbeat_work_callback: Callable[[], Any] | None = None,
        event_watcher_enabled: bool = True,
    ) -> None:
        self.state_db = state_db
        self.registry = source_registry
        self.scan_runner = scan_runner
        self.cron = cron or CronScheduler(state_db, poll_seconds=poll_seconds)
        self.debounce_seconds = max(float(debounce_seconds), 0.1)
        self.reconciliation_seconds = max(float(reconciliation_seconds), 1.0)
        self.integrity_seconds = max(float(integrity_seconds), 1.0)
        self.heartbeat_seconds = max(min(float(heartbeat_seconds), 5.0), 0.05)
        self.heartbeat_work_callback = heartbeat_work_callback
        # The watcher remains injectable for compatibility and test coverage,
        # while the packaged macOS runtime opts into safer periodic mode.
        self.event_watcher_enabled = bool(event_watcher_enabled)
        self.automation_mode = (
            "event_watcher" if self.event_watcher_enabled else "periodic_reconciliation"
        )
        self.next_reconciliation_seconds = self.reconciliation_seconds
        self.watcher = watcher or AutomaticMemoryWatcher(
            source_provider=self._source,
            on_change=lambda source_id: self.reconcile(source_id, reason="event"),
            on_error=self._watch_error,
        )
        self._lock = threading.RLock()
        self._running = False
        self._paused = False
        self._inflight: dict[str, Future[ReconciliationReport]] = {}
        self._listener_registered = False
        self._listener_callback: Callable[[Any], None] | None = None
        self._lifecycle_generation = 0
        self._scheduler_owner = f"automatic-memory-scheduler-{uuid4().hex}"
        self._scheduler_lease_seconds = 30.0
        self._source_cleanup_errors: dict[str, str] = {}
        self._cleanup_error_parts: dict[str, dict[str, str]] = {}
        self._stop_lock = threading.Lock()
        self.instance_id = f"automatic-memory-{uuid4().hex}"
        self.generation = 0
        self._heartbeat_last_error: str | None = None
        self._heartbeat_reason: str | None = None

    @property
    def source_cleanup_errors(self) -> dict[str, str]:
        with self._lock:
            return dict(self._source_cleanup_errors)

    def _record_cleanup_error(self, key: str, owner: str, error: str) -> None:
        with self._lock:
            parts = self._cleanup_error_parts.setdefault(key, {})
            parts[owner] = error
            self._source_cleanup_errors[key] = "; ".join(parts.values())

    def _clear_cleanup_owner(self, owner: str) -> None:
        with self._lock:
            for key, parts in tuple(self._cleanup_error_parts.items()):
                if owner not in parts:
                    continue
                parts.pop(owner, None)
                if parts:
                    self._source_cleanup_errors[key] = "; ".join(parts.values())
                else:
                    self._cleanup_error_parts.pop(key, None)
                    self._source_cleanup_errors.pop(key, None)

    def _clear_watcher_cleanup_errors(self) -> None:
        with self._lock:
            for key, parts in tuple(self._cleanup_error_parts.items()):
                for owner in tuple(parts):
                    if owner == "watcher" or owner.startswith("watcher:"):
                        parts.pop(owner, None)
                if parts:
                    self._source_cleanup_errors[key] = "; ".join(parts.values())
                else:
                    self._cleanup_error_parts.pop(key, None)
                    self._source_cleanup_errors.pop(key, None)

    def start(self) -> None:
        with self._stop_lock:
            with self._lock:
                if self._running:
                    return
                self._lifecycle_generation += 1
                self.generation = self._lifecycle_generation
                generation = self._lifecycle_generation
                listener = lambda source, token=generation: self._on_source_lifecycle(source, token)
                self._listener_callback = listener
                self.registry.add_lifecycle_listener(listener)
                self._listener_registered = True
                self._paused = False
                self._running = True
                sources = self.registry.list_sources()
                for source in sources:
                    self._attach_source(source)
                self._write_heartbeat("running")
                configure_heartbeat = getattr(self.cron, "configure_heartbeat", None)
                if callable(configure_heartbeat):
                    configure_heartbeat(self._heartbeat_tick, interval_seconds=self.heartbeat_seconds)
                try:
                    self.cron.start(self._run_cron_job)
                except BaseException as exc:
                    self._running = False
                    self._write_heartbeat("degraded", reason=f"scheduler start failed: {exc}")
                    raise

    def stop(self) -> None:
        # Serialize start, shutdown, and retries so lifecycle generations cannot
        # interleave while an owned watcher or cron thread is being measured.
        with self._stop_lock:
            with self._lock:
                self._running = False
                self._lifecycle_generation += 1
                callback = self._listener_callback
                if callback is not None:
                    self.registry.remove_lifecycle_listener(callback)
                self._listener_callback = None
                self._listener_registered = False
            self._write_heartbeat("stopping")
            watcher_result: dict[str, object] = {}
            watcher_error: BaseException | None = None
            if self.event_watcher_enabled:
                try:
                    watcher_result = self.watcher.stop() or {}
                except BaseException as exc:
                    watcher_error = exc
            cron_error: BaseException | None = None
            try:
                self.cron.stop()
            except BaseException as exc:
                cron_error = exc
            errors = [error for error in (watcher_error, cron_error) if error is not None]
            survivors = watcher_result.get("surviving_threads") or []
            if watcher_error is not None:
                self._record_cleanup_error(
                    "__scheduler__", "watcher", str(watcher_error)
                )
            elif survivors:
                watcher_message = (
                    "automatic-memory watcher threads survived stop: "
                    + ", ".join(str(item) for item in survivors)
                )
                errors.append(RuntimeError(watcher_message))
                self._record_cleanup_error("__scheduler__", "watcher", watcher_message)
            else:
                self._clear_watcher_cleanup_errors()
            cron_running = bool(getattr(self.cron, "running", False))
            if cron_running and cron_error is None:
                cron_error = RuntimeError("automatic-memory cron scheduler remained alive after stop")
                errors.append(cron_error)
            if cron_error is not None:
                self._record_cleanup_error("__scheduler__", "cron", str(cron_error))
            else:
                self._clear_cleanup_owner("cron")
            if errors:
                self._write_heartbeat("degraded", reason="; ".join(str(error) for error in errors))
                raise RuntimeError("; ".join(str(error) for error in errors))
            self._write_heartbeat("stopped")

    def heartbeat_status(self) -> dict[str, Any] | None:
        try:
            rows = self.state_db.list_automatic_memory_heartbeats(instance_id=self.instance_id)
        except Exception as exc:
            return {
                "instance_id": self.instance_id,
                "generation": self.generation,
                "state": "degraded",
                "heartbeat_at": None,
                "reason": f"heartbeat read failed: {exc}",
                "last_error": str(exc)[:2000],
            }
        row = rows[0] if rows else None
        if self._heartbeat_last_error:
            if row is None:
                return {
                    "instance_id": self.instance_id,
                    "generation": self.generation,
                    "state": "degraded",
                    "heartbeat_at": None,
                    "reason": self._heartbeat_reason,
                    "last_error": self._heartbeat_last_error,
                }
            row = dict(row)
            row["state"] = "degraded"
            row["reason"] = self._heartbeat_reason
            row["last_error"] = self._heartbeat_last_error
        return row

    def _heartbeat_tick(self) -> None:
        with self._lock:
            if not self._running:
                return
            state = "paused" if self._paused else "running"
            # Keep the lifecycle lock through the write.  Otherwise stop could
            # publish ``stopped`` and then lose the race to a tick that had
            # already observed ``_running``.
            self._write_heartbeat(state)
            callback = self.heartbeat_work_callback
            if callback is not None:
                try:
                    callback()
                except Exception as exc:
                    error = str(exc)[:2000] or exc.__class__.__name__
                    reason = f"active work heartbeat failed: {error}"
                    self._heartbeat_last_error = error
                    self._write_heartbeat("degraded", reason=reason)

    def _write_heartbeat(self, state: str, *, reason: str | None = None) -> None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        try:
            self.state_db.upsert_automatic_memory_heartbeat(
                self.instance_id,
                self.generation,
                state,
                heartbeat_at=timestamp,
                reason=reason,
                last_error=self._heartbeat_last_error if state == "degraded" else None,
            )
            self._heartbeat_last_error = None
            self._heartbeat_reason = reason
        except Exception as exc:
            self._heartbeat_last_error = str(exc)[:2000]
            self._heartbeat_reason = f"heartbeat write failed: {self._heartbeat_last_error}"

    def pause(self) -> None:
        with self._lock:
            self._paused = True
        if self.event_watcher_enabled:
            self.watcher.pause()
        self.cron.set_jobs_enabled(self.JOB_PREFIX, False)
        self._write_heartbeat("paused")

    def resume(self) -> None:
        with self._lock:
            self._paused = False
        self.cron.set_jobs_enabled(self.JOB_PREFIX, True)
        for source in self.registry.list_sources():
            if source.status != "authorized":
                self._disable_source(source.source_id)
        if self.event_watcher_enabled:
            self.watcher.resume()
        self._write_heartbeat("running")

    def status(self) -> tuple[ScanRun, ...]:
        rows = self.state_db.list_automatic_memory_scans()
        return tuple(
            ScanRun(
                scan_id=row["scan_id"],
                source_id=row["source_id"],
                status=row["status"],
                cursor=row.get("cursor"),
                progress=int(row.get("progress") or 0),
                total=int(row["total"]) if row.get("total") is not None else None,
                last_error=row.get("last_error"),
                recovery_token=row.get("recovery_token"),
                source_sentinel=row.get("source_sentinel"),
                lease_id=row.get("lease_id"),
                attempt=int(row.get("attempt") or 0),
                queued=(
                    int(row["queued_count"])
                    if row.get("queued_count") is not None
                    else None
                ),
                reused=(
                    int(row["reused_count"])
                    if row.get("reused_count") is not None
                    else None
                ),
                counts_present=tuple(
                    key
                    for key, value in (
                        ("queued", row.get("queued_count")),
                        ("reused", row.get("reused_count")),
                    )
                    if value is not None
                ),
                updated_at=row.get("updated_at"),
            )
            for row in rows
        )

    def reconcile(self, source_id: str, *, reason: str = "reconciliation") -> ReconciliationReport:
        """Run one source at a time and merge concurrent triggers."""
        with self._lock:
            future = self._inflight.get(source_id)
            owner = future is None
            if owner:
                future = Future()
                self._inflight[source_id] = future
        if not owner:
            return future.result()
        try:
            result = self._reconcile_once(source_id, reason=reason)
            future.set_result(result)
            return result
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._inflight.pop(source_id, None)

    def _reconcile_once(self, source_id: str, *, reason: str) -> ReconciliationReport:
        if self._paused:
            return ReconciliationReport(0, 0, 0, ("scheduler is paused",), False)
        scan = None
        try:
            source = self._source(source_id)
            if source.status != "authorized":
                self._disable_source(source_id)
                return ReconciliationReport(0, 0, 0, (f"source status is {source.status}",), False)
            scan = self._start_or_retry_scan(source_id)
            scheduler_lease_id = f"scheduler-lease-{uuid4().hex}"
            claimed = self.state_db.claim_automatic_memory_scheduler_scan(
                scan.scan_id,
                scheduler_lease_id,
                self._scheduler_owner,
                ttl_seconds=self._scheduler_lease_seconds,
            )
            if claimed is None:
                return ReconciliationReport(
                    0,
                    0,
                    0,
                    ("scan is already being processed",),
                    False,
                    scan_id=scan.scan_id,
                    work_id=f"automatic-memory:{scan.scan_id}",
                )
            heartbeat_stop = threading.Event()
            heartbeat = threading.Thread(
                target=self._scheduler_lease_heartbeat,
                args=(scan.scan_id, scheduler_lease_id, heartbeat_stop),
                daemon=True,
                name=f"lingji-memory-scan-heartbeat-{source_id}",
            )
            heartbeat.start()
            try:
                result = self._invoke_runner(scan.scan_id, source_id, reason)
            finally:
                heartbeat_stop.set()
                if heartbeat is not threading.current_thread():
                    heartbeat.join(timeout=1.0)
            report = replace(
                self._report(result),
                scan_id=scan.scan_id,
                work_id=f"automatic-memory:{scan.scan_id}",
            )
            if report.complete:
                current = self.registry.get_scan(scan.scan_id)
                if current.status == "completed":
                    finalized = current
                elif current.status == "cancelled":
                    finalized = None
                else:
                    finalized = self.registry.complete_scan_if_authorized(
                        scan.scan_id,
                        progress=max(report.queued, report.discovered - report.unchanged),
                        total=report.discovered,
                        queued_count=report.queued if report.counts_measured else None,
                        reused_count=report.reused if report.counts_measured else None,
                    )
                if finalized is None:
                    current = self.registry.get_scan(scan.scan_id)
                    if current.status == "running":
                        self.registry.fail_scan_if_running(
                            scan.scan_id,
                            last_error="source authorization changed during reconciliation",
                            progress=report.queued,
                            total=report.discovered,
                        )
                    error = (
                        "source authorization revoked during reconciliation"
                        if current.status == "cancelled"
                        else "source authorization changed during reconciliation"
                    )
                    report = replace(report, errors=(error,), complete=False)
            else:
                error = "; ".join(report.errors)[:2000] or "reconciliation incomplete"
                self.registry.fail_scan_if_running(
                    scan.scan_id,
                    progress=report.queued,
                    total=report.discovered,
                    last_error=error,
                )
            self.state_db.append_event(
                "automatic_memory_reconciliation",
                "source",
                source_id,
                {
                    "reason": reason,
                    "scan_id": report.scan_id,
                    "work_id": report.work_id,
                    "discovered": report.discovered,
                    "queued": report.queued,
                    "unchanged": report.unchanged,
                    "errors": list(report.errors),
                    "complete": report.complete,
                    "next_action": (
                        "wait for watcher or scheduled reconciliation"
                        if report.complete
                        else "retry on the next event or scheduled reconciliation"
                    ),
                },
            )
            return report
        except Exception as exc:
            error = str(exc)[:2000] or exc.__class__.__name__
            if scan is not None:
                try:
                    self.registry.fail_scan_if_running(scan.scan_id, last_error=error)
                except Exception:
                    pass
            self.state_db.append_event(
                "automatic_memory_reconciliation_failed",
                "source",
                source_id,
                {
                    "reason": reason,
                    "scan_id": scan.scan_id if scan is not None else None,
                    "work_id": (f"automatic-memory:{scan.scan_id}" if scan is not None else None),
                    "error": error,
                    "complete": False,
                    "next_action": "retry this source on the next scheduled pass",
                },
            )
            return ReconciliationReport(
                0,
                0,
                0,
                (error,),
                False,
                scan_id=scan.scan_id if scan is not None else None,
                work_id=(f"automatic-memory:{scan.scan_id}" if scan is not None else None),
            )
        finally:
            if scan is not None and "scheduler_lease_id" in locals():
                try:
                    self.state_db.release_automatic_memory_scheduler_scan_lease(
                        scan.scan_id, scheduler_lease_id
                    )
                except Exception:
                    pass

    def _run_cron_job(self, name: str) -> None:
        parts = name.split(":")
        if len(parts) != 3 or parts[0] != "automatic_memory":
            return
        source_id, kind = parts[1], parts[2]
        if kind == "reconciliation":
            report = self.reconcile(source_id, reason="reconciliation")
            if not report.complete:
                raise RuntimeError("; ".join(report.errors) or "reconciliation failed")
        elif kind == "integrity":
            report = self.reconcile(source_id, reason="integrity")
            if not report.complete:
                raise RuntimeError("; ".join(report.errors) or "integrity check failed")

    def _watch_error(self, source_id: str, error: str) -> None:
        self.state_db.append_event(
            "automatic_memory_watcher_failed",
            "source",
            source_id,
            {
                "error": error[:2000],
                "complete": False,
                "next_action": "reconciliation remains authoritative and will retry",
            },
        )

    def _disable_source(self, source_id: str) -> None:
        # Disable admission before asking a watcher backend to stop. The
        # bounded join is deliberately short: revocation is a linearized
        # lifecycle transition and must not block on an uncooperative backend.
        cron_errors: list[str] = []
        watcher_errors: list[str] = []
        try:
            self.cron.set_jobs_enabled(self._source_prefix(source_id), False)
        except Exception as exc:
            cron_errors.append(f"failed to disable source jobs: {exc}")
        if self.event_watcher_enabled:
            try:
                result = self.watcher.stop_source(source_id, timeout_seconds=0.1) or {}
            except Exception as exc:
                result = {}
                watcher_errors.append(f"failed to stop source watcher: {exc}")
        else:
            result = {}
        survivors = result.get("surviving_threads") or []
        if survivors:
            watcher_errors.append(
                "source watcher cleanup pending: "
                + ", ".join(str(item) for item in survivors)
            )
        if cron_errors:
            self._record_cleanup_error(
                source_id, f"cron:{source_id}", "; ".join(cron_errors)
            )
        else:
            self._clear_cleanup_owner(f"cron:{source_id}")
        if watcher_errors:
            self._record_cleanup_error(
                source_id, f"watcher:{source_id}", "; ".join(watcher_errors)
            )
        else:
            self._clear_cleanup_owner(f"watcher:{source_id}")
        errors = cron_errors + watcher_errors
        if errors:
            try:
                self.state_db.append_event(
                    "automatic_memory_source_cleanup_failed",
                    "source",
                    source_id,
                    {"error": "; ".join(errors), "cleanup_pending": bool(survivors)},
                )
            except Exception:
                # In-memory status remains authoritative if audit persistence
                # is unavailable; lifecycle observers must not hide the fact.
                pass

    def _attach_source(self, source) -> None:
        """Attach one newly authorized source to this scheduler instance."""
        if source.status != "authorized":
            return
        prefix = self._source_prefix(source.source_id)
        self.cron.add_job(
            f"{prefix}reconciliation",
            self.reconciliation_seconds / 3600.0,
            run_on_start=True,
        )
        self.cron.add_job(
            f"{prefix}integrity",
            self.integrity_seconds / 3600.0,
            run_on_start=False,
        )
        if self.event_watcher_enabled:
            try:
                self.watcher.start(source.source_id, debounce_seconds=self.debounce_seconds)
            except Exception as exc:
                self._watch_error(source.source_id, str(exc)[:2000])
        if self._paused:
            self.cron.set_jobs_enabled(prefix, False)

    def _on_source_lifecycle(self, source, generation: int | None = None) -> None:
        with self._lock:
            if (
                not self._running
                or not self._listener_registered
                or generation is not None
                and generation != self._lifecycle_generation
            ):
                return
            # Keep the generation token valid through the side effect.  This
            # prevents stop/start from interleaving between validation and
            # disabling a newly-started scheduler's jobs.
            if source.status != "authorized":
                self._disable_source(source.source_id)
            else:
                self._attach_source(source)

    def _scheduler_lease_heartbeat(
        self, scan_id: str, lease_id: str, stop: threading.Event
    ) -> None:
        interval = max(min(self._scheduler_lease_seconds / 3.0, 1.0), 0.05)
        while not stop.wait(interval):
            if not self.state_db.renew_automatic_memory_scheduler_scan_lease(
                scan_id, lease_id, ttl_seconds=self._scheduler_lease_seconds
            ):
                return

    def _start_or_retry_scan(self, source_id: str) -> ScanRun:
        try:
            return self.registry.start_scan(source_id)
        except ValueError as exc:
            if "failed scan must be retried" not in str(exc):
                raise
            failed = next(
                (
                    row
                    for row in self.state_db.list_automatic_memory_scans(source_id)
                    if row.get("status") == "failed"
                ),
                None,
            )
            if failed is None:
                raise
            return self.registry.retry_scan(failed["scan_id"])

    def _invoke_runner(self, scan_id: str, source_id: str, reason: str) -> Any:
        signature = inspect.signature(self.scan_runner)
        positional = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        if any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in signature.parameters.values()):
            return self.scan_runner(scan_id, source_id, reason)
        if len(positional) >= 3:
            return self.scan_runner(scan_id, source_id, reason)
        if len(positional) == 2:
            # SnapshotJobRunner.run(scan_id, crash_at="none") is a real
            # two-parameter runner, but its second argument is a control
            # option rather than the source-id injection used by Task 4
            # callbacks.  Keep the established two-argument callback
            # contract for every other callable.
            if positional[1].name == "crash_at":
                return self.scan_runner(scan_id)
            return self.scan_runner(scan_id, source_id)
        return self.scan_runner(scan_id)

    @staticmethod
    def _report(result: Any) -> ReconciliationReport:
        if isinstance(result, ReconciliationReport):
            return result
        if isinstance(result, ScanRun):
            complete = result.status == "completed"
            return ReconciliationReport(
                int(result.total or result.progress) if complete else int(result.progress),
                int(result.queued or 0) if complete else int(result.progress),
                0,
                (result.last_error or f"scan ended with status {result.status}",)
                if not complete
                else (),
                complete,
                int(result.reused or 0),
                counts_measured=(
                    result.queued is not None and result.reused is not None
                ),
            )
        if result is None:
            raise TypeError("automatic-memory scan runner must return a report")
        raise TypeError("automatic-memory scan runner returned an unsupported report")

    def _source(self, source_id: str):
        for source in self.registry.list_sources():
            if source.source_id == source_id:
                return source
        raise LookupError(f"source not found: {source_id}")

    @classmethod
    def _source_prefix(cls, source_id: str) -> str:
        return f"{cls.JOB_PREFIX}{source_id}:"
