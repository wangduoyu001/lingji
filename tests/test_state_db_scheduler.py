import tempfile
import time
import unittest
import threading
from pathlib import Path

from src.scheduler.cron import CronScheduler
from src.storage.state_db import StateDatabase


class StateDatabaseSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = StateDatabase(Path(self.temp_dir.name) / "state.db")
        self.schedulers = []

    def tearDown(self):
        for scheduler in self.schedulers:
            scheduler.stop()
        self.temp_dir.cleanup()

    def _scheduler(self):
        scheduler = CronScheduler(self.db, poll_seconds=0.05, max_workers=1)
        self.schedulers.append(scheduler)
        return scheduler

    def test_job_does_not_run_immediately_by_default(self):
        calls = []
        scheduler = self._scheduler()
        scheduler.add_job("daily", 1, run_on_start=False)
        scheduler.start(lambda name: calls.append(name))
        time.sleep(0.2)
        self.assertEqual(calls, [])

    def test_run_on_start_job_persists_success(self):
        calls = []
        scheduler = self._scheduler()
        scheduler.add_job("startup", 1, run_on_start=True)
        scheduler.start(lambda name: calls.append(name))
        deadline = time.time() + 2
        while not calls and time.time() < deadline:
            time.sleep(0.05)
        self.assertEqual(calls, ["startup"])
        deadline = time.time() + 2
        job = None
        while time.time() < deadline:
            job = next(item for item in self.db.list_scheduler_jobs() if item["name"] == "startup")
            if job["status"] == "success":
                break
            time.sleep(0.05)
        self.assertEqual(job["status"], "success")
        self.assertIsNotNone(job["last_finished_at"])

    def test_processing_hash_is_independent_from_file_index(self):
        self.assertTrue(self.db.needs_processing("source-1", "summary", "1", "hash-a"))
        self.db.mark_processing_started("source-1", "summary", "1", "hash-a")
        self.db.mark_processing_finished(
            "source-1",
            "summary",
            "1",
            "hash-a",
            success=True,
            result={"summary": "done"},
        )
        self.assertFalse(self.db.needs_processing("source-1", "summary", "1", "hash-a"))
        self.assertTrue(self.db.needs_processing("source-1", "summary", "1", "hash-b"))

    def test_events_are_append_only(self):
        first = self.db.append_event("created", "source", "source-1", {"value": 1})
        second = self.db.append_event("updated", "source", "source-1", {"value": 2})
        self.assertGreater(second, first)
        events = self.db.recent_events(limit=10)
        self.assertEqual(events[0]["event_type"], "updated")
        self.assertEqual(events[1]["event_type"], "created")

    def test_stale_running_job_is_reclaimed_after_restart(self):
        self.db.upsert_scheduler_job("stale", 1, run_on_start=True)
        self.db.mark_job_started("stale")
        with self.db._lock, self.db._connection() as connection:
            connection.execute(
                "UPDATE scheduler_jobs SET status = 'running', lease_expires_at = ?, next_run_at = ? WHERE name = ?",
                ("2000-01-01T00:00:00", "2000-01-01T00:00:00", "stale"),
            )
        calls = []
        scheduler = self._scheduler()
        scheduler.start(lambda name: calls.append(name))
        deadline = time.time() + 2
        while not calls and time.time() < deadline:
            time.sleep(0.02)
        self.assertEqual(calls, ["stale"])

    def test_two_scheduler_instances_claim_one_due_job(self):
        self.db.upsert_scheduler_job("shared", 1, run_on_start=True)
        calls = []
        gate = threading.Event()
        release = threading.Event()

        def runner(name):
            calls.append(name)
            gate.set()
            release.wait(1)

        first = CronScheduler(self.db, poll_seconds=0.01, max_workers=1)
        second = CronScheduler(self.db, poll_seconds=0.01, max_workers=1)
        self.schedulers.extend([first, second])
        first.start(runner)
        second.start(runner)
        assert gate.wait(1)
        time.sleep(0.1)
        release.set()
        deadline = time.time() + 2
        while len(calls) < 1 and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual(calls, ["shared"])


if __name__ == "__main__":
    unittest.main()
