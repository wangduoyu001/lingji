"""Composition boundary for the packaged automatic-memory runtime.

This module deliberately contains orchestration only.  Discovery, adapter
selection and snapshot-job consumption remain owned by the existing
components (and are completed by the later automatic-memory tasks).
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Any, Callable

from concurrent.futures import TimeoutError as FuturesTimeoutError

import logging

_logger = logging.getLogger(__name__)
from src.storage import StateDatabase

from .checkpoint import SnapshotJobRunner
from .pipeline_health import PipelineHealth
from .scheduler import AutomaticMemoryScheduler
from .snapshot import ConsistentSnapshot
from .source_registry import SourceRegistry
from .models import SourceRecord
from .policy import resolve_event_watcher_enabled
from .path_policy import enumerate_authorized_files
from .job_facts import association_from_status, resolve_job_facts, summarize_job_facts
from src.work.capture_bridge import CaptureWorkBridge
from src.work.models import ExecutionEvent, WorkItem
from src.work.projector import WorkProjector
from src.work.store import WorkStore


def _optional_float(value: Any) -> float | None:
    try:
        numeric = float(value) if value is not None else None
        return numeric if numeric is not None and math.isfinite(numeric) and numeric > 0 else None
    except (TypeError, ValueError):
        return None


def _effective_batch(base: int, pending: int) -> int:
    """积压消化期自适应提速：历史积压大时批次 ×3（上限 8），稳态回基础批次。

    云端通道单段 7-22s，基础批次 2 对几周攒下的数百段积压要 ~10 小时；
    提 3 倍只影响积压期，稳态行为不变。
    """
    base = max(int(base), 1)
    if int(pending) > 50:
        return min(base * 3, 8)
    return base


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
        platform_provider: Callable[[], str] | None = None,
        semantic_provider: Any | None = None,
    ) -> None:
        self.state_db = state_db
        self.settings = settings
        # 网关已有的语义写入通道（QdrantSemanticProvider）：chunk 回填复用它，
        # 避免自建第二个 embedded Qdrant 客户端撞单进程锁。
        self._semantic_provider = semantic_provider
        if pipeline is None and settings is not None:
            # Import lazily: extraction adapters import automatic_memory models
            # during bootstrap, so a module-level import would create a cycle.
            from src.extraction.bootstrap import build_extraction_pipeline

            pipeline = build_extraction_pipeline(settings)
        self.pipeline = pipeline
        self._platform_provider = platform_provider
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
        # B1 收尾：runner 阈值 provider 复用一个懒创建的 RuntimeSettingsStore
        # （存 self 上，与提炼/晋升各自独立），读失败回退静态 settings 值。
        self._runner_settings_store: Any | None = None
        self._runner_settings_store_failed = False
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
                raw_max_bytes=int(getattr(settings, "automatic_memory_raw_max_bytes", 10 * 1024 ** 3)),
                value_gate_enabled=bool(getattr(settings, "value_gate_enabled", False)),
                value_gate_min_turns=int(getattr(settings, "value_gate_min_turns", 2)),
                value_gate_min_chars=int(getattr(settings, "value_gate_min_chars", 300)),
                value_gate_config_provider=self._value_gate_config,
            )
            configured_event_watcher = getattr(
                settings, "automatic_memory_event_watcher_enabled", None
            )
            if self._platform_provider is None:
                event_watcher_enabled = resolve_event_watcher_enabled(
                    configured_event_watcher
                )
            else:
                event_watcher_enabled = resolve_event_watcher_enabled(
                    configured_event_watcher,
                    platform_name=self._platform_provider(),
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
                event_watcher_enabled=event_watcher_enabled,
                heartbeat_seconds=float(
                    getattr(settings, "automatic_memory_heartbeat_seconds", 5.0)
                ),
                snapshot_throttle_seconds=float(
                    getattr(settings, "automatic_memory_snapshot_throttle_seconds", 1800.0)
                ),
                vector_backfill_callback=self._wake_vector_backfill,
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
        self._distiller = self._build_distiller(settings)
        self._distill_stop = Event()
        self._distill_thread: Thread | None = None
        self._promotion = self._build_auto_promotion(settings)
        self._promotion_stop = Event()
        self._promotion_thread: Thread | None = None
        self._backfill_drain = self._build_vector_backfill_callback(settings)
        # 手动扫描专用单线程执行器（2026-09-27 事故加固）：整库重拷+哈希绝不
        # 占用 FastAPI 线程池；单 worker 天然串行化手动扫描（源级并发另有
        # 调度器 single-flight 管辖）。
        from concurrent.futures import ThreadPoolExecutor

        self._scan_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lingji-manual-scan")
        # 快路径（早退/小源）在预算内同步返回真实报告，兼容既有契约；
        # 超预算才转"已受理"。
        self._scan_now_budget_seconds = 5.0
        self._backfill_wake = Event()
        self._backfill_stop = Event()
        self._backfill_thread: Thread | None = None
        # 三个 daemon 的故障可见性：吞异常可以，但必须计数、限频上报、status 可见。
        self._pipeline_health = {
            name: PipelineHealth(name, state_db)
            for name in ("distill", "promotion", "vector_backfill")
        }
        if hasattr(self.scheduler, "heartbeat_work_callback"):
            self.scheduler.heartbeat_work_callback = self._touch_active_scan_work
        if hasattr(self.registry, "add_lifecycle_listener"):
            # Project StateDB authorization transitions into the existing
            # structured read/index rows before current retrieval can observe
            # them. This is a read-model projection, not a second authority.
            self.registry.add_lifecycle_listener(self._on_source_lifecycle_projection)
        if hasattr(self.pipeline, "add_lifecycle_callback"):
            self.pipeline.add_lifecycle_callback(self._on_extraction_lifecycle)

    def _value_gate_config(self) -> tuple[bool, int, int]:
        """动态读取入口价值预判阈值；主人改设置后运行中 runner 立即生效。

        B1 收尾：store 懒创建并复用（存 self 上）；任何读取异常都回退构造
        时的静态 settings 值，绝不因设置读取失败阻断扫描。
        """
        settings = self.settings
        if self._runner_settings_store is None and not self._runner_settings_store_failed:
            try:
                from src.control.runtime_settings import RuntimeSettingsStore

                self._runner_settings_store = RuntimeSettingsStore(settings)
            except Exception:
                self._runner_settings_store_failed = True
        store = self._runner_settings_store
        if store is not None:
            try:
                # 只取主人在设置页显式写下的覆盖项（overrides）；目录默认值
                # 不得压过静态配置（env/config），否则部署级开关会被悄悄翻掉。
                overrides = store.snapshot()["overrides"]
                fallback = (
                    bool(getattr(settings, "value_gate_enabled", False)),
                    int(getattr(settings, "value_gate_min_turns", 2)),
                    int(getattr(settings, "value_gate_min_chars", 300)),
                )
                return (
                    bool(overrides.get("value_gate_enabled", fallback[0])),
                    int(overrides.get("value_gate_min_turns", fallback[1])),
                    int(overrides.get("value_gate_min_chars", fallback[2])),
                )
            except Exception:
                pass
        return (
            bool(getattr(settings, "value_gate_enabled", False)),
            int(getattr(settings, "value_gate_min_turns", 2)),
            int(getattr(settings, "value_gate_min_chars", 300)),
        )

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
                for scan in self.state_db.list_automatic_memory_scans():
                    if scan.get("status") in {"completed", "failed", "cancelled"}:
                        self._maybe_finalize_scan_work(str(scan.get("scan_id") or ""))
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
            self._start_distill_thread()

    def _start_distill_thread(self) -> None:
        """提炼是可重建派生层：daemon 线程推进，不参与启停成败判定。

        晋升与向量回填线程在此一并启动，但各自独立存在（提炼关闭不影响
        晋升与回填）。"""
        if self._distiller is not None and self._distill_thread is None:
            self._distill_stop.clear()
            self._distill_thread = Thread(
                target=self._distill_loop,
                name="lingji-knowledge-distiller",
                daemon=True,
            )
            self._distill_thread.start()
        if self._promotion is not None and self._promotion_thread is None:
            self._promotion_stop.clear()
            self._promotion_thread = Thread(
                target=self._promotion_loop,
                name="lingji-auto-promotion",
                daemon=True,
            )
            self._promotion_thread.start()
        if self._backfill_drain is not None and self._backfill_thread is None:
            self._backfill_stop.clear()
            self._backfill_wake.set()
            self._backfill_thread = Thread(
                target=self._backfill_loop,
                name="lingji-vector-backfill",
                daemon=True,
            )
            self._backfill_thread.start()

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
        self._distill_stop.set()
        self._promotion_stop.set()
        self._backfill_stop.set()
        self._backfill_wake.set()
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
            "next_reconciliation_seconds": _optional_float(
                getattr(self.scheduler, "next_reconciliation_seconds", None)
            ),
            "reconciliation_interval_seconds": _optional_float(
                getattr(self.scheduler, "next_reconciliation_seconds", None)
            ),
            "max_change_detection_delay_seconds": _optional_float(
                getattr(self.scheduler, "next_reconciliation_seconds", None)
            ),
            "pipelines": {
                name: health.snapshot()
                for name, health in self._pipeline_health.items()
            },
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

    def _build_vector_backfill_callback(self, settings: Any) -> Callable[[], object] | None:
        """每轮核对后自动补算向量；embedding 不可用时静默跳过。"""
        try:
            from src.model_center import build_embedding_provider
            from src.retrieval.vector_backfill import VectorBackfill

            provider = build_embedding_provider(settings)
            if provider is None:
                return None
            backfill = VectorBackfill(settings, provider=provider)
            chunk_drain = self._build_chunk_backfill(settings)

            def _run() -> object:
                # 每轮核对只补 200 条：新来源批量入库（如 ZCode 会话采集）会留下
                # 数千条长期缺口，语义检索覆盖掉到 84% 却要等数小时。改为在时间
                # 预算内循环追平积压；仍追不完的部分由下一轮核对继续，失败隔离
                # 语义不变。消息层与 chunk 层同一预算循环推进，两层都无进展才停。
                import time as _time

                deadline = _time.monotonic() + 300.0
                embedded_total = 0
                chunk_embedded_total = 0
                rounds = 0
                while _time.monotonic() < deadline:
                    result = backfill.run_once(limit=500)
                    embedded = int((result or {}).get("embedded") or 0)
                    embedded_total += embedded
                    chunk_result = chunk_drain() if chunk_drain is not None else None
                    chunk_embedded = int((chunk_result or {}).get("embedded") or 0)
                    chunk_embedded_total += chunk_embedded
                    rounds += 1
                    if not embedded and not chunk_embedded:
                        break
                return {
                    "embedded": embedded_total,
                    "chunk_embedded": chunk_embedded_total,
                    "rounds": rounds,
                }

            return _run
        except Exception:
            return None

    def _build_chunk_backfill(self, settings: Any) -> Callable[[], object] | None:
        """chunk 级正式语义集合的自动补齐。

        /api/vector/coverage 的缺口只有手动 vectorize 端点会补、从无自动触发，
        这是缺口长存的根因；这里把 ChunkVectorBackfill 并入 drain 线程。
        provider 复用网关的 semantic_provider（同进程共享 Qdrant 客户端池），
        网关缺位（单测/词法网关）时保持 None，不改变既有行为。
        """
        provider = self._semantic_provider
        if provider is None:
            return None
        try:
            from src.retrieval.chunk_backfill import ChunkVectorBackfill
            from src.retrieval.memory_db import MemoryDatabase

            database = MemoryDatabase(settings.memory_db_path)
            backfill = ChunkVectorBackfill(database, provider)

            def _run() -> object:
                # 全量重建实测嵌入为瓶颈（qwen3 0.6B ~2.5-4 条/秒）：每轮 500 条
                # 摊薄 coverage/孤儿扫描的固定开销，一轮无进展即交还外层预算循环。
                import time as _time

                deadline = _time.monotonic() + 120.0
                embedded_total = 0
                while True:
                    result = backfill.run_once(limit=500)
                    embedded = int((result or {}).get("embedded") or 0)
                    embedded_total += embedded
                    if not embedded or _time.monotonic() >= deadline:
                        break
                return {"embedded": embedded_total}

            return _run
        except Exception:
            return None

    def _build_distiller(self, settings: Any) -> Any | None:
        """全自动知识提炼器；Ollama 不可用时返回 None，提炼自动停用。"""
        if not bool(getattr(settings, "distill_enabled", True)):
            return None
        try:
            from src.automatic_memory.distillation import KnowledgeDistiller
            from src.control.runtime_settings import RuntimeSettingsStore

            store = RuntimeSettingsStore(settings)

            def _model_override() -> str:
                return str(store.snapshot()["values"].get("distill_model", "") or "")

            def _provider_override() -> str:
                return str(store.snapshot()["values"].get("distill_provider", "local") or "local")

            def _key_override() -> str:
                return str(store.snapshot()["values"].get("zhipu_api_key", "") or "")

            return KnowledgeDistiller(
                settings,
                model_override=_model_override,
                provider_override=_provider_override,
                api_key_override=_key_override,
            )
        except Exception:
            try:
                from src.automatic_memory.distillation import KnowledgeDistiller

                return KnowledgeDistiller(settings)
            except Exception:
                return None

    def _distill_loop(self) -> None:
        """daemon：每轮有界提炼若干段对话；失败退避，绝不影响扫描。

        节流策略控制发热：批量回填期（待提炼多）拉长轮间隔，让 GPU/CPU 有
        充分冷却窗口；接近完成（稳态增量）才用短间隔保证新对话及时入库。
        """
        poll = float(getattr(self.settings, "distill_poll_seconds", 20.0) or 20.0)
        batch = int(getattr(self.settings, "distill_batch_size", 2) or 2)
        bulk_poll = max(poll * 4.0, 60.0)
        backoff = Event()
        health = self._pipeline_health["distill"]
        next_batch = batch
        while not self._distill_stop.is_set():
            distiller = self._distiller
            if distiller is None or self._paused:
                if self._distill_stop.wait(timeout=5.0):
                    return
                continue
            try:
                result = distiller.run_once(limit=next_batch)
                status = str((result or {}).get("status") or "")
                pending = int((result or {}).get("pending") or 0)
                next_batch = _effective_batch(batch, pending)
                if status != "ok":
                    health.record_failure(f"run_once status={status or 'empty'}")
                else:
                    health.record_success()
                # 本地模型批量回填才需要拉长间隔控制发热；云端调用不占本机算力。
                bulk = pending > batch * 4 and getattr(distiller, "provider", "local") == "local"
                idle = bulk_poll if bulk else poll
                if status != "ok":
                    idle = max(poll * 3.0, 60.0)
                backoff.wait(timeout=idle)
            except Exception as exc:
                health.record_failure(f"{type(exc).__name__}: {exc}")
                backoff.wait(timeout=max(poll * 3.0, 60.0))

    @property
    def distill_stats(self) -> dict[str, Any]:
        distiller = self._distiller
        if distiller is None:
            return {"available": False}
        try:
            return dict(distiller.stats())
        except Exception:
            return {"available": False}

    def _build_auto_promotion(self, settings: Any) -> Any | None:
        """自动记忆晋升管线；构建便宜且不读开关（开关每轮动态判定，支持运行时切换）。"""
        try:
            from src.control.runtime_settings import RuntimeSettingsStore
            from src.memory.auto_promotion import AutoMemoryPromotionPipeline
            from src.memory.lifecycle import MemoryLifecycleService
            from src.memory.vault_layout import VaultLayout

            store = RuntimeSettingsStore(settings)
            lifecycle = MemoryLifecycleService(VaultLayout(settings.vault_path), self.state_db)
            semantic: dict[str, Any] = {"provider": None}

            def _setting_reader(name: str) -> Any:
                return store.snapshot()["values"].get(name)

            def _semantic_similarity(text: str, document: str) -> float:
                provider = semantic["provider"]
                if provider is None:
                    from src.model_center import build_embedding_provider

                    provider = build_embedding_provider(settings)
                    semantic["provider"] = provider
                if provider is None:
                    raise RuntimeError("embedding provider unavailable")
                vectors = provider.embed_many([text, document])
                if len(vectors) != 2:
                    raise RuntimeError("embedding provider returned no vectors")
                import math

                first, second = vectors[0], vectors[1]
                dot = sum(float(a) * float(b) for a, b in zip(first, second))
                norm_a = math.sqrt(sum(float(a) * float(a) for a in first))
                norm_b = math.sqrt(sum(float(b) * float(b) for b in second))
                if not norm_a or not norm_b:
                    return 0.0
                return dot / (norm_a * norm_b)

            def _post_promotion_sync() -> dict[str, Any]:
                # 晋升写 vault 后把 Core 目录对账进可重建投影；MemoryDatabase
                # 每次调用独立连接，用完即弃，无句柄残留。语义分块由既有
                # 后台向量回填接管。
                from src.retrieval.incremental_sync import IncrementalMemorySynchronizer
                from src.retrieval.memory_db import MemoryDatabase

                database = MemoryDatabase(settings.memory_db_path)
                result = dict(
                    IncrementalMemorySynchronizer(database).sync_core(
                        settings.vault_path, settings.storage_path
                    )
                )
                # 数据权威 = Vault + Git（架构 §4）：自动晋升写入权威层后必须
                # 留版本锚点，否则误写无法回滚。git 失败不阻塞晋升，但计数进
                # 管道健康，status 可见（绝不静默）。
                committed = _vault_git_autocommit(settings.vault_path)
                if committed is not None:
                    result["vault_git_committed"] = committed
                return result

            return AutoMemoryPromotionPipeline(
                settings=settings,
                lifecycle=lifecycle,
                state_db=self.state_db,
                memory_db_path=settings.memory_db_path,
                semantic_similarity=_semantic_similarity,
                setting_reader=_setting_reader,
                post_promotion_sync=_post_promotion_sync,
            )
        except Exception:
            return None

    def _promotion_loop(self) -> None:
        """daemon：开关每轮动态读取；关闭时空转等待，绝不影响扫描与提炼。"""
        poll = float(getattr(self.settings, "auto_promote_poll_seconds", 300.0) or 300.0)
        backoff = Event()
        health = self._pipeline_health["promotion"]
        while not self._promotion_stop.is_set():
            pipeline = self._promotion
            if pipeline is None or self._paused or not pipeline.enabled():
                if self._promotion_stop.wait(timeout=15.0):
                    return
                continue
            try:
                pipeline.run_once(limit=5)
                health.record_success()
            except Exception as exc:
                health.record_failure(f"{type(exc).__name__}: {exc}")
            try:
                # Vault 根部 Home 仪表盘：主人打开 Obsidian 即见记忆生长。
                # 托管文件只写 Home.md 一个，失败绝不影响晋升管线本身。
                from src.memory.home_dashboard import refresh_home_dashboard, deliver_home_dashboard

                refresh_home_dashboard(getattr(self.settings, "vault_path", ""))
                delivery = str(getattr(self.settings, "memory_home_delivery_path", "") or "").strip()
                if delivery:
                    deliver_home_dashboard(getattr(self.settings, "vault_path", ""), delivery)
            except Exception:
                pass
            backoff.wait(timeout=poll)

    def _wake_vector_backfill(self) -> None:
        """核对完成后的非阻塞唤醒：调度线程绝不等待向量化。"""
        self._backfill_wake.set()

    def _backfill_loop(self) -> None:
        """daemon：唤醒即追平向量积压（时间预算内循环），平时休眠。"""
        wake = self._backfill_wake
        stop = self._backfill_stop
        health = self._pipeline_health["vector_backfill"]
        while not stop.is_set():
            if not wake.wait(timeout=15.0):
                continue
            wake.clear()
            if stop.is_set() or self._paused:
                continue
            drain = self._backfill_drain
            if drain is None:
                continue
            try:
                drain()
                health.record_success()
            except Exception as exc:
                health.record_failure(f"{type(exc).__name__}: {exc}")

    @property
    def auto_promotion_stats(self) -> dict[str, Any]:
        pipeline = self._promotion
        if pipeline is None:
            return {"available": False}
        try:
            return dict(pipeline.stats())
        except Exception:
            return {"available": False}

    def scan_now(self, source_id: str) -> dict[str, object]:
        """手动核对：立即受理、在专用执行器中执行（2026-09-27 事故加固）。

        扫描（整库重拷+流式哈希）不再同步占用 HTTP 线程池；响应只代表
        "已受理"，真实进度经 /api/automatic-memory/scans 轮询。无效来源
        仍同步报错（快路径，不进执行器）。
        """
        def _run() -> Any:
            return self.scheduler.reconcile(source_id, reason="manual")

        future = self._scan_executor.submit(_run)
        try:
            result = future.result(timeout=self._scan_now_budget_seconds)
        except FuturesTimeoutError:
            # 慢路径（整库重拷/哈希）：限时预算内没跑完就转"已受理"，绝不让
            # HTTP 线程池等它；剩余工作在专用执行器里继续，进度走 /scans 轮询。
            return {
                "source_id": source_id,
                "status": "admitted",
                "complete": True,
                "next_action": "manual scan admitted; progress via /api/automatic-memory/scans",
            }
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
        effective_home = Path(record.root).expanduser().parent.parent if record.kind == "codex_rollout" else None
        return enumerate_authorized_files(record, effective_home=effective_home)

    def _run_scan(self, scan_id: str, source_id: str, reason: str = "scheduled") -> Any:
        work_id = f"automatic-memory:{scan_id}"
        source = next((item for item in self.registry.list_sources() if item.source_id == source_id), None)
        title = f"扫描 {source.kind if source else source_id}"
        work = self.work_store.get_work(work_id)
        if work is None:
            work = self.work_store.create_work(WorkItem(work_id=work_id, title=title, source_id=source_id, status="accepted", owner_approved=True))
            self.work_store.append_event(ExecutionEvent(work_id=work_id, event_id=f"scan:{scan_id}:started", event_type="scan.started", detail={"scan_id": scan_id, "source_id": source_id, "reason": reason}))
        try:
            if reason == "integrity" and isinstance(self.runner, SnapshotJobRunner):
                result = self.runner.run(scan_id, force_capture=True)
            else:
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
        if not isinstance(payload, dict):
            return
        job_id = str(job.get("job_id") or "")
        scan_ids = set(self.state_db.list_automatic_memory_scan_ids_for_job(job_id)) if job_id else set()
        if payload.get("scan_id"):
            scan_ids.add(str(payload["scan_id"]))
        for scan_id in sorted(scan_ids):
            work_id = f"automatic-memory:{scan_id}"
            self.work_store.append_event(ExecutionEvent(work_id=work_id, event_id=f"extraction:{job_id}:{phase}", event_type=f"extraction.{phase}", detail={"job_id": job_id, "error": error, "source_type": payload.get("source_type")}))
            self._maybe_finalize_scan_work(scan_id, job_override=job)

    def _jobs_for_scan(
        self, scan_id: str, *, job_override: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        scan = self.state_db.get_automatic_memory_scan(scan_id) or {}
        source_id = str(scan.get("source_id") or "")
        direct_jobs: list[dict[str, Any]] = []
        offset = 0
        page_size = 100
        while True:
            page = self.queue.list_page(
                source_type="automatic_memory_snapshot", scan_id=scan_id,
                limit=page_size, offset=offset,
            )
            direct_jobs.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        override_id = ""
        override_payload: dict[str, Any] = {}
        if isinstance(job_override, dict):
            override_id = str(job_override.get("job_id") or "")
            raw_override_payload = job_override.get("payload")
            if isinstance(raw_override_payload, dict):
                override_payload = raw_override_payload
            if str(override_payload.get("scan_id") or "") == scan_id:
                direct_jobs = [
                    job_override if str(item.get("job_id") or "") == override_id else item
                    for item in direct_jobs
                ]
                if override_id and not any(
                    str(item.get("job_id") or "") == override_id for item in direct_jobs
                ):
                    direct_jobs.append(job_override)
        associated_jobs: list[tuple[dict[str, Any], str]] = []
        for manifest in self.state_db.list_automatic_memory_scan_items(scan_id):
            association = association_from_status(manifest.get("status"))
            if association is None:
                continue
            if association[0] == override_id and isinstance(job_override, dict):
                item = job_override
            else:
                try:
                    item = self.queue.get(association[0])
                except LookupError:
                    continue
            payload = item.get("payload") if isinstance(item, dict) else None
            if isinstance(payload, dict) and str(payload.get("source_id") or "") == str(manifest.get("source_id") or "") and str(payload.get("relative_path") or "") == str(manifest.get("relative_path") or ""):
                associated_jobs.append((item, association[1]))
        return resolve_job_facts(
            source_id=source_id, direct_jobs=direct_jobs, associated_jobs=associated_jobs
        )

    def _maybe_finalize_scan_work(
        self,
        scan_id: str,
        report: Any | None = None,
        *,
        job_override: dict[str, Any] | None = None,
    ) -> None:
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
        jobs = self._jobs_for_scan(scan_id, job_override=job_override)
        facts = summarize_job_facts(jobs)
        if facts["pending"]:
            return
        failed_jobs = [item for item in jobs if item.get("status") in {"failed", "cancelled"}]
        completed_jobs = [item for item in jobs if item.get("status") == "completed"]
        imported_jobs = [
            item for item in completed_jobs
            if item.get("_automatic_memory_association") != "existing"
        ]
        if failed_jobs:
            # 逐文件携带可行动信息：相对路径、job_id、原始适配器错误、尝试次数，
            # 供失败聚合（work_failures 按来源+阶段+原因指纹）与主人待办使用。
            file_failures = []
            for item in failed_jobs:
                payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
                file_failures.append({
                    "relative_path": str(payload.get("relative_path") or ""),
                    "job_id": str(item.get("job_id") or ""),
                    "error": str(item.get("last_error") or ""),
                    "attempts": item.get("attempts"),
                })
            self.work_bridge.record_failure(work_id, stage="extraction", reason="一个或多个来源文件提取失败，其他来源仍可继续", retryable=False, evidence={"scan_id": scan_id, "completed_jobs": len(completed_jobs), "failed_jobs": [item.get("job_id") for item in failed_jobs], "processing_status": "partial_failure" if completed_jobs else "failed"}, file_failures=file_failures)
            self._scan_reports.pop(scan_id, None)
            return
        queued_raw = getattr(report, "queued", None) if report is not None else None
        reused_raw = getattr(report, "reused", None) if report is not None else None
        reported_queued = queued_raw if isinstance(queued_raw, int) and not isinstance(queued_raw, bool) else None
        reported_reused = reused_raw if isinstance(reused_raw, int) and not isinstance(reused_raw, bool) else None
        queued = facts["new"] if jobs else reported_queued
        reused = facts["reused"] if jobs else reported_reused
        queued_for_math = queued if queued is not None else 0
        reused_for_math = reused if reused is not None else 0
        reported_total = scan.get("total")
        if reported_total is None and report is not None:
            reported_total = getattr(report, "total", None)
        if reported_total is None and report is not None:
            reported_total = getattr(report, "discovered", None)
        if reported_total is None:
            total = queued_for_math + reused_for_math if report is not None else len(jobs)
        else:
            total = max(int(reported_total or 0), len(jobs))
        if not jobs and reused is None and queued is None and report is None:
            return
        queued_label = str(queued) if queued is not None else "尚未获得"
        reused_label = str(reused) if reused is not None else "尚未获得"
        if reused and not imported_jobs:
            summary = f"处理完成：已检查 {total} 个来源文件，未重复导入；复用 {reused_label} 个先前已导入内容"
        else:
            summary = f"处理完成：已检查 {total} 个来源文件，实际导入 {len(imported_jobs)} 个（新增 {queued_label}，复用 {reused_label}）"
        self.work_bridge.complete_extraction(work_id, summary, evidence={"scan_id": scan_id, "jobs": len(jobs), "completed_jobs": len(imported_jobs), "queued": queued, "reused": reused, "processing_status": "imported" if imported_jobs else "scan_completed", "next_actor": "system"})
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


def _vault_git_autocommit(vault_path: Any) -> bool | None:
    """Vault 未提交变更时补一个自动提交；失败只记录不抛出。

    返回 True=产生了新提交，False=无变更或 git 不可用，None=调用方环境不支持。
    绝不 push、绝不 amend、绝不碰 Vault 里灵机托管目录之外的内容语义。
    """
    import subprocess

    root = Path(str(vault_path or "")).expanduser()
    if not root.is_dir():
        return None
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root, capture_output=True, text=True, timeout=15, check=True,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root, capture_output=True, text=True, timeout=15, check=True,
        )
        if not status.stdout.strip():
            return False
        subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True, text=True, timeout=30, check=True)
        subprocess.run(
            ["git", "commit", "-m", "memory: auto-promotion snapshot [lingji]"],
            cwd=root, capture_output=True, text=True, timeout=30, check=True,
        )
        return True
    except Exception as exc:
        _logger.warning("vault git autocommit failed: %s", f"{type(exc).__name__}: {exc}"[:200])
        return False
