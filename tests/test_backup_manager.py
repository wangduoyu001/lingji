from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.config import Settings
from src.storage import BackupManager


class BackupManagerTests(unittest.TestCase):
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
        self.settings.vault_path.mkdir(parents=True)
        self.settings.storage_path.mkdir(parents=True)
        (self.settings.vault_path / "note.md").write_text("# 记忆\n", encoding="utf-8")
        self.settings.runtime_settings_path.write_text('{"schema_version": 1, "overrides": {}}\n', encoding="utf-8")
        for db_path in (self.settings.state_db_path, self.settings.memory_db_path):
            with sqlite3.connect(db_path) as connection:
                connection.execute("CREATE TABLE sample(value TEXT)")
                connection.execute("INSERT INTO sample(value) VALUES ('ok')")
        (self.settings.storage_path / "pemis_index.json").write_text('{"entries": {}}\n', encoding="utf-8")
        self.manager = BackupManager(self.settings)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_metadata_backup_is_created_and_verified(self):
        result = self.manager.create_backup(profile="metadata")
        backup = Path(result["path"])
        self.assertTrue(backup.exists())
        self.assertTrue(result["verification"]["valid"])
        self.assertGreater(result["summary"]["files"], 0)
        listed = self.manager.list_backups()
        self.assertEqual(listed[0]["backup_id"], result["backup_id"])

    def test_restore_is_staged_without_overwriting_vault(self):
        result = self.manager.create_backup(profile="metadata")
        current = self.settings.vault_path / "note.md"
        current.write_text("# 当前版本\n", encoding="utf-8")
        staged = self.manager.stage_restore(
            result["path"], f"STAGE_RESTORE:{result['backup_id']}"
        )
        staged_note = Path(staged["staging_path"]) / "data" / "vault" / "note.md"
        self.assertTrue(staged_note.exists())
        self.assertEqual(staged_note.read_text(encoding="utf-8"), "# 记忆\n")
        self.assertEqual(current.read_text(encoding="utf-8"), "# 当前版本\n")

    def test_restore_rejects_wrong_confirmation(self):
        result = self.manager.create_backup(profile="metadata")
        with self.assertRaises(PermissionError):
            self.manager.stage_restore(result["path"], "wrong")

    def test_backup_path_cannot_escape_backup_root(self):
        outside = Path(self.temp_dir.name) / "outside.zip"
        outside.write_bytes(b"not a backup")
        with self.assertRaises(PermissionError):
            self.manager.verify_backup(outside)


if __name__ == "__main__":
    unittest.main()
