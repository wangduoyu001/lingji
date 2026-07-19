from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import threading
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

from .models import ExtractionRequest
from .queue import SQLiteExtractionQueue
from .registry import AdapterRegistry
from .sink import VaultExtractionSink

logger = logging.getLogger("lingji.extraction")

DocumentsWrittenCallback = Callable[[dict[str, Any]], None]
DefaultOptionsProvider = Callable[[str], Mapping[str, Any]]
DefaultPriorityProvider = Callable[[str], int]


class ExtractionPipeline:
    def __init__(
        self,
        queue: SQLiteExtractionQueue,
        registry: AdapterRegistry,
        sink: VaultExtractionSink,
        *,
        default_max_attempts: int = 3,
        lease_heartbeat_seconds: float = 30.0,
        stale_after_seconds: int = 1800,
        on_documents_written: DocumentsWrittenCallback | None = None,
        default_options_provider: DefaultOptionsProvider | None = None,
        default_priority_provider: DefaultPriorityProvider | None = None,
    ):
        self.queue = queue
        self.registry = registry
        self.sink = sink
        self.default_max_attempts = max(int(default_max_attempts), 1)
        self.lease_heartbeat_seconds = max(float(lease_heartbeat_seconds), 2.0)
        self.stale_after_seconds = max(int(stale_after_seconds), 30)
        self.on_documents_written = on_documents_written
        self.default_options_provider = default_options_provider
        self.default_priority_provider = default_priority_provider

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
        normalized_options = self._effective_options(source_type, options)
        normalized_payload = dict(payload or {})
        if input_path:
            input_path = Path(input_path).expanduser()
            if not input_path.exists():
                raise FileNotFoundError(input_path)
        adapter = self.registry.resolve(
            source_type,
            input_path,
            normalized_payload,
            preferred=adapter_name,
        )
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

    def execute(
        self,
        source_type: str,
        *,
        input_path: Path | str | None = None,
        payload: Mapping[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
        adapter_name: str | None = None,
        execution_id: str | None = None,
    ) -> dict[str, Any]:
        request = ExtractionRequest(
            job_id=execution_id or f"LJ-EXEC-{uuid4().hex[:12].upper()}",
            source_type=source_type,
            adapter_name=adapter_name,
            input_path=Path(input_path).expanduser() if input_path else None,
            payload=payload or {},
            options=self._effective_options(source_type, options),
        )
        adapter = self.registry.resolve(
            source_type,
            request.input_path,
            request.payload,
            preferred=adapter_name,
        )
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
        if self.on_documents_written:
            try:
                self.on_documents_written(response)
                response["indexed"] = True
            except Exception as exc:
                logger.exception("Post-extraction index synchronization failed")
                response["indexed"] = False
                response["index_error"] = str(exc)[:1000]
        return response

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
            )
            completed = self.queue.complete(
                job["job_id"],
                result,
                worker_id=worker_id,
                lease_token=lease_token,
            )
            return {"job": completed, "result": result}
        except Exception as exc:
            logger.exception("Extraction job failed: %s", job["job_id"])
            try:
                failed = self.queue.fail(
                    job["job_id"],
                    str(exc),
                    worker_id=worker_id,
                    lease_token=lease_token,
                )
            except RuntimeError as lease_error:
                failed = self.queue.get(job["job_id"])
                return {
                    "job": failed,
                    "error": str(exc),
                    "lease_error": str(lease_error),
                }
            return {"job": failed, "error": str(exc)}
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
        for _ in range(max(int(limit), 1)):
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
        summary["queue"] = self.queue.stats()
        return summary

    def process_job(self, job_id: str, *, worker_id: str | None = None) -> dict[str, Any]:
        current = self.queue.get(job_id)
        if current["status"] == "completed":
            return {"job": current, "result": current.get("result") or {}}
        outcome = self.process_next(worker_id=worker_id, job_id=job_id)
        if outcome is None:
            return {"job": self.queue.get(job_id), "result": {}}
        return outcome

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
        file_identity: dict[str, Any] = {}
        if input_path:
            if input_path.is_file():
                stat = input_path.stat()
                file_identity = {
                    "size": stat.st_size,
                    "sha256": self._sha256_file(input_path),
                }
            else:
                file_identity = {"manifest": self._directory_manifest(input_path)}
        material = {
            "source_type": source_type,
            "adapter_name": adapter_name or "",
            "adapter_version": adapter_version,
            "input": file_identity,
            "payload": payload or {},
            "options": options or {},
        }
        encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _directory_manifest(path: Path) -> list[dict[str, Any]]:
        result = []
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file() and not file_path.is_symlink():
                stat = file_path.stat()
                result.append(
                    {
                        "path": file_path.relative_to(path).as_posix(),
                        "size": stat.st_size,
                        "sha256": ExtractionPipeline._sha256_file(file_path),
                    }
                )
        return result

    @staticmethod
    def _worker_id() -> str:
        return f"{socket.gethostname()}:{os.getpid()}"
