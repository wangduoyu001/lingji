from __future__ import annotations

import inspect
import json
import math
import os
import threading
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4

from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase
from src.storage.state_db import LeaseLostError

from .models import ScanRun
from .snapshot import ConsistentSnapshot


@dataclass(frozen=True)
class ResumeToken:
    scan_id: str
    cursor: str
    source_sentinel: str
    lease_id: str
    attempt: int


class CheckpointStore:
    """Persist scan recovery in the existing StateDatabase scan row."""

    def __init__(self, state_db: StateDatabase | Path | str, *, lease_ttl_seconds: float = 30.0):
        self.state_db = (
            state_db if isinstance(state_db, StateDatabase) else StateDatabase(state_db)
        )
        self.lease_ttl_seconds = max(float(lease_ttl_seconds), 0.1)

    def save(self, token: ResumeToken) -> None:
        payload = json.dumps(
            {
                "scan_id": token.scan_id,
                "cursor": token.cursor,
                "source_sentinel": token.source_sentinel,
                "lease_id": token.lease_id,
                "attempt": int(token.attempt),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        self.state_db.update_automatic_memory_scan_owned(
            token.scan_id,
            token.lease_id,
            lease_ttl_seconds=self.lease_ttl_seconds,
            cursor=token.cursor or None,
            source_sentinel=token.source_sentinel,
            attempt=int(token.attempt),
            recovery_token=payload,
        )
        if token.cursor and token.source_sentinel:
            scan = self.state_db.get_automatic_memory_scan(token.scan_id)
            if scan is not None:
                self.state_db.upsert_automatic_memory_scan_item_owned(
                    token.scan_id,
                    token.lease_id,
                    source_id=scan["source_id"],
                    relative_path=token.cursor,
                    sentinel=token.source_sentinel,
                )

    def load(self, scan_id: str) -> ResumeToken | None:
        row = self.state_db.get_automatic_memory_scan(scan_id)
        if row is None:
            return None
        payload = row.get("recovery_token")
        if payload:
            try:
                decoded = json.loads(payload)
                if isinstance(decoded, dict) and decoded.get("scan_id") == scan_id:
                    return ResumeToken(
                        scan_id=scan_id,
                        cursor=str(decoded.get("cursor") or ""),
                        source_sentinel=str(decoded.get("source_sentinel") or ""),
                        lease_id=str(decoded.get("lease_id") or ""),
                        attempt=int(decoded.get("attempt") or 0),
                    )
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        if not row.get("cursor") and not row.get("source_sentinel") and not row.get("lease_id"):
            return None
        return ResumeToken(
            scan_id=scan_id,
            cursor=str(row.get("cursor") or ""),
            source_sentinel=str(row.get("source_sentinel") or ""),
            lease_id=str(row.get("lease_id") or ""),
            attempt=int(row.get("attempt") or 0),
        )


PathProvider = Callable[[Any, Any], Any]


class SnapshotJobRunner:
    """Admit authorized snapshots to the existing extraction queue."""

    def __init__(
        self,
        snapshot: ConsistentSnapshot | None = None,
        queue: SQLiteExtractionQueue | None = None,
        state_db: StateDatabase | Path | str | None = None,
        *,
        path_provider: PathProvider,
        checkpoint_store: CheckpointStore | None = None,
        snapshotter: ConsistentSnapshot | None = None,
        before_checkpoint: Callable[[int, int], None] | None = None,
        before_queue: Callable[[], None] | None = None,
        after_lease: Callable[[], None] | None = None,
        lease_ttl_seconds: float = 30.0,
    ):
        if snapshot is None:
            snapshot = snapshotter
        if snapshot is None or queue is None or state_db is None:
            raise TypeError("snapshot, queue and state_db are required")
        self.snapshot = snapshot
        self.queue = queue
        self.state_db = state_db if isinstance(state_db, StateDatabase) else StateDatabase(state_db)
        self.path_provider = path_provider
        self.lease_ttl_seconds = max(float(lease_ttl_seconds), 0.1)
        self.checkpoints = checkpoint_store or CheckpointStore(
            self.state_db, lease_ttl_seconds=self.lease_ttl_seconds
        )
        self.before_checkpoint = before_checkpoint
        self.before_queue = before_queue
        self.after_lease = after_lease
        self._heartbeat_stop: threading.Event | None = None
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_error: BaseException | None = None

    def _validate_single_database(self) -> None:
        state_path = Path(self.state_db.path).expanduser()
        queue_path = Path(self.queue.path).expanduser()
        try:
            same = os.path.samefile(state_path, queue_path)
        except (FileNotFoundError, OSError):
            same = state_path.resolve(strict=False) == queue_path.resolve(strict=False)
        if not same:
            raise ValueError(
                "SnapshotJobRunner requires state database and extraction queue to use the same SQLite file"
            )

    def _start_heartbeat(self, scan_id: str, lease_id: str) -> None:
        stop = threading.Event()
        self._heartbeat_stop = stop
        self._heartbeat_error = None

        def renew() -> None:
            interval = max(min(self.lease_ttl_seconds / 3.0, 1.0), 0.05)
            while not stop.wait(interval):
                try:
                    self.state_db.renew_automatic_memory_scan_lease(
                        scan_id,
                        lease_id,
                        ttl_seconds=self.lease_ttl_seconds,
                    )
                except LeaseLostError:
                    return
                except Exception as exc:
                    self._heartbeat_error = exc
                    return

        self._heartbeat_thread = threading.Thread(
            target=renew,
            name=f"lingji-automatic-memory-heartbeat-{scan_id}",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat(self) -> None:
        stop, thread = self._heartbeat_stop, self._heartbeat_thread
        self._heartbeat_stop = None
        self._heartbeat_thread = None
        if stop is not None:
            stop.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(self.lease_ttl_seconds, 0.2))

    def _assert_heartbeat(self) -> None:
        if self._heartbeat_error is not None:
            raise LeaseLostError(f"automatic-memory lease heartbeat failed: {self._heartbeat_error}")

    def _handle_lease_loss(self, scan_id: str, lease_id: str) -> ScanRun:
        heartbeat_error = self._heartbeat_error
        self._stop_heartbeat()
        if heartbeat_error is not None:
            try:
                self.state_db.update_automatic_memory_scan_owned(
                    scan_id,
                    lease_id,
                    lease_ttl_seconds=self.lease_ttl_seconds,
                    status="failed",
                    last_error=f"lease heartbeat failed: {heartbeat_error}"[:2000],
                    updated_at=self._updated_at(),
                )
            except LeaseLostError:
                pass
        try:
            self._release(scan_id, lease_id)
        except LeaseLostError:
            pass
        return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

    def run(
        self,
        scan_id: str,
        crash_at: Literal["none", "30%", "70%", "after-lease"] = "none",
    ) -> ScanRun:
        if crash_at not in {"none", "30%", "70%", "after-lease"}:
            raise ValueError(f"unsupported crash_at: {crash_at}")
        self._validate_single_database()
        row = self.state_db.get_automatic_memory_scan(scan_id)
        if row is None:
            raise LookupError(f"scan not found: {scan_id}")
        if row["status"] == "cancelled":
            return self._scan(row)
        if row["status"] == "completed" and crash_at == "none":
            return self._scan(row)
        source_id = str(row["source_id"])
        source = self.state_db.get_automatic_memory_source(
            source_id, now=self._updated_at()
        )
        if source is None:
            raise PermissionError("source is not authorized for scanning")
        if source.get("status") != "authorized":
            current = self.state_db.get_automatic_memory_scan(scan_id)
            if current and current["status"] == "cancelled":
                return self._scan(current)
            self.state_db.update_automatic_memory_scan(
                scan_id,
                status="failed",
                last_error="source authorization is not active",
                updated_at=self._updated_at(),
            )
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

        paths = self._paths(row, source)
        total = len(paths)
        token = self.checkpoints.load(scan_id)
        cursor = token.cursor if token else ""
        sentinels = {
            item["relative_path"]: item["sentinel"]
            for item in self.state_db.list_automatic_memory_scan_items(scan_id)
        }
        pending: list[Path] = []
        completed_before = 0
        for path in paths:
            relative = self._relative(source, path)
            try:
                current_sentinel = self._path_sentinel(path)
            except OSError:
                current_sentinel = ""
            if current_sentinel and sentinels.get(relative) == current_sentinel:
                completed_before += 1
            else:
                pending.append(path)
        paths = pending
        queued_count = 0
        reused_count = 0
        source_sentinel = sentinels.get(cursor, "")
        lease_id = uuid4().hex
        attempt = int(row.get("attempt") or 0) + 1
        acquired = self.state_db.acquire_automatic_memory_scan_lease(
            scan_id, lease_id, ttl_seconds=self.lease_ttl_seconds
        )
        if acquired is None:
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
        attempt = int(acquired.get("attempt") or attempt)
        self.state_db.update_automatic_memory_scan_owned(
            scan_id,
            lease_id,
            lease_ttl_seconds=self.lease_ttl_seconds,
            total=total,
            last_error=None,
            updated_at=self._updated_at(),
        )
        self._start_heartbeat(scan_id, lease_id)
        try:
            initial = ResumeToken(scan_id, cursor, source_sentinel, lease_id, attempt)
            self.checkpoints.save(initial)
            if self.after_lease is not None:
                self.after_lease()
            if crash_at == "after-lease":
                return self._pause(scan_id, initial)
        except LeaseLostError:
            return self._handle_lease_loss(scan_id, lease_id)
        except Exception as exc:
            self._stop_heartbeat()
            try:
                self.state_db.update_automatic_memory_scan_owned(
                    scan_id,
                    lease_id,
                    lease_ttl_seconds=self.lease_ttl_seconds,
                    status="failed",
                    last_error=str(exc)[:2000],
                    updated_at=self._updated_at(),
                )
                self._release(scan_id, lease_id)
            except LeaseLostError:
                pass
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

        crash_index = (
            math.ceil(total * 0.3)
            if crash_at == "30%"
            else math.ceil(total * 0.7)
            if crash_at == "70%"
            else None
        )
        processed = completed_before
        try:
            for path in paths:
                self._assert_heartbeat()
                result = self.snapshot.capture(
                    source_id,
                    path,
                    scan_id=scan_id,
                    lease_id=lease_id,
                    lease_guard=self._assert_heartbeat,
                )
                if not result.stable:
                    raise RuntimeError(
                        f"source changed during snapshot: {result.relative_path}"
                    )
                raw_path = self.snapshot.raw_root / result.raw_id
                if self.before_queue is not None:
                    self.before_queue()
                try:
                    admission = self.queue.enqueue_authorized_snapshot(
                        scan_id=scan_id,
                        lease_id=lease_id,
                        source_id=source_id,
                        relative_path=result.relative_path,
                        raw_id=result.raw_id,
                        sha256=result.sha256,
                        input_path=raw_path,
                        source_type=str(source.get("kind") or ""),
                    )
                    if admission.get("existing_job"):
                        reused_count += 1
                    else:
                        queued_count += 1
                except Exception as exc:
                    raise RuntimeError(
                        "raw committed before queue admission; orphan raw evidence "
                        f"raw_id={result.raw_id} relative_path={result.relative_path}: {exc}"
                    ) from exc
                processed += 1
                if self.before_checkpoint is not None:
                    self.before_checkpoint(processed, total)
                sentinel = self._sentinel(result)
                sentinels[result.relative_path] = sentinel
                source_sentinel = sentinel
                checkpoint = ResumeToken(
                    scan_id, result.relative_path, source_sentinel, lease_id, attempt
                )
                self.checkpoints.save(checkpoint)
                cursor = result.relative_path
                source_sentinel = sentinel
                self.state_db.update_automatic_memory_scan_owned(
                    scan_id,
                    lease_id,
                    lease_ttl_seconds=self.lease_ttl_seconds,
                    progress=processed,
                    total=total,
                    updated_at=self._updated_at(),
                )
                self._assert_heartbeat()
                if crash_index is not None and processed >= crash_index:
                    return self._pause(scan_id, checkpoint)
        except LeaseLostError:
            return self._handle_lease_loss(scan_id, lease_id)
        except Exception as exc:
            checkpoint = ResumeToken(scan_id, cursor, source_sentinel, lease_id, attempt)
            try:
                self._stop_heartbeat()
                self.checkpoints.save(checkpoint)
                existing_error = (self.state_db.get_automatic_memory_scan(scan_id) or {}).get(
                    "last_error"
                )
                error_text = (
                    str(existing_error)
                    if isinstance(existing_error, str) and existing_error.startswith("raw conflict")
                    else str(exc)[:2000]
                )
                self.state_db.update_automatic_memory_scan_owned(
                    scan_id,
                    lease_id,
                    lease_ttl_seconds=self.lease_ttl_seconds,
                    status="failed",
                    total=total,
                    progress=processed,
                    last_error=error_text,
                    updated_at=self._updated_at(),
                )
                self._release(scan_id, lease_id)
            except LeaseLostError:
                return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
        try:
            self._stop_heartbeat()
            finalized = self.state_db.finalize_automatic_memory_scan_lease(
                scan_id,
                lease_id,
                cursor=cursor if not paths else self._relative(source, paths[-1]),
                progress=total,
                total=total,
                last_error=None,
                updated_at=self._updated_at(),
            )
        except LeaseLostError:
            self._stop_heartbeat()
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
        return replace(self._scan(finalized), queued=queued_count, reused=reused_count)

    def _pause(self, scan_id: str, token: ResumeToken) -> ScanRun:
        self._stop_heartbeat()
        self.state_db.update_automatic_memory_scan_owned(
            scan_id,
            token.lease_id,
            lease_ttl_seconds=self.lease_ttl_seconds,
            status="paused",
            cursor=token.cursor or None,
            recovery_token=json.dumps(token.__dict__, sort_keys=True),
            updated_at=self._updated_at(),
        )
        self._release(scan_id, token.lease_id)
        return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

    def _release(self, scan_id: str, lease_id: str) -> None:
        self._stop_heartbeat()
        self.state_db.release_automatic_memory_scan_lease(
            scan_id, lease_id, now=self._updated_at()
        )

    def _paths(self, scan: dict[str, Any], source: dict[str, Any]) -> list[Path]:
        provider = self.path_provider
        try:
            signature = inspect.signature(provider)
            values = provider(scan, source) if len(signature.parameters) >= 2 else provider(scan)
        except (TypeError, ValueError):
            values = provider(scan, source)
        paths = [Path(value).expanduser() for value in (values or [])]
        return sorted(paths, key=lambda path: self._relative(source, path))

    @staticmethod
    def _relative(source: dict[str, Any], path: Path) -> str:
        return Path(path).expanduser().absolute().relative_to(
            Path(source["root"]).expanduser().absolute()
        ).as_posix()

    @staticmethod
    def _sentinel(result: Any) -> str:
        stat = result.stat_after
        return f"{stat.size}:{stat.mtime_ns}:{int(stat.inode or 0)}"

    @staticmethod
    def _path_sentinel(path: Path) -> str:
        stat = path.lstat()
        if not path.is_file() or path.is_symlink():
            return ""
        return f"{stat.st_size}:{stat.st_mtime_ns}:{int(getattr(stat, 'st_ino', 0) or 0)}"


    @staticmethod
    def _updated_at() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @staticmethod
    def _scan(row: dict[str, Any]) -> ScanRun:
        return ScanRun(
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
        )


__all__ = ["CheckpointStore", "ResumeToken", "SnapshotJobRunner"]
