from __future__ import annotations

import logging
import os
import re
import socket
import threading
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

from .errors import safe_extraction_error
from .idempotency import directory_manifest, extraction_key_for_request, sha256_file
from .models import ExtractionRequest
from .queue import (
    SQLiteExtractionQueue,
    _without_lease_material,
)
from .registry import AdapterRegistry
from .sink import VaultExtractionSink
from .structured_sink import StructuredReadModelSink
from .transient import automatic_memory_dispatch_path, reconcile_automatic_memory_transients
from src.storage import StateDatabase

logger = logging.getLogger("lingji.extraction")

DocumentsWrittenCallback = Callable[[dict[str, Any]], None]
LifecycleCallback = Callable[[str, Mapping[str, Any], Mapping[str, Any] | None, str | None], None]
DefaultOptionsProvider = Callable[[str], Mapping[str, Any]]
DefaultPriorityProvider = Callable[[str], int]
_LEASE_TOKEN_PATTERN = re.compile(r"[0-9a-f]{32}")
_LEASE_FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{64}")


def _trusted_claim_materials(lease_token: Any) -> tuple[str, ...]:
    """Return scrub material only for a validated queue-generated claim."""

    if not isinstance(lease_token, str) or _LEASE_TOKEN_PATTERN.fullmatch(lease_token) is None:
        return ()
    fingerprint = SQLiteExtractionQueue.lease_fingerprint(lease_token)
    if _LEASE_FINGERPRINT_PATTERN.fullmatch(fingerprint) is None:
        return ()
    return (lease_token, fingerprint)


def _validated_trusted_materials(materials: tuple[str, ...]) -> tuple[str, ...]:
    """Bound and validate the callback projection's trusted material input."""

    try:
        values = tuple(materials)
    except Exception:
        return ()
    if len(values) > 2:
        return ()
    if any(not isinstance(value, str) for value in values):
        return ()
    if any(
        _LEASE_TOKEN_PATTERN.fullmatch(value) is None
        and _LEASE_FINGERPRINT_PATTERN.fullmatch(value) is None
        for value in values
    ):
        return ()
    if len(values) == 2:
        token = next((value for value in values if _LEASE_TOKEN_PATTERN.fullmatch(value)), None)
        fingerprint = next((value for value in values if _LEASE_FINGERPRINT_PATTERN.fullmatch(value)), None)
        if token is None or fingerprint is None or SQLiteExtractionQueue.lease_fingerprint(token) != fingerprint:
            return ()
    return tuple(sorted(set(values), key=len, reverse=True))


