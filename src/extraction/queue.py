from __future__ import annotations

from datetime import datetime
from typing import Any

from ._queue_core import SQLiteExtractionQueue as _SQLiteExtractionQueue
from ._queue_core import TERMINAL_STATUSES


CANCELLABLE_STATUSES = ("queued", "retrying")
RETRYABLE_STATUSES = ("failed", "cancelled")


class SQLiteExtractionQueue(_SQLiteExtractionQueue):
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

    def list_page(
        self,
        *,
        status: str | None = None,
        source_type: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        normalized_limit = max(min(int(limit), 200), 1)
        normalized_offset = max(int(offset), 0)
        where, values = self._filters(status=status, source_type=source_type, q=q)
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM extraction_jobs{where} "
                "ORDER BY created_at DESC, job_id DESC LIMIT ? OFFSET ?",
                tuple(values + [normalized_limit, normalized_offset]),
            ).fetchall()
        return [
            parsed
            for row in rows
            if (parsed := self._parse_row(row)) is not None
        ]

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
        return self.list_page(status=status, limit=limit, offset=0)
