from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from uuid import uuid4

from .idempotency import extraction_key_for_request
from src.storage.state_db import LeaseLostError

TERMINAL_STATUSES = ("completed", "failed", "cancelled")
CANCELLABLE_STATUSES = ("queued", "retrying")
RETRYABLE_STATUSES = ("failed", "cancelled")


class _SQLiteExtractionQueueBase:
    """Durable extraction queue with canonical idempotency and lease ownership."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS extraction_jobs (
                    job_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    adapter_name TEXT,
                    adapter_version TEXT NOT NULL DEFAULT '',
                    input_path TEXT,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    options_json TEXT NOT NULL DEFAULT '{}',
                    idempotency_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 100,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    next_run_at TEXT NOT NULL,
                    locked_at TEXT,
                    locked_by TEXT,
                    lease_token TEXT,
                    heartbeat_at TEXT,
                    progress_current INTEGER NOT NULL DEFAULT 0,
                    progress_total INTEGER NOT NULL DEFAULT 0,
                    progress_message TEXT,
                    last_error TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_extraction_jobs_due
                    ON extraction_jobs(status, next_run_at, priority, created_at);
                CREATE INDEX IF NOT EXISTS idx_extraction_jobs_source
                    ON extraction_jobs(source_type, created_at);
                CREATE INDEX IF NOT EXISTS idx_extraction_jobs_lease
                    ON extraction_jobs(status, heartbeat_at, locked_at);
                """
            )
            self._ensure_columns(connection)

    @staticmethod
    def _ensure_columns(connection: sqlite3.Connection) -> None:
        existing = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(extraction_jobs)").fetchall()
        }
        columns = {
            "adapter_version": "TEXT NOT NULL DEFAULT ''",
            "lease_token": "TEXT",
            "heartbeat_at": "TEXT",
            "progress_current": "INTEGER NOT NULL DEFAULT 0",
            "progress_total": "INTEGER NOT NULL DEFAULT 0",
            "progress_message": "TEXT",
        }
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE extraction_jobs ADD COLUMN {name} {definition}")

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat(timespec="seconds")

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _parse_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        result = dict(row)
        for key in ("payload_json", "options_json", "result_json"):
            raw = result.pop(key, None)
            target = key.removesuffix("_json")
            if raw:
                try:
                    result[target] = json.loads(raw)
                except json.JSONDecodeError:
                    result[target] = {}
            else:
                result[target] = {}
        return result

    @staticmethod
    def build_idempotency_key(
        source_type: str,
        input_path: str | Path | None,
        payload: Mapping[str, Any] | None,
        options: Mapping[str, Any] | None = None,
        adapter_name: str | None = None,
        adapter_version: str = "",
    ) -> str:
        """Compatibility signature backed by the canonical identity module."""

        return extraction_key_for_request(
            source_type=source_type,
            adapter_name=adapter_name or "",
            adapter_version=adapter_version,
            input_path=input_path,
            payload=payload,
            effective_options=options,
        )

    def enqueue(
        self,
        source_type: str,
        *,
        input_path: Path | str | None = None,
        payload: Mapping[str, Any] | None = None,
        options: Mapping[str, Any] | None = None,
        adapter_name: str | None = None,
        adapter_version: str = "",
        idempotency_key: str | None = None,
        priority: int = 100,
        max_attempts: int = 3,
        force: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now()
        normalized_path = str(Path(input_path).expanduser()) if input_path else None
        key = idempotency_key or self.build_idempotency_key(
            source_type,
            normalized_path,
            payload,
            options,
            adapter_name,
            adapter_version,
        )
        job_id = f"LJ-JOB-{uuid4().hex[:12].upper()}"
        selected_job_id = job_id
        existing_job = False
        with self._lock, self._connection() as connection:
            existing = connection.execute(
                "SELECT * FROM extraction_jobs WHERE idempotency_key = ?", (key,)
            ).fetchone()
            if existing:
                parsed = self._parse_row(existing)
                if not parsed:
                    raise RuntimeError("Unable to parse existing extraction job")
                existing_job = True
                selected_job_id = str(parsed["job_id"])
                if not force or parsed["status"] not in TERMINAL_STATUSES:
                    return {**parsed, "existing_job": True}
                connection.execute(
                    """
                    UPDATE extraction_jobs
                    SET source_type = ?, adapter_name = ?, adapter_version = ?, input_path = ?,
                        payload_json = ?, options_json = ?, status = 'queued', priority = ?,
                        attempts = 0, max_attempts = ?, next_run_at = ?, locked_at = NULL,
                        locked_by = NULL, lease_token = NULL, heartbeat_at = NULL,
                        progress_current = 0, progress_total = 0, progress_message = NULL,
                        last_error = NULL, result_json = NULL, completed_at = NULL, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (
                        source_type,
                        adapter_name,
                        adapter_version,
                        normalized_path,
                        self._json(payload),
                        self._json(options),
                        int(priority),
                        max(int(max_attempts), 1),
                        self._iso(now),
                        self._iso(now),
                        selected_job_id,
                    ),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO extraction_jobs (
                        job_id, source_type, adapter_name, adapter_version, input_path,
                        payload_json, options_json, idempotency_key, status, priority,
                        max_attempts, next_run_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        source_type,
                        adapter_name,
                        adapter_version,
                        normalized_path,
                        self._json(payload),
                        self._json(options),
                        key,
                        int(priority),
                        max(int(max_attempts), 1),
                        self._iso(now),
                        self._iso(now),
                        self._iso(now),
                    ),
                )
        return {**self.get(selected_job_id), "existing_job": existing_job}

    def claim(
        self,
        worker_id: str,
        *,
        job_id: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        now = now or datetime.now()
        lease_token = uuid4().hex
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if job_id:
                row = connection.execute(
                    """
                    SELECT * FROM extraction_jobs
                    WHERE job_id = ? AND status IN ('queued', 'retrying') AND next_run_at <= ?
                    """,
                    (job_id, self._iso(now)),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT * FROM extraction_jobs
                    WHERE status IN ('queued', 'retrying') AND next_run_at <= ?
                    ORDER BY priority ASC, created_at ASC
                    LIMIT 1
                    """,
                    (self._iso(now),),
                ).fetchone()
            if not row:
                return None
            updated = connection.execute(
                """
                UPDATE extraction_jobs
                SET status = 'running', attempts = attempts + 1, locked_at = ?, locked_by = ?,
                    lease_token = ?, heartbeat_at = ?, progress_message = 'started', updated_at = ?
                WHERE job_id = ? AND status IN ('queued', 'retrying')
                """,
                (
                    self._iso(now),
                    worker_id,
                    lease_token,
                    self._iso(now),
                    self._iso(now),
                    row["job_id"],
                ),
            )
            if updated.rowcount != 1:
                return None
            claimed = connection.execute(
                "SELECT * FROM extraction_jobs WHERE job_id = ?", (row["job_id"],)
            ).fetchone()
            return self._parse_row(claimed)

    def heartbeat(
        self,
        job_id: str,
        worker_id: str,
        lease_token: str,
        *,
        progress_current: int | None = None,
        progress_total: int | None = None,
        progress_message: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        now = now or datetime.now()
        assignments = ["heartbeat_at = ?", "updated_at = ?"]
        values: list[Any] = [self._iso(now), self._iso(now)]
        if progress_current is not None:
            assignments.append("progress_current = ?")
            values.append(max(int(progress_current), 0))
        if progress_total is not None:
            assignments.append("progress_total = ?")
            values.append(max(int(progress_total), 0))
        if progress_message is not None:
            assignments.append("progress_message = ?")
            values.append(str(progress_message)[:500])
        values.extend([job_id, worker_id, lease_token])
        with self._lock, self._connection() as connection:
            cursor = connection.execute(
                f"""
                UPDATE extraction_jobs SET {', '.join(assignments)}
                WHERE job_id = ? AND status = 'running' AND locked_by = ? AND lease_token = ?
                """,
                tuple(values),
            )
            return cursor.rowcount == 1

    def complete(
        self,
        job_id: str,
        result: Any = None,
        *,
        worker_id: str | None = None,
        lease_token: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now()
        where = "job_id = ? AND status = 'running'"
        params: list[Any] = [self._json(result), self._iso(now), self._iso(now)]
        identity: list[Any] = [job_id]
        if worker_id is not None or lease_token is not None:
            where += " AND locked_by = ? AND lease_token = ?"
            identity.extend([worker_id or "", lease_token or ""])
        with self._lock, self._connection() as connection:
            cursor = connection.execute(
                f"""
                UPDATE extraction_jobs
                SET status = 'completed', result_json = ?, completed_at = ?, progress_message = 'completed',
                    locked_at = NULL, locked_by = NULL, lease_token = NULL, heartbeat_at = NULL,
                    last_error = NULL, updated_at = ?
                WHERE {where}
                """,
                tuple(params + identity),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Extraction lease lost before completion: {job_id}")
        return self.get(job_id)

    def fail(
        self,
        job_id: str,
        error: str,
        *,
        worker_id: str | None = None,
        lease_token: str | None = None,
        retry_delay_seconds: int | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT attempts, max_attempts, locked_by, lease_token, status FROM extraction_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if not row:
                raise LookupError(f"Unknown extraction job: {job_id}")
            if row["status"] != "running":
                raise RuntimeError(f"Extraction job is not running: {job_id}")
            if worker_id is not None and (
                str(row["locked_by"] or "") != worker_id
                or str(row["lease_token"] or "") != str(lease_token or "")
            ):
                raise RuntimeError(f"Extraction lease lost before failure handling: {job_id}")
            attempts = int(row["attempts"])
            max_attempts = int(row["max_attempts"])
            should_retry = attempts < max_attempts
            delay = retry_delay_seconds
            if delay is None:
                delay = min(60 * (2 ** max(attempts - 1, 0)), 3600)
            next_run = now + timedelta(seconds=max(int(delay), 0))
            connection.execute(
                """
                UPDATE extraction_jobs
                SET status = ?, next_run_at = ?, last_error = ?, progress_message = ?,
                    locked_at = NULL, locked_by = NULL, lease_token = NULL, heartbeat_at = NULL,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (
                    "retrying" if should_retry else "failed",
                    self._iso(next_run if should_retry else now),
                    str(error)[:2000],
                    "retrying" if should_retry else "failed",
                    self._iso(now),
                    job_id,
                ),
            )
        return self.get(job_id)

    def release_stale(
        self,
        stale_after_seconds: int = 1800,
        *,
        now: datetime | None = None,
    ) -> int:
        now = now or datetime.now()
        cutoff = now - timedelta(seconds=max(int(stale_after_seconds), 1))
        with self._lock, self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE extraction_jobs
                SET status = 'retrying', next_run_at = ?, locked_at = NULL, locked_by = NULL,
                    lease_token = NULL, heartbeat_at = NULL, last_error = 'worker lease expired',
                    progress_message = 'lease expired; retrying', updated_at = ?
                WHERE status = 'running' AND COALESCE(heartbeat_at, locked_at) < ?
                """,
                (self._iso(now), self._iso(now), self._iso(cutoff)),
            )
            return int(cursor.rowcount)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM extraction_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        parsed = self._parse_row(row)
        if parsed is None:
            raise LookupError(f"Unknown extraction job: {job_id}")
        return parsed

    def list(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self._connection() as connection:
            if status:
                rows = connection.execute(
                    "SELECT * FROM extraction_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, max(int(limit), 1)),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM extraction_jobs ORDER BY created_at DESC LIMIT ?",
                    (max(int(limit), 1),),
                ).fetchall()
        return [parsed for row in rows if (parsed := self._parse_row(row)) is not None]

    def stats(self) -> dict[str, int]:
        result = {
            "queued": 0,
            "retrying": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM extraction_jobs GROUP BY status"
            ).fetchall()
        for row in rows:
            result[str(row["status"])] = int(row["count"])
        result["pending"] = result["queued"] + result["retrying"] + result["running"]
        return result


class SQLiteExtractionQueue(_SQLiteExtractionQueueBase):
    """Public extraction queue extended with user-facing control operations."""

    def cancel(self, job_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT status FROM extraction_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if not row:
                raise LookupError(f"Unknown extraction job: {job_id}")
            status = str(row["status"])
            if status not in CANCELLABLE_STATUSES:
                raise RuntimeError(f"Extraction job is not cancellable: {status}")
            cursor = connection.execute(
                """
                UPDATE extraction_jobs
                SET status = 'cancelled', completed_at = ?, next_run_at = ?,
                    locked_at = NULL, locked_by = NULL, lease_token = NULL, heartbeat_at = NULL,
                    progress_message = 'cancelled', updated_at = ?
                WHERE job_id = ? AND status IN ('queued', 'retrying')
                """,
                (self._iso(now), self._iso(now), self._iso(now), job_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Extraction job state changed before cancellation")
        return self.get(job_id)

    def retry(self, job_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT status FROM extraction_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if not row:
                raise LookupError(f"Unknown extraction job: {job_id}")
            status = str(row["status"])
            if status not in RETRYABLE_STATUSES:
                raise RuntimeError(f"Extraction job is not retryable: {status}")
            cursor = connection.execute(
                """
                UPDATE extraction_jobs
                SET status = 'queued', attempts = 0, last_error = NULL, result_json = NULL,
                    completed_at = NULL, next_run_at = ?, locked_at = NULL, locked_by = NULL,
                    lease_token = NULL, heartbeat_at = NULL, progress_current = 0,
                    progress_total = 0, progress_message = NULL, updated_at = ?
                WHERE job_id = ? AND status IN ('failed', 'cancelled')
                """,
                (self._iso(now), self._iso(now), job_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Extraction job state changed before retry")
        return self.get(job_id)

    def get_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM extraction_jobs WHERE idempotency_key = ?",
                (str(idempotency_key),),
            ).fetchone()
        return self._parse_row(row)

    def enqueue_authorized_snapshot(
        self,
        *,
        scan_id: str,
        lease_id: str,
        source_id: str,
        relative_path: str,
        raw_id: str,
        sha256: str,
        input_path: Path | str,
    ) -> dict[str, Any]:
        """Insert a snapshot job while serializing against source revoke."""

        from .idempotency import build_snapshot_idempotency_key

        now = datetime.now()
        key = build_snapshot_idempotency_key(source_id, relative_path, sha256)
        job_id = f"LJ-JOB-{uuid4().hex[:12].upper()}"
        normalized_path = str(Path(input_path).expanduser())
        payload = {
            "source_id": source_id,
            "relative_path": relative_path,
            "raw_id": raw_id,
            "sha256": sha256,
        }
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            authorized = connection.execute(
                """
                SELECT scans.scan_id
                FROM automatic_memory_scans AS scans
                JOIN automatic_memory_sources AS sources ON sources.source_id = scans.source_id
                JOIN automatic_memory_grants AS grants ON grants.grant_id = sources.grant_id
                WHERE scans.scan_id = ? AND scans.status = 'running'
                  AND scans.lease_id = ? AND scans.source_id = ?
                  AND sources.status = 'authorized' AND grants.owner_confirmed = 1
                  AND (grants.expires_at IS NULL OR grants.expires_at > ?)
                """,
                (
                    scan_id,
                    str(lease_id),
                    source_id,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            ).fetchone()
            if authorized is None:
                raise LeaseLostError(f"queue admission lost or source revoked: {scan_id}")
            existing = connection.execute(
                "SELECT * FROM extraction_jobs WHERE idempotency_key = ?", (key,)
            ).fetchone()
            if existing is not None:
                return self._parse_row(existing)
            connection.execute(
                """
                INSERT INTO extraction_jobs (
                    job_id, source_type, adapter_name, adapter_version, input_path,
                    payload_json, options_json, idempotency_key, status, priority,
                    max_attempts, next_run_at, created_at, updated_at
                ) VALUES (?, 'automatic_memory_snapshot', 'automatic_memory_snapshot', '1', ?, ?, ?, ?, 'queued', 100, 3, ?, ?, ?)
                """,
                (
                    job_id,
                    normalized_path,
                    self._json(payload),
                    self._json({"snapshot": True}),
                    key,
                    self._iso(now),
                    self._iso(now),
                    self._iso(now),
                ),
            )
            row = connection.execute(
                "SELECT * FROM extraction_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return self._parse_row(row)

    @staticmethod
    def _filters(
        *,
        status: str | None = None,
        source_type: str | None = None,
        q: str | None = None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        if status:
            clauses.append("status = ?")
            values.append(str(status))
        if source_type:
            clauses.append("source_type = ?")
            values.append(str(source_type))
        if q and str(q).strip():
            needle = f"%{str(q).strip()}%"
            clauses.append(
                "(job_id LIKE ? OR source_type LIKE ? OR COALESCE(adapter_name, '') LIKE ? "
                "OR COALESCE(input_path, '') LIKE ? OR COALESCE(progress_message, '') LIKE ?)"
            )
            values.extend([needle] * 5)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", values

    @staticmethod
    def _page_values(limit: int, offset: int) -> tuple[int, int]:
        normalized_limit = int(limit)
        normalized_offset = int(offset)
        if normalized_limit < 1 or normalized_limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if normalized_offset < 0:
            raise ValueError("offset must be greater than or equal to zero")
        return normalized_limit, normalized_offset

    def list_page(
        self,
        *,
        status: str | None = None,
        source_type: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        normalized_limit, normalized_offset = self._page_values(limit, offset)
        where, values = self._filters(status=status, source_type=source_type, q=q)
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM extraction_jobs{where} "
                "ORDER BY created_at DESC, job_id DESC LIMIT ? OFFSET ?",
                tuple(values + [normalized_limit, normalized_offset]),
            ).fetchall()
        return [parsed for row in rows if (parsed := self._parse_row(row)) is not None]

    def count(
        self,
        *,
        status: str | None = None,
        source_type: str | None = None,
        q: str | None = None,
    ) -> int:
        where, values = self._filters(status=status, source_type=source_type, q=q)
        with self._connection() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS count FROM extraction_jobs{where}", tuple(values)
            ).fetchone()
        return int(row["count"] if row else 0)

    def list(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return super().list(status=status, limit=limit)
