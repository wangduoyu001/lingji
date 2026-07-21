from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from src.config import Settings
from src.control.api import create_control_app
from src.control.service import LocalControlService
from src.hardware.runner import SafeRunner
from src.hardware.system_detectors import cpu_snapshot
from src.hardware.tool_detectors import cuda_snapshot
from src.model_center import LocalModelInventoryService

from fastapi.testclient import TestClient


class P3FixesTests(unittest.TestCase):
    """Tests for P3 fixes and Brain Status endpoint."""

    def make_settings(self, root: Path, **overrides) -> Settings:
        values = {
            "_env_file": None,
            "vault_dir": str(root / "vault"),
            "storage_dir": str(root / "storage"),
            "backup_dir": str(root / "backups"),
            "log_dir": str(root / "logs"),
            "llm_model": "qwen3:8b",
            "fallback_llm": "missing-chat:latest",
            "embed_model": "bge-m3",
            "fallback_embed_model": "nomic-embed-text",
            "startup_min_free_gb": 0,
        }
        values.update(overrides)
        return Settings(**values)

    # ---- P3-01: Model Center tag normalization ----
    def test_latest_tag_normalization_matches_configured_models(self):
        """Models with :latest tag should match bare names in settings."""
        class LatestTagTransport:
            def get_json(self, url: str, timeout: float = 3.0):
                if "/api/tags" in url:
                    return {
                        "models": [
                            {
                                "name": "bge-m3:latest", "model": "bge-m3:latest",
                                "size": 1_000_000_000, "digest": "bge-digest",
                                "modified_at": "2026-07-20T10:00:00Z",
                                "details": {"format": "gguf", "family": "bert",
                                            "parameter_size": "500M", "quantization_level": "Q8_0"},
                            },
                            {
                                "name": "qwen3:8b", "model": "qwen3:8b",
                                "size": 5_200_000_000, "digest": "chat-digest",
                                "modified_at": "2026-07-19T10:00:00Z",
                                "details": {"format": "gguf", "family": "qwen3",
                                            "parameter_size": "8.2B", "quantization_level": "Q4_K_M"},
                            },
                        ]
                    }
                if "/api/ps" in url:
                    return {"models": []}
                raise OSError(f"unexpected GET {url}")
            def post_json(self, url: str, payload: dict, timeout: float = 3.0):
                if not url.endswith("/api/show"):
                    raise OSError(f"unexpected POST {url}")
                return {"capabilities": ["embedding"], "details": {"family": "bert"}}
            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory), embed_model="bge-m3")
            service = LocalModelInventoryService(
                settings,
                transport=LatestTagTransport(),
                package_finder=lambda _name: False,
                environment={},
            )
            inventory = service.inventory(force=True)
            assignments = {item["role"]: item for item in inventory["assignments"]}
            self.assertTrue(assignments["embedding_primary"]["installed"])
            self.assertEqual(assignments["embedding_primary"]["status"], "available")

    # ---- P3-02: PowerShell CIM CPU model ----
    def test_cpu_snapshot_uses_powershell_cim_on_windows(self):
        """CPU model should use PowerShell Get-CimInstance on Windows for real product name."""
        class MockRunner:
            def __call__(self, args, timeout=3.0):
                cmd = args[0].lower()
                if cmd == "powershell":
                    return {
                        "returncode": 0,
                        "stdout": "Intel(R) Core(TM) i7-9700 CPU @ 3.00GHz",
                        "stderr": "",
                    }
                return {"returncode": 1, "stdout": "", "stderr": "unsupported"}

        runner = SafeRunner(command_runner=MockRunner())
        with patch("src.hardware.system_detectors.platform.system", return_value="Windows"):
            snapshot = cpu_snapshot(None, runner=runner)
        self.assertIn("i7-9700", snapshot["model"])
        self.assertNotIn("Family", snapshot["model"])

    # ---- P3-03: CUDA fallback ----
    def test_cuda_fallback_from_nvidia_smi_when_nvcc_absent(self):
        """When nvcc is absent, CUDA version should come from nvidia-smi header."""
        class FallbackRunner:
            def __call__(self, args, timeout=3.0):
                cmd = args[0].lower()
                if cmd == "nvcc":
                    return {"returncode": 1, "stdout": "", "stderr": "not found"}
                if cmd == "nvidia-smi":
                    return {
                        "returncode": 0,
                        "stdout": "NVIDIA-SMI 595.79    Driver Version: 595.79    CUDA Version: 13.2\n...",
                        "stderr": "",
                    }
                return {"returncode": 1, "stdout": "", "stderr": "unsupported"}

        runner = SafeRunner(command_runner=FallbackRunner())
        snapshot = cuda_snapshot(runner, driver_available=True)
        self.assertFalse(snapshot["runtime_available"])
        self.assertEqual(snapshot["source"], "not_available")
        self.assertEqual(snapshot["driver_cuda_version"], "13.2")

    # ---- Brain Status API ----
    def test_brain_status_endpoint_returns_aggregated_snapshot(self):
        """Brain Status API returns memory, model, GPU and task info."""
        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory), embed_model="bge-m3")
            control = LocalControlService(settings)
            with TestClient(create_control_app(settings, service=control, token="secret")) as client:
                headers = {"X-LingJi-Token": "secret"}
                resp = client.get("/api/brain/status", headers=headers)
                self.assertEqual(resp.status_code, 200)
                body = resp.json()
                self.assertIn("memory_count", body)
                self.assertIn("chat_model", body)
                self.assertIn("embed_model", body)
                self.assertEqual(body["chat_model"], "qwen3:8b")
                self.assertEqual(body["embed_model"], "bge-m3")
                self.assertIn("system_status", body)
                self.assertIn("processing_status", body)
                self.assertIn("installed_models", body)

    # ---- CUDA when nvidia-smi also missing ----
    def test_cuda_still_graceful_when_both_nvcc_and_nvidia_smi_absent(self):
        """When both nvcc and nvidia-smi fail, no CUDA version should be reported."""
        class EmptyRunner:
            def __call__(self, args, timeout=3.0):
                return {"returncode": 1, "stdout": "", "stderr": "not found"}

        runner = SafeRunner(command_runner=EmptyRunner())
        snapshot = cuda_snapshot(runner, driver_available=False)
        self.assertIsNone(snapshot["driver_cuda_version"])
        self.assertFalse(snapshot["runtime_available"])


if __name__ == "__main__":
    unittest.main()