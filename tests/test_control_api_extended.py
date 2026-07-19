from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app


class ExtendedControlApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(root / "vault"),
            storage_dir=str(root / "storage"),
            log_dir=str(root / "logs"),
            backup_dir=str(root / "backups"),
            startup_min_free_gb=0,
            startup_health_timeout_seconds=0.2,
        )
        self.settings.vault_path.mkdir(parents=True)
        self.settings.log_path.mkdir(parents=True)
        (self.settings.vault_path / "note.md").write_text("# note\n", encoding="utf-8")
        (self.settings.log_path / "lingji_service.log").write_text("line one\nline two\n", encoding="utf-8")
        derived = self.settings.storage_path / "derived" / "media"
        derived.mkdir(parents=True)
        self.old_derived = derived / "old.txt"
        self.old_derived.write_text("old", encoding="utf-8")
        os.utime(self.old_derived, (1_600_000_000, 1_600_000_000))
        self.client_context = TestClient(create_control_app(self.settings, token="secret"))
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.headers = {"X-LingJi-Token": "secret"}

    @patch("src.health.requests.get", side_effect=requests.ConnectionError("offline"))
    def test_overview_jobs_logs_and_providers(self, _mock_get):
        overview = self.client.get("/api/overview", headers=self.headers)
        self.assertEqual(overview.status_code, 200)
        payload = overview.json()
        self.assertIn("queue", payload)
        self.assertIn("storage", payload)
        self.assertIn("providers", payload)
        jobs = self.client.get("/api/jobs", headers=self.headers)
        self.assertEqual(jobs.status_code, 200)
        self.assertIn("stats", jobs.json())
        logs = self.client.get("/api/logs?lines=1", headers=self.headers)
        self.assertEqual(logs.status_code, 200)
        self.assertEqual(logs.json()["lines"], ["line two"])

    def test_storage_plan_execute_and_restore_requires_confirmation(self):
        self.client.patch(
            "/api/settings",
            headers=self.headers,
            json={"values": {"storage_derived_retention_days": 1}},
        )
        response = self.client.post("/api/storage/plans", headers=self.headers, json={})
        self.assertEqual(response.status_code, 200)
        plan = response.json()
        self.assertEqual(plan["summary"]["files"], 1)
        wrong = self.client.post(
            f"/api/storage/plans/{plan['plan_id']}/execute",
            headers=self.headers,
            json={"confirmation": "wrong"},
        )
        self.assertEqual(wrong.status_code, 403)
        executed = self.client.post(
            f"/api/storage/plans/{plan['plan_id']}/execute",
            headers=self.headers,
            json={"confirmation": f"EXECUTE_STORAGE_PLAN:{plan['plan_id']}"},
        )
        self.assertEqual(executed.status_code, 200)
        self.assertFalse(self.old_derived.exists())
        restored = self.client.post(
            f"/api/storage/plans/{plan['plan_id']}/restore",
            headers=self.headers,
            json={"confirmation": f"RESTORE_STORAGE_PLAN:{plan['plan_id']}"},
        )
        self.assertEqual(restored.status_code, 200)
        self.assertTrue(self.old_derived.exists())

    def test_backup_create_verify_and_stage_restore(self):
        created = self.client.post(
            "/api/backups", headers=self.headers, json={"profile": "metadata"}
        )
        self.assertEqual(created.status_code, 200)
        backup = created.json()
        verified = self.client.post(
            "/api/backups/verify",
            headers=self.headers,
            json={"backup": backup["path"]},
        )
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(verified.json()["valid"])
        staged = self.client.post(
            "/api/backups/stage-restore",
            headers=self.headers,
            json={
                "backup": backup["path"],
                "confirmation": f"STAGE_RESTORE:{backup['backup_id']}",
            },
        )
        self.assertEqual(staged.status_code, 200)
        self.assertTrue(Path(staged.json()["staging_path"]).exists())

    def test_storage_and_media_settings_support_boolean_choice_and_string(self):
        response = self.client.patch(
            "/api/settings",
            headers=self.headers,
            json={
                "values": {
                    "storage_cold_enabled": True,
                    "storage_cold_path": str(Path(self.temp_dir.name) / "cold"),
                    "media_asr_provider": "faster_whisper",
                    "media_asr_model": "small",
                }
            },
        )
        self.assertEqual(response.status_code, 200)
        values = response.json()["values"]
        self.assertTrue(values["storage_cold_enabled"])
        self.assertEqual(values["media_asr_provider"], "faster_whisper")
        invalid = self.client.patch(
            "/api/settings",
            headers=self.headers,
            json={"values": {"media_asr_provider": "paid-cloud-magic"}},
        )
        self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
