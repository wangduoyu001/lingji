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

                CREATE TABLE IF NOT EXISTS automatic_memory_grants (
                    grant_id TEXT PRIMARY KEY,
                    source_kinds_json TEXT NOT NULL,
                    roots_json TEXT NOT NULL,
                    granted_at TEXT NOT NULL,
                    expires_at TEXT,
                    owner_confirmed INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS automatic_memory_sources (
                    source_id TEXT PRIMARY KEY,
                    grant_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    root TEXT NOT NULL,
                    status TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked_at TEXT,
                    UNIQUE(grant_id, kind, root)
                );

                CREATE TABLE IF NOT EXISTS automatic_memory_scans (
                    scan_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    cursor TEXT,
                    progress INTEGER NOT NULL DEFAULT 0,
                    total INTEGER,
                    last_error TEXT,
                    recovery_token TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_automatic_memory_sources_status
                    ON automatic_memory_sources(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_automatic_memory_scans_source
                    ON automatic_memory_scans(source_id, updated_at);
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

    def create_automatic_memory_grant(self, record: dict[str, Any]) -> None:
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                INSERT INTO automatic_memory_grants (
                    grant_id, source_kinds_json, roots_json, granted_at, expires_at,
                    owner_confirmed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["grant_id"],
                    record["source_kinds_json"],
                    record["roots_json"],
                    record["granted_at"],
                    record.get("expires_at"),
                    int(bool(record["owner_confirmed"])),
                    record["created_at"],
                ),
            )

    def get_automatic_memory_grant(self, grant_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM automatic_memory_grants WHERE grant_id = ?",
                (grant_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_automatic_memory_source(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                INSERT INTO automatic_memory_sources (
                    source_id, grant_id, kind, root, status, capability,
                    policy_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["source_id"],
                    record["grant_id"],
                    record["kind"],
                    record["root"],
                    record["status"],
                    record["capability"],
                    record["policy_version"],
                    record["created_at"],
                ),
            )
            row = connection.execute(
                "SELECT * FROM automatic_memory_sources WHERE source_id = ?",
                (record["source_id"],),
            ).fetchone()
        return dict(row)

    def get_automatic_memory_source(self, source_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM automatic_memory_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return dict(row) if row else None

    def find_automatic_memory_source(
        self, grant_id: str, kind: str, root: str
    ) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM automatic_memory_sources
                WHERE grant_id = ? AND kind = ? AND root = ?
                """,
                (grant_id, kind, root),
            ).fetchone()
        return dict(row) if row else None

    def list_automatic_memory_sources(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM automatic_memory_sources ORDER BY created_at, source_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def update_automatic_memory_source(
        self, source_id: str, *, status: str, revoked_at: str | None = None
    ) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                UPDATE automatic_memory_sources
                SET status = ?, revoked_at = ?
                WHERE source_id = ?
                """,
                (status, revoked_at, source_id),
            )
            row = connection.execute(
                "SELECT * FROM automatic_memory_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        if row is None:
            raise KeyError(source_id)
        return dict(row)

    def create_automatic_memory_scan(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                INSERT INTO automatic_memory_scans (
                    scan_id, source_id, status, cursor, progress, total,
                    last_error, recovery_token, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["scan_id"],
                    record["source_id"],
                    record["status"],
                    record.get("cursor"),
                    int(record.get("progress", 0)),
                    record.get("total"),
                    record.get("last_error"),
                    record.get("recovery_token"),
                    record["updated_at"],
                ),
            )
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?",
                (record["scan_id"],),
            ).fetchone()
        return dict(row)

    def get_automatic_memory_scan(self, scan_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?",
                (scan_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_automatic_memory_scan(self, scan_id: str, **values: Any) -> dict[str, Any]:
        allowed = {
            "status",
            "cursor",
            "progress",
            "total",
            "last_error",
            "recovery_token",
            "updated_at",
        }
        changes = {key: value for key, value in values.items() if key in allowed}
        if not changes:
            current = self.get_automatic_memory_scan(scan_id)
            if current is None:
                raise KeyError(scan_id)
            return current
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self._lock, self._connection() as connection:
            connection.execute(
                f"UPDATE automatic_memory_scans SET {assignments} WHERE scan_id = ?",
                (*changes.values(), scan_id),
            )
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?",
                (scan_id,),
            ).fetchone()
        if row is None:
            raise KeyError(scan_id)
        return dict(row)
