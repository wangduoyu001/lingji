from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from src.extraction.queue import SQLiteExtractionQueue


class SQLiteExtractionQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "state.db"
        self.queue = SQLiteExtractionQueue(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_enqueue_is_idempotent(self):
        first = self.queue.enqueue("chatgpt", payload={"a": 1})
        second = self.queue.enqueue("chatgpt", payload={"a": 1})
        self.assertEqual(first["job_id"], second["job_id"])
        self.assertEqual(self.queue.stats()["queued"], 1)

    def test_claim_complete(self):
        job = self.queue.enqueue("codex", payload={"summary": "done"})
        claimed = self.queue.claim("worker-1")
        self.assertEqual(claimed["job_id"], job["job_id"])
        self.assertEqual(claimed["status"], "running")
        self.assertEqual(claimed["attempts"], 1)
        completed = self.queue.complete(job["job_id"], {"ok": True})
        self.assertEqual(completed["status"], "completed")
        self.assertTrue(completed["result"]["ok"])

    def test_failure_retries_then_fails(self):
        job = self.queue.enqueue("chatgpt", payload={"a": 1}, max_attempts=2)
        first = self.queue.claim("worker")
        retrying = self.queue.fail(first["job_id"], "boom", retry_delay_seconds=0)
        self.assertEqual(retrying["status"], "retrying")
        second = self.queue.claim("worker")
        failed = self.queue.fail(second["job_id"], "boom again", retry_delay_seconds=0)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["attempts"], 2)

    def test_force_requeues_terminal_job(self):
        job = self.queue.enqueue("codex", payload={"summary": "done"})
        self.queue.claim("worker")
        self.queue.complete(job["job_id"], {"ok": True})
        forced = self.queue.enqueue("codex", payload={"summary": "done"}, force=True)
        self.assertEqual(forced["job_id"], job["job_id"])
        self.assertEqual(forced["status"], "queued")
        self.assertEqual(forced["attempts"], 0)

    def test_release_stale(self):
        past = datetime.now() - timedelta(hours=1)
        job = self.queue.enqueue("chatgpt", payload={"a": 1}, now=past)
        claimed = self.queue.claim("worker", now=past)
        self.assertEqual(claimed["status"], "running")
        released = self.queue.release_stale(stale_after_seconds=30, now=datetime.now())
        self.assertEqual(released, 1)
        self.assertEqual(self.queue.get(job["job_id"])["status"], "retrying")


if __name__ == "__main__":
    unittest.main()
