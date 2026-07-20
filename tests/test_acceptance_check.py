from __future__ import annotations

import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src.acceptance import AcceptanceChecker
from src.acceptance_reports import render_markdown
from src.config import Settings


class AcceptanceCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(root / "vault"),
            storage_dir=str(root / "storage"),
            log_dir=str(root / "logs"),
            backup_dir=str(root / "backups"),
            startup_min_free_gb=0,
            vault_auto_init=False,
        )
        self.settings.vault_path.mkdir(parents=True)
        self.settings.storage_path.mkdir(parents=True)
        (self.settings.vault_path / "note.md").write_text("# note\n\ncontent\n", encoding="utf-8")
        for path in (self.settings.state_db_path, self.settings.memory_db_path):
            with closing(sqlite3.connect(path)) as connection:
                with connection:
                    connection.execute("CREATE TABLE sample(value TEXT)")
        self.export = root / "chatgpt.zip"
        with zipfile.ZipFile(self.export, "w") as archive:
            archive.writestr("conversations.json", "[]")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("src.acceptance.StartupHealthChecker.run")
    def test_report_is_read_only_and_recognizes_export(self, health_run):
        health_run.return_value = {
            "checks": [{"name": "vault", "status": "ok", "message": "ok"}]
        }
        report = AcceptanceChecker(self.settings, chatgpt_export=self.export).run()
        self.assertTrue(report["read_only"])
        self.assertTrue(report["inputs_unchanged"])
        self.assertEqual(report["error_count"], 0)
        export_check = next(item for item in report["checks"] if item["name"] == "chatgpt_export")
        self.assertEqual(export_check["status"], "ok")
        markdown = render_markdown(report)
        self.assertIn("只读", markdown)
        self.assertIn("chatgpt_export", markdown)

    @patch("src.acceptance.StartupHealthChecker.run", return_value={"checks": []})
    def test_missing_vault_is_reported_without_creating_it(self, _health_run):
        missing = Path(self.temp_dir.name) / "missing-vault"
        settings = Settings(
            _env_file=None,
            vault_dir=str(missing),
            storage_dir=str(Path(self.temp_dir.name) / "other-storage"),
            backup_dir=str(Path(self.temp_dir.name) / "other-backup"),
            startup_min_free_gb=0,
            vault_auto_init=False,
        )
        report = AcceptanceChecker(settings).run()
        self.assertGreater(report["error_count"], 0)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
