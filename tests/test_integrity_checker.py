import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.scheduler.integrity import IntegrityChecker


class FakeIndex:
    def __init__(self, entries):
        self.entries = entries

    def get_all(self):
        return self.entries


class IntegrityCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.settings = SimpleNamespace(
            log_dir=str(base / "logs"),
            vault_path=base / "vault",
            index_private=False,
        )
        self.settings.vault_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detects_missing_source_broken_link_and_orphan(self):
        index = FakeIndex(
            [
                {
                    "id": "LJ-NOTE-1",
                    "relative_path": "03-Knowledge/AI/test.md",
                    "memory_type": "knowledge",
                    "status": "active",
                    "content_hash": "hash-1",
                    "is_private": False,
                    "project": [],
                    "related": ["[[03-Knowledge/AI/missing]]"],
                    "people": [],
                    "organizations": [],
                    "tools": [],
                    "models": [],
                    "sources": [],
                    "tasks": [],
                    "decisions": [],
                }
            ]
        )
        report = IntegrityChecker(self.settings).check(index)
        self.assertEqual(report["counts"]["missing_sources"], 1)
        self.assertEqual(report["counts"]["broken_links"], 1)
        self.assertTrue(report["healthy"])

    def test_private_leak_is_unhealthy(self):
        index = FakeIndex(
            [
                {
                    "id": "LJ-PRIVATE-1",
                    "relative_path": "08-Private/Personal/secret.md",
                    "memory_type": "source",
                    "status": "active",
                    "content_hash": "hash-private",
                    "is_private": True,
                    "project": [],
                    "related": [],
                    "people": [],
                    "organizations": [],
                    "tools": [],
                    "models": [],
                    "sources": [],
                    "tasks": [],
                    "decisions": [],
                }
            ]
        )
        report = IntegrityChecker(self.settings).check(index)
        self.assertFalse(report["healthy"])
        self.assertEqual(report["counts"]["private_leaks"], 1)


if __name__ == "__main__":
    unittest.main()
