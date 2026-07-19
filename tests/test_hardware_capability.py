from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app
from src.control.service import LocalControlService
from src.hardware import HardwareCapabilityService
from src.storage.state_db import StateDatabase


class FakePsutil:
    @staticmethod
    def cpu_count(logical: bool = True):
        return 12 if logical else 6

    @staticmethod
    def cpu_percent(interval=None):
        return 23.5

    @staticmethod
    def virtual_memory():
        return SimpleNamespace(total=32 * 1024**3, available=21 * 1024**3, percent=34.4)

    @staticmethod
    def disk_partitions(all: bool = False):
        return [SimpleNamespace(device="C:", mountpoint="C:/", fstype="NTFS", opts="rw,fixed")]

    @staticmethod
    def disk_usage(_mount: str):
        return SimpleNamespace(total=1024**4, used=400 * 1024**3, free=624 * 1024**3, percent=39.1)


class FakeRunner:
    def __init__(self, gpu: bool = True):
        self.gpu = gpu
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, args: list[str], timeout: float = 3.0):
        self.calls.append(tuple(args))
        command = args[0].lower()
        if command == "nvidia-smi":
            if not self.gpu:
                return {"returncode": 1, "stdout": "", "stderr": "not found"}
            return {
                "returncode": 0,
                "stdout": "NVIDIA GeForce RTX 4060, 8188, 7000, 12, 45, 555.85\n",
                "stderr": "",
            }
        if command == "nvcc":
            return {"returncode": 0, "stdout": "Cuda compilation tools, release 12.4, V12.4.99", "stderr": ""}
        if command in {"ffmpeg", "ffprobe"}:
            return {"returncode": 0, "stdout": f"{command} version 7.1 Copyright", "stderr": ""}
        if command in {"powershell", "pwsh"}:
            return {"returncode": 0, "stdout": '[{"FriendlyName":"NVMe","MediaType":"SSD","Size":1000000}]', "stderr": ""}
        return {"returncode": 1, "stdout": "", "stderr": "unsupported"}


def fake_url_reader(url: str, timeout: float = 3.0):
    if url.endswith("/api/tags"):
        return {
            "models": [
                {
                    "name": "qwen3:8b",
                    "size": 5_000_000_000,
                    "details": {"parameter_size": "8.2B", "quantization_level": "Q4_K_M"},
                }
            ]
        }
    raise OSError("unexpected URL")


class HardwareCapabilityTests(unittest.TestCase):
    def make_settings(self, root: Path) -> Settings:
        return Settings(
            _env_file=None,
            vault_dir=str(root / "vault"),
            storage_dir=str(root / "storage"),
            log_dir=str(root / "logs"),
            backup_dir=str(root / "backups"),
            startup_min_free_gb=0,
        )

    def test_capability_snapshot_uses_real_sources_and_never_claims_model_compatibility(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory))
            service = HardwareCapabilityService(
                settings,
                command_runner=FakeRunner(gpu=True),
                url_reader=fake_url_reader,
                psutil_module=FakePsutil,
            )

            snapshot = service.capabilities(force=True)

            self.assertEqual(snapshot["cpu"]["physical_cores"], 6)
            self.assertEqual(snapshot["cpu"]["logical_threads"], 12)
            self.assertEqual(snapshot["memory"]["total_bytes"], 32 * 1024**3)
            self.assertEqual(snapshot["gpus"][0]["name"], "NVIDIA GeForce RTX 4060")
            self.assertEqual(snapshot["gpus"][0]["free_vram_bytes"], 7000 * 1024**2)
            self.assertTrue(snapshot["cuda"]["driver_available"])
            self.assertEqual(snapshot["cuda"]["runtime_version"], "12.4")
            self.assertEqual(snapshot["toolchains"]["ollama"]["model_count"], 1)
            self.assertTrue(snapshot["toolchains"]["ffmpeg"]["available"])
            self.assertIn("compatibility_requires_load_test", snapshot)
            self.assertTrue(snapshot["compatibility_requires_load_test"])
            self.assertNotIn("models_can_run", snapshot)

    def test_missing_gpu_and_optional_dependencies_degrade_to_cpu_without_crashing(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory))
            service = HardwareCapabilityService(
                settings,
                command_runner=FakeRunner(gpu=False),
                url_reader=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("offline")),
                psutil_module=None,
            )

            snapshot = service.capabilities(force=True)
            telemetry = service.telemetry(force=True)
            policy = service.resolve_compute_policy("gpu_preferred")

            self.assertEqual(snapshot["gpus"], [])
            self.assertFalse(snapshot["cuda"]["driver_available"])
            self.assertFalse(snapshot["toolchains"]["ollama"]["available"])
            self.assertEqual(snapshot["memory"]["status"], "unavailable")
            self.assertEqual(telemetry["cpu_percent"], None)
            self.assertEqual(policy["candidate_device"], "cpu")
            self.assertEqual(policy["fallback_reason"], "gpu_unavailable")
            self.assertTrue(policy["basic_retrieval_available"])

    def test_runtime_settings_expose_compute_defaults_with_owner_help(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory))
            state_db = StateDatabase(settings.state_db_path)
            control = LocalControlService(
                settings,
                state_db=state_db,
                hardware=HardwareCapabilityService(
                    settings,
                    command_runner=FakeRunner(gpu=False),
                    url_reader=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("offline")),
                    psutil_module=None,
                ),
            )
            try:
                snapshot = control.get_settings()
                definition = snapshot["definitions"]["compute_mode"]
                self.assertEqual(definition["default"], "auto")
                self.assertEqual(definition["recommended"], "auto")
                self.assertTrue(definition["recommendation_reason"])
                self.assertTrue(definition["when_to_change"])
                self.assertEqual(definition["choices"], ["auto", "gpu_preferred", "cpu_only"])
                self.assertIn("hardware_foreground_interval_seconds", snapshot["definitions"])
            finally:
                control.close()

    def test_control_api_exposes_hardware_telemetry_and_compute_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = self.make_settings(Path(directory))
            hardware = HardwareCapabilityService(
                settings,
                command_runner=FakeRunner(gpu=True),
                url_reader=fake_url_reader,
                psutil_module=FakePsutil,
            )
            control = LocalControlService(settings, hardware=hardware)
            with TestClient(create_control_app(settings, service=control, token="secret")) as client:
                headers = {"X-LingJi-Token": "secret"}
                capabilities = client.get("/api/hardware/capabilities", headers=headers)
                telemetry = client.get("/api/hardware/telemetry", headers=headers)
                policy = client.get("/api/compute/policy", headers=headers)
                updated = client.patch(
                    "/api/compute/policy",
                    headers=headers,
                    json={"mode": "cpu_only"},
                )

                self.assertEqual(capabilities.status_code, 200)
                self.assertEqual(telemetry.status_code, 200)
                self.assertEqual(policy.status_code, 200)
                self.assertEqual(updated.status_code, 200)
                self.assertEqual(updated.json()["requested_mode"], "cpu_only")
                self.assertEqual(updated.json()["candidate_device"], "cpu")
                self.assertTrue(updated.json()["basic_retrieval_available"])


if __name__ == "__main__":
    unittest.main()
