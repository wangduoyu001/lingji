from pathlib import Path

import pytest

from src.capture.deduplication import CaptureDeduplicator
from src.capture.models import CaptureEnvelope, CaptureStatus
from src.capture.policy import CaptureMode, CapturePolicy
from src.capture.service import CaptureService


class FakePipeline:
    def __init__(self):
        self.enqueued = []
        self.executed = []

    def enqueue(self, source_type, **kwargs):
        self.enqueued.append((source_type, kwargs))
        return {"job_id": "job-1"}

    def execute(self, source_type, **kwargs):
        self.executed.append((source_type, kwargs))
        return {"execution_id": kwargs.get("execution_id", "exec-1")}


def test_low_power_queues_web_and_media():
    pipeline = FakePipeline()
    service = CaptureService(pipeline)
    web = service.submit_web("https://example.com/a?utm_source=x", title="A")
    assert web.status is CaptureStatus.QUEUED
    assert len(pipeline.enqueued) == 1


def test_normal_policy_executes_light_capture_but_queues_media(tmp_path):
    pipeline = FakePipeline()
    service = CaptureService(pipeline, policy=CapturePolicy.for_mode(CaptureMode.NORMAL))
    text = service.submit_text("hello")
    assert text.status is CaptureStatus.EXECUTED
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"media")
    result = service.submit_media(media)
    assert result.status is CaptureStatus.QUEUED


def test_paused_service_rejects_processing():
    service = CaptureService(FakePipeline(), policy=CapturePolicy.for_mode(CaptureMode.PAUSED))
    result = service.submit_text("hello")
    assert result.status is CaptureStatus.PAUSED


def test_normalized_url_and_clipboard_content_are_deduplicated():
    service = CaptureService(FakePipeline())
    first = service.submit_web("https://EXAMPLE.com/a/?utm_source=x", title="A")
    second = service.submit_web("https://example.com/a", title="A")
    assert first.status is CaptureStatus.QUEUED
    assert second.status is CaptureStatus.DUPLICATE

    text_service = CaptureService(FakePipeline())
    first_text = text_service.submit_text("same")
    second_text = text_service.submit_text("same")
    assert first_text.status is CaptureStatus.QUEUED
    assert second_text.status is CaptureStatus.DUPLICATE


def test_file_hash_changes_allow_new_capture(tmp_path):
    pipeline = FakePipeline()
    service = CaptureService(pipeline)
    path = tmp_path / "note.txt"
    path.write_text("one", encoding="utf-8")
    first = service.submit_file(path, source_type="web")
    second = service.submit_file(path, source_type="web")
    path.write_text("two", encoding="utf-8")
    third = service.submit_file(path, source_type="web")
    assert first.status is CaptureStatus.QUEUED
    assert second.status is CaptureStatus.DUPLICATE
    assert third.status is CaptureStatus.QUEUED


def test_sensitive_metadata_is_rejected():
    service = CaptureService(FakePipeline())
    envelope = CaptureEnvelope(
        capture_id="cap-sensitive",
        source_type="web",
        capture_method="mobile_share",
        text="hello",
        metadata={"token": "secret"},
    )
    with pytest.raises(ValueError):
        service.submit(envelope)
