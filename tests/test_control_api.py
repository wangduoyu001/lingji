from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app


class ControlApiTests(unittest.TestCase):
    def setUp(self):
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
        self.client_context = TestClient(create_control_app(self.settings, token="secret"))
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.headers = {"X-LingJi-Token": "secret"}

    def test_token_is_required(self):
        self.assertEqual(self.client.get("/api/settings").status_code, 401)

    def test_settings_can_be_read_updated_and_reset(self):
        response = self.client.get("/api/settings", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["values"]["media_max_keyframes"], 500)
        self.assertEqual(response.json()["runtime_contracts"]["mcp"]["port"], 8767)
        response = self.client.patch(
            "/api/settings",
            headers=self.headers,
            json={"values": {"media_max_keyframes": 888}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["values"]["media_max_keyframes"], 888)
        response = self.client.post(
            "/api/settings/reset",
            headers=self.headers,
            json={"keys": ["media_max_keyframes"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["values"]["media_max_keyframes"], 500)

    def test_mcp_status_exposes_configuration_without_claiming_running_state(self):
        response = self.client.get("/api/mcp/status", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["transport"], "stdio")
        self.assertEqual(payload["compatibility_port"], 8765)
        self.assertEqual(payload["control_port"], 8766)
        self.assertEqual(payload["port"], 8767)
        self.assertTrue(payload["contract_valid"])
        self.assertIsNone(payload["running"])


if __name__ == "__main__":
    unittest.main()
