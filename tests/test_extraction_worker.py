from __future__ import annotations

import tempfile
import time
import unittest
import threading
from datetime import datetime, timezone
from pathlib import Path

from src.extraction.base import ExtractionAdapter
from src.extraction.models import ExtractedDocument, ExtractionBatch
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.extraction.worker import ExtractionWorker
from src.memory import VaultLayout
from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.source_registry import SourceRegistry
from src.storage import StateDatabase


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
        class RevokingAdapter(ExtractionAdapter):
            name = "revoking"
            version = "1"
            source_types = ("revoking", "automatic_memory_snapshot")

            def __init__(self, registry, source_id):
                self.registry = registry
                self.source_id = source_id

            def extract(self, request):
                self.registry.revoke(self.source_id)
                return ExtractionBatch(
                    documents=(
                        ExtractedDocument(
                            stable_id="LJ-REVOKED-1",
                            title="must not write",
                            body="# revoked",
                            source_type="revoking",
                        ),
                    )
                )

        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            root = Path(tmp)
            layout = VaultLayout(root / "vault")
            layout.ensure()
            db_path = root / "lingji_state.db"
            state = StateDatabase(db_path)
            source_root = root / "authorized"
            source_root.mkdir()
            registry = SourceRegistry(state)
            source = registry.register(
                AuthorizationScope(
                    grant_id="grant-revoking-worker",
                    source_kinds=("generic_file",),
                    roots=(str(source_root),),
                    granted_at=datetime.now(timezone.utc),
                    expires_at=None,
                    owner_confirmed=True,
                ),
                "generic_file",
                str(source_root),
            )
            input_path = source_root / "snapshot.raw"
            input_path.write_bytes(b"authorized raw")
            queue = SQLiteExtractionQueue(db_path)
            adapters = AdapterRegistry()
            adapters.register(RevokingAdapter(registry, source.source_id))
            pipeline = ExtractionPipeline(
                queue,
                adapters,
                VaultExtractionSink(layout, root / "storage"),
            )
            job = pipeline.enqueue(
                "revoking",
                input_path=input_path,
                payload={"source_id": source.source_id},
            )
            # Make the job a snapshot job so revoke's same-DB cancellation
            # policy applies to the real worker path.
            with state._connection() as connection:
                connection.execute(
                    "UPDATE extraction_jobs SET source_type = 'automatic_memory_snapshot', automatic_memory_source_id = ? WHERE job_id = ?",
                    (source.source_id, job["job_id"]),
                )

            result = pipeline.process_job(job["job_id"], worker_id="revoking-worker")

            self.assertEqual(queue.get(job["job_id"])["status"], "cancelled")
            self.assertEqual(queue.stats()["completed"], 0)
            self.assertEqual(list((root / "vault").rglob("*.md")), [])

    def test_automatic_memory_downstream_race_commits_whole_batch_before_revoke(self):
        class TwoDocumentAdapter(ExtractionAdapter):
            name = "two-documents"
            version = "1"
            source_types = ("automatic_memory_snapshot",)

            def extract(self, request):
                return ExtractionBatch(
                    documents=tuple(
                        ExtractedDocument(
                            stable_id=f"LJ-RACE-{index}",
                            title=f"race-{index}",
                            body=f"# race {index}",
                            source_type="automatic_memory_snapshot",
                        )
                        for index in (1, 2)
                    )
                )

        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            root = Path(tmp)
            layout = VaultLayout(root / "vault")
            layout.ensure()
            state = StateDatabase(root / "lingji_state.db")
            source_root = root / "authorized"
            source_root.mkdir()
            registry = SourceRegistry(state)
            source = registry.register(
                AuthorizationScope(
                    grant_id="grant-race",
                    source_kinds=("generic_file",),
                    roots=(str(source_root),),
                    granted_at=datetime.now(timezone.utc),
                    expires_at=None,
                    owner_confirmed=True,
                ),
                "generic_file",
                str(source_root),
            )
            queue = SQLiteExtractionQueue(root / "lingji_state.db")
            real_sink = VaultExtractionSink(layout, root / "storage")
            revoke_started = threading.Event()
            revoke_done = threading.Event()
            revoke_thread: list[threading.Thread] = []

            class RaceSink(VaultExtractionSink):
                def write_batch(self, batch, *, adapter_name, adapter_version, raw_snapshot=None):
                    first = self.write_document(
                        batch.documents[0],
                        adapter_name=adapter_name,
                        adapter_version=adapter_version,
                        raw_snapshot=raw_snapshot,
                    )
                    revoke_started.set()
                    def revoke_source():
                        registry.revoke(source.source_id)
                        revoke_done.set()

                    worker = threading.Thread(target=revoke_source)
                    revoke_thread.append(worker)
                    worker.start()
                    time.sleep(0.05)
                    second = self.write_document(
                        batch.documents[1],
                        adapter_name=adapter_name,
                        adapter_version=adapter_version,
                        raw_snapshot=raw_snapshot,
                    )
                    return {
                        "documents": 2,
                        "created": [first, second],
                        "updated": [],
                        "skipped": [],
                        "paths": [first["path"], second["path"]],
                        "warnings": [],
                        "summary": {},
                        "raw_snapshot": raw_snapshot or {},
                    }

            sink = RaceSink(real_sink.layout, real_sink.storage_path)
            adapters = AdapterRegistry()
            adapters.register(TwoDocumentAdapter())
            pipeline = ExtractionPipeline(queue, adapters, sink)
            job = pipeline.enqueue(
                "automatic_memory_snapshot",
                payload={"source_id": source.source_id},
            )

            result = pipeline.process_job(job["job_id"], worker_id="race-worker")
            for worker in revoke_thread:
                worker.join(timeout=5)

            assert revoke_started.is_set()
            assert revoke_done.is_set()
            self.assertEqual(len(list((root / "vault").rglob("*.md"))), 2)
            self.assertEqual(queue.get(job["job_id"])["status"], "completed")
            self.assertEqual(state.get_automatic_memory_source(source.source_id)["status"], "revoked")

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


if __name__ == "__main__":
    unittest.main()
