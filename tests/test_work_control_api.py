from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app
from src.control.service import LocalControlService
from src.work.models import ExecutionEvent, NextAction, Outcome, PendingAction, WorkItem


class WorkControlApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(root / "vault"),
            storage_dir=str(root / "storage"),
            log_dir=str(root / "logs"),
            backup_dir=str(root / "backup"),
            startup_min_free_gb=0,
        )
        self.service = LocalControlService(self.settings)
        self.addCleanup(self.service.close)
        self.client_context = TestClient(
            create_control_app(self.settings, service=self.service, token="secret")
        )
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.headers = {"X-LingJi-Token": "secret"}
        self.store = self.service.work_control.store

    def test_work_routes_are_authenticated(self) -> None:
        for path in (
            "/api/work/current",
            "/api/work/recent",
            "/api/work/pending-actions",
            "/api/work/timeline/missing",
            "/api/work/missing",
        ):
            self.assertEqual(self.client.get(path).status_code, 401, path)

    def test_empty_current_work_is_a_real_successful_empty_state(self) -> None:
        response = self.client.get("/api/work/current", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "work": None,
                "events": [],
                "outcome": None,
                "next_action": None,
                "pending_actions": [],
            },
        )

    def test_current_detail_timeline_and_pending_use_same_contract(self) -> None:
        self.store.create_work(
            WorkItem(
                work_id="work-api",
                title="API 测试",
                source_id="capture-api",
                status="running",
                owner_approved=True,
                created_at="2026-08-22T10:00:00",
                updated_at="2026-08-22T10:00:00",
            )
        )
        self.store.append_event(
            ExecutionEvent(
                event_id="event-api",
                work_id="work-api",
                event_type="processing.started",
                detail={"stage": "extract"},
                created_at="2026-08-22T10:00:01",
            )
        )
        self.store.save_next_action(
            NextAction(work_id="work-api", actor="owner", description="确认范围")
        )
        self.store.add_pending_action(
            PendingAction(
                action_id="action-api",
                work_id="work-api",
                description="确认范围",
                reason="需要主人授权",
                created_at="2026-08-22T10:00:02",
            )
        )

        current = self.client.get("/api/work/current", headers=self.headers)
        detail = self.client.get("/api/work/work-api", headers=self.headers)
        timeline = self.client.get("/api/work/timeline/work-api", headers=self.headers)
        pending = self.client.get("/api/work/pending-actions", headers=self.headers)

        self.assertEqual(current.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(timeline.status_code, 200)
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(current.json()["work"]["work_id"], "work-api")
        self.assertEqual(detail.json()["work"]["work_id"], "work-api")
        self.assertEqual(current.json()["events"][0]["event_id"], "event-api")
        self.assertEqual(current.json()["events"][0]["event_type"], "processing.started")
        self.assertEqual(current.json()["events"][0]["detail"], {"stage": "extract"})
        self.assertEqual(current.json()["next_action"]["description"], "确认范围")
        self.assertEqual(current.json()["pending_actions"][0]["action_id"], "action-api")
        self.assertEqual(timeline.json()["work_id"], "work-api")
        self.assertEqual(timeline.json()["events"][0]["work_id"], "work-api")
        self.assertEqual(pending.json()["pending_actions"][0]["work_id"], "work-api")

    def test_finished_and_failed_work_appear_in_recent_not_current(self) -> None:
        self.store.create_work(WorkItem(work_id="work-success", title="成功", status="running"))
        self.store.save_outcome(
            Outcome(work_id="work-success", status="success", summary="完成")
        )
        self.store.create_work(WorkItem(work_id="work-failure", title="失败", status="running"))
        self.store.save_outcome(
            Outcome(work_id="work-failure", status="failure", summary="失败")
        )

        current = self.client.get("/api/work/current", headers=self.headers)
        recent = self.client.get("/api/work/recent?limit=20", headers=self.headers)
        failed = self.client.get("/api/work/work-failure", headers=self.headers)

        self.assertEqual(current.status_code, 200)
        self.assertIsNone(current.json()["work"])
        self.assertEqual(recent.status_code, 200)
        statuses = {item["work_id"]: item["status"] for item in recent.json()["work_items"]}
        self.assertEqual(statuses["work-success"], "completed")
        self.assertEqual(statuses["work-failure"], "failed")
        self.assertEqual(failed.status_code, 200)
        self.assertEqual(failed.json()["outcome"]["status"], "failure")
        self.assertEqual(failed.json()["outcome"]["summary"], "失败")

    def test_missing_work_returns_404_not_empty_success(self) -> None:
        detail = self.client.get("/api/work/missing", headers=self.headers)
        timeline = self.client.get("/api/work/timeline/missing", headers=self.headers)
        self.assertEqual(detail.status_code, 404)
        self.assertEqual(timeline.status_code, 404)


if __name__ == "__main__":
    unittest.main()
