from __future__ import annotations

import inspect
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4

from src.extraction.idempotency import build_snapshot_idempotency_key
from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase

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

    def __init__(self, state_db: StateDatabase | Path | str):
        self.state_db = (
            state_db if isinstance(state_db, StateDatabase) else StateDatabase(state_db)
        )

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
        self.state_db.update_automatic_memory_scan(
            token.scan_id,
            cursor=token.cursor or None,
            source_sentinel=token.source_sentinel,
            lease_id=token.lease_id,
            attempt=int(token.attempt),
            recovery_token=payload,
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
    ):
        if snapshot is None:
            snapshot = snapshotter
        if snapshot is None or queue is None or state_db is None:
            raise TypeError("snapshot, queue and state_db are required")
        self.snapshot = snapshot
        self.queue = queue
        self.state_db = state_db if isinstance(state_db, StateDatabase) else StateDatabase(state_db)
        self.path_provider = path_provider
        self.checkpoints = checkpoint_store or CheckpointStore(state_db)

    def run(
        self,
        scan_id: str,
        crash_at: Literal["none", "30%", "70%", "after-lease"] = "none",
    ) -> ScanRun:
        if crash_at not in {"none", "30%", "70%", "after-lease"}:
            raise ValueError(f"unsupported crash_at: {crash_at}")
        row = self.state_db.get_automatic_memory_scan(scan_id)
        if row is None:
            raise LookupError(f"scan not found: {scan_id}")
        if row["status"] == "completed" and crash_at == "none":
            return self._scan(row)
        source_id = str(row["source_id"])
        source = self.state_db.get_automatic_memory_source(
            source_id, now=self._updated_at()
        )
        if source is None:
            raise PermissionError("source is not authorized for scanning")
        if source.get("status") != "authorized":
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
        source_sentinel = token.source_sentinel if token else ""
        paths = [path for path in paths if self._relative(source, path) > cursor]
        lease_id = uuid4().hex
        attempt = int(row.get("attempt") or 0) + 1
        self.state_db.update_automatic_memory_scan(
            scan_id,
            status="running",
            total=total,
            lease_id=lease_id,
            attempt=attempt,
            last_error=None,
            updated_at=self._updated_at(),
        )
        initial = ResumeToken(scan_id, cursor, source_sentinel, lease_id, attempt)
        self.checkpoints.save(initial)
        if crash_at == "after-lease":
            return self._pause(scan_id, initial)

        completed_before = total - len(paths)
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
                result = self.snapshot.capture(source_id, path)
                if not result.stable:
                    raise RuntimeError(
                        f"source changed during snapshot: {result.relative_path}"
                    )
                raw_path = self.snapshot.raw_root / result.raw_id
                key = build_snapshot_idempotency_key(
                    source_id, result.relative_path, result.sha256
                )
                self.queue.enqueue(
                    "automatic_memory_snapshot",
                    input_path=raw_path,
                    payload={
                        "source_id": source_id,
                        "relative_path": result.relative_path,
                        "raw_id": result.raw_id,
                        "sha256": result.sha256,
                    },
                    options={"snapshot": True},
                    adapter_name="automatic_memory_snapshot",
                    adapter_version="1",
                    idempotency_key=key,
                )
                processed += 1
                sentinel = self._sentinel(result)
                checkpoint = ResumeToken(
                    scan_id, result.relative_path, sentinel, lease_id, attempt
                )
                self.checkpoints.save(checkpoint)
                cursor = result.relative_path
                source_sentinel = sentinel
                self.state_db.update_automatic_memory_scan(
                    scan_id,
                    progress=processed,
                    total=total,
                    updated_at=self._updated_at(),
                )
                if crash_index is not None and processed >= crash_index:
                    return self._pause(scan_id, checkpoint)
        except Exception as exc:
            checkpoint = ResumeToken(scan_id, cursor, source_sentinel, lease_id, attempt)
            self.checkpoints.save(checkpoint)
            self.state_db.update_automatic_memory_scan(
                scan_id,
                status="failed",
                total=total,
                progress=processed,
                last_error=str(exc)[:2000],
                updated_at=self._updated_at(),
            )
            self._release(scan_id)
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
        self.state_db.update_automatic_memory_scan(
            scan_id,
            status="completed",
            cursor=cursor if not paths else self._relative(source, paths[-1]),
            progress=total,
            total=total,
            last_error=None,
            updated_at=self._updated_at(),
        )
        self._release(scan_id)
        return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

    def _pause(self, scan_id: str, token: ResumeToken) -> ScanRun:
        self.state_db.update_automatic_memory_scan(
            scan_id,
            status="paused",
            cursor=token.cursor or None,
            lease_id=token.lease_id,
            recovery_token=json.dumps(token.__dict__, sort_keys=True),
            updated_at=self._updated_at(),
        )
        self._release(scan_id)
        return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

    def _release(self, scan_id: str) -> None:
        self.state_db.update_automatic_memory_scan(
            scan_id, lease_id=None, updated_at=self._updated_at()
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
        return f"{result.relative_path}:{stat.size}:{stat.mtime_ns}:{stat.inode or ''}"

    @staticmethod
    def _updated_at() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat(timespec="seconds")

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
