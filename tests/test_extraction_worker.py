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

    def test_revoked_automatic_memory_job_cannot_write_downstream_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layout = VaultLayout(root / "vault")
            layout.ensure()
            db_path = root / "lingji_state.db"
            queue = SQLiteExtractionQueue(db_path)
            job = queue.enqueue(
                "automatic_memory_snapshot", payload={"source_id": "source-a"}
            )
            pipeline = ExtractionPipeline(queue, AdapterRegistry(), VaultExtractionSink(layout, root / "storage"))

            result = pipeline.process_job(job["job_id"], worker_id="revoking-worker")

            self.assertEqual(result["job"]["status"], "failed")
            self.assertIn("authorization", result["job"]["last_error"])
            self.assertEqual(queue.stats()["completed"], 0)
            self.assertEqual(list((root / "vault").rglob("*.md")), [])

    def test_ordinary_job_payload_source_id_does_not_trigger_automatic_memory_gate(self):
        class OrdinaryAdapter(ExtractionAdapter):
            name = "ordinary-source"
            version = "1"
            source_types = ("ordinary",)

            def extract(self, request):
                return ExtractionBatch(
                    documents=(
                        ExtractedDocument(
                            stable_id="LJ-ORDINARY-1",
                            title="ordinary",
                            body="# ordinary",
                            source_type="ordinary",
                        ),
                    )
                )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layout = VaultLayout(root / "vault")
            layout.ensure()
            queue = SQLiteExtractionQueue(root / "state.db")
            adapters = AdapterRegistry()
            adapters.register(OrdinaryAdapter())
            pipeline = ExtractionPipeline(queue, adapters, VaultExtractionSink(layout, root / "storage"))
            job = pipeline.enqueue("ordinary", payload={"source_id": "unrelated-source"})

            result = pipeline.process_job(job["job_id"], worker_id="ordinary-worker")

            self.assertEqual(result["job"]["status"], "completed")

    def test_common_pipeline_rejects_direct_internal_snapshot_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layout = VaultLayout(root / "vault")
            layout.ensure()
            queue = SQLiteExtractionQueue(root / "state.db")
            pipeline = ExtractionPipeline(queue, AdapterRegistry(), VaultExtractionSink(layout, root / "storage"))

            with self.assertRaisesRegex(PermissionError, "専用|dedicated|internal"):
                pipeline.execute(
                    "automatic_memory_snapshot",
                    payload={"source_id": "source-a"},
                    execution_id="snapshot-job",
                )


if __name__ == "__main__":
    unittest.main()
