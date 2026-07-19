from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app
from src.control.service import LocalControlService
from src.model_center import LocalModelInventoryService


class FakeOllamaTransport:
    def get_json(self, url: str, timeout: float = 3.0):
        if url.endswith("/api/tags"):
            return {
                "models": [
                    {
                        "name": "qwen3:8b",
                        "model": "qwen3:8b",
                        "size": 5_200_000_000,
                        "digest": "chat-digest",
                        "modified_at": "2026-07-19T10:00:00Z",
                        "details": {
                            "format": "gguf",
                            "family": "qwen3",
                            "parameter_size": "8.2B",
                            "quantization_level": "Q4_K_M",
                        },
                    },
                    {
                        "name": "qwen3-embedding:0.6b",
                        "model": "qwen3-embedding:0.6b",
                        "size": 639_000_000,
                        "digest": "embed-digest",
                        "modified_at": "2026-07-19T11:00:00Z",
                        "details": {
                            "format": "gguf",
                            "family": "qwen3",
                            "parameter_size": "596.8M",
                            "quantization_level": "F16",
                        },
                    },
                ]
            }
        if url.endswith("/api/ps"):
            return {
                "models": [
                    {
                        "name": "qwen3:8b",
                        "model": "qwen3:8b",
                        "digest": "chat-digest",
                        "size": 5_200_000_000,
                        "size_vram": 4_900_000_000,
                        "context_length": 8192,
                        "expires_at": "2026-07-19T12:00:00Z",
                    }
                ]
            }
        raise OSError(f"unexpected GET {url}")

    def post_json(self, url: str, payload: dict, timeout: float = 3.0):
        if not url.endswith("/api/show"):
            raise OSError(f"unexpected POST {url}")
        model = payload["model"]
        if model == "qwen3:8b":
            return {
                "capabilities": ["completion", "tools"],
                "details": {"family": "qwen3", "parameter_size": "8.2B", "quantization_level": "Q4_K_M"},
                "model_info": {"qwen3.context_length": 32768},
                "license": "Apache-2.0",
            }
        if model == "qwen3-embedding:0.6b":
            return {
                "capabilities": ["embedding"],
                "details": {"family": "qwen3", "parameter_size": "596.8M", "quantization_level": "F16"},
                "model_info": {"qwen3.embedding_length": 1024, "qwen3.context_length": 32768},
                "license": "Apache-2.0",
            }
        raise OSError(f"unexpected model {model}")


