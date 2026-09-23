from __future__ import annotations

import inspect
import json
import math
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4

from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase
from src.storage.state_db import LeaseLostError

from .models import ScanRun
from .snapshot import ConsistentSnapshot, SnapshotResult


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

    def save(self, token: ResumeToken, *, manifest_status: str = "processed") -> None:
        self._save(token, manifest_status=manifest_status)

    def save_token_only(self, token: ResumeToken) -> None:
        self._save(token, manifest_status=None)

    def _save(self, token: ResumeToken, *, manifest_status: str | None) -> None:
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
        if token.cursor and token.source_sentinel and manifest_status is not None:
            scan = self.state_db.get_automatic_memory_scan(token.scan_id)
            if scan is not None:
                self.state_db.upsert_automatic_memory_scan_item_owned(
                    token.scan_id,
                    token.lease_id,
                    source_id=scan["source_id"],
                    relative_path=token.cursor,
                    sentinel=token.source_sentinel,
                    status=manifest_status,
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
        raw_max_bytes: int = 10 * 1024 ** 3,
    ):
        if snapshot is None:
            snapshot = snapshotter
        if snapshot is None or queue is None or state_db is None:
            raise TypeError("snapshot, queue and state_db are required")
        self.snapshot = snapshot
        self.raw_max_bytes = max(int(raw_max_bytes), 1)
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

    def _reconcile_snapshot_temporary_files(self, scan_id: str | None = None) -> dict[str, Any]:
        """Run snapshot cleanup and persist only a generic retryable error."""
        try:
            result = self.snapshot.reconcile_temporary_snapshots()
        except Exception:
            result = {
                "scanned": 0,
                "removed": 0,
                "preserved": 0,
                "errors": ("snapshot_reconcile_failed",),
                "clean": False,
            }
        errors = tuple(
            str(error)
            for error in (result.get("errors") or ())
            if str(error)
        ) if isinstance(result, dict) else ("snapshot_reconcile_failed",)
        if errors and scan_id:
            try:
                row = self.state_db.get_automatic_memory_scan(scan_id)
                existing = row.get("last_error") if row else None
                detail = "snapshot temporary cleanup failed: " + ",".join(
                    dict.fromkeys(errors)
                )
                if isinstance(existing, str) and existing and existing != detail:
                    detail = f"{existing[:1600]}; {detail}"
                self.state_db.update_automatic_memory_scan(
                    scan_id,
                    last_error=detail[:2000],
                    updated_at=self._updated_at(),
                )
            except Exception:
                # The receipt remains available to the caller; never turn a
                # cleanup observation into a false successful scan.
                pass
        return result if isinstance(result, dict) else {
            "scanned": 0,
            "removed": 0,
            "preserved": 0,
            "errors": ("snapshot_reconcile_failed",),
            "clean": False,
        }

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
        self._reconcile_snapshot_temporary_files(scan_id)
        return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

    def run(
        self,
        scan_id: str,
        crash_at: Literal["none", "30%", "70%", "after-lease"] = "none",
        *,
        force_capture: bool = False,
    ) -> ScanRun:
        if crash_at not in {"none", "30%", "70%", "after-lease"}:
            raise ValueError(f"unsupported crash_at: {crash_at}")
        self._validate_single_database()
        row = self.state_db.get_automatic_memory_scan(scan_id)
        if row is None:
            raise LookupError(f"scan not found: {scan_id}")
        if row["status"] == "cancelled":
            self._reconcile_snapshot_temporary_files(scan_id)
            return self._scan(row)
        if row["status"] == "completed" and crash_at == "none":
            self._reconcile_snapshot_temporary_files(scan_id)
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id) or row)
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
            self._reconcile_snapshot_temporary_files(scan_id)
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

        paths = self._paths(row, source)
        previous = {} if force_capture else self._previous_manifest(source_id, scan_id)
        raw_used = sum(p.stat().st_size for p in self.snapshot.raw_root.iterdir()
                       if p.is_file() and not p.is_symlink())
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
            if current_sentinel and self._sentinel_matches(sentinels.get(relative, ""), current_sentinel):
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
        self._reconcile_snapshot_temporary_files(scan_id)
        self._start_heartbeat(scan_id, lease_id)
        try:
            initial = ResumeToken(scan_id, cursor, source_sentinel, lease_id, attempt)
            self.checkpoints.save_token_only(initial)
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
                self._reconcile_snapshot_temporary_files(scan_id)
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
                relative = self._relative(source, path)
                result = self._reuse_snapshot(source_id, path, previous.get(relative))
                if result is None:
                    size = path.stat().st_size
                    if raw_used + size > self.raw_max_bytes:
                        raise RuntimeError(
                            f"raw storage limit reached ({raw_used}/{self.raw_max_bytes} bytes); "
                            "existing evidence preserved; free space or raise automatic_memory_raw_max_bytes"
                        )
                    result = self.snapshot.capture(
                        source_id, path, scan_id=scan_id, lease_id=lease_id,
                        lease_guard=self._assert_heartbeat,
                    )
                    # Conservative within-scan accounting also bounds staging space.
                    raw_used += result.stat_after.size
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
                    admission_status = str(admission.get("status") or "").lower()
                    existing_payload = admission.get("payload") if isinstance(admission.get("payload"), dict) else {}
                    association = "existing" if admission.get("existing_job") and str(existing_payload.get("scan_id") or "") != scan_id else "new"
                    if association == "existing" and admission_status == "completed":
                        reused_count += 1
                    elif not admission.get("existing_job"):
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
                job_id = str(admission.get("job_id") or "")
                existing_payload = admission.get("payload") if isinstance(admission.get("payload"), dict) else {}
                association = "existing" if admission.get("existing_job") and str(existing_payload.get("scan_id") or "") != scan_id else "new"
                manifest_status = f"job:{job_id}:{association}" if job_id else "queued"
                self.checkpoints.save(checkpoint, manifest_status=manifest_status)
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
                self.checkpoints.save_token_only(checkpoint)
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
                self._reconcile_snapshot_temporary_files(scan_id)
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
                queued_count=queued_count,
                reused_count=reused_count,
                updated_at=self._updated_at(),
            )
            self._reconcile_snapshot_temporary_files(scan_id)
        except LeaseLostError:
            self._stop_heartbeat()
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
        final_row = self.state_db.get_automatic_memory_scan(scan_id) or finalized
        return self._scan(final_row)

    def _previous_manifest(self, source_id: str, scan_id: str) -> dict[str, Any]:
        scans = self.state_db.list_automatic_memory_scans(source_id)
        completed = [s for s in scans if s['scan_id'] != scan_id and s['status'] == 'completed']
        if not completed:
            return {}
        latest = completed[0]  # StateDatabase orders by timestamp, then insertion order.
        return {i['relative_path']: i for i in self.state_db.list_automatic_memory_scan_items(latest['scan_id'])}

    def _reuse_snapshot(self, source_id: str, path: Path, item: dict | None) -> SnapshotResult | None:
        if not item or not str(item.get('status', '')).startswith('job:'):
            return None
        # Reuse never bypasses authorization, path checks, or queue admission.
        _, relative = self.snapshot._authorized_path(source_id, path)
        before = self.snapshot._file_stat(path)
        if not self._sentinel_matches(item['sentinel'], self._path_sentinel(path)):
            return None
        try:
            job = self.queue.get(item['status'].split(':')[1])
        except (KeyError, LookupError):
            return None
        payload = job.get('payload') or {}
        digest = str(payload.get('sha256') or '')
        if (job.get('status') not in {'queued', 'running', 'completed'}
                or payload.get('source_id') != source_id
                or payload.get('relative_path') != relative
                or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)
                or payload.get('raw_id') != digest):
            return None
        raw = self.snapshot.raw_root / digest
        if raw.is_symlink() or not raw.is_file() or raw.stat().st_size != before.size:
            return None
        after = self.snapshot._file_stat(path)
        if before != after:
            return None
        return SnapshotResult(source_id, relative, digest, digest, before, after, True, 0)

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
        self._reconcile_snapshot_temporary_files(scan_id)
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
        return f"{stat.size}:{stat.mtime_ns}:{int(stat.inode or 0)}:{int(getattr(stat, 'mode', 0) or 0)}"

    @staticmethod
    def _path_sentinel(path: Path) -> str:
        stat = path.lstat()
        if not path.is_file() or path.is_symlink():
            return ""
        sentinel = f"{stat.st_size}:{stat.st_mtime_ns}:{int(getattr(stat, 'st_ino', 0) or 0)}:{int(stat.st_mode)}"
        # SQLite WAL：主库文件在 checkpoint 前不反映最新提交；WAL 的体积/时间
        # 变化必须进入哨兵，否则 WAL 模式数据库源（如 ZCode 会话库）永远
        # 被当作未变化而跳过采集。
        try:
            wal_stat = path.with_name(path.name + "-wal").lstat()
            if wal_stat.st_size:
                sentinel += f":wal{wal_stat.st_size}:{wal_stat.st_mtime_ns}"
        except OSError:
            pass
        return sentinel

    @staticmethod
    def _sentinel_matches(stored: str, current: str) -> bool:
        """Compare sentinels across the pre-mode checkpoint format.

        New sentinels carry ``size:mtime_ns:inode:mode``; checkpoints written
        before the mode segment only have three segments, so they compare on
        their common prefix and an unchanged file stays completed instead of
        being re-admitted once after an upgrade. Any other shape (empty,
        truncated, malformed) is treated as changed, which is the safe
        direction: it re-admits rather than silently skipping.
        """
        if not stored or not current:
            return False
        stored_segments = stored.split(":")
        current_segments = current.split(":")
        if len(stored_segments) == 3:
            stored_segments = stored_segments[:3]
            current_segments = current_segments[:3]
        return stored_segments == current_segments


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


__all__ = ["CheckpointStore", "ResumeToken", "SnapshotJobRunner"]
