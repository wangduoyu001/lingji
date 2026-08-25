from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator


class LeaseLostError(RuntimeError):
    """Raised when a stale worker attempts to mutate a newer scan lease."""


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
                    source_sentinel TEXT,
                    lease_id TEXT,
                    lease_owner_pid INTEGER,
                    lease_owner_thread TEXT,
                    lease_heartbeat_at TEXT,
                    lease_expires_at TEXT,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_automatic_memory_sources_status
                    ON automatic_memory_sources(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_automatic_memory_scans_source
                    ON automatic_memory_scans(source_id, updated_at);

                CREATE TABLE IF NOT EXISTS automatic_memory_scan_items (
                    scan_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    sentinel TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'processed',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(scan_id, relative_path)
                );

                CREATE INDEX IF NOT EXISTS idx_automatic_memory_scan_items_source
                    ON automatic_memory_scan_items(source_id, scan_id, relative_path);
                """
            )
            # Task 1 databases may already have the scan table. Keep the
            # migration additive so existing state and recovery tokens survive.
            columns = {
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(automatic_memory_scans)"
                ).fetchall()
            }
            for name, definition in (
                ("source_sentinel", "TEXT"),
                ("lease_id", "TEXT"),
                ("lease_owner_pid", "INTEGER"),
                ("lease_owner_thread", "TEXT"),
                ("lease_heartbeat_at", "TEXT"),
                ("lease_expires_at", "TEXT"),
                ("attempt", "INTEGER NOT NULL DEFAULT 0"),
            ):
                if name not in columns:
                    connection.execute(
                        f"ALTER TABLE automatic_memory_scans ADD COLUMN {name} {definition}"
                    )

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat(timespec="seconds")

    @staticmethod
    def _lease_expiry(timestamp: str, ttl_seconds: float) -> str:
        value = datetime.fromisoformat(timestamp)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (value + timedelta(seconds=max(float(ttl_seconds), 1.0))).isoformat(
            timespec="seconds"
        )

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

    def get_automatic_memory_source(
        self, source_id: str, *, now: str | None = None
    ) -> dict[str, Any] | None:
        with self._lock, self._connection() as connection:
            if now is not None:
                connection.execute(
                    """
                    UPDATE automatic_memory_sources
                    SET status = 'expired'
                    WHERE source_id = ? AND status = 'authorized'
                      AND EXISTS (
                        SELECT 1 FROM automatic_memory_grants AS grants
                        WHERE grants.grant_id = automatic_memory_sources.grant_id
                          AND grants.expires_at IS NOT NULL
                          AND grants.expires_at <= ?
                      )
                    """,
                    (source_id, now),
                )
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

    def list_automatic_memory_sources(
        self, *, now: str | None = None
    ) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            if now is not None:
                connection.execute(
                    """
                    UPDATE automatic_memory_sources
                    SET status = 'expired'
                    WHERE status = 'authorized'
                      AND EXISTS (
                        SELECT 1 FROM automatic_memory_grants AS grants
                        WHERE grants.grant_id = automatic_memory_sources.grant_id
                          AND grants.expires_at IS NOT NULL
                          AND grants.expires_at <= ?
                      )
                    """,
                    (now,),
                )
            rows = connection.execute(
                "SELECT * FROM automatic_memory_sources ORDER BY created_at, source_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def register_automatic_memory_source_atomic(
        self, grant: dict[str, Any], source: dict[str, Any]
    ) -> dict[str, Any]:
        """Persist grant and source together, serializing duplicate registration."""
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_grant = connection.execute(
                "SELECT * FROM automatic_memory_grants WHERE grant_id = ?",
                (grant["grant_id"],),
            ).fetchone()
            if existing_grant is None:
                connection.execute(
                    """
                    INSERT INTO automatic_memory_grants (
                        grant_id, source_kinds_json, roots_json, granted_at, expires_at,
                        owner_confirmed, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        grant["grant_id"],
                        grant["source_kinds_json"],
                        grant["roots_json"],
                        grant["granted_at"],
                        grant.get("expires_at"),
                        int(bool(grant["owner_confirmed"])),
                        grant["created_at"],
                    ),
                )
            else:
                expected = (
                    grant["source_kinds_json"],
                    grant["roots_json"],
                    grant["granted_at"],
                    grant.get("expires_at"),
                    int(bool(grant["owner_confirmed"])),
                )
                actual = tuple(
                    existing_grant[key]
                    for key in (
                        "source_kinds_json",
                        "roots_json",
                        "granted_at",
                        "expires_at",
                        "owner_confirmed",
                    )
                )
                if actual != expected:
                    raise ValueError("authorization grant does not match persisted scope")

            existing_source = connection.execute(
                """
                SELECT * FROM automatic_memory_sources
                WHERE grant_id = ? AND kind = ? AND root = ?
                """,
                (source["grant_id"], source["kind"], source["root"]),
            ).fetchone()
            if existing_source is None:
                connection.execute(
                    """
                    INSERT INTO automatic_memory_sources (
                        source_id, grant_id, kind, root, status, capability,
                        policy_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source["source_id"],
                        source["grant_id"],
                        source["kind"],
                        source["root"],
                        source["status"],
                        source["capability"],
                        source["policy_version"],
                        source["created_at"],
                    ),
                )
                existing_source = connection.execute(
                    "SELECT * FROM automatic_memory_sources WHERE source_id = ?",
                    (source["source_id"],),
                ).fetchone()
        return dict(existing_source)

    def start_automatic_memory_scan_atomic(
        self, source_id: str, scan: dict[str, Any], *, now: str
    ) -> dict[str, Any]:
        """Recheck authorization and serialize the one-active-scan invariant."""
        expired = False
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            source = connection.execute(
                """
                SELECT sources.*, grants.expires_at, grants.owner_confirmed
                FROM automatic_memory_sources AS sources
                JOIN automatic_memory_grants AS grants ON grants.grant_id = sources.grant_id
                WHERE sources.source_id = ?
                """,
                (source_id,),
            ).fetchone()
            if source is None:
                raise KeyError(source_id)
            if (
                source["status"] == "authorized"
                and source["owner_confirmed"]
                and source["expires_at"] is not None
                and source["expires_at"] <= now
            ):
                connection.execute(
                    "UPDATE automatic_memory_sources SET status = 'expired' WHERE source_id = ?",
                    (source_id,),
                )
                expired = True
            if expired:
                active = None
            elif source["status"] != "authorized" or not source["owner_confirmed"]:
                raise PermissionError("source is not authorized for scanning")
            else:
                active = connection.execute(
                    """
                    SELECT * FROM automatic_memory_scans
                    WHERE source_id = ? AND status IN ('running', 'paused')
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    (source_id,),
                ).fetchone()
            if active is not None:
                return dict(active)
            if expired:
                failed = None
            else:
                failed = connection.execute(
                    """
                    SELECT 1 FROM automatic_memory_scans
                    WHERE source_id = ? AND status = 'failed' LIMIT 1
                    """,
                    (source_id,),
                ).fetchone()
            if failed is not None:
                raise ValueError("failed scan must be retried before starting a new scan")
            if not expired:
                connection.execute(
                    """
                    INSERT INTO automatic_memory_scans (
                        scan_id, source_id, status, cursor, progress, total,
                        last_error, recovery_token, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scan["scan_id"],
                        scan["source_id"],
                        scan["status"],
                        scan.get("cursor"),
                        int(scan.get("progress", 0)),
                        scan.get("total"),
                        scan.get("last_error"),
                        scan.get("recovery_token"),
                        scan["updated_at"],
                    ),
                )
                created = connection.execute(
                    "SELECT * FROM automatic_memory_scans WHERE scan_id = ?",
                    (scan["scan_id"],),
                ).fetchone()
            else:
                created = None
        if expired:
            raise PermissionError("source authorization has expired")
        return dict(created)

    def pause_automatic_memory_scan_atomic(
        self, scan_id: str, *, recovery_token: str, now: str
    ) -> dict[str, Any]:
        """Pause only while the source grant is active in the same transaction."""
        expired = False
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT scans.*, sources.status AS source_status,
                       grants.expires_at, grants.owner_confirmed
                FROM automatic_memory_scans AS scans
                JOIN automatic_memory_sources AS sources ON sources.source_id = scans.source_id
                JOIN automatic_memory_grants AS grants ON grants.grant_id = sources.grant_id
                WHERE scans.scan_id = ?
                """,
                (scan_id,),
            ).fetchone()
            if row is None:
                raise KeyError(scan_id)
            if (
                row["source_status"] == "authorized"
                and row["owner_confirmed"]
                and row["expires_at"] is not None
                and row["expires_at"] <= now
            ):
                connection.execute(
                    "UPDATE automatic_memory_sources SET status = 'expired' WHERE source_id = ?",
                    (row["source_id"],),
                )
                expired = True
            elif row["source_status"] != "authorized" or not row["owner_confirmed"]:
                raise PermissionError("source is not authorized for scanning")
            elif row["status"] not in {"running", "failed"}:
                raise ValueError(f"scan cannot be paused from {row['status']}")
            else:
                connection.execute(
                    """
                    UPDATE automatic_memory_scans
                    SET status = 'paused', recovery_token = ?, updated_at = ?
                    WHERE scan_id = ?
                    """,
                    (recovery_token, now, scan_id),
                )
                row = connection.execute(
                    "SELECT * FROM automatic_memory_scans WHERE scan_id = ?",
                    (scan_id,),
                ).fetchone()
        if expired:
            raise PermissionError("source authorization has expired")
        return dict(row)

    def retry_automatic_memory_scan_atomic(
        self, scan_id: str, *, now: str
    ) -> dict[str, Any]:
        """Retry only while the source grant is active in the same transaction."""
        expired = False
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT scans.*, sources.status AS source_status,
                       grants.expires_at, grants.owner_confirmed
                FROM automatic_memory_scans AS scans
                JOIN automatic_memory_sources AS sources ON sources.source_id = scans.source_id
                JOIN automatic_memory_grants AS grants ON grants.grant_id = sources.grant_id
                WHERE scans.scan_id = ?
                """,
                (scan_id,),
            ).fetchone()
            if row is None:
                raise KeyError(scan_id)
            if (
                row["source_status"] == "authorized"
                and row["owner_confirmed"]
                and row["expires_at"] is not None
                and row["expires_at"] <= now
            ):
                connection.execute(
                    "UPDATE automatic_memory_sources SET status = 'expired' WHERE source_id = ?",
                    (row["source_id"],),
                )
                expired = True
            elif row["source_status"] != "authorized" or not row["owner_confirmed"]:
                raise PermissionError("source is not authorized for scanning")
            elif row["status"] == "running":
                pass
            elif row["status"] in {"paused", "failed"}:
                connection.execute(
                    """
                    UPDATE automatic_memory_scans
                    SET status = 'running', last_error = NULL, updated_at = ?
                    WHERE scan_id = ?
                    """,
                    (now, scan_id),
                )
                row = connection.execute(
                    "SELECT * FROM automatic_memory_scans WHERE scan_id = ?",
                    (scan_id,),
                ).fetchone()
            else:
                raise ValueError(f"scan cannot be retried from {row['status']}")
        if expired:
            raise PermissionError("source authorization has expired")
        return dict(row)

    def revoke_automatic_memory_source_atomic(
        self, source_id: str, *, revoked_at: str, reason: str
    ) -> dict[str, Any]:
        """Revoke a source and cancel all resumable scans in one transaction."""
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            source = connection.execute(
                "SELECT * FROM automatic_memory_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            if source is None:
                raise KeyError(source_id)
            connection.execute(
                """
                UPDATE automatic_memory_sources
                SET status = 'revoked', revoked_at = ?
                WHERE source_id = ?
                """,
                (revoked_at, source_id),
            )
            connection.execute(
                """
                UPDATE automatic_memory_scans
                SET status = 'cancelled', last_error = ?, lease_id = NULL,
                    lease_owner_pid = NULL, lease_owner_thread = NULL,
                    lease_heartbeat_at = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE source_id = ? AND status IN ('running', 'paused', 'failed')
                """,
                (reason, revoked_at, source_id),
            )
            updated = connection.execute(
                "SELECT * FROM automatic_memory_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return dict(updated)

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
            "source_sentinel",
            "attempt",
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

    def acquire_automatic_memory_scan_lease(
        self,
        scan_id: str,
        lease_id: str,
        *,
        now: str | None = None,
        ttl_seconds: float = 30.0,
    ) -> dict[str, Any] | None:
        """Atomically acquire a scan lease, reclaiming only a dead owner."""

        timestamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        pid = os.getpid()
        thread_id = str(threading.get_ident())
        expires = self._lease_expiry(timestamp, ttl_seconds)
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
            if row is None:
                raise KeyError(scan_id)
            existing_pid = row["lease_owner_pid"]
            if row["lease_id"]:
                expired = not row["lease_expires_at"] or row["lease_expires_at"] <= timestamp
                owner_alive = False
                if not expired and existing_pid:
                    same_process_thread_alive = (
                        int(existing_pid) == pid
                        and str(row["lease_owner_thread"] or "")
                        in {str(thread.ident) for thread in threading.enumerate()}
                    )
                    try:
                        os.kill(int(existing_pid), 0)
                        owner_alive = True
                    except OSError:
                        owner_alive = False
                    owner_alive = owner_alive and not (
                        int(existing_pid) == pid and not same_process_thread_alive
                    )
                if owner_alive:
                    return None
            updated = connection.execute(
                """
                UPDATE automatic_memory_scans
                SET status = 'running', lease_id = ?, lease_owner_pid = ?,
                    lease_owner_thread = ?, lease_heartbeat_at = ?, lease_expires_at = ?,
                    attempt = attempt + 1,
                    last_error = NULL, updated_at = ?
                WHERE scan_id = ? AND status IN ('running', 'paused', 'failed')
                  AND (lease_id IS NULL OR lease_owner_pid IS NULL OR lease_owner_pid != ?
                       OR lease_owner_thread != ? OR lease_expires_at <= ?)
                """,
                (
                    str(lease_id), pid, thread_id, timestamp, expires, timestamp,
                    scan_id, pid, thread_id, timestamp,
                ),
            )
            if updated.rowcount != 1:
                return None
            current = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(current)

    def renew_automatic_memory_scan_lease(
        self,
        scan_id: str,
        lease_id: str,
        *,
        now: str | None = None,
        ttl_seconds: float = 30.0,
    ) -> dict[str, Any]:
        timestamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        expires = self._lease_expiry(timestamp, ttl_seconds)
        with self._lock, self._connection() as connection:
            updated = connection.execute(
                """
                UPDATE automatic_memory_scans
                SET lease_heartbeat_at = ?, lease_expires_at = ?, updated_at = ?
                WHERE scan_id = ? AND status = 'running' AND lease_id = ?
                """,
                (timestamp, expires, timestamp, scan_id, str(lease_id)),
            )
            if updated.rowcount != 1:
                raise LeaseLostError(f"scan lease lost: {scan_id}")
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(row)

    def update_automatic_memory_scan_owned(
        self, scan_id: str, lease_id: str, **values: Any
    ) -> dict[str, Any]:
        """Update checkpoint/progress only while this exact lease owns the row."""

        allowed = {
            "status",
            "cursor",
            "progress",
            "total",
            "last_error",
            "recovery_token",
            "source_sentinel",
            "attempt",
            "updated_at",
        }
        changes = {key: value for key, value in values.items() if key in allowed}
        if not changes:
            return self.renew_automatic_memory_scan_lease(scan_id, lease_id)
        changes["lease_heartbeat_at"] = values.get(
            "updated_at", datetime.now(timezone.utc).isoformat(timespec="seconds")
        )
        changes["lease_expires_at"] = self._lease_expiry(
            changes["lease_heartbeat_at"], 30.0
        )
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self._lock, self._connection() as connection:
            updated = connection.execute(
                f"""
                UPDATE automatic_memory_scans
                SET {assignments}
                WHERE scan_id = ? AND status = 'running' AND lease_id = ?
                """,
                (*changes.values(), scan_id, str(lease_id)),
            )
            if updated.rowcount != 1:
                raise LeaseLostError(f"scan lease lost: {scan_id}")
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(row)

    def finalize_automatic_memory_scan_lease(
        self, scan_id: str, lease_id: str, **values: Any
    ) -> dict[str, Any]:
        values["status"] = "completed"
        allowed = {"status", "cursor", "progress", "total", "last_error", "updated_at"}
        changes = {key: value for key, value in values.items() if key in allowed}
        changes["lease_id"] = None
        changes["lease_owner_pid"] = None
        changes["lease_owner_thread"] = None
        changes["lease_heartbeat_at"] = None
        changes["lease_expires_at"] = None
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self._lock, self._connection() as connection:
            updated = connection.execute(
                f"UPDATE automatic_memory_scans SET {assignments} "
                "WHERE scan_id = ? AND status = 'running' AND lease_id = ?",
                (*changes.values(), scan_id, str(lease_id)),
            )
            if updated.rowcount != 1:
                raise LeaseLostError(f"scan lease lost: {scan_id}")
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(row)

    def release_automatic_memory_scan_lease(
        self, scan_id: str, lease_id: str, *, now: str | None = None
    ) -> dict[str, Any]:
        timestamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock, self._connection() as connection:
            updated = connection.execute(
                """
                UPDATE automatic_memory_scans
                SET lease_id = NULL, lease_owner_pid = NULL,
                    lease_owner_thread = NULL, lease_heartbeat_at = NULL,
                    lease_expires_at = NULL, updated_at = ?
                WHERE scan_id = ? AND lease_id = ?
                """,
                (timestamp, scan_id, str(lease_id)),
            )
            if updated.rowcount != 1:
                raise LeaseLostError(f"scan lease lost: {scan_id}")
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(row)

    def list_automatic_memory_scan_items(self, scan_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT scan_id, source_id, relative_path, sentinel, status, updated_at
                FROM automatic_memory_scan_items
                WHERE scan_id = ? ORDER BY relative_path
                """,
                (scan_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_automatic_memory_scan_item_owned(
        self,
        scan_id: str,
        lease_id: str,
        *,
        source_id: str,
        relative_path: str,
        sentinel: str,
        status: str = "processed",
        now: str | None = None,
    ) -> dict[str, Any]:
        timestamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            owned = connection.execute(
                """
                SELECT scans.scan_id, scans.source_id
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
            if owned is None:
                raise LeaseLostError(f"scan lease lost or source revoked: {scan_id}")
            connection.execute(
                """
                INSERT INTO automatic_memory_scan_items
                    (scan_id, source_id, relative_path, sentinel, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(scan_id, relative_path) DO UPDATE SET
                    source_id = excluded.source_id,
                    sentinel = excluded.sentinel,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (scan_id, source_id, relative_path, sentinel, status, timestamp),
            )
            row = connection.execute(
                """
                SELECT scan_id, source_id, relative_path, sentinel, status, updated_at
                FROM automatic_memory_scan_items
                WHERE scan_id = ? AND relative_path = ?
                """,
                (scan_id, relative_path),
            ).fetchone()
        return dict(row)

    def commit_authorized_snapshot(
        self,
        scan_id: str,
        lease_id: str,
        source_id: str,
        commit_callback: Any,
    ) -> Any:
        """Linearize filesystem raw commit against source revoke in SQLite."""

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
                raise LeaseLostError(f"snapshot admission lost or source revoked: {scan_id}")
            return commit_callback()