class ModelInventoryTests(unittest.TestCase):
    def make_settings(self, root: Path, **overrides) -> Settings:
        values = {
            "_env_file": None,
            "vault_dir": str(root / "vault"),
            "storage_dir": str(root / "storage"),
            "backup_dir": str(root / "backups"),
            "log_dir": str(root / "logs"),
            "llm_model": "qwen3:8b",
            "fallback_llm": "missing-chat:latest",
            "embed_model": "nomic-embed-text",
            "fallback_embed_model": "nomic-embed-text",
            "startup_min_free_gb": 0,
        }
        values.update(overrides)
        return Settings(**values)

    def test_ollama_inventory_uses_official_capabilities_and_separates_install_running_and_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory))
            service = LocalModelInventoryService(
                settings,
                transport=FakeOllamaTransport(),
                package_finder=lambda name: name == "faster_whisper",
                environment={"PADDLE_OCR_BASE_DIR": str(Path(directory) / "paddle-models")},
            )

            inventory = service.inventory(force=True)
            models = {item["model_id"]: item for item in inventory["models"]}
            chat = models["ollama:qwen3:8b"]
            embedding = models["ollama:qwen3-embedding:0.6b"]

            self.assertTrue(chat["installed"])
            self.assertTrue(chat["running"])
            self.assertEqual(chat["runtime"]["vram_bytes"], 4_900_000_000)
            self.assertIn("chat_reasoning", chat["capabilities"])
            self.assertEqual(chat["compatibility"]["status"], "unverified")
            self.assertTrue(chat["compatibility"]["requires_load_test"])
            self.assertNotIn("compatible", chat)

            self.assertTrue(embedding["installed"])
            self.assertFalse(embedding["running"])
            self.assertEqual(embedding["embedding_dimension"], 1024)
            self.assertEqual(embedding["capabilities"], ["embedding"])

    def test_configured_missing_models_are_visible_instead_of_silently_disappearing(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory))
            service = LocalModelInventoryService(
                settings,
                transport=FakeOllamaTransport(),
                package_finder=lambda _name: False,
                environment={},
            )

            inventory = service.inventory(force=True)
            assignments = {item["role"]: item for item in inventory["assignments"]}

            self.assertEqual(assignments["chat_primary"]["model"], "qwen3:8b")
            self.assertTrue(assignments["chat_primary"]["installed"])
            self.assertEqual(assignments["chat_fallback"]["model"], "missing-chat:latest")
            self.assertFalse(assignments["chat_fallback"]["installed"])
            self.assertEqual(assignments["embedding_primary"]["model"], "nomic-embed-text")
            self.assertFalse(assignments["embedding_primary"]["installed"])

    def test_optional_media_providers_report_package_and_model_location_without_triggering_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local_asr = root / "whisper-small"
            local_asr.mkdir()
            settings = self.make_settings(root, media_asr_model=str(local_asr))
            service = LocalModelInventoryService(
                settings,
                transport=FakeOllamaTransport(),
                package_finder=lambda name: name in {"faster_whisper", "paddleocr"},
                environment={"PADDLE_OCR_BASE_DIR": str(root / "paddle-models")},
            )

            inventory = service.inventory(force=True)
            providers = {item["provider_id"]: item for item in inventory["providers"]}

            self.assertTrue(providers["faster_whisper"]["package_available"])
            self.assertEqual(providers["faster_whisper"]["configured_model"], str(local_asr))
            self.assertEqual(providers["faster_whisper"]["installation_status"], "local_path_present")
            self.assertTrue(providers["paddleocr"]["package_available"])
            self.assertEqual(providers["paddleocr"]["installation_status"], "model_cache_not_verified")
            self.assertFalse(inventory["mutating_operations_enabled"])

    def test_inventory_degrades_when_ollama_is_offline(self):
        class OfflineTransport:
            def get_json(self, *_args, **_kwargs):
                raise OSError("offline")

            def post_json(self, *_args, **_kwargs):
                raise OSError("offline")

        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory))
            service = LocalModelInventoryService(
                settings,
                transport=OfflineTransport(),
                package_finder=lambda _name: False,
                environment={},
            )

            inventory = service.inventory(force=True)

            self.assertFalse(inventory["provider_status"]["ollama"]["available"])
            self.assertEqual(inventory["models"], [])
            self.assertGreaterEqual(len(inventory["assignments"]), 4)
            self.assertTrue(all(item["compatibility"]["status"] == "unverified" for item in inventory["assignments"]))

    def test_control_api_exposes_registry_inventory_and_read_only_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory))
            model_inventory = LocalModelInventoryService(
                settings,
                transport=FakeOllamaTransport(),
                package_finder=lambda _name: False,
                environment={},
            )
            control = LocalControlService(settings, model_inventory=model_inventory)

            with TestClient(create_control_app(settings, service=control, token="secret")) as client:
                headers = {"X-LingJi-Token": "secret"}
                registry = client.get("/api/models/registry", headers=headers)
                inventory = client.get("/api/models", headers=headers)
                refreshed = client.post("/api/models/refresh", headers=headers, json={})

                self.assertEqual(registry.status_code, 200)
                self.assertEqual(inventory.status_code, 200)
                self.assertEqual(refreshed.status_code, 200)
                self.assertIn("embedding", registry.json()["capabilities"])
                self.assertFalse(refreshed.json()["mutating_operations_enabled"])


if __name__ == "__main__":
    unittest.main()
