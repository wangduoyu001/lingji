from __future__ import annotations

from src.config import Settings
from src.control.capture import CaptureControlService, CaptureRuntimeSettingsStore
from src.extraction.bootstrap import build_extraction_pipeline
from src.storage.state_db import StateDatabase
from src.work.capture_bridge import CaptureWorkBridge
from src.work.store import WorkStore


def make_settings(tmp_path, *, max_attempts: int = 1) -> Settings:
    return Settings(
        _env_file=None,
        vault_dir=str(tmp_path / "vault"),
        storage_dir=str(tmp_path / "storage"),
        log_dir=str(tmp_path / "logs"),
        backup_dir=str(tmp_path / "backup"),
        startup_min_free_gb=0,
        extraction_max_attempts=max_attempts,
        web_network_fetch_enabled=False,
    )


def build_harness(tmp_path, *, max_attempts: int = 1):
    settings = make_settings(tmp_path, max_attempts=max_attempts)
    state_db = StateDatabase(settings.state_db_path)
    runtime = CaptureRuntimeSettingsStore(settings, state_db=state_db)
    pipeline = build_extraction_pipeline(settings, runtime_settings=runtime)
    store = WorkStore(state_db)
    service = CaptureControlService(
        settings,
        pipeline=pipeline,
        queue=pipeline.queue,
        runtime_settings=runtime,
        state_db=state_db,
        work_bridge=CaptureWorkBridge(store),
    )
    return settings, state_db, pipeline, store, service


def test_real_text_capture_is_traceable_through_completed_outcome(tmp_path):
    settings, _, pipeline, store, service = build_harness(tmp_path)

    submitted = service.submit_text(
        {"title": "SB1 lifecycle", "text": "Remember this durable capture fact."}
    )

    assert submitted["capture_id"]
    assert submitted["work_id"]
    assert submitted["job_id"]
    assert submitted["status"] == "queued"
    queued = pipeline.queue.get(submitted["job_id"])
    assert queued["options"]["_lingji_work_id"] == submitted["work_id"]
    assert queued["options"]["_lingji_capture_id"] == submitted["capture_id"]

    before = store.get_work(submitted["work_id"])
    assert before is not None
    assert before.status == "accepted"
    assert [event.event_type for event in store.list_events(before.work_id)] == [
        "capture.accepted",
        "extraction.queued",
    ]

    processed = pipeline.process_job(submitted["job_id"], worker_id="sb1-test-worker")
    assert processed["job"]["status"] == "completed"

    reopened = WorkStore(StateDatabase(settings.state_db_path))
    work = reopened.get_work(submitted["work_id"])
    assert work is not None
    assert work.status == "completed"
    assert [event.event_type for event in reopened.list_events(work.work_id)] == [
        "capture.accepted",
        "extraction.queued",
        "extraction.started",
        "extraction.completed",
    ]
    outcome = reopened.get_outcome(work.work_id)
    assert outcome is not None
    assert outcome.status == "success"
    assert outcome.evidence["job_id"] == submitted["job_id"]
    next_action = reopened.get_next_action(work.work_id)
    assert next_action is not None
    assert next_action.actor == "none"


def test_duplicate_after_control_recreation_reuses_same_job_and_work(tmp_path):
    settings, _, pipeline, store, first_service = build_harness(tmp_path)
    first = first_service.submit_text({"title": "same", "text": "same durable content"})

    fresh_state = StateDatabase(settings.state_db_path)
    fresh_runtime = CaptureRuntimeSettingsStore(settings, state_db=fresh_state)
    fresh_pipeline = build_extraction_pipeline(settings, runtime_settings=fresh_runtime)
    fresh_store = WorkStore(fresh_state)
    second_service = CaptureControlService(
        settings,
        pipeline=fresh_pipeline,
        queue=fresh_pipeline.queue,
        runtime_settings=fresh_runtime,
        state_db=fresh_state,
        work_bridge=CaptureWorkBridge(fresh_store),
    )

    duplicate = second_service.submit_text({"title": "same", "text": "same durable content"})

    assert duplicate["duplicate"] is True
    assert duplicate["status"] == "duplicate"
    assert duplicate["job_id"] == first["job_id"]
    assert duplicate["work_id"] == first["work_id"]
    assert len(fresh_store.list_work(limit=20)) == 1
    assert [event.event_type for event in fresh_store.list_events(first["work_id"])] == [
        "capture.accepted",
        "extraction.queued",
        "capture.duplicate",
    ]
    assert pipeline.queue.get(first["job_id"])["idempotency_key"] == fresh_pipeline.queue.get(first["job_id"])["idempotency_key"]


def test_real_worker_failure_persists_failed_work_and_safe_outcome(tmp_path):
    settings, _, pipeline, store, service = build_harness(tmp_path, max_attempts=1)
    submitted = service.submit_text({"title": "failure", "text": "will fail in worker"})

    def fail_execute(*_args, **_kwargs):
        raise RuntimeError(r"secret failure at D:\Users\Owner\private.db token=abc")

    pipeline.execute = fail_execute  # type: ignore[method-assign]
    processed = pipeline.process_job(submitted["job_id"], worker_id="sb1-failing-worker")

    assert processed["job"]["status"] == "failed"
    work = store.get_work(submitted["work_id"])
    assert work is not None
    assert work.status == "failed"
    outcome = store.get_outcome(work.work_id)
    assert outcome is not None
    assert outcome.status == "failure"
    assert "Users" not in outcome.summary
    assert "token=abc" not in outcome.summary
    assert outcome.evidence == {
        "job_id": submitted["job_id"],
        "error_code": "CAPTURE_JOB_FAILED",
    }
    assert store.list_events(work.work_id)[-1].event_type == "extraction.failed"


def test_rejected_text_does_not_create_owner_work(tmp_path):
    _, _, _, store, service = build_harness(tmp_path)
    try:
        service.submit_text({"text": ""})
    except Exception:
        pass
    assert store.list_work(limit=20) == []
