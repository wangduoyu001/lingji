from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from src.storage.state_db import StateDatabase

from .models import ExecutionEvent, Failure, NextAction, Outcome, PendingAction, WorkItem


class WorkStore:
    """Durable Work Fact persistence backed by the existing StateDatabase."""

    def __init__(self, state: StateDatabase):
        self.state = state
        self._init_tables()

    def _init_tables(self) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS work_items (
                    work_id TEXT PRIMARY KEY, title TEXT NOT NULL, source_id TEXT,
                    status TEXT NOT NULL, owner_approved INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS execution_events (
                    event_id TEXT PRIMARY KEY, work_id TEXT NOT NULL, event_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS work_outcomes (
                    work_id TEXT PRIMARY KEY, status TEXT NOT NULL, summary TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '{}', created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS work_next_actions (
                    work_id TEXT PRIMARY KEY, action_id TEXT NOT NULL, description TEXT NOT NULL,
                    actor TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pending_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, work_id TEXT NOT NULL,
                    description TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0,
                    action_id TEXT, actor TEXT NOT NULL DEFAULT 'owner', created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS work_failures (
                    failure_id TEXT PRIMARY KEY, work_id TEXT NOT NULL, stage TEXT NOT NULL,
                    reason TEXT NOT NULL, retryable INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
                );
                """
            )
            for table, columns in {
                "work_items": {"updated_at": "TEXT"},
                "work_outcomes": {"created_at": "TEXT"},
                "pending_actions": {"action_id": "TEXT", "actor": "TEXT NOT NULL DEFAULT 'owner'", "created_at": "TEXT"},
            }.items():
                present = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
                for name, definition in columns.items():
                    if name not in present:
                        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
            connection.execute("UPDATE pending_actions SET action_id = 'legacy-' || id WHERE action_id IS NULL")
            connection.execute("UPDATE pending_actions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            connection.execute("UPDATE work_outcomes SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            duplicate_action_ids = connection.execute(
                "SELECT action_id FROM pending_actions GROUP BY action_id HAVING COUNT(*) > 1"
            ).fetchall()
            for duplicate in duplicate_action_ids:
                rows = connection.execute(
                    "SELECT id, resolved FROM pending_actions WHERE action_id = ? ORDER BY resolved ASC, id ASC",
                    (duplicate[0],),
                ).fetchall()
                for row in rows[1:]:
                    connection.execute("DELETE FROM pending_actions WHERE id = ?", (row[0],))
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_actions_action_id_unique ON pending_actions(action_id)"
            )
        self.reconcile_extraction_jobs()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _work(row: Any) -> WorkItem:
        return WorkItem(work_id=row[0], title=row[1], source_id=row[2], status=row[3], owner_approved=bool(row[4]), created_at=row[5], updated_at=row[6])

    def create_work(self, item: WorkItem) -> WorkItem:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("INSERT OR IGNORE INTO work_items(work_id, title, source_id, status, owner_approved, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (item.work_id, item.title, item.source_id, item.status, int(item.owner_approved), item.created_at, item.updated_at or item.created_at))
            row = connection.execute("SELECT work_id, title, source_id, status, owner_approved, created_at, updated_at FROM work_items WHERE work_id = ?", (item.work_id,)).fetchone()
        return self._work(row)

    def get_work(self, work_id: str) -> WorkItem | None:
        with self.state._connection() as connection:
            row = connection.execute("SELECT work_id, title, source_id, status, owner_approved, created_at, updated_at FROM work_items WHERE work_id = ?", (work_id,)).fetchone()
        return self._work(row) if row else None

    def get_work_by_source_id(self, source_id: str) -> WorkItem | None:
        with self.state._connection() as connection:
            row = connection.execute("SELECT work_id, title, source_id, status, owner_approved, created_at, updated_at FROM work_items WHERE source_id = ? ORDER BY created_at LIMIT 1", (source_id,)).fetchone()
        return self._work(row) if row else None

    def append_event(self, event: ExecutionEvent) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("INSERT OR IGNORE INTO execution_events(event_id, work_id, event_type, detail_json, created_at) VALUES (?, ?, ?, ?, ?)", (event.event_id, event.work_id, event.event_type, self._json(event.detail), event.created_at))
            connection.execute("UPDATE work_items SET updated_at = ? WHERE work_id = ?", (event.created_at, event.work_id))

    def save_outcome(self, outcome: Outcome) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("INSERT INTO work_outcomes(work_id, status, summary, evidence_json, created_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(work_id) DO UPDATE SET status=excluded.status, summary=excluded.summary, evidence_json=excluded.evidence_json, created_at=excluded.created_at", (outcome.work_id, outcome.status, outcome.summary, self._json(outcome.evidence), outcome.created_at))

    def get_outcome(self, work_id: str) -> Outcome | None:
        with self.state._connection() as connection:
            row = connection.execute("SELECT status, summary, evidence_json, created_at FROM work_outcomes WHERE work_id = ?", (work_id,)).fetchone()
        return Outcome(work_id=work_id, status=row[0], summary=row[1], evidence=json.loads(row[2] or "{}"), created_at=row[3] or "") if row else None

    def save_next_action(self, action: NextAction) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("INSERT INTO work_next_actions(work_id, action_id, description, actor, created_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(work_id) DO UPDATE SET action_id=excluded.action_id, description=excluded.description, actor=excluded.actor, created_at=excluded.created_at", (action.work_id, action.action_id, action.description, action.actor, action.created_at))

    def get_next_action(self, work_id: str) -> NextAction | None:
        with self.state._connection() as connection:
            row = connection.execute("SELECT action_id, description, actor, created_at FROM work_next_actions WHERE work_id = ?", (work_id,)).fetchone()
        return NextAction(work_id=work_id, action_id=row[0], description=row[1], actor=row[2], created_at=row[3]) if row else None

    def save_failure(self, failure: Failure) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("INSERT OR REPLACE INTO work_failures(failure_id, work_id, stage, reason, retryable, created_at) VALUES (?, ?, ?, ?, ?, ?)", (failure.failure_id, failure.work_id, failure.stage, failure.reason, int(failure.retryable), failure.created_at))

    def get_failure(self, work_id: str) -> Failure | None:
        with self.state._connection() as connection:
            row = connection.execute("SELECT failure_id, stage, reason, retryable, created_at FROM work_failures WHERE work_id = ? ORDER BY created_at DESC LIMIT 1", (work_id,)).fetchone()
        return Failure(work_id=work_id, failure_id=row[0], stage=row[1], reason=row[2], retryable=bool(row[3]), created_at=row[4]) if row else None

    def add_pending_action(self, action: PendingAction) -> None:
        with self.state._lock, self.state._connection() as connection:
            existing = connection.execute("SELECT id FROM pending_actions WHERE action_id = ? LIMIT 1", (action.action_id,)).fetchone()
            if existing:
                connection.execute(
                    "UPDATE pending_actions SET work_id = ?, description = ?, resolved = ?, actor = ?, created_at = ? WHERE id = ?",
                    (action.work_id, action.description, int(action.resolved), action.actor, action.created_at, existing[0]),
                )
                return
            connection.execute("INSERT INTO pending_actions(work_id, description, resolved, action_id, actor, created_at) VALUES (?, ?, ?, ?, ?, ?)", (action.work_id, action.description, int(action.resolved), action.action_id, action.actor, action.created_at))

    def resolve_pending(self, work_id: str) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0", (work_id,))

    @staticmethod
    def _parse_transition_time(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _transition_rank(phase: str) -> int:
        return {"retrying": 1, "failed": 2, "completed": 3}[phase]

    def apply_extraction_transition(
        self,
        work_id: str,
        phase: Literal["retrying", "completed", "failed"],
        *,
        summary: str,
        evidence: Mapping[str, Any],
        stage: str = "extraction",
        retryable: bool = False,
        occurred_at: str | None = None,
    ) -> None:
        """Apply one idempotent extraction lifecycle transition atomically."""
        if phase not in {"retrying", "completed", "failed"}:
            raise ValueError(f"Unsupported extraction transition: {phase}")
        timestamp = occurred_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        incoming_time = self._parse_transition_time(timestamp)
        with self.state._lock, self.state._connection() as connection:
            if not connection.execute("SELECT 1 FROM work_items WHERE work_id = ?", (work_id,)).fetchone():
                raise LookupError(f"Unknown work item: {work_id}")

            outcome_row = connection.execute(
                "SELECT status, summary, evidence_json, created_at FROM work_outcomes WHERE work_id = ?",
                (work_id,),
            ).fetchone()
            current_phase: str | None = str(outcome_row[0]) if outcome_row else None
            current_timestamp = str(outcome_row[3] or "") if outcome_row else ""
            if current_phase not in {"failed", "completed"}:
                current_phase = None
            if current_phase is None:
                candidates: list[tuple[datetime, int, str, str, str]] = []
                for event in connection.execute(
                    """
                    SELECT event_id, event_type, created_at
                    FROM execution_events
                    WHERE work_id = ? AND event_type IN ('work.retrying', 'work.failed', 'extraction.completed')
                    """,
                    (work_id,),
                ).fetchall():
                    event_phase = {
                        "work.retrying": "retrying",
                        "work.failed": "failed",
                        "extraction.completed": "completed",
                    }[str(event[1])]
                    event_time = self._parse_transition_time(str(event[2] or ""))
                    if event_time is not None:
                        candidates.append((event_time, self._transition_rank(event_phase), str(event[0]), event_phase, str(event[2] or "")))
                if candidates:
                    _event_time, _rank, _event_id, current_phase, current_timestamp = max(candidates)

            current_time = self._parse_transition_time(current_timestamp)
            if current_time is not None and incoming_time is None:
                return
            if current_time is not None and incoming_time is not None:
                if incoming_time < current_time:
                    return
                if incoming_time == current_time and current_phase is not None:
                    if self._transition_rank(phase) < self._transition_rank(current_phase):
                        return

            evidence_json = self._json(dict(evidence))
            if phase == "retrying":
                connection.execute("DELETE FROM work_outcomes WHERE work_id = ?", (work_id,))
                connection.execute("UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0", (work_id,))
                connection.execute(
                    """
                    INSERT OR IGNORE INTO execution_events(event_id, work_id, event_type, detail_json, created_at)
                    VALUES (?, ?, 'work.retrying', ?, ?)
                    """,
                    (f"work:{work_id}:retrying", work_id, self._json({"summary": summary, "evidence": dict(evidence), "actor": "system"}), timestamp),
                )
                connection.execute(
                    """
                    INSERT INTO work_next_actions(work_id, action_id, description, actor, created_at)
                    VALUES (?, ?, ?, 'system', ?)
                    ON CONFLICT(work_id) DO UPDATE SET action_id=excluded.action_id, description=excluded.description, actor=excluded.actor, created_at=excluded.created_at
                    """,
                    (work_id, f"next:{work_id}:retrying", "系统自动重试提取", timestamp),
                )
            elif phase == "completed":
                connection.execute(
                    """
                    INSERT INTO work_outcomes(work_id, status, summary, evidence_json, created_at)
                    VALUES (?, 'completed', ?, ?, ?)
                    ON CONFLICT(work_id) DO UPDATE SET status='completed', summary=excluded.summary, evidence_json=excluded.evidence_json, created_at=excluded.created_at
                    """,
                    (work_id, summary, evidence_json, timestamp),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO execution_events(event_id, work_id, event_type, detail_json, created_at)
                    VALUES (?, ?, 'extraction.completed', ?, ?)
                    """,
                    (f"work:{work_id}:extraction.completed", work_id, self._json({"summary": summary, "evidence": dict(evidence)}), timestamp),
                )
                connection.execute("UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0", (work_id,))
                connection.execute(
                    """
                    INSERT INTO work_next_actions(work_id, action_id, description, actor, created_at)
                    VALUES (?, ?, ?, 'system', ?)
                    ON CONFLICT(work_id) DO UPDATE SET action_id=excluded.action_id, description=excluded.description, actor=excluded.actor, created_at=excluded.created_at
                    """,
                    (work_id, f"next:{work_id}:completed", "系统继续维护可检索记忆", timestamp),
                )
            else:
                failure_id = f"failure:{work_id}:{stage}"
                connection.execute(
                    """
                    INSERT OR REPLACE INTO work_failures(failure_id, work_id, stage, reason, retryable, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (failure_id, work_id, stage, summary, int(retryable), timestamp),
                )
                connection.execute(
                    """
                    INSERT INTO work_outcomes(work_id, status, summary, evidence_json, created_at)
                    VALUES (?, 'failed', ?, ?, ?)
                    ON CONFLICT(work_id) DO UPDATE SET status='failed', summary=excluded.summary, evidence_json=excluded.evidence_json, created_at=excluded.created_at
                    """,
                    (work_id, summary, evidence_json, timestamp),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO execution_events(event_id, work_id, event_type, detail_json, created_at)
                    VALUES (?, ?, 'work.failed', ?, ?)
                    """,
                    (f"work:{work_id}:failed:{stage}", work_id, self._json({"stage": stage, "reason": summary, "retryable": retryable, "evidence": dict(evidence)}), timestamp),
                )
                if retryable:
                    connection.execute("UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0", (work_id,))
                    action_id = f"next:{work_id}:retrying"
                    description = "重试处理"
                    actor = "system"
                else:
                    connection.execute("UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0", (work_id,))
                    owner_action_id = f"owner-failure:{work_id}"
                    updated = connection.execute(
                        """
                        UPDATE pending_actions
                        SET work_id = ?, description = ?, resolved = 0, actor = 'owner', created_at = ?
                        WHERE action_id = ?
                        """,
                        (work_id, "查看提取失败原因并决定下一步", timestamp, owner_action_id),
                    )
                    if updated.rowcount == 0:
                        connection.execute(
                            """
                            INSERT INTO pending_actions(work_id, description, resolved, action_id, actor, created_at)
                            VALUES (?, ?, 0, ?, 'owner', ?)
                            """,
                            (work_id, "查看提取失败原因并决定下一步", owner_action_id, timestamp),
                        )
                    action_id = f"next:{work_id}:failed"
                    description = "等待主人查看失败原因"
                    actor = "owner"
                connection.execute(
                    """
                    INSERT INTO work_next_actions(work_id, action_id, description, actor, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(work_id) DO UPDATE SET action_id=excluded.action_id, description=excluded.description, actor=excluded.actor, created_at=excluded.created_at
                    """,
                    (work_id, action_id, description, actor, timestamp),
                )
            connection.execute("UPDATE work_items SET updated_at = ? WHERE work_id = ?", (timestamp, work_id))

    def reconcile_extraction_jobs(self) -> None:
        """Replay terminal extraction facts after a crash between queue and callback."""
        try:
            with self.state._connection() as connection:
                rows = connection.execute(
                    "SELECT job_id, status, source_type, payload_json, result_json, updated_at FROM extraction_jobs WHERE status IN ('completed', 'failed') ORDER BY updated_at ASC, job_id ASC"
                ).fetchall()
        except sqlite3.Error:
            return
        for row in rows:
            try:
                payload = json.loads(row[3] or "{}")
                if not isinstance(payload, dict):
                    continue
                capture_id = str(payload.get("capture_id") or "").strip()
                if not capture_id:
                    continue
                work = self.get_work_by_source_id(capture_id)
                if work is None:
                    continue
                if row[1] == "completed":
                    result = json.loads(row[4] or "{}")
                    if not isinstance(result, dict):
                        result = {}
                    summary = self._safe_result_summary(result)
                    self.apply_extraction_transition(work.work_id, "completed", summary=summary, evidence={"job_id": str(row[0]), "source_type": str(row[2] or "")}, occurred_at=str(row[5] or ""))
                else:
                    reason = "提取失败，灵机无法安全完成这条输入"
                    self.apply_extraction_transition(work.work_id, "failed", summary=reason, evidence={"stage": "extraction", "job_id": str(row[0]), "source_type": str(row[2] or "")}, occurred_at=str(row[5] or ""))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue

    @staticmethod
    def _safe_result_summary(result: dict[str, Any]) -> str:
        allowed = ("execution_id", "source_type", "adapter", "adapter_version", "indexed", "document_count", "memory_count")
        summary = {key: result[key] for key in allowed if key in result and isinstance(result[key], (str, int, float, bool, type(None)))}
        return json.dumps(summary, ensure_ascii=False, sort_keys=True) if summary else "Extraction completed"

    def list_pending(self, limit: int = 20, *, work_id: str | None = None) -> list[PendingAction]:
        query = "SELECT action_id, work_id, description, resolved, actor, created_at FROM pending_actions WHERE resolved = 0"
        params: list[Any] = []
        if work_id:
            query += " AND work_id = ?"
            params.append(work_id)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(max(int(limit), 1))
        with self.state._connection() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [PendingAction(action_id=r[0], work_id=r[1], description=r[2], resolved=bool(r[3]), actor=r[4] or "owner", created_at=r[5] or "") for r in rows]

    def list_work(self, limit: int = 20) -> list[WorkItem]:
        with self.state._connection() as connection:
            rows = connection.execute("SELECT work_id, title, source_id, status, owner_approved, created_at, updated_at FROM work_items ORDER BY COALESCE(updated_at, created_at) DESC, work_id DESC LIMIT ?", (max(int(limit), 1),)).fetchall()
        return [self._work(r) for r in rows]

    def list_events(self, work_id: str, limit: int = 100) -> list[ExecutionEvent]:
        with self.state._connection() as connection:
            rows = connection.execute("SELECT event_id, event_type, detail_json, created_at FROM execution_events WHERE work_id = ? ORDER BY created_at DESC, event_id DESC LIMIT ?", (work_id, max(int(limit), 1))).fetchall()
        return [ExecutionEvent(work_id=work_id, event_id=r[0], event_type=r[1], detail=json.loads(r[2] or "{}"), created_at=r[3]) for r in rows]
