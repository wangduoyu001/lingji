from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.storage.state_db import StateDatabase
from src.work.models import ExecutionEvent, NextAction, Outcome, PendingAction, WorkItem
from src.work.projector import WorkProjector
from src.work.store import WorkStore


class WorkProjectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        state = StateDatabase(Path(self.temp_dir.name) / "state.db")
        self.store = WorkStore(state)
        self.projector = WorkProjector(self.store)

    def test_empty_current_work_is_explicit_not_fabricated(self) -> None:
        self.assertEqual(
            self.projector.current_work(),
            {
                "work": None,
                "events": [],
                "outcome": None,
                "next_action": None,
                "pending_actions": [],
            },
        )

    def test_current_detail_uses_same_work_id_across_facts(self) -> None:
        self.store.create_work(
            WorkItem(
                work_id="work-active",
                title="当前任务",
                status="running",
                created_at="2026-08-22T10:00:00",
                updated_at="2026-08-22T10:00:00",
            )
        )
        self.store.append_event(
            ExecutionEvent(
                event_id="event-active",
                work_id="work-active",
                event_type="processing.started",
                created_at="2026-08-22T10:00:01",
            )
        )
        self.store.save_next_action(
            NextAction(work_id="work-active", actor="system", description="继续处理")
        )
        self.store.add_pending_action(
            PendingAction(
                action_id="action-active",
                work_id="work-active",
                description="确认范围",
                reason="超出自动授权范围",
                created_at="2026-08-22T10:00:02",
            )
        )

        current = self.projector.current_work()
        self.assertEqual(current["work"]["work_id"], "work-active")
        self.assertEqual(current["events"][0]["work_id"], "work-active")
        self.assertEqual(current["next_action"]["work_id"], "work-active")
        self.assertEqual(current["pending_actions"][0]["work_id"], "work-active")

    def test_finished_work_leaves_current_and_appears_in_recent(self) -> None:
        self.store.create_work(
            WorkItem(
                work_id="work-finished",
                title="已完成",
                status="running",
                created_at="2026-08-22T09:00:00",
                updated_at="2026-08-22T09:00:00",
            )
        )
        self.store.save_outcome(
            Outcome(
                work_id="work-finished",
                status="success",
                summary="完成",
                completed_at="2026-08-22T09:05:00",
            )
        )
        self.assertIsNone(self.projector.current_work()["work"])
        recent = self.projector.recent_work(limit=10)
        self.assertEqual(recent["work_items"][0]["work_id"], "work-finished")
        self.assertEqual(recent["work_items"][0]["status"], "completed")

    def test_failed_work_is_preserved_as_failure(self) -> None:
        self.store.create_work(
            WorkItem(work_id="work-failed", title="失败任务", status="running")
        )
        self.store.save_outcome(
            Outcome(work_id="work-failed", status="failure", summary="解析失败")
        )
        detail = self.projector.work_detail("work-failed")
        self.assertEqual(detail["work"]["status"], "failed")
        self.assertEqual(detail["outcome"]["status"], "failure")
        self.assertEqual(detail["outcome"]["summary"], "解析失败")

    def test_pending_projection_excludes_resolved_actions(self) -> None:
        self.store.create_work(WorkItem(work_id="work-attention", title="待确认"))
        self.store.add_pending_action(
            PendingAction(
                action_id="action-open",
                work_id="work-attention",
                description="打开",
            )
        )
        self.store.add_pending_action(
            PendingAction(
                action_id="action-resolved",
                work_id="work-attention",
                description="已处理",
            )
        )
        self.store.resolve_pending_action("action-resolved")
        projected = self.projector.pending_actions()
        self.assertEqual(
            [item["action_id"] for item in projected["pending_actions"]],
            ["action-open"],
        )

    def test_unknown_work_is_not_silently_empty(self) -> None:
        with self.assertRaises(LookupError):
            self.projector.work_detail("missing")
        with self.assertRaises(LookupError):
            self.projector.timeline("missing")


if __name__ == "__main__":
    unittest.main()
