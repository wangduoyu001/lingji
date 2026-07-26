from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator


class StateDatabase:
    """Small SQLite state store for scheduler, processing and audit events."""

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
        connection.execute("PRAGMA foreign_keys = ON")
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
                CREATE TABLE IF NOT EXISTS scheduler_jobs (
                    name TEXT PRIMARY KEY,
                    interval_seconds REAL NOT NULL,
                    min_mode TEXT NOT NULL DEFAULT 'NORMAL',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    run_on_start INTEGER NOT NULL DEFAULT 0,
                    last_started_at TEXT,
                    last_finished_at TEXT,
                    next_run_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    last_error TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS processing_states (
                    source_id TEXT NOT NULL,
                    processor TEXT NOT NULL,
                    processor_version TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_started_at TEXT,
                    last_finished_at TEXT,
                    last_error TEXT,
                    result_json TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (source_id, processor, processor_version)
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_scheduler_due
                    ON scheduler_jobs(enabled, next_run_at);
                CREATE INDEX IF NOT EXISTS idx_processing_status
                    ON processing_states(status, updated_at);
                CREATE INDEX IF NOT EXISTS idx_events_entity
                    ON events(entity_type, entity_id, created_at);
                """
            )

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat(timespec="seconds")

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)

    def upsert_scheduler_job(
        self,
        name: str,
        interval_hours: float,
        min_mode: str = "NORMAL",
        enabled: bool = True,
        run_on_start: bool = False,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now()
        interval_seconds = max(float(interval_hours) * 3600, 1.0)
        with self._lock, self._connection() as connection:
            existing = connection.execute(
                "SELECT next_run_at FROM scheduler_jobs WHERE name = ?", (name,)
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE scheduler_jobs
                    SET interval_seconds = ?, min_mode = ?, enabled = ?, run_on_start = ?, updated_at = ?
                    WHERE name = ?
                    """,
                    (
                        interval_seconds,
                        min_mode,
                        int(enabled),
                        int(run_on_start),
                        self._iso(now),
                        name,
                    ),
                )
                return
            next_run = now if run_on_start else now + timedelta(seconds=interval_seconds)
            connection.execute(
                """
                INSERT INTO scheduler_jobs (
                    name, interval_seconds, min_mode, enabled, run_on_start,
                    next_run_at, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    name,
                    interval_seconds,
                    min_mode,
                    int(enabled),
                    int(run_on_start),
                    self._iso(next_run),
                    self._iso(now),
                ),
            )

    def due_scheduler_jobs(self, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now()
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM scheduler_jobs
                WHERE enabled = 1 AND next_run_at <= ? AND status != 'running'
                ORDER BY next_run_at ASC
                """,
                (self._iso(now),),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_job_started(self, name: str, now: datetime | None = None) -> None:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                UPDATE scheduler_jobs
                SET status = 'running', last_started_at = ?, last_error = NULL, updated_at = ?
                WHERE name = ?
                """,
                (self._iso(now), self._iso(now), name),
            )

    def mark_job_finished(
        self,
        name: str,
        success: bool,
        error: str | None = None,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT interval_seconds FROM scheduler_jobs WHERE name = ?", (name,)
            ).fetchone()
            if not row:
                return
            next_run = now + timedelta(seconds=float(row["interval_seconds"]))
            connection.execute(
                """
                UPDATE scheduler_jobs
                SET status = ?, last_finished_at = ?, next_run_at = ?, last_error = ?, updated_at = ?
                WHERE name = ?
                """,
                (
                    "success" if success else "failed",
                    self._iso(now),
                    self._iso(next_run),
                    None if success else str(error or "unknown error")[:1000],
                    self._iso(now),
                    name,
                ),
            )

    def list_scheduler_jobs(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM scheduler_jobs ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def needs_processing(
        self,
        source_id: str,
        processor: str,
        processor_version: str,
        content_hash: str,
    ) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT content_hash, status FROM processing_states
                WHERE source_id = ? AND processor = ? AND processor_version = ?
                """,
                (source_id, processor, processor_version),
            ).fetchone()
        return not row or row["content_hash"] != content_hash or row["status"] != "success"

    def mark_processing_started(
        self,
        source_id: str,
        processor: str,
        processor_version: str,
        content_hash: str,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                INSERT INTO processing_states (
                    source_id, processor, processor_version, content_hash, status,
                    last_started_at, updated_at
                ) VALUES (?, ?, ?, ?, 'running', ?, ?)
                ON CONFLICT(source_id, processor, processor_version) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    status = 'running',
                    last_started_at = excluded.last_started_at,
                    last_error = NULL,
                    updated_at = excluded.updated_at
                """,
                (
                    source_id,
                    processor,
                    processor_version,
                    content_hash,
                    self._iso(now),
                    self._iso(now),
                ),
            )

    def mark_processing_finished(
        self,
        source_id: str,
        processor: str,
        processor_version: str,
        content_hash: str,
        success: bool,
        result: Any = None,
        error: str | None = None,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                INSERT INTO processing_states (
                    source_id, processor, processor_version, content_hash, status,
                    last_finished_at, last_error, result_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, processor, processor_version) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    status = excluded.status,
                    last_finished_at = excluded.last_finished_at,
                    last_error = excluded.last_error,
                    result_json = excluded.result_json,
                    updated_at = excluded.updated_at
                """,
                (
                    source_id,
                    processor,
                    processor_version,
                    content_hash,
                    "success" if success else "failed",
                    self._iso(now),
                    None if success else str(error or "unknown error")[:1000],
                    self._json(result),
                    self._iso(now),
                ),
            )

    def append_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str | None = None,
        payload: Any = None,
        now: datetime | None = None,
    ) -> int:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events(event_type, entity_type, entity_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_type, entity_type, entity_id, self._json(payload), self._iso(now)),
            )
            return int(cursor.lastrowid)

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM events ORDER BY event_id DESC LIMIT ?", (int(limit),)
            ).fetchall()
        return [dict(row) for row in rows]
