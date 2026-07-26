from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from src.extraction.base import ExtractionAdapter
from src.extraction.models import ExtractedDocument, ExtractionBatch
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.extraction.worker import ExtractionWorker
from src.memory import VaultLayout


class DummyAdapter(ExtractionAdapter):
    name = "dummy"
    version = "1"
    source_types = ("dummy",)

    def extract(self, request):
        return ExtractionBatch(
            documents=(
                ExtractedDocument(
                    stable_id="LJ-DUMMY-1",
                    title="dummy",
                    body="# dummy",
                    source_type="chatgpt",
                ),
            )
        )


class ExtractionWorkerTests(unittest.TestCase):
    def test_worker_processes_queue_and_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layout = VaultLayout(root / "vault")
            layout.ensure()
            queue = SQLiteExtractionQueue(root / "storage" / "state.db")
            registry = AdapterRegistry()
            registry.register(DummyAdapter())
            pipeline = ExtractionPipeline(
                queue,
                registry,
                VaultExtractionSink(layout, root / "storage"),
            )
            job = pipeline.enqueue("dummy")
            worker = ExtractionWorker(pipeline, poll_seconds=0.05, batch_size=1)
            worker.start()
            deadline = time.time() + 2
            while time.time() < deadline and queue.get(job["job_id"])["status"] != "completed":
                time.sleep(0.02)
            worker.stop()
            self.assertFalse(worker.running)
            self.assertEqual(queue.get(job["job_id"])["status"], "completed")


if __name__ == "__main__":
    unittest.main()
