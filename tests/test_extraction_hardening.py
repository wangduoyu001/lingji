from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.extraction.models import ExtractedDocument, ExtractionBatch
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout


class ExtractionHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.db = root / "state.db"
        self.vault = root / "vault"
        self.storage = root / "storage"
        self.layout = VaultLayout(self.vault)
        self.layout.ensure()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_options_are_part_of_idempotency(self):
        queue = SQLiteExtractionQueue(self.db)
        first = queue.enqueue("chatgpt", payload={}, options={"project_id": "LingJi"})
        second = queue.enqueue("chatgpt", payload={}, options={"project_id": "Drama"})
        self.assertNotEqual(first["job_id"], second["job_id"])

    def test_force_requeue_refreshes_same_job_parameters(self):
        queue = SQLiteExtractionQueue(self.db)
        job = queue.enqueue(
            "chatgpt",
            payload={"version": 1},
            options={"project_id": "LingJi"},
            idempotency_key="fixed-key",
            priority=100,
            max_attempts=2,
        )
        queue.claim("worker")
        queue.complete(job["job_id"], {"ok": True})
        forced = queue.enqueue(
            "chatgpt",
            payload={"version": 2},
            options={"project_id": "Drama", "privacy_scan": False},
            idempotency_key="fixed-key",
            priority=10,
            max_attempts=5,
            force=True,
        )
        self.assertEqual(forced["job_id"], job["job_id"])
        self.assertEqual(forced["status"], "queued")
        self.assertEqual(forced["payload"]["version"], 2)
        self.assertEqual(forced["options"]["project_id"], "Drama")
        self.assertFalse(forced["options"]["privacy_scan"])
        self.assertEqual(forced["priority"], 10)
        self.assertEqual(forced["max_attempts"], 5)

    def test_lease_token_blocks_stale_worker_completion(self):
        queue = SQLiteExtractionQueue(self.db)
        job = queue.enqueue("chatgpt", payload={})
        claimed = queue.claim("worker-a")
        with self.assertRaises(RuntimeError):
            queue.complete(
                job["job_id"],
                {"ok": True},
                worker_id="worker-a",
                lease_token="wrong-token",
            )
        completed = queue.complete(
            job["job_id"],
            {"ok": True},
            worker_id="worker-a",
            lease_token=claimed["lease_token"],
        )
        self.assertEqual(completed["status"], "completed")

    def test_sink_preserves_owner_review_and_manual_notes(self):
        sink = VaultExtractionSink(self.layout, self.storage)
        document = ExtractedDocument(
            stable_id="LJ-DECISION-001",
            title="候选决策",
            body="# 候选决策\n\n自动内容",
            source_type="codex",
            destination="decision",
            metadata={"status": "needs_review", "owner_confirmed": False},
        )
        first = sink.write_batch(
            ExtractionBatch(documents=(document,)),
            adapter_name="test",
            adapter_version="1",
        )
        path = Path(first["created"][0]["path"])
        text = path.read_text(encoding="utf-8")
        text = text.replace("owner_confirmed: false", "owner_confirmed: true")
        text = text.replace("status: needs_review", "status: active")
        text = text.replace("## 人工备注\n\n", "## 人工备注\n\n主人已确认。\n")
        path.write_text(text, encoding="utf-8")

        changed = ExtractedDocument(
            stable_id=document.stable_id,
            title=document.title,
            body="# 候选决策\n\n自动内容已更新",
            source_type="codex",
            destination="decision",
            metadata={"status": "needs_review", "owner_confirmed": False},
        )
        sink.write_batch(
            ExtractionBatch(documents=(changed,)),
            adapter_name="test",
            adapter_version="2",
        )
        updated = path.read_text(encoding="utf-8")
        self.assertIn("owner_confirmed: true", updated)
        self.assertIn("status: active", updated)
        self.assertIn("主人已确认", updated)


if __name__ == "__main__":
    unittest.main()
