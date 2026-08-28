from __future__ import annotations

import json
import hashlib
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Collection, Iterator, Mapping
from uuid import uuid4

from .idempotency import extraction_key_for_request
from src.storage.state_db import LeaseLostError

TERMINAL_STATUSES = ("completed", "failed", "cancelled")
CANCELLABLE_STATUSES = ("queued", "retrying")
RETRYABLE_STATUSES = ("failed", "cancelled")
_LEASE_SENSITIVE_KEYS = frozenset(
    {
        "lease_token",
        "last_claim_lease_fingerprint",
        # Explicit wire/internal spellings only.  Do not broaden this to
        # generic ``token``/``secret`` keys: queue payloads can contain chat.
        "claim_lease_token",
        "claim_lease_fingerprint",
        "leasetoken",
        "lastclaimleasefingerprint",
        "claimleasetoken",
        "claimleasefingerprint",
    }
)
_LEASE_SCRUB_MAX_DEPTH = 32
_LEASE_SCRUB_MAX_NODES = 10_000
_LEASE_SCRUB_MAX_STRING = 1_000_000


def _without_lease_material(value: Any, *, redact_values: tuple[str, ...] = ()) -> Any:
    """Recursively scrub explicit lease material without serializing by repr.

    This is shared by persistence and public DTO boundaries.  Traversal is
    bounded and cycle-safe so hostile adapter payloads cannot recurse forever;
    bounded branches fail closed with a redaction marker.  Only explicit lease
    field names are removed.  Ordinary text is changed only when it contains a
    token/fingerprint supplied by the caller as known material.
    """

    known = tuple(
        sorted(
            {str(item) for item in redact_values if str(item)},
            key=len,
            reverse=True,
        )
    )
    state = {"nodes": 0}

    def scrub(item: Any, *, depth: int, active: set[int]) -> Any:
        if depth > _LEASE_SCRUB_MAX_DEPTH or state["nodes"] >= _LEASE_SCRUB_MAX_NODES:
            return "[REDACTED]"
        state["nodes"] += 1
        if isinstance(item, str):
            result = item
            for secret in known:
                result = result.replace(secret, "[REDACTED]")
            if len(result) > _LEASE_SCRUB_MAX_STRING:
                return "[REDACTED]"
            return result
        if isinstance(item, Mapping):
            identity = id(item)
            if identity in active:
                return "[REDACTED]"
            active.add(identity)
            try:
                output: dict[Any, Any] = {}
                for key, child in item.items():
                    if state["nodes"] >= _LEASE_SCRUB_MAX_NODES:
                        output["[REDACTED]"] = "[REDACTED]"
                        break
                    normalized_key = str(key).strip().lower().replace("-", "_")
                    if normalized_key in _LEASE_SENSITIVE_KEYS:
                        continue
                    output[key] = scrub(child, depth=depth + 1, active=active)
                return output
            finally:
                active.remove(identity)
        if isinstance(item, list):
            identity = id(item)
            if identity in active:
                return "[REDACTED]"
            active.add(identity)
            try:
                output: list[Any] = []
                for child in item:
                    if state["nodes"] >= _LEASE_SCRUB_MAX_NODES:
                        output.append("[REDACTED]")
                        break
                    output.append(scrub(child, depth=depth + 1, active=active))
                return output
            finally:
                active.remove(identity)
        if isinstance(item, tuple):
            identity = id(item)
            if identity in active:
                return "[REDACTED]"
            active.add(identity)
            try:
                output: list[Any] = []
                for child in item:
                    if state["nodes"] >= _LEASE_SCRUB_MAX_NODES:
                        output.append("[REDACTED]")
                        break
                    output.append(scrub(child, depth=depth + 1, active=active))
                return tuple(output)
            finally:
                active.remove(identity)
        # Keep the existing json serializer boundary for unknown objects; in
        # particular, never call repr() and accidentally persist a secret.
        return item

    return scrub(value, depth=0, active=set())


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
                    automatic_memory_source_id TEXT,
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

                """
            )
            self._ensure_columns(connection)
            connection.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_extraction_jobs_due
                    ON extraction_jobs(status, next_run_at, priority, created_at);
                CREATE INDEX IF NOT EXISTS idx_extraction_jobs_source
                    ON extraction_jobs(source_type, created_at);
                CREATE INDEX IF NOT EXISTS idx_extraction_jobs_lease
                    ON extraction_jobs(status, heartbeat_at, locked_at);
                """
            )

    @staticmethod
    def _ensure_columns(connection: sqlite3.Connection) -> None:
        existing = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(extraction_jobs)").fetchall()
        }
        columns = {
            "automatic_memory_source_id": "TEXT",
            "adapter_version": "TEXT NOT NULL DEFAULT ''",
            "lease_token": "TEXT",
            "last_claim_lease_fingerprint": "TEXT",
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
    def _json(value: Any, *, known_material: tuple[str, ...] = ()) -> str:
        scrubbed = _without_lease_material(
            value if value is not None else {}, redact_values=known_material
        )
        return json.dumps(scrubbed, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _parse_row(
        row: sqlite3.Row | None,
        *,
        include_lease: bool = False,
    ) -> dict[str, Any] | None:
        if row is None:
            return None
        result = dict(row)
        lease_values = tuple(
            str(result.get(key) or "")
            for key in ("lease_token", "last_claim_lease_fingerprint")
        )
        for key in ("payload_json", "options_json", "result_json"):
            raw = result.pop(key, None)
            target = key.removesuffix("_json")
            if raw:
                try:
                    result[target] = _without_lease_material(
                        json.loads(raw), redact_values=lease_values
                    )
                except json.JSONDecodeError:
                    result[target] = {}
            else:
                result[target] = {}
        if result.get("last_error") is not None:
            result["last_error"] = _without_lease_material(
                str(result["last_error"]), redact_values=lease_values
            )
        if not include_lease:
            result.pop("lease_token", None)
            result.pop("last_claim_lease_fingerprint", None)
        else:
            # The current plaintext token is needed only by the worker claim
            # path. Durable fingerprints stay inside ownership_receipt().
            result.pop("last_claim_lease_fingerprint", None)
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
        automatic_memory_source_id = None
        if source_type == "automatic_memory_snapshot" and payload:
            automatic_memory_source_id = str(payload.get("source_id") or "") or None
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
                        automatic_memory_source_id = ?,
                        payload_json = ?, options_json = ?, status = 'queued', priority = ?,
                        attempts = 0, max_attempts = ?, next_run_at = ?, locked_at = NULL,
                        locked_by = NULL, lease_token = NULL, last_claim_lease_fingerprint = NULL, heartbeat_at = NULL,
                        progress_current = 0, progress_total = 0, progress_message = NULL,
                        last_error = NULL, result_json = NULL, completed_at = NULL, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (
                        source_type,
                        adapter_name,
                        adapter_version,
                        normalized_path,
                        automatic_memory_source_id,
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
                        automatic_memory_source_id,
                        payload_json, options_json, idempotency_key, status, priority,
                        max_attempts, next_run_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        source_type,
                        adapter_name,
                        adapter_version,
                        normalized_path,
                        automatic_memory_source_id,
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
        allowed_source_types: Collection[str] | None = None,
    ) -> dict[str, Any] | None:
        now = now or datetime.now()
        lease_token = uuid4().hex
        lease_fingerprint = self.lease_fingerprint(lease_token)
        if allowed_source_types is None:
            source_filter = "source_type <> 'automatic_memory_snapshot'"
            source_params: tuple[Any, ...] = ()
        else:
            types = tuple(sorted({str(value) for value in allowed_source_types}))
            if not types:
                source_filter = "1 = 0"
                source_params = ()
            else:
                source_filter = "source_type IN (" + ", ".join("?" for _ in types) + ")"
                source_params = types
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if job_id:
                row = connection.execute(
                    f"""
                    SELECT * FROM extraction_jobs
                    WHERE job_id = ? AND {source_filter}
                      AND status IN ('queued', 'retrying') AND next_run_at <= ?
                    """,
                    (job_id, *source_params, self._iso(now)),
                ).fetchone()
            else:
                row = connection.execute(
                    f"""
                    SELECT * FROM extraction_jobs
                    WHERE {source_filter}
                      AND status IN ('queued', 'retrying') AND next_run_at <= ?
                    ORDER BY priority ASC, created_at ASC
                    LIMIT 1
                    """,
                    (*source_params, self._iso(now)),
                ).fetchone()
            if not row:
                return None
            updated = connection.execute(
                """
                UPDATE extraction_jobs
                SET status = 'running', attempts = attempts + 1, locked_at = ?, locked_by = ?,
                    lease_token = ?, last_claim_lease_fingerprint = ?, heartbeat_at = ?,
                    progress_message = 'started', updated_at = ?
                WHERE job_id = ? AND status IN ('queued', 'retrying')
                """,
                (
                    self._iso(now),
                    worker_id,
                    lease_token,
                    lease_fingerprint,
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
            return self._parse_row(claimed, include_lease=True)

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

    @staticmethod
    def lease_fingerprint(lease_token: str) -> str:
        """Return the non-reversible durable receipt for a random lease token."""

        return hashlib.sha256(str(lease_token).encode("utf-8")).hexdigest()

    def ownership_receipt(self, job_id: str, marker_lease_fingerprint: str) -> dict[str, Any]:
        """Read non-secret facts needed by transient cleanup."""

        candidate = str(marker_lease_fingerprint or "").lower()
        empty = {
            "status": "unknown",
            "input_path": None,
            "locked_by": None,
            "heartbeat_at": None,
            "locked_at": None,
            "current_lease_matches": False,
            "durable_lease_matches": False,
            "durable_lease_present": False,
        }
        if len(candidate) != 64 or any(char not in "0123456789abcdef" for char in candidate):
            return empty
        try:
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT status, input_path, locked_by, heartbeat_at, locked_at, lease_token, "
                    "last_claim_lease_fingerprint FROM extraction_jobs WHERE job_id = ?",
                    (job_id,),
                ).fetchone()
        except Exception:
            raise
        if row is None:
            return empty
        current = str(row["lease_token"] or "")
        durable = str(row["last_claim_lease_fingerprint"] or "").lower()
        return {
            "status": str(row["status"] or ""),
            "input_path": row["input_path"],
            "locked_by": row["locked_by"],
            "heartbeat_at": row["heartbeat_at"],
            "locked_at": row["locked_at"],
            "current_lease_matches": bool(current and self.lease_fingerprint(current) == candidate),
            "durable_lease_matches": bool(durable and durable == candidate),
            "durable_lease_present": bool(durable),
        }

    def _get_claimed_job_internal(self, job_id: str) -> dict[str, Any]:
        """Read one job for internal lease-owner operations only.

        This intentionally private seam is not used by public projections. It
        returns the existing plaintext current lease token, but never the
        durable fingerprint or any new sensitive field.
        """

        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM extraction_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        parsed = self._parse_row(row, include_lease=True)
        if parsed is None:
            raise LookupError(f"Unknown extraction job: {job_id}")
        return parsed

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
        identity: list[Any] = [job_id]
        if worker_id is not None or lease_token is not None:
            where += " AND locked_by = ? AND lease_token = ?"
            identity.extend([worker_id or "", lease_token or ""])
        with self._lock, self._connection() as connection:
            current = connection.execute(
                "SELECT lease_token, last_claim_lease_fingerprint FROM extraction_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            known_material = tuple(
                value
                for value in (
                    str(current["lease_token"] or "") if current else "",
                    str(current["last_claim_lease_fingerprint"] or "") if current else "",
                    str(lease_token or ""),
                )
                if value
            )
            # Scrub while the transaction still owns the current lease.  The
            # current token is cleared by the same UPDATE below.
            params: list[Any] = [
                self._json(result, known_material=known_material),
                self._iso(now),
                self._iso(now),
            ]
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
        terminal: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT attempts, max_attempts, locked_by, lease_token, last_claim_lease_fingerprint, status "
                "FROM extraction_jobs WHERE job_id = ?",
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
            should_retry = not terminal and attempts < max_attempts
            delay = retry_delay_seconds
            if delay is None:
                delay = min(60 * (2 ** max(attempts - 1, 0)), 3600)
            next_run = now + timedelta(seconds=max(int(delay), 0))
            known_material = tuple(
                value
                for value in (
                    str(row["lease_token"] or ""),
                    str(lease_token or ""),
                    str(row["last_claim_lease_fingerprint"] or ""),
                )
                if value
            )
            scrubbed_error = self._json(
                str(error), known_material=known_material
            )
            # _json returns a JSON string; decode the scrubbed scalar so the
            # SQLite error column remains the established plain-text shape.
            scrubbed_error = str(json.loads(scrubbed_error))[:2000]
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
                    scrubbed_error,
                    "retrying" if should_retry else "failed",
                    self._iso(now),
                    job_id,
                ),
            )
        return self.get(job_id)

    def release_claim(self, job_id: str, *, worker_id: str, lease_token: str) -> dict[str, Any]:
        """Return a claimed job to queued when admission is temporarily absent."""
        now = datetime.now()
        with self._lock, self._connection() as connection:
            updated = connection.execute(
                """UPDATE extraction_jobs SET status='queued', locked_at=NULL, locked_by=NULL,
                   lease_token=NULL, heartbeat_at=NULL, progress_message='awaiting authorization', updated_at=?
                   WHERE job_id=? AND status='running' AND locked_by=? AND lease_token=?""",
                (self._iso(now), job_id, worker_id, lease_token),
            )
            if updated.rowcount != 1:
                raise RuntimeError(f"Extraction lease lost before release: {job_id}")
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

    def cancel_running(
        self,
        job_id: str,
        *,
        worker_id: str,
        lease_token: str,
        reason: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Cancel an executing job when authorization is revoked."""
        now = now or datetime.now()
        with self._lock, self._connection() as connection:
            current = connection.execute(
                "SELECT lease_token, last_claim_lease_fingerprint FROM extraction_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            known_material = tuple(
                value
                for value in (
                    str(current["lease_token"] or "") if current else "",
                    str(current["last_claim_lease_fingerprint"] or "") if current else "",
                    str(lease_token or ""),
                )
                if value
            )
            scrubbed_reason = _without_lease_material(
                str(reason), redact_values=known_material
            )
            cursor = connection.execute(
                """
                UPDATE extraction_jobs
                SET status = 'cancelled', completed_at = ?, next_run_at = ?,
                    locked_at = NULL, locked_by = NULL, lease_token = NULL,
                    heartbeat_at = NULL, progress_message = 'cancelled',
                    last_error = ?, updated_at = ?
                WHERE job_id = ? AND status = 'running' AND locked_by = ? AND lease_token = ?
                """,
                (
                    self._iso(now),
                    self._iso(now),
                    str(scrubbed_reason)[:2000],
                    self._iso(now),
                    job_id,
                    worker_id,
                    lease_token,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Extraction job lease lost before cancellation")
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
                    lease_token = NULL, last_claim_lease_fingerprint = NULL, heartbeat_at = NULL, progress_current = 0,
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
        source_type: str = "",
    ) -> dict[str, Any]:
        """Insert a snapshot job while serializing against source revoke."""

        from .idempotency import build_snapshot_idempotency_key

        now = datetime.now()
        key = build_snapshot_idempotency_key(source_id, relative_path, sha256)
        job_id = f"LJ-JOB-{uuid4().hex[:12].upper()}"
        normalized_path = str(Path(input_path).expanduser())
        payload = {
            "scan_id": scan_id,
            "source_id": source_id,
            "relative_path": relative_path,
            "raw_id": raw_id,
            "sha256": sha256,
            "source_type": str(source_type or ""),
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
                raise LeaseLostError(f"queue admission lost or source revoked: {scan_id}")
            existing = connection.execute(
                "SELECT * FROM extraction_jobs WHERE idempotency_key = ?", (key,)
            ).fetchone()
            if existing is not None:
                return {**self._parse_row(existing), "existing_job": True}
            connection.execute(
                """
                INSERT INTO extraction_jobs (
                    job_id, source_type, adapter_name, adapter_version, input_path,
                    automatic_memory_source_id,
                    payload_json, options_json, idempotency_key, status, priority,
                    max_attempts, next_run_at, created_at, updated_at
                ) VALUES (?, 'automatic_memory_snapshot', 'automatic_memory_snapshot', '1', ?, ?, ?, ?, ?, 'queued', 100, 1, ?, ?, ?)
                """,
                (
                    job_id,
                    normalized_path,
                    source_id,
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
        return {**self._parse_row(row), "existing_job": False}

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
