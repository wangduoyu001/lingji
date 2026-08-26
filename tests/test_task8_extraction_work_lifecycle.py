from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.control.capture import CaptureControlService, CaptureRuntimeSettingsStore
from src.extraction.adapters.web import WebCaptureAdapter
from src.extraction.base import ExtractionAdapter
from src.extraction.models import ExtractedDocument, ExtractionBatch
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.memory import VaultLayout
from src.storage.state_db import StateDatabase
from src.work.store import WorkStore


class AlwaysFailAdapter(ExtractionAdapter):
    name = "always-fail"
    version = "1"
    source_types = ("always_fail",)

    def extract(self, request):
        raise RuntimeError("fixture extraction failure")


def _service(tmp_path: Path, *, failing: bool = False):
    state_path = tmp_path / "lingji_state.db"
    state = StateDatabase(state_path)
    queue = SQLiteExtractionQueue(state_path)
    layout = VaultLayout(tmp_path / "vault")
    layout.ensure()
    registry = AdapterRegistry()
    registry.register(AlwaysFailAdapter() if failing else WebCaptureAdapter())
    pipeline = ExtractionPipeline(queue, registry, VaultExtractionSink(layout, tmp_path / "storage"))
    settings = SimpleNamespace(storage_path=tmp_path / "storage", runtime_settings_file=tmp_path / "runtime.json")
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    service = CaptureControlService(
        settings,
        pipeline=pipeline,
        queue=queue,
        runtime_settings=CaptureRuntimeSettingsStore(settings, state_db=state),
        state_db=state,
    )
    return state, queue, pipeline, service


def _make_retry_due(queue: SQLiteExtractionQueue, job_id: str) -> None:
    with queue._connection() as connection:
        connection.execute("UPDATE extraction_jobs SET next_run_at = CURRENT_TIMESTAMP WHERE job_id = ?", (job_id,))


def test_real_extraction_completion_writes_work_outcome_and_survives_restart(tmp_path: Path):
    state, queue, pipeline, service = _service(tmp_path)
    submitted = service.submit_text({"capture_id": "capture-e2e", "title": "e2e", "text": "hello"})
    work_id = submitted["work_id"]
    result = pipeline.process_job(submitted["job_id"], worker_id="task8")

    assert result["job"]["status"] == "completed"
    store = WorkStore(state)
    fact = __import__("src.work.projector", fromlist=["WorkProjector"]).WorkProjector(store).fact(work_id)
    assert fact["outcome"] is not None
    assert fact["outcome"]["status"] == "completed"
    assert any(event["event_type"] == "extraction.completed" for event in fact["events"])
    assert len([event for event in fact["events"] if event["event_type"] == "extraction.completed"]) == 1

    reopened = WorkStore(StateDatabase(tmp_path / "lingji_state.db"))
    assert reopened.get_outcome(work_id).status == "completed"
    assert queue.get(submitted["job_id"])["status"] == "completed"


def test_real_extraction_terminal_failure_writes_failure_and_owner_pending_without_retry_pending(tmp_path: Path):
    state, queue, pipeline, service = _service(tmp_path, failing=True)
    submitted = service.submit_text({"capture_id": "capture-fail", "source_type": "always_fail", "adapter_name": "always-fail", "title": "fail", "text": "hello"})
    work_id = submitted["work_id"]

    retrying = pipeline.process_job(submitted["job_id"], worker_id="task8")
    assert retrying["job"]["status"] == "retrying"
    store = WorkStore(state)
    assert store.list_pending(work_id=work_id) == []
    _make_retry_due(queue, submitted["job_id"])
    pipeline.process_job(submitted["job_id"], worker_id="task8")
    _make_retry_due(queue, submitted["job_id"])
    pipeline.process_job(submitted["job_id"], worker_id="task8")
    _make_retry_due(queue, submitted["job_id"])
    final = pipeline.process_job(submitted["job_id"], worker_id="task8")
    assert final["job"]["status"] == "failed"
    failure = store.get_failure(work_id)
    assert failure is not None
    assert store.get_outcome(work_id).status == "failed"
    assert len(store.list_pending(work_id=work_id)) == 1

    pipeline.process_job(submitted["job_id"], worker_id="task8")
    assert len(store.list_pending(work_id=work_id)) == 1
    assert len([event for event in store.list_events(work_id) if event.event_type == "work.failed"]) == 1


def test_direct_execute_lifecycle_callback_writes_work_fact(tmp_path: Path):
    state, _queue, pipeline, service = _service(tmp_path)
    work = service.work_bridge.create_from_capture("capture-direct", "direct")
    pipeline.execute(
        "web",
        payload={"capture_id": "capture-direct", "title": "direct", "text": "hello"},
        adapter_name="web_capture",
        execution_id="direct-execution",
    )
    outcome = WorkStore(state).get_outcome(work.work_id)
    assert outcome is not None
    assert outcome.status == "completed"


def test_lifecycle_callback_failure_does_not_change_queue_status(tmp_path: Path):
    state, queue, pipeline, service = _service(tmp_path)

    def broken_callback(*_args):
        raise RuntimeError("callback fixture failure")

    pipeline.add_lifecycle_callback(broken_callback)
    submitted = service.submit_text({"capture_id": "capture-callback", "text": "hello"})
    result = pipeline.process_job(submitted["job_id"], worker_id="task8")
    assert result["job"]["status"] == "completed"
    assert WorkStore(state).get_outcome(submitted["work_id"]).status == "completed"
