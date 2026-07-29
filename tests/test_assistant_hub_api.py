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

    def test_status_scan_and_connector_routes_require_control_token(self) -> None:
        self.assertEqual(self.client.get("/api/assistant-hub/status").status_code, 401)
        self.assertEqual(self.client.post("/api/assistant-hub/scan").status_code, 401)
        self.assertEqual(self.client.get("/api/assistant-hub/connections").status_code, 401)
        self.assertEqual(
            self.client.post("/api/assistant-hub/connections/codex/preview").status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/api/assistant-hub/connections/codex/apply",
                json={"confirmation": "CONNECT_CODEX_TO_LINGJI"},
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post("/api/assistant-hub/connections/codex/test").status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/api/assistant-hub/connections/codex/rollback",
                json={"confirmation": "DISCONNECT_CODEX_FROM_LINGJI"},
            ).status_code,
            401,
        )

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

    def test_connection_status_is_truthful_about_runtime_and_memory_policy(self) -> None:
        response = self.client.get("/api/assistant-hub/connections", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["mcp_runtime"]["host"], "127.0.0.1")
        self.assertEqual(payload["mcp_runtime"]["port"], 8767)
        self.assertEqual(payload["mcp_runtime"]["authentication"], "bearer_token")
        self.assertTrue(payload["mcp_runtime"]["loopback_only"])
        self.assertTrue(payload["shared_memory_policy"]["owner_approved_memory_only"])
        self.assertFalse(payload["shared_memory_policy"]["automatic_core_memory_write"])
        self.assertTrue(payload["shared_memory_policy"]["candidate_write_available"])
        self.assertEqual(
            {item["id"] for item in payload["connectors"]},
            {"codex", "claude_code", "workbuddy"},
        )

    def test_connector_management_rejects_unknown_clients_and_implicit_confirmation(self) -> None:
        unknown = self.client.post(
            "/api/assistant-hub/connections/random-ai/preview",
            headers=self.headers,
        )
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.json()["detail"]["code"], "UNSUPPORTED_CONNECTOR")

        implicit = self.client.post(
            "/api/assistant-hub/connections/codex/apply",
            headers=self.headers,
            json={"confirmation": "yes"},
        )
        self.assertEqual(implicit.status_code, 403)
        self.assertEqual(implicit.json()["detail"]["code"], "CONFIRMATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
