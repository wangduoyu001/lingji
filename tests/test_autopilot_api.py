from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.control.autopilot_api import register_autopilot_routes


class FakeEngine:
    def status(self):
        return {
            "enabled": True,
            "running": True,
            "state": "healthy",
            "summary": "系统正常，自动维护持续运行",
            "cycle_count": 3,
            "automatic_repair_count": 1,
            "last_cycle_at": "2026-08-11T12:00:00Z",
            "last_success_at": "2026-08-11T12:00:00Z",
            "recent_actions": [],
            "background_issue_count": 0,
            "background_issues": [],
            "owner_action_count": 0,
            "owner_actions": [],
            "last_error": None,
        }


class AutopilotApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        register_autopilot_routes(app, FakeEngine(), token="secret")
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)

    def test_status_requires_local_control_token(self):
        self.assertEqual(self.client.get("/api/autopilot/status").status_code, 401)

    def test_status_is_read_only_and_authenticated(self):
        response = self.client.get(
            "/api/autopilot/status",
            headers={"X-LingJi-Token": "secret"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], "healthy")
        self.assertEqual(payload["owner_action_count"], 0)
        self.assertEqual(payload["automatic_repair_count"], 1)
        post = self.client.post(
            "/api/autopilot/status",
            headers={"X-LingJi-Token": "secret"},
        )
        self.assertEqual(post.status_code, 405)


if __name__ == "__main__":
    unittest.main()
