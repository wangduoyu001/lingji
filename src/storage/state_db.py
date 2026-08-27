from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from uuid import uuid4


class LeaseLostError(RuntimeError):
    """Raised when a stale worker attempts to mutate a newer scan lease."""


_PROCESS_INSTANCE_ID = uuid4().hex
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
                    lease_id TEXT,
                    lease_owner TEXT,
                    lease_heartbeat_at TEXT,
                    lease_expires_at TEXT,
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
                    created_at TEXT NOT NULL,
                    stable_event_id TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS promotion_operation_leases (
                    decision_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    lease_expires_at TEXT NOT NULL,
                    heartbeat_at TEXT NOT NULL
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
                    lease_owner_instance TEXT,
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
                    PRIMARY KEY(scan_id, relative_path),
                    FOREIGN KEY(scan_id) REFERENCES automatic_memory_scans(scan_id) ON DELETE CASCADE,
                    FOREIGN KEY(source_id) REFERENCES automatic_memory_sources(source_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_automatic_memory_scan_items_source
                    ON automatic_memory_scan_items(source_id, scan_id, relative_path);

                DROP TRIGGER IF EXISTS automatic_memory_source_status_fails_scans;

                CREATE TRIGGER automatic_memory_source_status_fails_scans
                AFTER UPDATE OF status ON automatic_memory_sources
                WHEN NEW.status IN ('unsupported', 'degraded', 'expired')
                BEGIN
                    UPDATE automatic_memory_scans
                    SET status = 'failed',
                        last_error = 'source status changed to ' || NEW.status,
                        lease_id = NULL, lease_owner_pid = NULL,
                        lease_owner_thread = NULL, lease_owner_instance = NULL,
                        lease_heartbeat_at = NULL, lease_expires_at = NULL,
                        scheduler_lease_id = NULL, scheduler_lease_owner = NULL,
                        scheduler_lease_heartbeat_at = NULL,
                        scheduler_lease_expires_at = NULL,
                        updated_at = strftime('%Y-%m-%dT%H:%M:%S','now')
                    WHERE source_id = NEW.source_id AND status = 'running';
                END;
                """
            )
            event_columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(events)").fetchall()}
            if "stable_event_id" not in event_columns:
                connection.execute("ALTER TABLE events ADD COLUMN stable_event_id TEXT NULL")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_events_stable_event_id ON events(stable_event_id) WHERE stable_event_id IS NOT NULL")
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
                ("lease_owner_instance", "TEXT"),
                ("lease_heartbeat_at", "TEXT"),
                ("lease_expires_at", "TEXT"),
                ("attempt", "INTEGER NOT NULL DEFAULT 0"),
                ("scheduler_lease_id", "TEXT"),
                ("scheduler_lease_owner", "TEXT"),
                ("scheduler_lease_heartbeat_at", "TEXT"),
                ("scheduler_lease_expires_at", "TEXT"),
            ):
                if name not in columns:
                    connection.execute(
                        f"ALTER TABLE automatic_memory_scans ADD COLUMN {name} {definition}"
                    )
            scheduler_columns = {
                str(row[1])
                for row in connection.execute(
                    "PRAGMA table_info(scheduler_jobs)"
                ).fetchall()
            }
            for name, definition in (
                ("lease_id", "TEXT"),
                ("lease_owner", "TEXT"),
                ("lease_heartbeat_at", "TEXT"),
                ("lease_expires_at", "TEXT"),
            ):
                if name not in scheduler_columns:
                    connection.execute(
                        f"ALTER TABLE scheduler_jobs ADD COLUMN {name} {definition}"
                    )

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat(timespec="seconds")

    @staticmethod
    def _lease_expiry(timestamp: str, ttl_seconds: float) -> str:
        value = datetime.fromisoformat(timestamp)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (value + timedelta(seconds=max(float(ttl_seconds), 0.1))).isoformat(
            timespec="microseconds"
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
                    SET interval_seconds = ?, min_mode = ?, enabled = ?, run_on_start = ?,
                        next_run_at = CASE WHEN ? = 1 THEN ? ELSE next_run_at END,
                        updated_at = ?
                    WHERE name = ?
                    """,
                    (
                        interval_seconds,
                        min_mode,
                        int(enabled),
                        int(run_on_start),
                        int(run_on_start),
                        self._iso(now),
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

    def claim_due_scheduler_jobs(
        self,
        owner: str,
        *,
        now: datetime | None = None,
        lease_seconds: float = 30.0,
        current_mode: str = "NORMAL",
    ) -> list[dict[str, Any]]:
        """Atomically reclaim stale jobs and claim each due job once.

        The claim is serialized by SQLite's write transaction, so separate
        CronScheduler instances sharing one StateDatabase cannot run the same
        due row concurrently.
        """
        now = now or datetime.now()
        now_text = self._iso(now)
        lease_id_prefix = f"{owner}-"
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE scheduler_jobs
                SET status = 'pending', lease_id = NULL, lease_owner = NULL,
                    lease_heartbeat_at = NULL, lease_expires_at = NULL,
                    next_run_at = CASE WHEN next_run_at <= ? THEN next_run_at ELSE ? END,
                    updated_at = ?
                WHERE status = 'running'
                  AND (lease_expires_at IS NULL OR lease_expires_at <= ?)
                """,
                (now_text, now_text, now_text, now_text),
            )
            rows = connection.execute(
                """
                SELECT * FROM scheduler_jobs
                WHERE enabled = 1 AND next_run_at <= ? AND status != 'running'
                ORDER BY next_run_at ASC
                """,
                (now_text,),
            ).fetchall()
            claimed: list[dict[str, Any]] = []
            for row in rows:
                required = str(row["min_mode"] or "NORMAL").upper()
                active = str(current_mode or "NORMAL").upper()
                if active == "EMERGENCY":
                    allowed = required == "EMERGENCY"
                elif active == "MAINTENANCE":
                    allowed = required in {"NORMAL", "MAINTENANCE"}
                else:
                    allowed = required == "NORMAL"
                if not allowed:
                    continue
                lease_id = f"{lease_id_prefix}{uuid4().hex}"
                lease_expires = self._lease_expiry(now_text, lease_seconds)
                connection.execute(
                    """
                    UPDATE scheduler_jobs
                    SET status = 'running', last_started_at = ?, last_error = NULL,
                        lease_id = ?, lease_owner = ?, lease_heartbeat_at = ?,
                        lease_expires_at = ?, updated_at = ?
                    WHERE name = ? AND status != 'running'
                    """,
                    (
                        now_text,
                        lease_id,
                        str(owner),
                        now_text,
                        lease_expires,
                        now_text,
                        row["name"],
                    ),
                )
                current = connection.execute(
                    "SELECT * FROM scheduler_jobs WHERE name = ?", (row["name"],)
                ).fetchone()
                if current is not None and current["lease_id"] == lease_id:
                    claimed.append(dict(current))
            return claimed

    def renew_scheduler_job_lease(
        self,
        name: str,
        owner: str,
        lease_id: str,
        *,
        lease_seconds: float = 30.0,
        now: datetime | None = None,
    ) -> bool:
        now = now or datetime.now()
        now_text = self._iso(now)
        with self._lock, self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE scheduler_jobs
                SET lease_heartbeat_at = ?, lease_expires_at = ?, updated_at = ?
                WHERE name = ? AND status = 'running' AND lease_owner = ? AND lease_id = ?
                """,
                (
                    now_text,
                    self._lease_expiry(now_text, lease_seconds),
                    now_text,
                    name,
                    str(owner),
                    str(lease_id),
                ),
            )
        return cursor.rowcount == 1

    def mark_job_started(self, name: str, now: datetime | None = None) -> None:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                UPDATE scheduler_jobs
                SET status = 'running', last_started_at = ?, last_error = NULL,
                    lease_id = NULL, lease_owner = NULL, lease_heartbeat_at = NULL,
                    lease_expires_at = NULL, updated_at = ?
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
        owner: str | None = None,
        lease_id: str | None = None,
    ) -> None:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT interval_seconds FROM scheduler_jobs WHERE name = ?", (name,)
            ).fetchone()
            if not row:
                return
            next_run = now + timedelta(seconds=float(row["interval_seconds"]))
            where = "name = ?"
            values: list[Any] = [
                "success" if success else "failed",
                self._iso(now),
                self._iso(next_run),
                None if success else str(error or "unknown error")[:1000],
                self._iso(now),
                name,
            ]
            if owner is not None and lease_id is not None:
                where += " AND status = 'running' AND lease_owner = ? AND lease_id = ?"
                values.extend([str(owner), str(lease_id)])
            connection.execute(
                f"""
                UPDATE scheduler_jobs
                SET status = ?, last_finished_at = ?, next_run_at = ?, last_error = ?,
                    lease_id = NULL, lease_owner = NULL, lease_heartbeat_at = NULL,
                    lease_expires_at = NULL, updated_at = ?
                WHERE {where}
                """,
                tuple(values),
            )

    def list_scheduler_jobs(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM scheduler_jobs ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def set_scheduler_jobs_enabled(self, prefix: str, enabled: bool) -> None:
        """Pause/resume one owner-owned job family without another scheduler."""
        with self._lock, self._connection() as connection:
            connection.execute(
                "UPDATE scheduler_jobs SET enabled = ?, updated_at = ? WHERE name LIKE ?",
                (
                    int(bool(enabled)),
                    self._iso(datetime.now()),
                    f"{prefix}%",
                ),
            )

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

    @staticmethod
    def _promotion_json(payload: Any, *, event_type: str | None = None) -> str:
        top_level = {"candidate_id", "decision_id", "memory_id", "content_hash", "policy_version", "state", "messages", "error_codes", "errors"}
        message_keys = {"message_id", "content_hash", "external_key"}
        external_keys = {"source_external_id", "conversation_external_id", "message_external_id"}
        forbidden = re.compile(r"(?:sk-[a-z0-9]|api[_ -]?key|token|secret|password|authorization|fixture|evaluator|exception|traceback)", re.I)

        string_fields = {"candidate_id", "decision_id", "memory_id", "content_hash", "policy_version", "state", "message_id", "source_external_id", "conversation_external_id", "message_external_id"}

        def check(value: Any, context: str = "top") -> None:
            if isinstance(value, Mapping):
                if context == "top":
                    allowed = top_level
                elif context == "message":
                    allowed = message_keys
                elif context == "external":
                    allowed = external_keys
                else:
                    raise ValueError("promotion_payload_schema_invalid")
                if any(str(name) not in allowed for name in value):
                    raise ValueError("promotion_payload_schema_invalid")
                if context == "message" and set(value) != message_keys:
                    raise ValueError("promotion_payload_schema_invalid")
                if context == "external" and set(value) != external_keys:
                    raise ValueError("promotion_payload_schema_invalid")
                for name, item in value.items():
                    if context == "top" and name == "messages":
                        child = "messages"
                    elif context == "message" and name == "external_key":
                        child = "external"
                    else:
                        child = "scalar"
                    if child == "scalar" and str(name) in string_fields and not isinstance(item, str):
                        raise ValueError("promotion_payload_schema_invalid")
                    check(item, child)
            elif isinstance(value, (list, tuple)):
                if context == "messages" and any(not isinstance(item, Mapping) for item in value):
                    raise ValueError("promotion_payload_schema_invalid")
                child = "message" if context == "messages" else "scalar"
                for item in value:
                    check(item, child)
            elif isinstance(value, str):
                normalized_path = value.replace("\\/", "/").replace("\\\\", "\\")
                if forbidden.search(value) or normalized_path.startswith(("/", "\\")) or re.match(r"^[a-z]:[\\/]", normalized_path, re.I):
                    raise ValueError("promotion_payload_forbidden_content")
            elif isinstance(value, float) and not math.isfinite(value):
                raise ValueError("promotion_payload_schema_invalid")
            elif value is not None and not isinstance(value, (bool, int, float)):
                raise ValueError("promotion_payload_schema_invalid")
        if isinstance(payload, Mapping):
            if "messages" in payload and not isinstance(payload["messages"], (list, tuple)):
                raise ValueError("promotion_payload_schema_invalid")
            for field in ("error_codes", "errors"):
                if field in payload and (not isinstance(payload[field], (list, tuple)) or any(not isinstance(item, str) for item in payload[field])):
                    raise ValueError("promotion_payload_schema_invalid")
            if event_type in {
                "memory_promotion_preparing", "memory_projection_activated",
                "memory_projection_rolled_back", "memory_projection_repair_required",
            } and any(not isinstance(payload.get(field), str) or not str(payload.get(field)).strip() for field in ("decision_id", "memory_id", "state")):
                raise ValueError("promotion_payload_schema_invalid")
        check(payload, "top")
        return json.dumps(payload if payload is not None else {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def _safe_promotion_payload(cls, payload: Any) -> dict[str, Any]:
        """Return the allowlisted, owner-safe shape used by ordinary audit events."""
        allowed = {
            "candidate_id", "decision_id", "memory_id", "title", "content", "memory_type",
            "importance", "privacy", "project_ids", "proposed_by", "source_refs", "evidence_refs",
            "content_hash", "metadata", "confidence", "authority", "source_kind", "extractor_version",
            "structured_content", "risk_flags", "provenance_errors", "status", "reason_codes",
            "policy_version", "mutation_performed", "error", "promotion_evidence", "state",
        }
        redacted = False
        forbidden = re.compile(r"(?:sk-[a-z0-9]|api[_ -]?key|token|secret|password|authorization|fixture|evaluator|exception|traceback)", re.I)

        def clean(value: Any, key: str = "") -> Any:
            nonlocal redacted
            key_text = str(key)
            if key_text.lower() in {"error", "errors", "exception", "traceback"}:
                redacted = True
                return None
            if re.search(r"token|secret|password|authorization|api[_ -]?key|fixture|path", key_text, re.I):
                redacted = True
                return None
            if isinstance(value, Mapping):
                output: dict[str, Any] = {}
                for name, item in value.items():
                    cleaned = clean(item, str(name))
                    if cleaned is not None:
                        output[str(name)] = cleaned
                return output
            if isinstance(value, (list, tuple, set)):
                return [item for item in (clean(item, key) for item in value) if item is not None]
            if isinstance(value, str):
                normalized = value.replace("\\/", "/").replace("\\\\", "\\")
                if forbidden.search(value) or normalized.startswith(("/", "\\")) or re.match(r"^[a-z]:[\\/]", normalized, re.I):
                    redacted = True
                    return "[redacted]"
                return value
            if value is None or isinstance(value, (bool, int, float)):
                return value
            redacted = True
            return None

        source = payload if isinstance(payload, Mapping) else {}
        output = {str(name): clean(item, str(name)) for name, item in source.items() if str(name) in allowed}
        output = {name: item for name, item in output.items() if item is not None}
        if redacted:
            codes = output.get("reason_codes")
            if not isinstance(codes, list):
                codes = list(codes) if isinstance(codes, tuple) else []
            if "promotion_payload_redacted" not in codes:
                codes.append("promotion_payload_redacted")
            output["reason_codes"] = codes
            output.pop("error", None)
        return output

    def append_promotion_event(self, event_type: str, entity_id: str | None, payload: Any) -> int:
        return self.append_event(event_type, "memory_candidate", entity_id, self._safe_promotion_payload(payload))

    def get_event(self, event_id: int | str) -> dict[str, Any] | None:
        with self._connection() as connection:
            if isinstance(event_id, int) or str(event_id).isdigit():
                row = connection.execute("SELECT * FROM events WHERE event_id=?", (int(event_id),)).fetchone()
            else:
                row = connection.execute("SELECT * FROM events WHERE stable_event_id=?", (str(event_id),)).fetchone()
        return dict(row) if row else None

    def record_promotion_event_once(
        self, decision_id: str, event_type: str, entity_id: str | None, payload: Any,
    ) -> str:
        decision = str(decision_id or "").strip()
        selected_type = str(event_type or "").strip()
        if not decision or not selected_type:
            raise ValueError("promotion event identity is required")
        stable_id = f"promotion:{decision}:{selected_type}"
        if selected_type in {"memory_projection_activated", "memory_projection_rolled_back", "memory_projection_repair_required"} and isinstance(payload, Mapping) and not payload.get("memory_id") and entity_id:
            payload = dict(payload)
            payload["memory_id"] = str(entity_id)
        body = self._promotion_json(payload, event_type=selected_type)
        terminal = {"memory_projection_activated", "memory_projection_rolled_back", "memory_projection_repair_required"}
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT * FROM events WHERE stable_event_id=?", (stable_id,)).fetchone()
            if existing is not None:
                if str(existing["event_type"]) != selected_type or str(existing["entity_id"] or "") != str(entity_id or "") or str(existing["payload_json"]) != body:
                    raise ValueError("promotion_event_conflict")
                return stable_id
            if selected_type in terminal:
                rows = connection.execute("SELECT event_type,payload_json FROM events WHERE entity_type='memory_candidate' AND event_type IN (?,?,?)", (*terminal,)).fetchall()
                for other in rows:
                    try:
                        prior = json.loads(str(other["payload_json"]))
                    except (TypeError, ValueError, json.JSONDecodeError):
                        prior = {}
                    if str(prior.get("decision_id") or "") == decision and str(other["event_type"]) != selected_type:
                        raise ValueError("promotion_terminal_conflict")
            connection.execute("INSERT INTO events(event_type,entity_type,entity_id,payload_json,created_at,stable_event_id) VALUES(?,?,?,?,?,?)", (selected_type, "memory_candidate", entity_id, body, datetime.now().isoformat(timespec="seconds"), stable_id))
        return stable_id

    def claim_promotion_lease(self, decision_id: str, owner_id: str, *, now: datetime | None = None, ttl_seconds: float = 60.0) -> bool:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("lease clock must be timezone-aware")
        decision, owner = str(decision_id or ""), str(owner_id or "")
        expiry = (now.astimezone(timezone.utc) + timedelta(seconds=max(float(ttl_seconds), 0.1))).isoformat()
        stamp = now.astimezone(timezone.utc).isoformat()
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT owner_id,lease_expires_at FROM promotion_operation_leases WHERE decision_id=?", (decision,)).fetchone()
            if row is not None:
                try:
                    existing_expiry = datetime.fromisoformat(str(row["lease_expires_at"]))
                    if existing_expiry.tzinfo is None:
                        return False
                except (TypeError, ValueError):
                    return False
                if existing_expiry > now.astimezone(timezone.utc) and str(row["owner_id"]) != owner:
                    return False
                connection.execute("UPDATE promotion_operation_leases SET owner_id=?,lease_expires_at=?,heartbeat_at=? WHERE decision_id=?", (owner, expiry, stamp, decision))
            else:
                connection.execute("INSERT INTO promotion_operation_leases(decision_id,owner_id,lease_expires_at,heartbeat_at) VALUES(?,?,?,?)", (decision, owner, expiry, stamp))
        return True

    def renew_promotion_lease(self, decision_id: str, owner_id: str, *, now: datetime | None = None, ttl_seconds: float = 60.0) -> bool:
        return self.claim_promotion_lease(decision_id, owner_id, now=now, ttl_seconds=ttl_seconds)

    def release_promotion_lease(self, decision_id: str, owner_id: str) -> bool:
        with self._lock, self._connection() as connection:
            cursor = connection.execute("DELETE FROM promotion_operation_leases WHERE decision_id=? AND owner_id=?", (str(decision_id), str(owner_id)))
            return bool(cursor.rowcount)

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

    def is_automatic_memory_source_authorized(
        self, source_id: str, *, now: str | None = None
    ) -> bool:
        timestamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT sources.source_id
                FROM automatic_memory_sources AS sources
                JOIN automatic_memory_grants AS grants ON grants.grant_id = sources.grant_id
                WHERE sources.source_id = ? AND sources.status = 'authorized'
                  AND grants.owner_confirmed = 1
                  AND (grants.expires_at IS NULL OR grants.expires_at > ?)
                """,
                (str(source_id), timestamp),
            ).fetchone()
        return row is not None

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

    def list_automatic_memory_scans(self, source_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM automatic_memory_scans"
        values: tuple[Any, ...] = ()
        if source_id is not None:
            query += " WHERE source_id = ?"
            values = (str(source_id),)
        query += " ORDER BY updated_at DESC, scan_id DESC"
        with self._connection() as connection:
            rows = connection.execute(query, values).fetchall()
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
                    SET status = 'paused', recovery_token = ?,
                        scheduler_lease_id = NULL, scheduler_lease_owner = NULL,
                        scheduler_lease_heartbeat_at = NULL,
                        scheduler_lease_expires_at = NULL, updated_at = ?
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
            return self._revoke_automatic_memory_source_on_connection(
                connection, source_id, revoked_at=revoked_at, reason=reason
            )

    @staticmethod
    def _revoke_automatic_memory_source_on_connection(
        connection: sqlite3.Connection,
        source_id: str,
        *,
        revoked_at: str,
        reason: str,
    ) -> dict[str, Any]:
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
                lease_owner_instance = NULL,
                lease_heartbeat_at = NULL, lease_expires_at = NULL,
                scheduler_lease_id = NULL, scheduler_lease_owner = NULL,
                scheduler_lease_heartbeat_at = NULL,
                scheduler_lease_expires_at = NULL, updated_at = ?
            WHERE source_id = ? AND status IN ('running', 'paused', 'failed')
            """,
            (reason, revoked_at, source_id),
        )
        # Snapshot jobs live in this same state database.  Cancellation is
        # part of the revoke transaction so a runner cannot claim an
        # admitted job after the authorization linearization point.
        jobs_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'extraction_jobs'"
        ).fetchone()
        if jobs_table is not None:
            job_columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(extraction_jobs)").fetchall()
            }
            if "automatic_memory_source_id" in job_columns:
                source_filter = "automatic_memory_source_id = ? OR (automatic_memory_source_id IS NULL AND json_extract(payload_json, '$.source_id') = ?)"
                source_params: tuple[Any, ...] = (source_id, source_id)
            else:
                source_filter = "json_extract(payload_json, '$.source_id') = ?"
                source_params = (source_id,)
            connection.execute(
                f"""
                UPDATE extraction_jobs
                SET status = 'cancelled', completed_at = ?, next_run_at = ?,
                    locked_at = NULL, locked_by = NULL, lease_token = NULL,
                    heartbeat_at = NULL, progress_message = 'source authorization revoked',
                    last_error = ?, updated_at = ?
                WHERE source_type = 'automatic_memory_snapshot'
                  AND ({source_filter})
                  AND status IN ('queued', 'retrying', 'running')
                """,
                (revoked_at, revoked_at, reason, revoked_at, *source_params),
            )
        updated = connection.execute(
            "SELECT * FROM automatic_memory_sources WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        return dict(updated)

    def update_automatic_memory_source(
        self, source_id: str, *, status: str, revoked_at: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE automatic_memory_sources
                SET status = ?, revoked_at = ?
                WHERE source_id = ?
                """,
                (status, revoked_at, source_id),
            )
            if status in {"unsupported", "degraded", "expired"} and reason:
                connection.execute(
                    """
                    UPDATE automatic_memory_scans
                    SET last_error = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%S','now')
                    WHERE source_id = ? AND status = 'failed'
                    """,
                    (str(reason)[:2000], source_id),
                )
            row = connection.execute(
                "SELECT * FROM automatic_memory_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        if row is None:
            raise KeyError(source_id)
        return dict(row)

    def claim_automatic_memory_scheduler_scan(
        self,
        scan_id: str,
        lease_id: str,
        lease_owner: str,
        *,
        now: str | None = None,
        ttl_seconds: float = 30.0,
    ) -> dict[str, Any] | None:
        """Claim the scheduler runner role for a scan in the shared state DB.

        SnapshotJobRunner has a separate scan lease.  A live snapshot lease is
        respected so a scheduler cannot invoke a second runner; an expired
        scheduler lease is reclaimable after an owner crash.
        """
        timestamp = now or datetime.now(timezone.utc).isoformat(timespec="microseconds")
        expires = self._lease_expiry(timestamp, ttl_seconds)
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
            if row is None:
                raise KeyError(scan_id)
            if row["status"] not in {"running", "paused", "failed"}:
                return None
            scheduler_expiry = row["scheduler_lease_expires_at"]
            if (
                row["scheduler_lease_id"]
                and scheduler_expiry
                and scheduler_expiry > timestamp
            ):
                return None
            snapshot_expiry = row["lease_expires_at"]
            if row["lease_id"] and snapshot_expiry and snapshot_expiry > timestamp:
                return None
            updated = connection.execute(
                """
                UPDATE automatic_memory_scans
                SET scheduler_lease_id = ?, scheduler_lease_owner = ?,
                    scheduler_lease_heartbeat_at = ?, scheduler_lease_expires_at = ?,
                    updated_at = ?
                WHERE scan_id = ? AND status IN ('running', 'paused', 'failed')
                  AND (scheduler_lease_id IS NULL OR scheduler_lease_expires_at IS NULL
                       OR scheduler_lease_expires_at <= ?)
                  AND (lease_id IS NULL OR lease_expires_at IS NULL
                       OR lease_expires_at <= ?)
                """,
                (
                    str(lease_id), str(lease_owner), timestamp, expires, timestamp,
                    scan_id, timestamp, timestamp,
                ),
            )
            if updated.rowcount != 1:
                return None
            current = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(current) if current is not None else None

    def renew_automatic_memory_scheduler_scan_lease(
        self,
        scan_id: str,
        lease_id: str,
        *,
        now: str | None = None,
        ttl_seconds: float = 30.0,
    ) -> bool:
        timestamp = now or datetime.now(timezone.utc).isoformat(timespec="microseconds")
        expires = self._lease_expiry(timestamp, ttl_seconds)
        with self._lock, self._connection() as connection:
            updated = connection.execute(
                """
                UPDATE automatic_memory_scans
                SET scheduler_lease_heartbeat_at = ?, scheduler_lease_expires_at = ?,
                    updated_at = ?
                WHERE scan_id = ? AND scheduler_lease_id = ?
                  AND status = 'running'
                  AND scheduler_lease_expires_at > ?
                """,
                (timestamp, expires, timestamp, scan_id, str(lease_id), timestamp),
            )
        return updated.rowcount == 1

    def release_automatic_memory_scheduler_scan_lease(
        self, scan_id: str, lease_id: str
    ) -> dict[str, Any] | None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        with self._lock, self._connection() as connection:
            connection.execute(
                """
                UPDATE automatic_memory_scans
                SET scheduler_lease_id = NULL, scheduler_lease_owner = NULL,
                    scheduler_lease_heartbeat_at = NULL,
                    scheduler_lease_expires_at = NULL, updated_at = ?
                WHERE scan_id = ? AND scheduler_lease_id = ?
                """,
                (timestamp, scan_id, str(lease_id)),
            )
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def complete_automatic_memory_scan_if_authorized(
        self, scan_id: str, *, progress: int, total: int
    ) -> dict[str, Any] | None:
        """Complete only the scan that still owns an active authorization.

        Revoke and this transition serialize on the same SQLite write lock;
        whichever commits first determines the truthful terminal state.
        """
        now = self._iso(datetime.now(timezone.utc))
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE automatic_memory_scans
                SET status = 'completed', progress = ?, total = ?, last_error = NULL,
                    lease_id = NULL, lease_owner_pid = NULL, lease_owner_thread = NULL,
                    lease_owner_instance = NULL, lease_heartbeat_at = NULL,
                    lease_expires_at = NULL, scheduler_lease_id = NULL,
                    scheduler_lease_owner = NULL, scheduler_lease_heartbeat_at = NULL,
                    scheduler_lease_expires_at = NULL, updated_at = ?
                WHERE scan_id = ? AND status = 'running'
                  AND EXISTS (
                    SELECT 1
                    FROM automatic_memory_sources AS sources
                    JOIN automatic_memory_grants AS grants ON grants.grant_id = sources.grant_id
                    WHERE sources.source_id = automatic_memory_scans.source_id
                      AND sources.status = 'authorized'
                      AND grants.owner_confirmed = 1
                      AND (grants.expires_at IS NULL OR grants.expires_at > ?)
                  )
                """,
                (int(progress), int(total), now, scan_id, now),
            )
            if cursor.rowcount != 1:
                return None
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def fail_automatic_memory_scan_if_running(
        self,
        scan_id: str,
        *,
        last_error: str,
        progress: int | None = None,
        total: int | None = None,
    ) -> dict[str, Any] | None:
        now = self._iso(datetime.now(timezone.utc))
        assignments = [
            "status = 'failed'", "last_error = ?",
            "lease_id = NULL", "lease_owner_pid = NULL",
            "lease_owner_thread = NULL", "lease_owner_instance = NULL",
            "lease_heartbeat_at = NULL", "lease_expires_at = NULL",
            "scheduler_lease_id = NULL", "scheduler_lease_owner = NULL",
            "scheduler_lease_heartbeat_at = NULL",
            "scheduler_lease_expires_at = NULL", "updated_at = ?",
        ]
        values: list[Any] = [str(last_error)[:2000], now]
        if progress is not None:
            assignments.append("progress = ?")
            values.append(int(progress))
        if total is not None:
            assignments.append("total = ?")
            values.append(int(total))
        values.append(scan_id)
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                f"UPDATE automatic_memory_scans SET {', '.join(assignments)} "
                "WHERE scan_id = ? AND status = 'running'",
                tuple(values),
            )
            if cursor.rowcount != 1:
                return None
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(row) if row is not None else None

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
        if values.get("status") in {"paused", "failed", "cancelled", "completed"}:
            changes.update(
                {
                    "scheduler_lease_id": None,
                    "scheduler_lease_owner": None,
                    "scheduler_lease_heartbeat_at": None,
                    "scheduler_lease_expires_at": None,
                }
            )
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

        timestamp = now or datetime.now(timezone.utc).isoformat(timespec="microseconds")
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
                if not expired:
                    # TTL remains the safety boundary for an active owner.
                    # A process-death probe is only an early-reclaim hint;
                    # the instance UUID prevents a recycled PID from being
                    # mistaken for the original owner.
                    same_process_thread_alive = (
                        int(existing_pid or 0) == pid
                        and str(row["lease_owner_instance"] or "") == _PROCESS_INSTANCE_ID
                        and str(row["lease_owner_thread"] or "")
                        in {str(thread.ident) for thread in threading.enumerate()}
                    )
                    if same_process_thread_alive:
                        return None
                    if int(existing_pid or 0) == pid and str(row["lease_owner_instance"] or "") != _PROCESS_INSTANCE_ID:
                        return None
                    if int(existing_pid or 0) != pid:
                        try:
                            os.kill(int(existing_pid), 0)
                            return None
                        except OSError:
                            pass
            updated = connection.execute(
                """
                UPDATE automatic_memory_scans
                SET status = 'running', lease_id = ?, lease_owner_pid = ?,
                    lease_owner_thread = ?, lease_owner_instance = ?, lease_heartbeat_at = ?, lease_expires_at = ?,
                    attempt = attempt + 1,
                    last_error = NULL, updated_at = ?
                WHERE scan_id = ? AND status IN ('running', 'paused', 'failed')
                  AND (lease_id IS NULL OR lease_owner_pid IS NULL OR lease_owner_pid != ?
                       OR lease_owner_thread != ? OR lease_expires_at IS NULL
                       OR lease_expires_at <= ?)
                """,
                (
                    str(lease_id), pid, thread_id, _PROCESS_INSTANCE_ID, timestamp, expires, timestamp,
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
        timestamp = now or datetime.now(timezone.utc).isoformat(timespec="microseconds")
        expires = self._lease_expiry(timestamp, ttl_seconds)
        with self._lock, self._connection() as connection:
            updated = connection.execute(
                """
                UPDATE automatic_memory_scans
                SET lease_heartbeat_at = ?, lease_expires_at = ?, updated_at = ?
                WHERE scan_id = ? AND status = 'running' AND lease_id = ?
                  AND (lease_expires_at IS NULL OR lease_expires_at > ?)
                """,
                (timestamp, expires, timestamp, scan_id, str(lease_id), timestamp),
            )
            if updated.rowcount != 1:
                raise LeaseLostError(f"scan lease lost: {scan_id}")
            row = connection.execute(
                "SELECT * FROM automatic_memory_scans WHERE scan_id = ?", (scan_id,)
            ).fetchone()
        return dict(row)

    def update_automatic_memory_scan_owned(
        self, scan_id: str, lease_id: str, *, lease_ttl_seconds: float = 30.0, **values: Any
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
        if values.get("status") in {"paused", "failed", "cancelled", "completed"}:
            changes.update(
                {
                    "scheduler_lease_id": None,
                    "scheduler_lease_owner": None,
                    "scheduler_lease_heartbeat_at": None,
                    "scheduler_lease_expires_at": None,
                }
            )
        if not changes:
            return self.renew_automatic_memory_scan_lease(
                scan_id, lease_id, ttl_seconds=lease_ttl_seconds
            )
        changes["lease_heartbeat_at"] = values.get(
            "updated_at", datetime.now(timezone.utc).isoformat(timespec="microseconds")
        )
        changes["lease_expires_at"] = self._lease_expiry(
            changes["lease_heartbeat_at"], lease_ttl_seconds
        )
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self._lock, self._connection() as connection:
            updated = connection.execute(
                f"""
                UPDATE automatic_memory_scans
                SET {assignments}
                WHERE scan_id = ? AND status = 'running' AND lease_id = ?
                  AND (lease_expires_at IS NULL OR lease_expires_at > ?)
                """,
                (*changes.values(), scan_id, str(lease_id), changes["lease_heartbeat_at"]),
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
        timestamp = values.get(
            "updated_at", datetime.now(timezone.utc).isoformat(timespec="microseconds")
        )
        allowed = {"status", "cursor", "progress", "total", "last_error", "updated_at"}
        changes = {key: value for key, value in values.items() if key in allowed}
        changes["lease_id"] = None
        changes["lease_owner_pid"] = None
        changes["lease_owner_thread"] = None
        changes["lease_owner_instance"] = None
        changes["lease_heartbeat_at"] = None
        changes["lease_expires_at"] = None
        changes["scheduler_lease_id"] = None
        changes["scheduler_lease_owner"] = None
        changes["scheduler_lease_heartbeat_at"] = None
        changes["scheduler_lease_expires_at"] = None
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self._lock, self._connection() as connection:
            updated = connection.execute(
                f"""UPDATE automatic_memory_scans SET {assignments}
                WHERE scan_id = ? AND status = 'running' AND lease_id = ?
                  AND (lease_expires_at IS NULL OR lease_expires_at > ?)""",
                (*changes.values(), scan_id, str(lease_id), timestamp),
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
                    lease_owner_thread = NULL, lease_owner_instance = NULL,
                    lease_heartbeat_at = NULL,
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

    def cleanup_automatic_memory_scan_manifest(self, scan_id: str) -> int:
        """Delete per-path recovery rows only for a retired scan.

        Completed/cancelled scans no longer need path sentinels.  Running and
        paused scans are retained so recovery cannot lose its durable cursor.
        """
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT status FROM automatic_memory_scans WHERE scan_id = ?",
                (scan_id,),
            ).fetchone()
            if row is None:
                raise KeyError(scan_id)
            if str(row["status"]) not in {"completed", "cancelled"}:
                raise ValueError(
                    "automatic-memory scan manifest cleanup requires completed or cancelled status"
                )
            cursor = connection.execute(
                "DELETE FROM automatic_memory_scan_items WHERE scan_id = ?", (scan_id,)
            )
            connection.execute(
                """
                INSERT INTO events(event_type, entity_type, entity_id, payload_json, created_at)
                VALUES ('automatic_memory_manifest_cleaned', 'automatic_memory_scan', ?, ?, ?)
                """,
                (
                    scan_id,
                    self._json({"deleted_items": int(cursor.rowcount), "reason": "retention"}),
                    datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                ),
            )
            return int(cursor.rowcount)

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
                  AND (scans.lease_expires_at IS NULL OR scans.lease_expires_at > ?)
                """,
                (
                    scan_id,
                    str(lease_id),
                    source_id,
                    datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                    datetime.now(timezone.utc).isoformat(timespec="microseconds"),
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
                  AND (scans.lease_expires_at IS NULL OR scans.lease_expires_at > ?)
                """,
                (
                    scan_id,
                    str(lease_id),
                    source_id,
                    datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                    datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                ),
            ).fetchone()
            if authorized is None:
                raise LeaseLostError(f"snapshot admission lost or source revoked: {scan_id}")
            return commit_callback()
