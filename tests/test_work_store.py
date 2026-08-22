from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.storage.state_db import StateDatabase
from src.work.models import ExecutionEvent, NextAction, Outcome, PendingAction, WorkItem
from src.work.store import WorkStore


class WorkStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "state.db"
        self.state = StateDatabase(self.path)
        self.store = WorkStore(self.state)

    def test_full_lifecycle_survives_reopen(self) -> None:
        work = WorkItem(
            work_id="work-1",
            title="记住一条测试信息",
            source_id="capture-1",
            status="accepted",
            owner_approved=True,
            created_at="2026-08-22T10:00:00",
            updated_at="2026-08-22T10:00:00",
        )
        self.store.create_work(work)
        self.store.append_event(
            ExecutionEvent(
                event_id="event-1",
                work_id=work.work_id,
                event_type="capture.accepted",
                detail={"capture_id": "capture-1"},
                created_at="2026-08-22T10:00:01",
            )
        )
        self.store.update_work_status(
            work.work_id,
            "running",
            updated_at="2026-08-22T10:00:02",
        )
        self.store.append_event(
            ExecutionEvent(
                event_id="event-2",
                work_id=work.work_id,
                event_type="extraction.started",
                detail={"stage": "extract"},
                created_at="2026-08-22T10:00:03",
            )
        )
        self.store.save_next_action(
            NextAction(work_id=work.work_id, actor="owner", description="确认候选记忆")
        )
        pending = PendingAction(
            action_id="action-1",
            work_id=work.work_id,
            description="确认候选记忆",
            reason="永久记忆需要主人批准",
            created_at="2026-08-22T10:00:04",
        )
        self.store.add_pending_action(pending)
        self.store.save_outcome(
            Outcome(
                work_id=work.work_id,
                status="success",
                summary="候选记忆已生成",
                evidence={"memory_id": "memory-1"},
                completed_at="2026-08-22T10:00:05",
            )
        )

        reopened = WorkStore(StateDatabase(self.path))
        restored = reopened.get_work(work.work_id)
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.status, "completed")
        self.assertEqual(restored.updated_at, "2026-08-22T10:00:05")
        self.assertEqual(
            [event.event_type for event in reopened.list_events(work.work_id)],
            ["capture.accepted", "extraction.started"],
        )
        outcome = reopened.get_outcome(work.work_id)
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertEqual(outcome.status, "success")
        self.assertEqual(outcome.evidence["memory_id"], "memory-1")
        next_action = reopened.get_next_action(work.work_id)
        self.assertIsNotNone(next_action)
        assert next_action is not None
        self.assertEqual(next_action.actor, "owner")
        self.assertEqual(reopened.list_pending()[0].action_id, "action-1")

    def test_pending_action_resolution_removes_owner_attention(self) -> None:
        self.store.create_work(WorkItem(work_id="work-2", title="需要确认"))
        action = PendingAction(
            action_id="action-2",
            work_id="work-2",
            description="确认",
            created_at="2026-08-22T10:01:00",
        )
        self.store.add_pending_action(action)
        self.assertEqual([item.action_id for item in self.store.list_pending()], ["action-2"])

        resolved = self.store.resolve_pending_action(
            "action-2", resolved_at="2026-08-22T10:02:00"
        )
        self.assertTrue(resolved.resolved)
        self.assertEqual(resolved.resolved_at, "2026-08-22T10:02:00")
        self.assertEqual(self.store.list_pending(), [])
        history = self.store.list_pending(include_resolved=True)
        self.assertEqual(len(history), 1)
        self.assertTrue(history[0].resolved)

    def test_latest_event_limit_is_chronological_and_does_not_regress_updated_at(self) -> None:
        self.store.create_work(
            WorkItem(
                work_id="work-3",
                title="事件排序",
                created_at="2026-08-22T10:00:00",
                updated_at="2026-08-22T10:00:00",
            )
        )
        for event_id, created_at in (
            ("event-c", "2026-08-22T10:00:30"),
            ("event-a", "2026-08-22T10:00:10"),
            ("event-b", "2026-08-22T10:00:20"),
        ):
            self.store.append_event(
                ExecutionEvent(
                    event_id=event_id,
                    work_id="work-3",
                    event_type=event_id,
                    created_at=created_at,
                )
            )

        events = self.store.list_events("work-3", limit=2)
        self.assertEqual([item.event_id for item in events], ["event-b", "event-c"])
        work = self.store.get_work("work-3")
        self.assertIsNotNone(work)
        assert work is not None
        self.assertEqual(work.updated_at, "2026-08-22T10:00:30")

    def test_legacy_draft_schema_migrates_without_data_loss(self) -> None:
        legacy_path = Path(self.temp_dir.name) / "legacy.db"
        legacy_state = StateDatabase(legacy_path)
        with legacy_state._lock, legacy_state._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE work_items (
                    work_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_id TEXT,
                    status TEXT NOT NULL,
                    owner_approved INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE execution_events (
                    event_id TEXT PRIMARY KEY,
                    work_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE work_outcomes (
                    work_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE pending_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    resolved INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            connection.execute(
                "INSERT INTO work_items VALUES (?, ?, ?, ?, ?, ?)",
                ("legacy-work", "旧工作", "legacy-source", "completed", 1, "2026-07-01T08:00:00"),
            )
            connection.execute(
                "INSERT INTO work_outcomes VALUES (?, ?, ?, ?)",
                ("legacy-work", "completed", "旧结果", "{}"),
            )
            connection.execute(
                "INSERT INTO pending_actions(work_id, description, resolved) VALUES (?, ?, 0)",
                ("legacy-work", "旧待办"),
            )

        migrated = WorkStore(legacy_state)
        work = migrated.get_work("legacy-work")
        self.assertIsNotNone(work)
        assert work is not None
        self.assertEqual(work.updated_at, "2026-07-01T08:00:00")
        outcome = migrated.get_outcome("legacy-work")
        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertEqual(outcome.status, "success")
        pending = migrated.list_pending()[0]
        self.assertEqual(pending.action_id, "legacy-1")
        self.assertEqual(pending.created_at, "2026-07-01T08:00:00")

    def test_invalid_statuses_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.store.create_work(WorkItem(title="bad", status="queued"))  # type: ignore[arg-type]
        self.store.create_work(WorkItem(work_id="work-4", title="valid"))
        with self.assertRaises(ValueError):
            self.store.update_work_status("work-4", "queued")
        with self.assertRaises(ValueError):
            self.store.save_next_action(
                NextAction(work_id="work-4", actor="robot", description="bad")  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
