from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import requests

from src.acceptance import AcceptanceChecker
from src.acceptance_reports import AcceptanceReportStore
from src.config import Settings


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ReadOnlyAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.vault = self.root / "vault"
        self.vault.mkdir()
        self.note = self.vault / "note.md"
        self.note.write_text("# note\n\nowner content\n", encoding="utf-8")
        self.attachment = self.vault / "image.bin"
        self.attachment.write_bytes(b"owner attachment")
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(self.vault),
            storage_dir=str(self.root / "storage"),
            log_dir=str(self.root / "logs"),
            backup_dir=str(self.root / "backups"),
            vault_auto_init=False,
            startup_min_free_gb=0,
            startup_health_timeout_seconds=0.2,
        )

    @patch("src.health.requests.get")
    def test_checker_does_not_create_runtime_directories_or_change_inputs(self, request_get):
        request_get.return_value.raise_for_status.return_value = None
        request_get.return_value.content = b'{"models": [{"name": "qwen3:8b"}]}'
        request_get.return_value.json.return_value = {"models": [{"name": "qwen3:8b"}]}
        before_note = sha256(self.note)
        before_attachment = sha256(self.attachment)
        before_stat = self.note.stat()

        report = AcceptanceChecker(self.settings, hash_inputs=True).run()

        self.assertTrue(report["read_only"])
        self.assertTrue(report["inputs_unchanged"])
        self.assertEqual(sha256(self.note), before_note)
        self.assertEqual(sha256(self.attachment), before_attachment)
        self.assertEqual(self.note.stat().st_mtime_ns, before_stat.st_mtime_ns)
        self.assertFalse(self.settings.storage_path.exists())
        self.assertFalse(self.settings.log_path.exists())
        self.assertFalse(self.settings.backup_path.exists())
        ollama = next(item for item in report["checks"] if item["name"] == "health:ollama")
        self.assertEqual(ollama["details"]["models"], ["qwen3:8b"])
        immutability = next(item for item in report["checks"] if item["name"] == "input_immutability")
        self.assertEqual(immutability["details"]["before"]["vault"]["files"], 2)

    @patch("src.health.requests.get", side_effect=requests.ConnectionError("offline"))
    def test_existing_sqlite_is_opened_without_modifying_it(self, _request_get):
        self.settings.storage_path.mkdir(parents=True)
        database = self.settings.memory_db_path
        with closing(sqlite3.connect(database)) as connection:
            with connection:
                connection.execute("CREATE TABLE sample(value TEXT)")
                connection.execute("INSERT INTO sample(value) VALUES ('ok')")
        before_hash = sha256(database)
        before_mtime = database.stat().st_mtime_ns

        report = AcceptanceChecker(self.settings, hash_inputs=True).run()

        check = next(item for item in report["checks"] if item["name"] == "memory_db")
        self.assertEqual(check["status"], "ok")
        self.assertEqual(sha256(database), before_hash)
        self.assertEqual(database.stat().st_mtime_ns, before_mtime)
        self.assertTrue(report["inputs_unchanged"])
        immutability = next(item for item in report["checks"] if item["name"] == "input_immutability")
        memory_fingerprint = immutability["details"]["before"]["memory_db"]
        self.assertEqual(set(memory_fingerprint), {"database", "wal", "shm"})

    @patch("src.health.requests.get", side_effect=requests.ConnectionError("offline"))
    def test_deep_zip_check_reports_crc_corruption(self, _request_get):
        archive_path = self.root / "chatgpt.zip"
        payload = b"hello acceptance crc"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("conversations.json", payload)
        raw = bytearray(archive_path.read_bytes())
        offset = raw.find(payload)
        self.assertGreaterEqual(offset, 0)
        raw[offset] ^= 0x01
        archive_path.write_bytes(raw)

        report = AcceptanceChecker(
            self.settings,
            chatgpt_export=archive_path,
            deep_zip_check=True,
            hash_inputs=True,
        ).run()

        check = next(item for item in report["checks"] if item["name"] == "chatgpt_export")
        self.assertEqual(check["status"], "error")
        self.assertIn("CRC", check["message"])

    def test_report_store_writes_only_to_report_directory(self):
        store = AcceptanceReportStore(self.settings.storage_path / "reports" / "acceptance")
        report = {
            "schema_version": 2,
            "generated_at": "2026-07-19T00:00:00+00:00",
            "status": "passed",
            "read_only": True,
            "checks": [],
            "error_count": 0,
            "warning_count": 0,
            "inputs_unchanged": True,
        }
        saved = store.save(report)
        self.assertTrue(Path(saved["json_path"]).is_file())
        self.assertTrue(Path(saved["markdown_path"]).is_file())
        listed = store.list_reports()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