class ExtractionPipeline:
    def __init__(
        self,
        queue: SQLiteExtractionQueue,
        registry: AdapterRegistry,
        sink: VaultExtractionSink,
        *,
        structured_sink: StructuredReadModelSink | None = None,
        default_max_attempts: int = 3,
        lease_heartbeat_seconds: float = 30.0,
        stale_after_seconds: int = 1800,
        on_documents_written: DocumentsWrittenCallback | None = None,
        on_lifecycle_event: LifecycleCallback | None = None,
        default_options_provider: DefaultOptionsProvider | None = None,
        default_priority_provider: DefaultPriorityProvider | None = None,
        effective_home: str | None = None,
    ):
        self.queue = queue
        self.registry = registry
        self.sink = sink
        self.structured_sink = structured_sink
        self.default_max_attempts = max(int(default_max_attempts), 1)
        self.lease_heartbeat_seconds = max(float(lease_heartbeat_seconds), 2.0)
        self.stale_after_seconds = max(int(stale_after_seconds), 30)
        self.on_documents_written = on_documents_written
        self._lifecycle_callbacks: list[LifecycleCallback] = []
        if on_lifecycle_event is not None:
            self._lifecycle_callbacks.append(on_lifecycle_event)
        self.default_options_provider = default_options_provider
        self.default_priority_provider = default_priority_provider
        self.effective_home = effective_home
        self._transient_cleanup_inventory: dict[str, Any] = self.reconcile_transient_files()

    @staticmethod
    def _scrub_lease_value(value: Any, lease_token: str) -> Any:
        token = str(lease_token or "")
        known = (token, SQLiteExtractionQueue.lease_fingerprint(token)) if token else ()
        return _without_lease_material(value, redact_values=known)

    @property
    def transient_cleanup_inventory(self) -> dict[str, Any]:
        return dict(self._transient_cleanup_inventory)

    def reconcile_transient_files(self) -> dict[str, Any]:
        """Reconcile adapter-dispatch links through the existing queue lease."""
        raw_root = getattr(self.sink, "raw_root", None)
        if raw_root is None:
            empty = {
                "scanned_count": 0,
                "removed_count": 0,
                "preserved_count": 0,
                "removed": [],
                "preserved": [],
                "errors": [],
            }
            self._transient_cleanup_inventory = empty
            return dict(empty)
        report = reconcile_automatic_memory_transients(
            raw_root,
            self.queue,
            stale_after_seconds=self.stale_after_seconds,
        )
        self._transient_cleanup_inventory = report
        return dict(report)

    def enqueue(
        self,
        source_type: str,
        *,
        input_path: Path | str | None = None,
        payload: Mapping[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
        adapter_name: str | None = None,
        idempotency_key: str | None = None,
        priority: int | None = None,
        max_attempts: int | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        if source_type == "automatic_memory_snapshot":
            raise PermissionError(
                "automatic_memory_snapshot is an internal job; use its dedicated consumer"
            )
        normalized_options = self._effective_options(source_type, options)
        normalized_payload = dict(payload or {})
        if input_path:
            input_path = Path(input_path).expanduser()
            if not input_path.exists():
                raise FileNotFoundError(input_path)
            self._validate_input_limits(input_path, normalized_options)
        try:
            adapter = self.registry.resolve(
                source_type,
                input_path,
                normalized_payload,
                preferred=adapter_name,
            )
        except Exception as exc:
            if source_type in {"codex", "codex_transcript", "codex_history"}:
                return self._record_preflight_failure(
                    source_type,
                    input_path=input_path,
                    payload=normalized_payload,
                    options=normalized_options,
                    adapter_name=adapter_name or source_type,
                    idempotency_key=idempotency_key,
                    priority=priority,
                    max_attempts=max_attempts,
                    force=force,
                    error=str(exc),
                )
            raise
        key = idempotency_key or self._idempotency_key(
            source_type,
            input_path=input_path,
            payload=normalized_payload,
            options=normalized_options,
            adapter_name=adapter.name,
            adapter_version=adapter.version,
        )
        effective_priority = int(priority) if priority is not None else self._default_priority(source_type)
        return self.queue.enqueue(
            source_type,
            input_path=input_path,
            payload=normalized_payload,
            options=normalized_options,
            adapter_name=adapter.name,
            adapter_version=adapter.version,
            idempotency_key=key,
            priority=effective_priority,
            max_attempts=max_attempts or self.default_max_attempts,
            force=force,
        )

    def _record_preflight_failure(
        self,
        source_type: str,
        *,
        input_path: Path | None,
        payload: Mapping[str, Any],
        options: Mapping[str, Any],
        adapter_name: str,
        idempotency_key: str | None,
        priority: int | None,
        max_attempts: int | None,
        force: bool,
        error: str,
    ) -> dict[str, Any]:
        """Persist schema preflight failures through the existing queue facts."""

        job = self.queue.enqueue(
            source_type,
            input_path=input_path,
            payload=payload,
            options=options,
            adapter_name=adapter_name,
            idempotency_key=idempotency_key,
            priority=int(priority) if priority is not None else self._default_priority(source_type),
            max_attempts=1 if max_attempts is None else max(min(int(max_attempts), 1), 1),
            force=force,
        )
        if job.get("status") in {"failed", "completed", "cancelled"}:
            return job
        worker_id = f"preflight:{self._worker_id()}"
        claimed = self.queue.claim(worker_id, job_id=job["job_id"])
        if claimed is None:
            return self.queue.get(job["job_id"])
        return self.queue.fail(
            job["job_id"],
            error,
            worker_id=worker_id,
            lease_token=str(claimed.get("lease_token") or ""),
            retry_delay_seconds=0,
        )

    def replay_automatic_snapshots(
        self,
        source_type: str,
        snapshot_paths: list[Path | str] | tuple[Path | str, ...],
        *,
        source_id: str,
        execution_id_prefix: str = "automatic-replay",
    ) -> list[dict[str, Any]]:
        """Replay ordered raw snapshots through the formal extraction path.

        The structured read model is intentionally not treated as a history
        authority: each snapshot is executed in order so the existing lexical
        projection can retain content-hash versions and their supersession
        links.  This is a synchronous rebuild seam for isolated maintenance
        and acceptance callers; it creates no queue or database.
        """
        if not str(source_id or "").strip():
            raise ValueError("source_id is required for automatic snapshot replay")
        if not snapshot_paths:
            return []
        return [
            self.execute(
                source_type,
                input_path=Path(path),
                payload={"source_id": str(source_id)},
                options={"automatic_memory": True},
                execution_id=f"{execution_id_prefix}-{index}",
            )
            for index, path in enumerate(snapshot_paths, 1)
        ]

    def execute(
        self,
        source_type: str,
        *,
        input_path: Path | str | None = None,
        payload: Mapping[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
        adapter_name: str | None = None,
        execution_id: str | None = None,
        notify_lifecycle: bool = True,
    ) -> dict[str, Any]:
        if source_type == "automatic_memory_snapshot":
            raise PermissionError(
                "automatic_memory_snapshot is an internal job; use its dedicated consumer"
            )
        request = ExtractionRequest(
            job_id=execution_id or f"LJ-EXEC-{uuid4().hex[:12].upper()}",
            source_type=source_type,
            adapter_name=adapter_name,
            input_path=Path(input_path).expanduser() if input_path else None,
            payload=payload or {},
            options=self._effective_options(source_type, options),
        )
        if request.input_path:
            self._validate_input_limits(request.input_path, request.options)
        adapter = self.registry.resolve(
            source_type,
            request.input_path,
            request.payload,
            preferred=adapter_name,
        )
        def downstream_commit() -> dict[str, Any]:
            raw_snapshot = self.sink.preserve_raw(request.input_path, source_type)
            batch = adapter.extract(request)
            result = self.sink.write_batch(
                batch,
                adapter_name=adapter.name,
                adapter_version=adapter.version,
                raw_snapshot=raw_snapshot,
            )
            response = {
                "execution_id": request.job_id,
                "source_type": source_type,
                "adapter": adapter.name,
                "adapter_version": adapter.version,
                **result,
            }
            indexing_succeeded = self.on_documents_written is None
            if self.on_documents_written:
                try:
                    self.on_documents_written(response)
                    response["indexed"] = True
                    indexing_succeeded = True
                except Exception as exc:
                    logger.exception("Post-extraction index synchronization failed")
                    response["indexed"] = False
                    response["index_error"] = safe_extraction_error(
                        exc,
                        message="Post-extraction index synchronization failed; see local logs",
                    )
                    indexing_succeeded = False
            response["structured_read_model"] = self._write_structured(
                batch=batch,
                raw_snapshot=raw_snapshot,
                vault_results=result,
                execution_id=request.job_id,
                adapter_name=adapter.name,
                adapter_version=adapter.version,
                indexing_succeeded=indexing_succeeded,
            )
            return response

        result = downstream_commit()
        if notify_lifecycle:
            self._notify_lifecycle(
                "completed",
                {"job_id": request.job_id, "payload": dict(request.payload), "status": "completed"},
                result,
                None,
            )
        return result

    def add_lifecycle_callback(self, callback: LifecycleCallback) -> None:
        if callback not in self._lifecycle_callbacks:
            self._lifecycle_callbacks.append(callback)

    def _notify_lifecycle(
        self,
        phase: str,
        job: Mapping[str, Any],
        result: Mapping[str, Any] | None,
        error: str | None,
        *,
        trusted_known_materials: tuple[str, ...] = (),
    ) -> None:
        # Keep the claimed worker object private.  Every callback receives a
        # fresh bounded projection.  Explicit lease-key values in payloads are
        # untrusted and are removed, never promoted to global replacements.
        try:
            known_material = _validated_trusted_materials(trusted_known_materials)
            safe_job = _without_lease_material(
                job, redact_values=known_material, fail_closed_unknown=True
            )
            safe_result = _without_lease_material(
                result, redact_values=known_material, fail_closed_unknown=True
            )
            safe_error = _without_lease_material(
                error, redact_values=known_material, fail_closed_unknown=True
            )
        except Exception:
            # A malformed callback payload must never roll back an already
            # committed terminal queue state or leak an exception repr.  Send
            # only a minimal, stable event envelope instead.
            safe_job = {}
            if isinstance(job, Mapping):
                try:
                    for key in ("job_id", "status", "source_type"):
                        value = job.get(key)
                        if isinstance(value, (str, int, float, bool)):
                            safe_job[key] = value
                except Exception:
                    safe_job = {}
            safe_result = None
            safe_error = "Lifecycle event payload redacted"
        for callback in tuple(self._lifecycle_callbacks):
            try:
                callback(phase, safe_job, safe_result, safe_error)
            except Exception:
                logger.error("Extraction lifecycle callback failed")

    def _write_structured(
        self,
        *,
        batch,
        raw_snapshot: Mapping[str, Any],
        vault_results: Mapping[str, Any],
        execution_id: str,
        adapter_name: str,
        adapter_version: str,
        indexing_succeeded: bool,
    ) -> dict[str, Any]:
        if self.structured_sink is None or not batch.structured_sources:
            return {
                "state": "not_applicable",
                "sources": 0,
                "conversations": 0,
                "messages": 0,
                "links": 0,
                "warnings": [],
            }
        return self.structured_sink.write_batch(
            batch,
            raw_snapshot=raw_snapshot,
            vault_results=vault_results,
            execution_id=execution_id,
            adapter_name=adapter_name,
            adapter_version=adapter_version,
            indexing_succeeded=indexing_succeeded,
        )

    def process_next(
        self,
        *,
        worker_id: str | None = None,
        job_id: str | None = None,
    ) -> dict[str, Any] | None:
        worker_id = worker_id or self._worker_id()
        job = self.queue.claim(worker_id, job_id=job_id)
        if not job:
            return None
        lease_token = str(job.get("lease_token") or "")
        stop_heartbeat = threading.Event()
        heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(stop_heartbeat, job["job_id"], worker_id, lease_token),
            name=f"lingji-extraction-heartbeat-{job['job_id']}",
            daemon=True,
        )
        heartbeat_thread.start()
        try:
            result = self.execute(
                job["source_type"],
                input_path=job.get("input_path"),
                payload=job.get("payload") or {},
                options=job.get("options") or {},
                adapter_name=job.get("adapter_name"),
                execution_id=job["job_id"],
                notify_lifecycle=False,
            )
            completed = self.queue.complete(
                job["job_id"],
                result,
                worker_id=worker_id,
                lease_token=lease_token,
            )
            safe_result = self._scrub_lease_value(result, lease_token)
            self._notify_lifecycle(
                "completed",
                {**job, "status": "completed"},
                safe_result,
                None,
                trusted_known_materials=_trusted_claim_materials(lease_token),
            )
            return {"job": completed, "result": safe_result}
        except Exception as exc:
            safe_error = self._scrub_lease_value(str(exc), lease_token)
            logger.error("Extraction job failed: %s: %s", job["job_id"], safe_error)
            try:
                failed = self.queue.fail(
                    job["job_id"],
                    safe_error,
                    worker_id=worker_id,
                    lease_token=lease_token,
                )
            except RuntimeError as lease_error:
                failed = self.queue.get(job["job_id"])
                return {
                    "job": failed,
                    "error": safe_error,
                    "lease_error": self._scrub_lease_value(str(lease_error), lease_token),
                }
            self._notify_lifecycle(
                "failed",
                {**job, **failed},
                None,
                safe_error,
                trusted_known_materials=_trusted_claim_materials(lease_token),
            )
            return {"job": failed, "error": safe_error}
        finally:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=max(self.lease_heartbeat_seconds, 2.0))

    def _heartbeat_loop(
        self,
        stop_event: threading.Event,
        job_id: str,
        worker_id: str,
        lease_token: str,
    ) -> None:
        while not stop_event.wait(self.lease_heartbeat_seconds):
            if not self.queue.heartbeat(
                job_id,
                worker_id,
                lease_token,
                progress_message="processing",
            ):
                logger.warning("Extraction lease heartbeat rejected: %s", job_id)
                return

    def process_pending(
        self,
        *,
        limit: int = 10,
        worker_id: str | None = None,
    ) -> dict[str, Any]:
        worker_id = worker_id or self._worker_id()
        self.queue.release_stale(self.stale_after_seconds)
        summary = {
            "processed": 0,
            "completed": 0,
            "retrying": 0,
            "failed": 0,
            "jobs": [],
        }
        self.reconcile_transient_files()
        for _ in range(max(int(limit), 1)):
            outcome = self.process_internal_next(worker_id=worker_id)
            if outcome is None:
                outcome = self.process_next(worker_id=worker_id)
            if outcome is None:
                break
            summary["processed"] += 1
            status = outcome["job"]["status"]
            if status in summary:
                summary[status] += 1
            summary["jobs"].append(
                {
                    "job_id": outcome["job"]["job_id"],
                    "status": status,
                    "error": outcome.get("error", ""),
                }
            )
        self.reconcile_transient_files()
        summary["queue"] = self.queue.stats()
        summary["transient_cleanup"] = self.transient_cleanup_inventory
        return summary

    def process_internal_next(self, *, worker_id: str | None = None) -> dict[str, Any] | None:
        """Consume one content-addressed automatic-memory snapshot."""
        worker_id = worker_id or self._worker_id()
        job = self.queue.claim(worker_id, allowed_source_types={"automatic_memory_snapshot"})
        if not job:
            return None
        lease_token = str(job.get("lease_token") or "")
        try:
            result = self._execute_internal_snapshot(job)
            completed = self.queue.complete(job["job_id"], result, worker_id=worker_id, lease_token=lease_token)
            safe_result = self._scrub_lease_value(result, lease_token)
            self._notify_lifecycle(
                "completed",
                {**job, "status": "completed"},
                safe_result,
                None,
                trusted_known_materials=_trusted_claim_materials(lease_token),
            )
            return {"job": completed, "result": safe_result}
        except PermissionError as exc:
            safe_error = self._scrub_lease_value(str(exc), lease_token)
            failed = self.queue.fail(
                job["job_id"],
                safe_error,
                worker_id=worker_id,
                lease_token=lease_token,
                terminal=True,
            )
            self._notify_lifecycle(
                "failed",
                {**job, **failed},
                None,
                safe_error,
                trusted_known_materials=_trusted_claim_materials(lease_token),
            )
            return {"job": failed, "error": safe_error}
        except Exception as exc:
            safe_error = self._scrub_lease_value(str(exc), lease_token)
            logger.error("Automatic-memory snapshot job failed: %s: %s", job["job_id"], safe_error)
            failed = self.queue.fail(job["job_id"], safe_error, worker_id=worker_id, lease_token=lease_token, terminal=True)
            self._notify_lifecycle(
                "failed",
                {**job, **failed},
                None,
                safe_error,
                trusted_known_materials=_trusted_claim_materials(lease_token),
            )
            return {"job": failed, "error": safe_error}

    def _execute_internal_snapshot(self, job: Mapping[str, Any]) -> dict[str, Any]:
        payload = job.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("malformed automatic-memory snapshot payload")
        source_id = str(payload.get("source_id") or "").strip()
        if source_id:
            state_db = StateDatabase(self.queue.path)
            if not state_db.is_automatic_memory_source_authorized(source_id):
                raise PermissionError("automatic-memory source authorization is no longer active")
        source_type = str(payload.get("source_type") or "").strip()
        raw_id = str(payload.get("raw_id") or "").strip()
        expected_sha = str(payload.get("sha256") or "").strip().lower()
        if not source_id or source_type in {"", "automatic_memory_snapshot"} or not raw_id or len(expected_sha) != 64 or any(char not in "0123456789abcdef" for char in expected_sha):
            raise ValueError("malformed automatic-memory snapshot metadata")
        state_db = StateDatabase(self.queue.path)
        source = state_db.get_automatic_memory_source(source_id)
        if source is None or str(source.get("kind") or "") != source_type:
            raise ValueError("automatic-memory snapshot source type does not match authorization")
        raw_path = Path(str(job.get("input_path") or "")).expanduser()
        if not raw_path.is_file() or raw_path.is_symlink():
            raise FileNotFoundError("automatic-memory raw snapshot is unavailable")
        if raw_path.name != raw_id:
            raise ValueError("automatic-memory raw snapshot identity mismatch")
        actual_sha = sha256_file(raw_path)
        if actual_sha != expected_sha:
            raise ValueError("automatic-memory raw snapshot hash mismatch")
        relative_path = str(payload.get("relative_path") or "")
        if not relative_path or Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
            raise ValueError("malformed automatic-memory relative path")
        request_path = raw_path
        temporary_path: Path | None = None
        original_suffix = Path(relative_path).suffix.lower()
        if original_suffix and raw_path.suffix.lower() != original_suffix and source_type != "codex_rollout":
            temporary_path = automatic_memory_dispatch_path(
                self.sink.raw_root,
                str(job.get("job_id") or ""),
                str(job.get("lease_token") or ""),
                original_suffix,
            )
            try:
                os.link(raw_path, temporary_path)
            except OSError as exc:
                raise ValueError(f"unable to stage raw snapshot for adapter dispatch: {exc}") from exc
            request_path = temporary_path
        request = ExtractionRequest(job_id=str(job["job_id"]), source_type=source_type, input_path=request_path,
                                    payload={"source_id": source_id, "relative_path": relative_path,
                                             "raw_id": raw_id, "sha256": expected_sha,
                                             "raw_path": str(raw_path),
                                             "raw_root": str(self.sink.raw_root),
                                             "source_path": str(Path(str(source.get("root") or "")) / relative_path),
                                             "authorized_root": str(source.get("root") or ""),
                                             "effective_home": self.effective_home},
                                    options={"automatic_memory": True})
        try:
            adapter = self.registry.resolve(source_type, request_path, request.payload)
            batch = adapter.extract(request)
            raw_snapshot = {"raw_path": str(raw_path), "sha256": actual_sha, "size": raw_path.stat().st_size, "kind": source_type}
            vault_result = {
                "documents": 0,
                "created": [],
                "updated": [],
                "skipped": [],
                "paths": [],
                "warnings": ["automatic-memory snapshot is retained as raw and structured evidence; Vault document publishing is disabled"],
                "raw_snapshot": raw_snapshot,
            }
            result: dict[str, Any] = {"execution_id": request.job_id, "source_type": source_type, "adapter": adapter.name, "adapter_version": adapter.version, "indexed": False, "index_error": "Vault/index document publishing unavailable for automatic-memory snapshots", **vault_result}
            indexing_succeeded = False
            result["structured_read_model"] = self._write_structured(batch=batch, raw_snapshot=raw_snapshot, vault_results=vault_result,
                                                                      execution_id=request.job_id, adapter_name=adapter.name,
                                                                      adapter_version=adapter.version, indexing_succeeded=indexing_succeeded)
            return result
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def process_job(self, job_id: str, *, worker_id: str | None = None) -> dict[str, Any]:
        current = self.queue.get(job_id)
        if current["status"] == "completed":
            return {"job": current, "result": current.get("result") or {}}
        if current.get("source_type") == "automatic_memory_snapshot":
            claimed = self.queue.claim(worker_id or self._worker_id(), job_id=job_id,
                                       allowed_source_types={"automatic_memory_snapshot"})
            if claimed is None:
                return {"job": self.queue.get(job_id), "result": {}}
            lease_token = str(claimed.get("lease_token") or "")
            try:
                result = self._execute_internal_snapshot(claimed)
                completed = self.queue.complete(job_id, result, worker_id=worker_id or self._worker_id(), lease_token=lease_token)
                safe_result = self._scrub_lease_value(result, lease_token)
                self._notify_lifecycle(
                    "completed",
                    {**claimed, "status": "completed"},
                    safe_result,
                    None,
                    trusted_known_materials=_trusted_claim_materials(lease_token),
                )
                return {"job": completed, "result": safe_result}
            except PermissionError as exc:
                safe_error = self._scrub_lease_value(str(exc), lease_token)
                failed = self.queue.fail(job_id, safe_error, worker_id=worker_id or self._worker_id(), lease_token=lease_token, terminal=True)
                self._notify_lifecycle(
                    "failed",
                    {**claimed, **failed},
                    None,
                    safe_error,
                    trusted_known_materials=_trusted_claim_materials(lease_token),
                )
                return {"job": failed, "error": safe_error}
            except Exception as exc:
                safe_error = self._scrub_lease_value(str(exc), lease_token)
                logger.error("Automatic-memory snapshot job failed: %s: %s", job_id, safe_error)
                failed = self.queue.fail(job_id, safe_error, worker_id=worker_id or self._worker_id(), lease_token=lease_token, terminal=True)
                self._notify_lifecycle(
                    "failed",
                    {**claimed, **failed},
                    None,
                    safe_error,
                    trusted_known_materials=_trusted_claim_materials(lease_token),
                )
                return {"job": failed, "error": safe_error}
        outcome = self.process_next(worker_id=worker_id, job_id=job_id)
        if outcome is None:
            return {"job": self.queue.get(job_id), "result": {}}
        return outcome

    @staticmethod
    def _validate_input_limits(input_path: Path, options: Mapping[str, Any]) -> None:
        if not input_path.is_file():
            return
        maximum = max(int(options.get("max_input_bytes") or 0), 0)
        size = input_path.stat().st_size
        if maximum and size > maximum:
            raise ValueError(
                f"输入文件大小 {size} bytes 超过当前限制 {maximum} bytes；可在本地 UI 调整"
            )

    def _effective_options(
        self,
        source_type: str,
        options: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        defaults: dict[str, Any] = {}
        if self.default_options_provider:
            provided = self.default_options_provider(source_type)
            if provided:
                defaults.update(dict(provided))
        defaults.update(dict(options or {}))
        return defaults

    def _default_priority(self, source_type: str) -> int:
        if self.default_priority_provider:
            return int(self.default_priority_provider(source_type))
        return 100

    def _idempotency_key(
        self,
        source_type: str,
        *,
        input_path: Path | None,
        payload: Mapping[str, Any] | None,
        options: Mapping[str, Any] | None,
        adapter_name: str | None,
        adapter_version: str = "",
    ) -> str:
        """Compatibility entry point delegated to the canonical identity module."""

        return extraction_key_for_request(
            source_type=source_type,
            adapter_name=adapter_name or "",
            adapter_version=adapter_version,
            input_path=input_path,
            payload=payload,
            effective_options=options,
        )

    @staticmethod
    def _sha256_file(path: Path) -> str:
        """Compatibility wrapper; new callers should import idempotency.sha256_file."""

        return sha256_file(path)

    @staticmethod
    def _directory_manifest(path: Path) -> list[dict[str, Any]]:
        """Compatibility wrapper; new callers should import idempotency.directory_manifest."""

        return directory_manifest(path)

    @staticmethod
    def _worker_id() -> str:
        return f"{socket.gethostname()}:{os.getpid()}"
