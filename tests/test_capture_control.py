from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.control.capture import (
    CAPTURE_JOB_NOT_CANCELLABLE,
    CAPTURE_JOB_NOT_RETRYABLE,
    CAPTURE_JOB_RUNNING,
    CAPTURE_PAUSED,
    CaptureControlError,
    CaptureControlService,
    CaptureRuntimeSettingsStore,
)
from src.extraction.queue import SQLiteExtractionQueue


class FakeStateDatabase:
    def __init__(self, fail=False):
        self.fail = fail
        self.events = []

    def append_event(self, event_type, entity_type, entity_id, payload):
        if self.fail:
            raise RuntimeError(r"audit failed D:\Users\Secret\state.db")
        self.events.append((event_type, entity_type, entity_id, dict(payload)))


class QueuePipeline:
    def __init__(self, queue):
        self.queue = queue
        self.calls = []
        self.execute_calls = []

    def enqueue(self, source_type, **kwargs):
        self.calls.append((source_type, kwargs))
        return self.queue.enqueue(source_type, **kwargs)

    def execute(self, source_type, **kwargs):
        self.execute_calls.append((source_type, kwargs))
        raise AssertionError("capture HTTP path must not execute synchronously")


@pytest.fixture()
def harness(tmp_path):
    settings = SimpleNamespace(
        storage_path=tmp_path / "storage",
        runtime_settings_file=Path("runtime-settings.json"),
    )
    settings.storage_path.mkdir(parents=True)
    queue = SQLiteExtractionQueue(tmp_path / "state.db")
    pipeline = QueuePipeline(queue)
    state_db = FakeStateDatabase()
    runtime = CaptureRuntimeSettingsStore(settings, state_db=state_db)
    service = CaptureControlService(
        settings,
        pipeline=pipeline,
        queue=queue,
        runtime_settings=runtime,
        state_db=state_db,
    )
    return settings, queue, pipeline, state_db, service


def test_all_capture_inputs_enqueue_and_service_is_long_lived(harness, tmp_path):
    _, queue, pipeline, _, service = harness
    service_id = id(service.capture_service)
    note = tmp_path / "note.txt"
    note.write_text("note", encoding="utf-8")
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"media")

    results = [
        service.submit_text({"text": "hello"}),
        service.submit_web({"url": "https://example.com/a"}),
        service.submit_file({"input_path": str(note), "source_type": "web"}),
        service.submit_media({"input_path": str(media), "allow_ocr": True}),
    ]

    assert all(item["status"] == "queued" for item in results)
    assert all(item["capture_id"] for item in results)
    assert all(item["job_id"] for item in results)
    assert len(pipeline.calls) == 4
    assert pipeline.calls[0][0] == "text"
    assert pipeline.execute_calls == []
    assert id(service.capture_service) == service_id
    assert pipeline.calls[-1][1]["options"]["allow_ocr"] is True

    stored = queue.get(results[0]["job_id"])
    assert stored["payload"]["capture_id"] == results[0]["capture_id"]
    projected = service.get_job(results[0]["job_id"])
    assert projected["work_item_id"] == results[0]["job_id"]
    assert projected["capture_id"] == results[0]["capture_id"]
    assert projected["outcome_state"] == "pending"
    assert projected["next_actor"] == "system"


def test_duplicate_returns_same_job_and_audit_event(harness):
    _, _, _, state_db, service = harness
    first = service.submit_text({"text": "same"})
    second = service.submit_text({"text": "same"})
    assert second["duplicate"] is True
    assert second["status"] == "duplicate"
    assert second["job_id"] == first["job_id"]
    assert second["capture_id"] == first["capture_id"]
    assert [event[0] for event in state_db.events][-2:] == [
        "capture_submitted",
        "capture_duplicate",
    ]
    submitted_event = state_db.events[-2]
    assert submitted_event[1] == "capture"
    assert submitted_event[2] == first["capture_id"]
    assert submitted_event[3]["capture_id"] == first["capture_id"]
    assert submitted_event[3]["job_id"] == first["job_id"]
    assert submitted_event[3]["source_type"] == "text"


