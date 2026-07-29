from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app


class AssistantHubApiTests(unittest.TestCase):
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
        self.settings.storage_path.mkdir(parents=True, exist_ok=True)
        self.client_context = TestClient(create_control_app(self.settings, token="secret"))
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.headers = {"X-LingJi-Token": "secret"}

    def test_status_and_scan_require_control_token(self) -> None:
        self.assertEqual(self.client.get("/api/assistant-hub/status").status_code, 401)
        self.assertEqual(self.client.post("/api/assistant-hub/scan").status_code, 401)

    def test_status_returns_truthful_safety_and_capability_shape(self) -> None:
        response = self.client.get("/api/assistant-hub/status", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(len(payload["assistants"]), 4)
        self.assertTrue(payload["safety"]["read_only"])
        self.assertFalse(payload["safety"]["content_read"])
        self.assertFalse(payload["safety"]["automatic_core_memory_write"])
        self.assertTrue(payload["safety"]["review_required_for_permanent_memory"])
        self.assertEqual(
            {item["id"] for item in payload["assistants"]},
            {"chatgpt", "codex", "claude_code", "workbuddy"},
        )
        for item in payload["assistants"]:
            self.assertIn(item["import_state"], {"available", "manual_export", "planned"})
            self.assertNotEqual(item["connection_state"], "connected")

    def test_rescan_uses_same_authenticated_contract(self) -> None:
        response = self.client.post("/api/assistant-hub/scan", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("scanned_at", response.json())


if __name__ == "__main__":
    unittest.main()
