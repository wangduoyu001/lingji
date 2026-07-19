from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4


TERMINAL_STATUSES = ("completed", "failed", "cancelled")


class SQLiteExtractionQueue:
    """Durable queue stored in LingJi's existing SQLite runtime database."""

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
                """
            )

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
        input_path: str | None,
        payload: Any,
        adapter_name: str | None = None,
    ) -> str:
        material = {
            "source_type": source_type,
            "adapter_name": adapter_name or "",
            "input_path": str(input_path or ""),
            "payload": payload or {},
        }
        encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def enqueue(
        self,
        source_type: str,
        *,
        input_path: Path | str | None = None,
        payload: Any = None,
        options: Any = None,
        adapter_name: str | None = None,
        idempotency_key: str | None = None,
        priority: int = 100,
        max_attempts: int = 3,
        force: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now()
        normalized_path = str(Path(input_path).expanduser()) if input_path else None
        key = idempotency_key or self.build_idempotency_key(
            source_type, normalized_path, payload, adapter_name
        )
        job_id = f"LJ-JOB-{uuid4().hex[:12].upper()}"
        forced_job_id = None
        with self._lock, self._connection() as connection:
            existing = connection.execute(
                "SELECT * FROM extraction_jobs WHERE idempotency_key = ?", (key,)
            ).fetchone()
            if existing:
                parsed = self._parse_row(existing)
                if force and parsed and parsed["status"] in TERMINAL_STATUSES:
                    connection.execute(
                        """
                        UPDATE extraction_jobs
                        SET status = 'queued', attempts = 0, next_run_at = ?,
                            locked_at = NULL, locked_by = NULL, last_error = NULL,
                            result_json = NULL, completed_at = NULL, updated_at = ?
                        WHERE job_id = ?
                        """,
                        (self._iso(now), self._iso(now), parsed["job_id"]),
                    )
                    forced_job_id = parsed["job_id"]
                else:
                    return parsed
            else:
                connection.execute(
                    """
                    INSERT INTO extraction_jobs (
                        job_id, source_type, adapter_name, input_path, payload_json,
                        options_json, idempotency_key, status, priority, max_attempts,
                        next_run_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        source_type,
                        adapter_name,
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
        return self.get(forced_job_id or job_id)

    def claim(
        self,
        worker_id: str,
        *,
        job_id: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        now = now or datetime.now()
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
                SET status = 'running', attempts = attempts + 1,
                    locked_at = ?, locked_by = ?, updated_at = ?
                WHERE job_id = ? AND status IN ('queued', 'retrying')
                """,
                (self._iso(now), worker_id, self._iso(now), row["job_id"]),
            )
            if updated.rowcount != 1:
                return None
            claimed = connection.execute(
                "SELECT * FROM extraction_jobs WHERE job_id = ?", (row["job_id"],)
            ).fetchone()
            return self._parse_row(claimed)

    def complete(
        self,
        job_id: str,
        result: Any = None,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                UPDATE extraction_jobs
                SET status = 'completed', result_json = ?, completed_at = ?,
                    locked_at = NULL, locked_by = NULL, last_error = NULL, updated_at = ?
                WHERE job_id = ?
                """,
                (self._json(result), self._iso(now), self._iso(now), job_id),
            )
        return self.get(job_id)

    def fail(
        self,
        job_id: str,
        error: str,
        *,
        retry_delay_seconds: int | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT attempts, max_attempts FROM extraction_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if not row:
                raise LookupError(f"Unknown extraction job: {job_id}")
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
                SET status = ?, next_run_at = ?, last_error = ?,
                    locked_at = NULL, locked_by = NULL, updated_at = ?
                WHERE job_id = ?
                """,
                (
                    "retrying" if should_retry else "failed",
                    self._iso(next_run if should_retry else now),
                    str(error)[:2000],
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
                SET status = 'retrying', next_run_at = ?, locked_at = NULL,
                    locked_by = NULL, last_error = 'worker lock expired', updated_at = ?
                WHERE status = 'running' AND locked_at < ?
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

    def list(
        self,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._connection() as connection:
            if status:
                rows = connection.execute(
                    """
                    SELECT * FROM extraction_jobs
                    WHERE status = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (status, max(int(limit), 1)),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM extraction_jobs ORDER BY created_at DESC LIMIT ?",
                    (max(int(limit), 1),),
                ).fetchall()
        return [self._parse_row(row) for row in rows]

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
