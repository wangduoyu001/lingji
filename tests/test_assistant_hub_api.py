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
        self.root = Path(self.temp_dir.name)
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(self.root / "vault"),
            storage_dir=str(self.root / "storage"),
            log_dir=str(self.root / "logs"),
            backup_dir=str(self.root / "backup"),
            startup_min_free_gb=0,
        )
        self.settings.storage_path.mkdir(parents=True, exist_ok=True)
        self.client_context = TestClient(create_control_app(self.settings, token="secret"))
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.headers = {"X-LingJi-Token": "secret"}

    def test_status_scan_import_and_connector_routes_require_control_token(self) -> None:
        self.assertEqual(self.client.get("/api/assistant-hub/status").status_code, 401)
        self.assertEqual(self.client.post("/api/assistant-hub/scan").status_code, 401)
        self.assertEqual(self.client.get("/api/assistant-hub/import-plan").status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/assistant-hub/import-selected-file",
                json={
                    "input_path": "x.json",
                    "source_id": "codex",
                    "confirmation": "AUTHORIZE_SELECTED_ASSISTANT_IMPORT",
                },
            ).status_code,
            401,
        )
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

    def test_status_returns_truthful_safety_capability_and_import_plan(self) -> None:
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

        plan = payload["import_plan"]
        self.assertTrue(plan["safety"]["metadata_only"])
        self.assertFalse(plan["safety"]["content_read"])
        self.assertFalse(plan["safety"]["arbitrary_path_submission"])
        self.assertTrue(plan["safety"]["owner_authorization_required"])
        self.assertEqual(
            {item["id"] for item in plan["sources"]},
            {"chatgpt", "codex", "claude_code", "workbuddy"},
        )
        self.assertTrue(all(item["owner_action_count"] <= 1 for item in plan["sources"]))

    def test_rescan_uses_same_authenticated_contract(self) -> None:
        response = self.client.post("/api/assistant-hub/scan", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("scanned_at", response.json())
        self.assertIn("import_plan", response.json())

    def test_import_plan_has_one_action_and_does_not_expose_paths(self) -> None:
        response = self.client.get("/api/assistant-hub/import-plan", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["schema_version"], 1)
        self.assertFalse(payload["safety"]["arbitrary_path_submission"])
        for source in payload["sources"]:
            self.assertLessEqual(source["owner_action_count"], 1)
            for candidate in source["candidates"]:
                self.assertNotIn("input_path", candidate)

    def test_selected_file_import_requires_exact_authorization_and_supported_type(self) -> None:
        report = self.root / "codex-work-report.json"
        report.write_text('{"schema_version": 1}', encoding="utf-8")

        rejected = self.client.post(
            "/api/assistant-hub/import-selected-file",
            headers=self.headers,
            json={
                "input_path": str(report),
                "source_id": "codex",
                "confirmation": "yes",
            },
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["detail"]["code"], "CONFIRMATION_REQUIRED")

        unsupported = self.client.post(
            "/api/assistant-hub/import-selected-file",
            headers=self.headers,
            json={
                "input_path": str(report),
                "source_id": "claude_code",
                "confirmation": "AUTHORIZE_SELECTED_ASSISTANT_IMPORT",
            },
        )
        self.assertEqual(unsupported.status_code, 422)
        self.assertEqual(unsupported.json()["detail"]["code"], "UNSUPPORTED_IMPORT_SOURCE")

        accepted = self.client.post(
            "/api/assistant-hub/import-selected-file",
            headers=self.headers,
            json={
                "input_path": str(report),
                "source_id": "codex",
                "confirmation": "AUTHORIZE_SELECTED_ASSISTANT_IMPORT",
            },
        )
        self.assertIn(accepted.status_code, {200, 202})
        self.assertIn("job_id", accepted.json())

    def test_discovered_candidate_endpoint_rejects_unknown_or_unconfirmed_candidate(self) -> None:
        unconfirmed = self.client.post(
            "/api/assistant-hub/import-candidates/not-a-candidate/authorize",
            headers=self.headers,
            json={"confirmation": "yes"},
        )
        self.assertEqual(unconfirmed.status_code, 403)

        missing = self.client.post(
            "/api/assistant-hub/import-candidates/not-a-candidate/authorize",
            headers=self.headers,
            json={"confirmation": "AUTHORIZE_ASSISTANT_IMPORT_NOT-A-CANDIDATE"},
        )
        self.assertEqual(missing.status_code, 409)
        self.assertEqual(missing.json()["detail"]["code"], "IMPORT_CANDIDATE_INVALID")

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
        codex = next(item for item in payload["connectors"] if item["id"] == "codex")
        self.assertIn("readiness", codex)
        self.assertIn("configuration", codex["readiness"])
        self.assertIn("client", codex["readiness"])
        self.assertIn("real_connection", codex["readiness"])

    def test_workbuddy_preview_is_redacted_until_confirmed_apply(self) -> None:
        preview = self.client.post(
            "/api/assistant-hub/connections/workbuddy/preview",
            headers=self.headers,
        )
        self.assertEqual(preview.status_code, 200)
        payload = preview.json()
        self.assertNotIn("copy_payload", payload)
        self.assertIn("<本机令牌已隐藏>", payload["preview"])
        self.assertNotIn("Bearer ey", payload["preview"])

        rejected = self.client.post(
            "/api/assistant-hub/connections/workbuddy/apply",
            headers=self.headers,
            json={"confirmation": "yes"},
        )
        self.assertEqual(rejected.status_code, 403)

        applied = self.client.post(
            "/api/assistant-hub/connections/workbuddy/apply",
            headers=self.headers,
            json={"confirmation": "COPY_WORKBUDDY_LINGJI_CONFIG"},
        )
        self.assertEqual(applied.status_code, 200)
        self.assertIn("copy_payload", applied.json())
        self.assertIn("Authorization", applied.json()["copy_payload"])

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
