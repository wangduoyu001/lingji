from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app


class ControlApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.runtime_root = root.resolve()
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(root / "vault"),
            storage_dir=str(root / "storage"),
            log_dir=str(root / "logs"),
            backup_dir=str(root / "backup"),
            startup_min_free_gb=0,
        )
        self.settings.storage_path.mkdir(parents=True, exist_ok=True)
        (self.settings.storage_path / "memory_status.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "source": "live",
                    "stale": False,
                    "state": "healthy",
                    "workspace": "production",
                    "memory": {
                        "state": "healthy",
                        "documents": 7,
                        "chunks": 12,
                        "core_memories": 2,
                        "revision": 5,
                        "database_bytes": 4096,
                        "database_path": str(self.settings.memory_db_path),
                    },
                    "embedding": {
                        "state": "healthy",
                        "available": True,
                        "primary_model": "bge-m3",
                        "active_model": "bge-m3",
                        "dimension": 1024,
                    },
                    "vector": {
                        "state": "healthy",
                        "ready": True,
                        "collection_exists": True,
                        "vectors": 12,
                        "dimension": 1024,
                        "collection": "lingji_memory_production",
                        "mode": "embedded",
                        "rebuild_required": False,
                        "last_error": None,
                    },
                    "coverage": {
                        "state": "healthy",
                        "expected": 12,
                        "indexed": 12,
                        "missing": 0,
                        "coverage": 1.0,
                        "missing_chunk_ids": [],
                        "missing_chunk_ids_truncated": False,
                    },
                    "warnings": [],
                }
            ),
            encoding="utf-8",
        )
        self.client_context = TestClient(create_control_app(self.settings, token="secret"))
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.headers = {"X-LingJi-Token": "secret"}

    def test_token_is_required(self):
        self.assertEqual(self.client.get("/api/settings").status_code, 401)
        self.assertEqual(self.client.get("/api/vector/status").status_code, 401)
        self.assertEqual(self.client.get("/api/runtime/ping").status_code, 401)

    def test_runtime_ping_is_authenticated_and_proves_binding_identity(self):
        response = self.client.get("/api/runtime/ping", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "binding_contract_version": 1,
                "data_root": str(self.runtime_root),
                "workspace": "production",
            },
        )

    def test_settings_can_be_read_updated_and_reset(self):
        response = self.client.get("/api/settings", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["values"]["media_max_keyframes"], 500)
        self.assertEqual(response.json()["runtime_contracts"]["mcp"]["port"], 8767)
        self.assertEqual(response.json()["runtime_contracts"]["memory"]["documents"], 7)
        self.assertEqual(response.json()["runtime_contracts"]["vector"]["vectors"], 12)
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

    def test_memory_vector_and_coverage_endpoints_return_shared_snapshot(self):
        memory = self.client.get("/api/memory/status", headers=self.headers)
        vector = self.client.get("/api/vector/status", headers=self.headers)
        coverage = self.client.get("/api/vector/coverage", headers=self.headers)
        brain = self.client.get("/api/brain/status", headers=self.headers)

        self.assertEqual(memory.status_code, 200)
        self.assertEqual(vector.status_code, 200)
        self.assertEqual(coverage.status_code, 200)
        self.assertEqual(brain.status_code, 200)
        self.assertEqual(memory.json()["documents"], 7)
        self.assertEqual(memory.json()["chunks"], 12)
        self.assertEqual(vector.json()["vectors"], 12)
        self.assertEqual(vector.json()["embedding"]["active_model"], "bge-m3")
        self.assertEqual(coverage.json()["coverage"], 1.0)
        self.assertEqual(brain.json()["memory_count"], 7)
        self.assertEqual(brain.json()["vector_count"], 12)
        self.assertEqual(brain.json()["embed_model"], "bge-m3")
        self.assertFalse(brain.json()["status_stale"])


if __name__ == "__main__":
    unittest.main()
