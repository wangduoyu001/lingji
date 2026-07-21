from __future__ import annotations

import sqlite3
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

    def test_cancel_only_accepts_queued_or_retrying(self):
        queued = self.queue.enqueue("web", payload={"title": "queued"})
        cancelled = self.queue.cancel(queued["job_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertIsNotNone(cancelled["completed_at"])
        self.assertIsNone(cancelled["lease_token"])
        with self.assertRaises(RuntimeError):
            self.queue.cancel(queued["job_id"])

        running = self.queue.enqueue("web", payload={"title": "running"})
        self.queue.claim("worker", job_id=running["job_id"])
        with self.assertRaises(RuntimeError):
            self.queue.cancel(running["job_id"])

    def test_retry_resets_failed_and_cancelled_jobs(self):
        failed = self.queue.enqueue("web", payload={"title": "failed"}, max_attempts=1)
        claimed = self.queue.claim("worker", job_id=failed["job_id"])
        self.queue.heartbeat(
            claimed["job_id"],
            "worker",
            claimed["lease_token"],
            progress_current=3,
            progress_total=9,
            progress_message="working",
        )
        self.queue.fail(claimed["job_id"], "private failure", retry_delay_seconds=0)
        retried = self.queue.retry(failed["job_id"])
        self.assertEqual(retried["status"], "queued")
        self.assertEqual(retried["attempts"], 0)
        self.assertIsNone(retried["last_error"])
        self.assertEqual(retried["result"], {})
        self.assertIsNone(retried["completed_at"])
        self.assertEqual(retried["progress_current"], 0)
        self.assertEqual(retried["progress_total"], 0)
        self.assertIsNone(retried["progress_message"])

        cancelled = self.queue.enqueue("media", payload={"title": "cancelled"})
        self.queue.cancel(cancelled["job_id"])
        self.assertEqual(self.queue.retry(cancelled["job_id"])["status"], "queued")

        completed = self.queue.enqueue("codex", payload={"title": "done"})
        self.queue.claim("worker", job_id=completed["job_id"])
        self.queue.complete(completed["job_id"], {"ok": True})
        with self.assertRaises(RuntimeError):
            self.queue.retry(completed["job_id"])

    def test_list_page_and_count_use_sql_filters_and_offsets(self):
        for index in range(5):
            self.queue.enqueue(
                "web" if index < 3 else "media",
                payload={"title": f"item-{index}"},
                adapter_name=f"adapter-{index}",
            )
        page = self.queue.list_page(source_type="web", q="adapter", limit=2, offset=1)
        self.assertEqual(len(page), 2)
        self.assertEqual(self.queue.count(source_type="web", q="adapter"), 3)
        self.assertTrue(all(item["source_type"] == "web" for item in page))
        with sqlite3.connect(self.db_path) as connection:
            plan = connection.execute(
                "EXPLAIN QUERY PLAN SELECT * FROM extraction_jobs WHERE source_type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                ("web", 2, 1),
            ).fetchall()
        self.assertTrue(plan)


if __name__ == "__main__":
    unittest.main()
