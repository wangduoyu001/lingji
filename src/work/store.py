from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable

from src.storage.state_db import StateDatabase

from .models import ExecutionEvent, NextAction, Outcome, PendingAction, WorkItem

WORK_STATUSES = {"pending", "accepted", "running", "completed", "failed", "skipped"}
OUTCOME_STATUSES = {"success", "failure", "skipped"}
WORK_ACTORS = {"system", "owner", "external", "none"}


class WorkStore:
    """SQLite persistence for owner-visible work facts.

    The store owns the durable WorkItem/Event/Outcome/NextAction/PendingAction
    contract. Desktop and API projections must read this store rather than
    reconstructing work semantics from generic runtime events or queue counts.
    """

    def __init__(self, state: StateDatabase):
        self.state = state
        self._init_tables()

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _columns(connection: Any, table: str) -> set[str]:
        return {str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})")}

    @classmethod
    def _add_column_if_missing(
        cls,
        connection: Any,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        if column not in cls._columns(connection, table):
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _init_tables(self) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS work_items (
                    work_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_id TEXT,
                    status TEXT NOT NULL,
                    owner_approved INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS execution_events (
                    event_id TEXT PRIMARY KEY,
                    work_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS work_outcomes (
                    work_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '{}',
                    completed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS next_actions (
                    work_id TEXT PRIMARY KEY,
                    actor TEXT NOT NULL,
                    description TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pending_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT,
                    work_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    reason TEXT,
                    resolved INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    resolved_at TEXT
                );
                """
            )

            # Non-destructive migration from the first Work Fact draft schema.
            self._add_column_if_missing(connection, "work_items", "updated_at", "TEXT")
            connection.execute(
                "UPDATE work_items SET updated_at = created_at "
                "WHERE updated_at IS NULL OR updated_at = ''"
            )

            self._add_column_if_missing(connection, "work_outcomes", "completed_at", "TEXT")
            connection.execute(
                """
                UPDATE work_outcomes
                SET completed_at = COALESCE(
                    (SELECT MAX(e.created_at)
                     FROM execution_events e
                     WHERE e.work_id = work_outcomes.work_id),
                    (SELECT w.updated_at
                     FROM work_items w
                     WHERE w.work_id = work_outcomes.work_id),
                    ?
                )
                WHERE completed_at IS NULL OR completed_at = ''
                """,
                (self._now(),),
            )

            self._add_column_if_missing(connection, "pending_actions", "action_id", "TEXT")
            self._add_column_if_missing(connection, "pending_actions", "reason", "TEXT")
            self._add_column_if_missing(connection, "pending_actions", "created_at", "TEXT")
            self._add_column_if_missing(connection, "pending_actions", "resolved_at", "TEXT")
            connection.execute(
                "UPDATE pending_actions SET action_id = 'legacy-' || id "
                "WHERE action_id IS NULL OR action_id = ''"
            )
            connection.execute(
                """
                UPDATE pending_actions
                SET created_at = COALESCE(
                    (SELECT w.created_at
                     FROM work_items w
                     WHERE w.work_id = pending_actions.work_id),
                    ?
                )
                WHERE created_at IS NULL OR created_at = ''
                """,
                (self._now(),),
            )

            connection.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_work_items_status_updated
                    ON work_items(status, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_execution_events_work_created
                    ON execution_events(work_id, created_at, event_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_actions_action_id
                    ON pending_actions(action_id);
                CREATE INDEX IF NOT EXISTS idx_pending_actions_resolved_created
                    ON pending_actions(resolved, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_pending_actions_work
                    ON pending_actions(work_id, resolved, created_at DESC);
                """
            )

    @staticmethod
    def _decode_dict(raw: Any) -> dict[str, Any]:
        try:
            value = json.loads(str(raw or "{}"))
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @classmethod
    def _work_from_row(cls, row: Any) -> WorkItem:
        return WorkItem(
            work_id=str(row["work_id"]),
            title=str(row["title"]),
            source_id=row["source_id"],
            status=str(row["status"]),
            owner_approved=bool(row["owner_approved"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"] or row["created_at"]),
        )

    @classmethod
    def _event_from_row(cls, row: Any) -> ExecutionEvent:
        return ExecutionEvent(
            event_id=str(row["event_id"]),
            work_id=str(row["work_id"]),
            event_type=str(row["event_type"]),
            detail=cls._decode_dict(row["detail_json"]),
            created_at=str(row["created_at"]),
        )

    @classmethod
    def _outcome_from_row(cls, row: Any) -> Outcome:
        return Outcome(
            work_id=str(row["work_id"]),
            status=str(row["status"]),
            summary=str(row["summary"]),
            evidence=cls._decode_dict(row["evidence_json"]),
            completed_at=str(row["completed_at"]),
        )

    @staticmethod
    def _next_action_from_row(row: Any) -> NextAction:
        return NextAction(
            work_id=str(row["work_id"]),
            actor=str(row["actor"]),
            description=str(row["description"]),
        )

    @staticmethod
    def _pending_from_row(row: Any) -> PendingAction:
        return PendingAction(
            action_id=str(row["action_id"]),
            work_id=str(row["work_id"]),
            description=str(row["description"]),
            reason=row["reason"],
            resolved=bool(row["resolved"]),
            created_at=str(row["created_at"]),
            resolved_at=row["resolved_at"],
        )

    @staticmethod
    def _limit(value: int, maximum: int = 200) -> int:
        return max(1, min(int(value), maximum))

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in WORK_STATUSES:
            raise ValueError(f"Unsupported work status: {status}")

    def create_work(self, item: WorkItem) -> WorkItem:
        self._validate_status(str(item.status))
        with self.state._lock, self.state._connection() as connection:
            connection.execute(
                """
                INSERT INTO work_items (
                    work_id, title, source_id, status, owner_approved, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.work_id,
                    item.title,
                    item.source_id,
                    item.status,
                    int(item.owner_approved),
                    item.created_at,
                    item.updated_at,
                ),
            )
        return item

    def get_work(self, work_id: str) -> WorkItem | None:
        with self.state._connection() as connection:
            row = connection.execute(
                "SELECT * FROM work_items WHERE work_id = ?",
                (work_id,),
            ).fetchone()
        return self._work_from_row(row) if row else None

    def list_work(
        self,
        *,
        limit: int = 20,
        statuses: Iterable[str] | None = None,
    ) -> list[WorkItem]:
        params: list[Any] = []
        where = ""
        if statuses is not None:
            normalized = tuple(dict.fromkeys(str(status) for status in statuses))
            for status in normalized:
                self._validate_status(status)
            if not normalized:
                return []
            where = f" WHERE status IN ({','.join('?' for _ in normalized)})"
            params.extend(normalized)
        params.append(self._limit(limit))
        with self.state._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM work_items{where} "
                "ORDER BY updated_at DESC, created_at DESC, work_id DESC LIMIT ?",
                tuple(params),
            ).fetchall()
        return [self._work_from_row(row) for row in rows]

    def update_work_status(
        self,
        work_id: str,
        status: str,
        *,
        updated_at: str | None = None,
    ) -> WorkItem:
        self._validate_status(status)
        timestamp = updated_at or self._now()
        with self.state._lock, self.state._connection() as connection:
            cursor = connection.execute(
                "UPDATE work_items SET status = ?, updated_at = ? WHERE work_id = ?",
                (status, timestamp, work_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"Unknown work item: {work_id}")
        item = self.get_work(work_id)
        if item is None:
            raise LookupError(f"Unknown work item: {work_id}")
        return item

    def append_event(self, event: ExecutionEvent) -> ExecutionEvent:
        with self.state._lock, self.state._connection() as connection:
            if not connection.execute(
                "SELECT 1 FROM work_items WHERE work_id = ?", (event.work_id,)
            ).fetchone():
                raise LookupError(f"Unknown work item: {event.work_id}")
            connection.execute(
                """
                INSERT INTO execution_events (
                    event_id, work_id, event_type, detail_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.work_id,
                    event.event_type,
                    json.dumps(event.detail, ensure_ascii=False, sort_keys=True),
                    event.created_at,
                ),
            )
            connection.execute(
                "UPDATE work_items SET updated_at = ? WHERE work_id = ?",
                (event.created_at, event.work_id),
            )
        return event

    def list_events(self, work_id: str, *, limit: int = 100) -> list[ExecutionEvent]:
        with self.state._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM execution_events
                WHERE work_id = ?
                ORDER BY created_at ASC, event_id ASC
                LIMIT ?
                """,
                (work_id, self._limit(limit, maximum=1000)),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def save_outcome(self, outcome: Outcome) -> Outcome:
        if str(outcome.status) not in OUTCOME_STATUSES:
            raise ValueError(f"Unsupported outcome status: {outcome.status}")
        work_status = {
            "success": "completed",
            "failure": "failed",
            "skipped": "skipped",
        }[str(outcome.status)]
        with self.state._lock, self.state._connection() as connection:
            cursor = connection.execute(
                "UPDATE work_items SET status = ?, updated_at = ? WHERE work_id = ?",
                (work_status, outcome.completed_at, outcome.work_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"Unknown work item: {outcome.work_id}")
            connection.execute(
                """
                INSERT INTO work_outcomes (
                    work_id, status, summary, evidence_json, completed_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(work_id) DO UPDATE SET
                    status = excluded.status,
                    summary = excluded.summary,
                    evidence_json = excluded.evidence_json,
                    completed_at = excluded.completed_at
                """,
                (
                    outcome.work_id,
                    outcome.status,
                    outcome.summary,
                    json.dumps(outcome.evidence, ensure_ascii=False, sort_keys=True),
                    outcome.completed_at,
                ),
            )
        return outcome

    def get_outcome(self, work_id: str) -> Outcome | None:
        with self.state._connection() as connection:
            row = connection.execute(
                "SELECT * FROM work_outcomes WHERE work_id = ?",
                (work_id,),
            ).fetchone()
        return self._outcome_from_row(row) if row else None

    def save_next_action(self, action: NextAction) -> NextAction:
        if str(action.actor) not in WORK_ACTORS:
            raise ValueError(f"Unsupported next-action actor: {action.actor}")
        with self.state._lock, self.state._connection() as connection:
            if not connection.execute(
                "SELECT 1 FROM work_items WHERE work_id = ?", (action.work_id,)
            ).fetchone():
                raise LookupError(f"Unknown work item: {action.work_id}")
            connection.execute(
                """
                INSERT INTO next_actions (work_id, actor, description)
                VALUES (?, ?, ?)
                ON CONFLICT(work_id) DO UPDATE SET
                    actor = excluded.actor,
                    description = excluded.description
                """,
                (action.work_id, action.actor, action.description),
            )
        return action

    def get_next_action(self, work_id: str) -> NextAction | None:
        with self.state._connection() as connection:
            row = connection.execute(
                "SELECT * FROM next_actions WHERE work_id = ?",
                (work_id,),
            ).fetchone()
        return self._next_action_from_row(row) if row else None

    def add_pending_action(self, action: PendingAction) -> PendingAction:
        with self.state._lock, self.state._connection() as connection:
            if not connection.execute(
                "SELECT 1 FROM work_items WHERE work_id = ?", (action.work_id,)
            ).fetchone():
                raise LookupError(f"Unknown work item: {action.work_id}")
            connection.execute(
                """
                INSERT INTO pending_actions (
                    action_id, work_id, description, reason, resolved, created_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.action_id,
                    action.work_id,
                    action.description,
                    action.reason,
                    int(action.resolved),
                    action.created_at,
                    action.resolved_at,
                ),
            )
        return action

    def list_pending(
        self,
        *,
        limit: int = 20,
        include_resolved: bool = False,
        work_id: str | None = None,
    ) -> list[PendingAction]:
        clauses: list[str] = []
        params: list[Any] = []
        if not include_resolved:
            clauses.append("resolved = 0")
        if work_id is not None:
            clauses.append("work_id = ?")
            params.append(work_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(self._limit(limit))
        with self.state._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM pending_actions{where} "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                tuple(params),
            ).fetchall()
        return [self._pending_from_row(row) for row in rows]

    def resolve_pending_action(
        self,
        action_id: str,
        *,
        resolved_at: str | None = None,
    ) -> PendingAction:
        timestamp = resolved_at or self._now()
        with self.state._lock, self.state._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE pending_actions
                SET resolved = 1, resolved_at = ?
                WHERE action_id = ?
                """,
                (timestamp, action_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"Unknown pending action: {action_id}")
            row = connection.execute(
                "SELECT * FROM pending_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f"Unknown pending action: {action_id}")
        return self._pending_from_row(row)
