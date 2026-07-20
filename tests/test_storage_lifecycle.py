from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.config import Settings
from src.storage import StorageLifecycleManager


class StorageLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(root / "vault"),
            storage_dir=str(root / "storage"),
            log_dir=str(root / "logs"),
            backup_dir=str(root / "backups"),
        )
        self.manager = StorageLifecycleManager(self.settings)
        self.settings.vault_path.mkdir(parents=True)
        (self.settings.storage_path / "raw" / "web").mkdir(parents=True)
        (self.settings.storage_path / "derived" / "media").mkdir(parents=True)
        (self.settings.storage_path / "versions").mkdir(parents=True)
        self.raw_file = self.settings.storage_path / "raw" / "web" / "source.html"
        self.derived_file = self.settings.storage_path / "derived" / "media" / "frame.jpg"
        self.version_file = self.settings.storage_path / "versions" / "note.md"
        self.vault_file = self.settings.vault_path / "knowledge.md"
        for path in (self.raw_file, self.derived_file, self.version_file, self.vault_file):
            path.write_text(path.name, encoding="utf-8")
        old = 1_600_000_000
        for path in (self.raw_file, self.derived_file, self.version_file, self.vault_file):
            os.utime(path, (old, old))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_preview_never_includes_raw_or_vault(self):
        plan = self.manager.create_plan(
            {
                "retention_days": {"raw": 1, "vault": 1, "derived": 1},
                "max_category_gb": {},
            }
        )
        sources = {row["source"] for row in plan["actions"]}
        self.assertIn(str(self.derived_file), sources)
        self.assertNotIn(str(self.raw_file), sources)
        self.assertNotIn(str(self.vault_file), sources)

    def test_execute_moves_to_recovery_area_and_restore_returns_file(self):
        plan = self.manager.create_plan(
            {"retention_days": {"derived": 1}, "max_category_gb": {}}
        )
        with self.assertRaises(PermissionError):
            self.manager.execute_plan(plan["plan_id"], "wrong")
        executed = self.manager.execute_plan(
            plan["plan_id"], f"EXECUTE_STORAGE_PLAN:{plan['plan_id']}"
        )
        self.assertEqual(executed["status"], "completed")
        self.assertFalse(self.derived_file.exists())
        recovery = Path(executed["completed_actions"][0]["recovery_path"])
        self.assertTrue(recovery.exists())
        restored = self.manager.restore_plan(
            plan["plan_id"], f"RESTORE_STORAGE_PLAN:{plan['plan_id']}"
        )
        self.assertEqual(restored["restore_status"], "completed")
        self.assertTrue(self.derived_file.exists())
        self.assertFalse(recovery.exists())

    def test_cold_archive_copies_verifies_and_removes_source(self):
        cold = Path(self.temp_dir.name) / "cold"
        plan = self.manager.create_plan(
            {
                "retention_days": {"versions": 1},
                "max_category_gb": {},
                "cold_storage_enabled": True,
                "cold_storage_path": str(cold),
                "archive_categories": ["versions"],
            }
        )
        executed = self.manager.execute_plan(
            plan["plan_id"], f"EXECUTE_STORAGE_PLAN:{plan['plan_id']}"
        )
        destination = cold / "versions" / "note.md"
        self.assertTrue(destination.exists())
        self.assertFalse(self.version_file.exists())
        self.assertEqual(destination.read_text(encoding="utf-8"), "note.md")
        self.assertEqual(executed["completed_actions"][0]["action"], "move_cold")

    def test_inventory_reports_categories_and_disk(self):
        result = self.manager.inventory()
        self.assertGreaterEqual(result["totals"]["files"], 4)
        self.assertIn("raw", result["categories"])
        self.assertTrue(result["categories"]["raw"]["protected"])
        self.assertGreater(result["totals"]["disk_total_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
