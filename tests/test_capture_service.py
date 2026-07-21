from pathlib import Path

import pytest

from src.capture.models import CaptureEnvelope, CaptureStatus
from src.capture.policy import CaptureMode, CapturePolicy
from src.capture.service import CaptureService


class FakePipeline:
    def __init__(self):
        self.enqueued = []
        self.executed = []
        self.fail_enqueue_once = False
        self.fail_execute_once = False

    def enqueue(self, source_type, **kwargs):
        self.enqueued.append((source_type, kwargs))
        if self.fail_enqueue_once:
            self.fail_enqueue_once = False
            raise RuntimeError("enqueue failed")
        return {"job_id": "job-1"}

    def execute(self, source_type, **kwargs):
        self.executed.append((source_type, kwargs))
        if self.fail_execute_once:
            self.fail_execute_once = False
            raise RuntimeError("execute failed")
        return {"execution_id": kwargs.get("execution_id", "exec-1")}


def test_manual_helpers_queue_even_under_normal_policy(tmp_path):
    pipeline = FakePipeline()
    service = CaptureService(pipeline, policy=CapturePolicy.for_mode(CaptureMode.NORMAL))
    assert service.submit_text("hello").status is CaptureStatus.QUEUED
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"media")
    assert service.submit_media(media).status is CaptureStatus.QUEUED
    assert not pipeline.executed


def test_explicit_realtime_envelope_can_execute_under_normal_policy():
    pipeline = FakePipeline()
    service = CaptureService(pipeline, policy=CapturePolicy.for_mode(CaptureMode.NORMAL))
    envelope = CaptureEnvelope(
        capture_id="cap-realtime",
        source_type="web",
        capture_method="local_control_share",
        adapter_name="web_capture",
        text="hello",
        process_later=False,
    )
    assert service.submit(envelope).status is CaptureStatus.EXECUTED


def test_paused_service_rejects_processing():
    service = CaptureService(FakePipeline(), policy=CapturePolicy.for_mode(CaptureMode.PAUSED))
    assert service.submit_text("hello").status is CaptureStatus.PAUSED


def test_normalized_url_and_text_are_deduplicated():
    service = CaptureService(FakePipeline())
    assert service.submit_web("https://EXAMPLE.com/a/?utm_source=x").status is CaptureStatus.QUEUED
    assert service.submit_web("https://example.com/a").status is CaptureStatus.DUPLICATE
    text_service = CaptureService(FakePipeline())
    assert text_service.submit_text("same").status is CaptureStatus.QUEUED
    assert text_service.submit_text("same").status is CaptureStatus.DUPLICATE


def test_file_hash_changes_allow_new_capture(tmp_path):
    pipeline = FakePipeline()
    service = CaptureService(pipeline)
    path = tmp_path / "note.txt"
    path.write_text("one", encoding="utf-8")
    assert service.submit_file(path).status is CaptureStatus.QUEUED
    assert service.submit_file(path).status is CaptureStatus.DUPLICATE
    path.write_text("two", encoding="utf-8")
    assert service.submit_file(path).status is CaptureStatus.QUEUED


def test_enqueue_failure_does_not_poison_deduplication():
    pipeline = FakePipeline()
    pipeline.fail_enqueue_once = True
    service = CaptureService(pipeline)
    with pytest.raises(RuntimeError):
        service.submit_text("retry enqueue")
    assert service.submit_text("retry enqueue").status is CaptureStatus.QUEUED


def test_execute_failure_does_not_poison_deduplication():
    pipeline = FakePipeline()
    pipeline.fail_execute_once = True
    service = CaptureService(pipeline, policy=CapturePolicy.for_mode(CaptureMode.NORMAL))
    envelope = CaptureEnvelope(
        capture_id="cap-execute",
        source_type="web",
        capture_method="local_control_share",
        adapter_name="web_capture",
        text="retry execute",
        process_later=False,
    )
    with pytest.raises(RuntimeError):
        service.submit(envelope)
    retry = CaptureEnvelope(**{**envelope.__dict__, "capture_id": "cap-execute-2"})
    assert service.submit(retry).status is CaptureStatus.EXECUTED


def test_successful_submit_is_remembered_only_after_pipeline_success():
    service = CaptureService(FakePipeline())
    assert service.submit_text("committed").status is CaptureStatus.QUEUED
    assert service.submit_text("committed").status is CaptureStatus.DUPLICATE


@pytest.mark.parametrize("key", ["token", "cookie", "api_key", "apikey"])
def test_nested_sensitive_metadata_is_rejected(key):
    service = CaptureService(FakePipeline())
    envelope = CaptureEnvelope(
        capture_id=f"cap-{key}",
        source_type="web",
        capture_method="mobile_share",
        text="hello",
        metadata={"outer": [{"inner": {key: "secret"}}]},
    )
    with pytest.raises(ValueError):
        service.submit(envelope)


@pytest.mark.parametrize(
    "key",
    ["source_type", "capture_method", "adapter_name", "input_path", "privacy", "project_ids", "tags", "priority"],
)
def test_metadata_cannot_override_manual_contract(key):
    service = CaptureService(FakePipeline())
    envelope = CaptureEnvelope(
        capture_id=f"cap-{key}",
        source_type="web",
        capture_method="manual_text",
        adapter_name="web_capture",
        text="hello",
        metadata={key: "spoofed"},
    )
    with pytest.raises(ValueError):
        service.submit(envelope)


def test_explicit_share_fields_are_forwarded_without_metadata_shadowing():
    pipeline = FakePipeline()
    service = CaptureService(pipeline)
    result = service.submit_web(
        "https://example.com/item",
        platform="xiaohongshu",
        description="saved manually",
        external_id="note-42",
        metadata={"labels": ["idea"]},
    )
    assert result.status is CaptureStatus.QUEUED
    payload = pipeline.enqueued[0][1]["payload"]
    assert payload["platform"] == "xiaohongshu"
    assert payload["description"] == "saved manually"
    assert payload["external_id"] == "note-42"
    assert payload["metadata"] == {"labels": ["idea"]}