def test_duplicate_after_service_restart_reuses_durable_work_item(harness):
    settings, queue, pipeline, state_db, service = harness
    first = service.submit_text({"text": "restart-safe duplicate"})

    restarted = CaptureControlService(
        settings,
        pipeline=pipeline,
        queue=queue,
        runtime_settings=CaptureRuntimeSettingsStore(settings, state_db=state_db),
        state_db=state_db,
    )
    second = restarted.submit_text({"text": "restart-safe duplicate"})

    assert second["duplicate"] is True
    assert second["job_id"] == first["job_id"]
    assert second["capture_id"] == first["capture_id"]
    stored = queue.get(first["job_id"])
    assert stored["payload"]["capture_id"] == first["capture_id"]
    assert restarted.get_job(first["job_id"])["capture_id"] == first["capture_id"]


def test_capture_mode_persists_pause_rejects_and_resume_restores(harness):
    settings, _, _, state_db, service = harness
    assert service.status()["capture_mode"] == "low_power"
    service.pause()
    assert service.status()["mode"] == "paused"
    assert service.status()["mode_label"] == "PAUSED"
    fresh = CaptureRuntimeSettingsStore(settings, state_db=state_db)
    assert fresh.snapshot()["values"]["capture_mode"] == "paused"
    with pytest.raises(CaptureControlError) as raised:
        service.submit_text({"text": "blocked"})
    assert raised.value.code == CAPTURE_PAUSED
    resumed = service.resume()
    assert resumed["capture_mode"] == "low_power"
    assert service.submit_text({"text": "accepted"})["status"] == "queued"


def test_queue_pagination_filtering_cancel_retry_and_conflicts(harness):
    _, queue, _, _, service = harness
    text1 = service.submit_text({"text": "alpha"})
    service.submit_text({"text": "beta"})
    media_path = Path(queue.path.parent) / "media.mp4"
    media_path.write_bytes(b"x")
    service.submit_media({"input_path": str(media_path)})

    page = service.list_jobs(source_type="text", q="LJ-JOB", limit=1, offset=1)
    assert page["pagination"]["limit"] == 1
    assert page["pagination"]["offset"] == 1
    assert page["pagination"]["total"] == 2
    assert len(page["items"]) == 1
    assert page["items"][0]["source_type"] == "text"

    assert service.cancel_job(text1["job_id"])["status"] == "cancelled"
    retried = service.retry_job(text1["job_id"])
    assert retried["status"] == "queued"
    assert retried["attempts"] == 0
    assert service.cancel_job(text1["job_id"])["status"] == "cancelled"
    with pytest.raises(CaptureControlError) as cancel_again:
        service.cancel_job(text1["job_id"])
    assert cancel_again.value.code == CAPTURE_JOB_NOT_CANCELLABLE

    running_job = service.submit_text({"text": "running"})
    queue.claim("worker", job_id=running_job["job_id"])
    running_dto = service.get_job(running_job["job_id"])
    assert running_dto["outcome_state"] == "running"
    assert running_dto["next_actor"] == "system"
    with pytest.raises(CaptureControlError) as running_cancel:
        service.cancel_job(running_job["job_id"])
    assert running_cancel.value.code == CAPTURE_JOB_RUNNING
    with pytest.raises(CaptureControlError) as running_retry:
        service.retry_job(running_job["job_id"])
    assert running_retry.value.code == CAPTURE_JOB_RUNNING

    complete_job = service.submit_text({"text": "complete"})
    claimed = queue.claim("worker", job_id=complete_job["job_id"])
    queue.complete(
        complete_job["job_id"],
        {
            "memory_id": "MEM-1",
            "created": [{"id": "DOC-1", "path": r"D:\Users\Secret\DOC-1.md", "relative_path": "05-Operations/DOC-1.md"}],
            "indexed": True,
        },
        worker_id="worker",
        lease_token=claimed["lease_token"],
    )
    completed_dto = service.get_job(complete_job["job_id"])
    assert completed_dto["outcome_state"] == "succeeded"
    assert completed_dto["next_actor"] == "none"
    assert completed_dto["result_refs"] == {"memory_id": "MEM-1"}
    assert completed_dto["result_object_ids"] == ["DOC-1"]
    assert "D:\\Users\\Secret" not in json.dumps(completed_dto)
    with pytest.raises(CaptureControlError) as completed_cancel:
        service.cancel_job(complete_job["job_id"])
    assert completed_cancel.value.code == CAPTURE_JOB_NOT_CANCELLABLE
    with pytest.raises(CaptureControlError) as completed_retry:
        service.retry_job(complete_job["job_id"])
    assert completed_retry.value.code == CAPTURE_JOB_NOT_RETRYABLE


