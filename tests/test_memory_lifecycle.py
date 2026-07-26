from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app
from src.retrieval.memory_db import MemoryDatabase
from src.scheduler.cron import CronScheduler
from src.storage.state_db import StateDatabase


def assert_sqlite_files_deletable(testcase: unittest.TestCase, path: Path) -> None:
    """Delete the database and any WAL sidecars; Windows fails here if a handle remains."""
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        if candidate.exists():
            candidate.unlink()
        testcase.assertFalse(candidate.exists(), f"SQLite file is still present: {candidate}")


class MemoryLifecycleTests(unittest.TestCase):
    def test_memory_database_releases_file_after_each_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "memory.db"
            for _ in range(20):
                database = MemoryDatabase(db_path)
                self.assertTrue(database.integrity_check()["healthy"])
                assert_sqlite_files_deletable(self, db_path)

    def test_scheduler_stop_waits_for_running_job_before_database_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "state.db"
            state_db = StateDatabase(db_path)
            started = threading.Event()
            release = threading.Event()

            def runner(_name: str) -> None:
                started.set()
                release.wait(timeout=2)

            scheduler = CronScheduler(state_db, poll_seconds=0.05, max_workers=1)
            scheduler.add_job("startup", 1, run_on_start=True)
            scheduler.start(runner)
            self.assertTrue(started.wait(timeout=2), "Scheduled job did not start")

            release.set()
            scheduler.stop()
            assert_sqlite_files_deletable(self, db_path)

    def test_control_api_context_releases_temporary_sqlite_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(
                _env_file=None,
                vault_dir=str(root / "vault"),
                storage_dir=str(root / "storage"),
                log_dir=str(root / "logs"),
                backup_dir=str(root / "backups"),
                startup_min_free_gb=0,
            )
            settings.vault_path.mkdir(parents=True)
            with TestClient(create_control_app(settings, token="secret")) as client:
                response = client.get("/api/settings", headers={"X-LingJi-Token": "secret"})
                self.assertEqual(response.status_code, 200)

            assert_sqlite_files_deletable(self, settings.state_db_path)


if __name__ == "__main__":
    unittest.main()
