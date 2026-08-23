from __future__ import annotations

import json
from typing import Any

from src.storage.state_db import StateDatabase

from .models import ExecutionEvent, PendingAction, WorkItem


class WorkStore:
    """Persistence layer for real WorkItem facts.

    Work pages must project from this store instead of inventing UI state.
    """

    def __init__(self, state: StateDatabase):
        self.state = state
        self._init_tables()

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
                    created_at TEXT NOT NULL
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
                    evidence_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS pending_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    resolved INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    def create_work(self, item: Any) -> None:
        with self.state._connection() as connection:
            connection.execute(
                "INSERT INTO work_items VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item.work_id,
                    item.title,
                    item.source_id,
                    item.status,
                    int(item.owner_approved),
                    item.created_at,
                ),
            )

    def append_event(self, event: Any) -> None:
        with self.state._connection() as connection:
            connection.execute(
                "INSERT INTO execution_events VALUES (?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    event.work_id,
                    event.event_type,
                    json.dumps(event.detail, ensure_ascii=False),
                    event.created_at,
                ),
            )

    def save_outcome(self, outcome: Any) -> None:
        with the state._connection() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO work_outcomes VALUES (?, ?, ?, ?)",
                (
                    outcome.work_id,
                    outcome.status,
                    outcome.summary,
                    json.dumps(outcome.evidence, ensure_ascii=False),
                ),
            )

    def add_pending_action(self, action: Any) -> None:
        with self.state._connection() as connection:
            connection.execute(
                "INSERT INTO pending_actions(work_id, description, resolved) VALUES (?, ?, ?)",
                (action.work_id, action.description, int(action.resolved)),
            )

    def list_work(self, limit: int = 20) -> list[WorkItem]:
        with self.state._connection() as connection:
            rows = connection.execute(
                "SELECT work_id, title, source_id, status, owner_approved, created_at FROM work_items ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [WorkItem(work_id=r[0], title=r[1], source_id=r[2], status=r[3], owner_approved=bool(r[4]), created_at=r[5]) for r in rows]

    def list_events(self, work_id: str, limit: int = 100) -> list[ExecutionEvent]:
        with self.state._connection() as connection:
            rows = connection.execute(
                "SELECT event_id, event_type, detail_json, created_at FROM execution_events WHERE work_id = ? ORDER BY created_at DESC LIMIT ?",
                (work_id, limit),
            ).fetchall()
        return [ExecutionEvent(work_id=work_id, event_id=r[0], event_type=r[1], detail=json.loads(r[2]), created_at=r[3]) for r in rows]

    def list_pending(self, limit: int = 20) -> list[PendingAction]:
        with self.state._connection() as connection:
            rows = connection.execute(
                "SELECT work_id, description, resolved FROM pending_actions WHERE resolved = 0 ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [PendingAction(work_id=r[0], description=r[1], resolved=bool(r[2])) for r in rows]