def test_job_dto_is_sanitized_and_uses_basename(harness, tmp_path):
    _, queue, _, _, service = harness
    path = tmp_path / "Secret Folder" / "private.txt"
    path.parent.mkdir()
    path.write_text("top secret body", encoding="utf-8")
    submitted = service.submit_file({"input_path": str(path), "metadata": {"safe": "value"}, "source_type": "web"})
    for _ in range(3):
        claimed = queue.claim("worker", job_id=submitted["job_id"])
        queue.fail(claimed["job_id"], r"failed at D:\Users\Secret\lingji_state.db with token=abc", retry_delay_seconds=0)
    dto = service.get_job(submitted["job_id"])
    serialized = json.dumps(dto)
    assert dto["file_name"] == "private.txt"
    assert dto["capture_id"] == submitted["capture_id"]
    assert dto["outcome_state"] == "failed"
    assert dto["next_actor"] == "none"
    assert dto["error_message"] == "Capture processing failed; see local logs"
    for forbidden in (
        "payload", "options", "input_path", "last_error", "lease_token",
        "locked_by", "heartbeat_at", "top secret body", "D:\\", "Users", "token=abc",
    ):
        assert forbidden not in serialized


def test_legacy_jobs_routes_reuse_sanitized_projection(harness, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.control.capture_api import register_capture_routes

    settings, queue, _, _, service = harness
    private_file = tmp_path / "Private" / "secret.txt"
    private_file.parent.mkdir()
    private_file.write_text("owner-private-body", encoding="utf-8")
    submitted = service.submit_file({
        "input_path": str(private_file),
        "source_type": "web",
        "metadata": {"safe": "yes"},
    })
    for _ in range(3):
        claimed = queue.claim("worker", job_id=submitted["job_id"])
        queue.fail(
            claimed["job_id"],
            r"failed D:\Users\Private\state.db token=legacy-secret",
            retry_delay_seconds=0,
        )

    app = FastAPI()

    @app.get("/api/jobs")
    def unsafe_jobs():
        return {"jobs": queue.list(limit=100)}

    @app.get("/api/jobs/{job_id}")
    def unsafe_job(job_id: str):
        return queue.get(job_id)

    control = SimpleNamespace(capture_control=service, queue=queue)
    register_capture_routes(app, settings, control, token="test-token")
    client = TestClient(app)
    headers = {"X-LingJi-Token": "test-token"}

    list_response = client.get("/api/jobs", headers=headers)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["jobs"]
    assert payload["jobs"][0]["work_item_id"]

    detail_response = client.get(f"/api/jobs/{submitted['job_id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["capture_id"] == submitted["capture_id"]
    assert detail["error_message"] == "Capture processing failed; see local logs"

    serialized = json.dumps({"list": payload, "detail": detail})
    for forbidden in (
        "owner-private-body",
        "legacy-secret",
        "D:\\Users\\Private",
        '"payload"',
        '"input_path"',
        '"last_error"',
        '"lease_token"',
    ):
        assert forbidden not in serialized


def test_audit_failure_does_not_break_operations(tmp_path):
    settings = SimpleNamespace(storage_path=tmp_path / "storage", runtime_settings_file=Path("runtime-settings.json"))
    settings.storage_path.mkdir(parents=True)
    queue = SQLiteExtractionQueue(tmp_path / "state.db")
    pipeline = QueuePipeline(queue)
    service = CaptureControlService(
        settings,
        pipeline=pipeline,
        queue=queue,
        runtime_settings=CaptureRuntimeSettingsStore(settings, state_db=None),
        state_db=FakeStateDatabase(fail=True),
    )
    submitted = service.submit_text({"text": "audit safe"})
    assert service.cancel_job(submitted["job_id"])["status"] == "cancelled"
    assert service.retry_job(submitted["job_id"])["status"] == "queued"
    assert service.pause()["paused"] is True
    assert service.resume()["paused"] is False
