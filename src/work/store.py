from __future__ import annotations

import json
import sqlite3
from typing import Any

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
                return
            connection.execute("INSERT OR IGNORE INTO pending_actions(work_id, description, resolved, action_id, actor, created_at) VALUES (?, ?, ?, ?, ?, ?)", (action.work_id, action.description, int(action.resolved), action.action_id, action.actor, action.created_at))

    def resolve_pending(self, work_id: str) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0", (work_id,))

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
                    self.save_outcome(Outcome(work_id=work.work_id, status="completed", summary=summary, evidence={"job_id": str(row[0]), "source_type": str(row[2] or "")}, created_at=str(row[5] or "")))
                    self.append_event(ExecutionEvent(work_id=work.work_id, event_id=f"work:{work.work_id}:extraction.completed", event_type="extraction.completed", detail={"summary": summary}, created_at=str(row[5] or "")))
                    self.resolve_pending(work.work_id)
                    self.save_next_action(NextAction(work_id=work.work_id, action_id=f"next:{work.work_id}:completed", description="系统继续维护可检索记忆", actor="system"))
                else:
                    reason = "提取失败，灵机无法安全完成这条输入"
                    failure = Failure(work_id=work.work_id, failure_id=f"failure:{work.work_id}:extraction", stage="extraction", reason=reason, retryable=False, created_at=str(row[5] or ""))
                    self.save_failure(failure)
                    self.save_outcome(Outcome(work_id=work.work_id, status="failed", summary=reason, evidence={"job_id": str(row[0]), "source_type": str(row[2] or "")}, created_at=failure.created_at))
                    self.append_event(ExecutionEvent(work_id=work.work_id, event_id=f"work:{work.work_id}:failed:extraction", event_type="work.failed", detail={"stage": "extraction", "reason": reason}, created_at=failure.created_at))
                    self.add_pending_action(PendingAction(action_id=f"owner-failure:{work.work_id}", work_id=work.work_id, description="查看提取失败原因并决定下一步", actor="owner", created_at=failure.created_at))
                    self.save_next_action(NextAction(work_id=work.work_id, action_id=f"next:{work.work_id}:failed", description="等待主人查看失败原因", actor="owner", created_at=failure.created_at))
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
