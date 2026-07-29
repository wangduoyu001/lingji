from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from src.config import Settings
from src.health import StartupHealthChecker


class StartupHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _settings(self, **overrides):
        values = {
            "_env_file": None,
            "vault_dir": str(self.root / "vault"),
            "storage_dir": str(self.root / "storage"),
            "log_dir": str(self.root / "logs"),
            "backup_dir": str(self.root / "backup"),
            "startup_health_fail_on_error": True,
            "startup_require_ollama": False,
            "startup_min_free_gb": 0,
        }
        values.update(overrides)
        return Settings(**values)

    def test_optional_dependencies_degrade_without_blocking_start(self):
        settings = self._settings()
        checker = StartupHealthChecker(settings)
        with patch("src.health.requests.get", side_effect=requests.ConnectionError("offline")), patch(
            "src.health.shutil.which", return_value=None
        ):
            report = checker.run()
        self.assertEqual(report["status"], "degraded")
        self.assertEqual(report["error_count"], 0)
        checker.ensure_startable(report)

    def test_invalid_vault_blocks_start_when_strict(self):
        vault = self.root / "vault-file"
        vault.write_text("not a directory", encoding="utf-8")
        settings = self._settings(vault_dir=str(vault), vault_auto_init=False)
        checker = StartupHealthChecker(settings)
        with patch("src.health.requests.get", side_effect=requests.ConnectionError("offline")), patch(
            "src.health.shutil.which", return_value="tool"
        ):
            report = checker.run()
        self.assertGreater(report["error_count"], 0)
        with self.assertRaises(RuntimeError):
            checker.ensure_startable(report)

    def test_packaged_runtime_requires_explicit_data_root(self):
        checker = StartupHealthChecker(self._settings())
        with patch.dict(
            "os.environ",
            {"LINGJI_PACKAGED_RUNTIME": "1", "LINGJI_WORKSPACE": "acceptance"},
            clear=False,
        ), patch("src.health.requests.get", side_effect=requests.ConnectionError("offline")), patch(
            "src.health.shutil.which", return_value="tool"
        ):
            report = checker.run()

        policy = next(item for item in report["checks"] if item["name"] == "data_root_policy")
        self.assertEqual(policy["status"], "error")
        self.assertEqual(policy["workspace"], "acceptance")

    def test_packaged_runtime_reports_non_system_drive_policy(self):
        checker = StartupHealthChecker(self._settings())
        with patch.dict(
            "os.environ",
            {
                "LINGJI_PACKAGED_RUNTIME": "1",
                "LINGJI_WORKSPACE": "acceptance",
                "LINGJI_OWNER_DATA_ROOT": str(self.root),
            },
            clear=False,
        ), patch.object(
            StartupHealthChecker,
            "_is_windows_system_drive",
            return_value=False,
        ), patch("src.health.requests.get", side_effect=requests.ConnectionError("offline")), patch(
            "src.health.shutil.which", return_value="tool"
        ):
            report = checker.run()

        policy = next(item for item in report["checks"] if item["name"] == "data_root_policy")
        self.assertEqual(policy["status"], "ok")
        self.assertFalse(policy["c_drive_write_detected"])

    def test_packaged_runtime_marks_c_drive_policy_as_error_without_io(self):
        checker = StartupHealthChecker(self._settings())
        checks = []
        with patch.dict(
            "os.environ",
            {
                "LINGJI_PACKAGED_RUNTIME": "1",
                "LINGJI_WORKSPACE": "production",
                "LINGJI_OWNER_DATA_ROOT": r"C:\LingJiData\production",
            },
            clear=False,
        ):
            checker._check_data_root_policy(checks)

        self.assertEqual(checks[0]["status"], "error")
        self.assertTrue(checks[0]["c_drive_write_detected"])


if __name__ == "__main__":
    unittest.main()
