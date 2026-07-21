from pathlib import Path

import pytest

from src.capture.models import CaptureEnvelope, CaptureStatus
from src.capture.policy import CaptureMode, CapturePolicy
from src.capture.service import CaptureService
from src.extraction.models import ExtractionBatch, StructuredConversation, StructuredMessage, StructuredSource
from src.extraction.structured_sink import StructuredReadModelSink


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


class FakeStructuredReadModel:
    def __init__(self):
        self.bundles = []

    def upsert_bundle(self, bundle):
        self.bundles.append(bundle)
        messages = bundle["conversations"][0]["messages"]
        links = [link for message in messages for link in message.get("memory_links", [])]
        return {"sources": 1, "conversations": 1, "messages": len(messages), "links": len(links)}


class FakeMemoryDatabase:
    def __init__(self, existing):
        self.existing = set(existing)

    def fetch_memory(self, memory_id, include_chunks=False):
        del include_chunks
        return {"memory_id": memory_id} if memory_id in self.existing else None


def test_low_power_queues_web_and_media():
    pipeline = FakePipeline()
    service = CaptureService(pipeline)
    web = service.submit_web("https://example.com/a?utm_source=x", title="A")
    assert web.status is CaptureStatus.QUEUED
    assert len(pipeline.enqueued) == 1


def test_manual_helpers_queue_under_normal_policy(tmp_path):
    pipeline = FakePipeline()
    service = CaptureService(pipeline, policy=CapturePolicy.for_mode(CaptureMode.NORMAL))
    text = service.submit_text("hello")
    assert text.status is CaptureStatus.QUEUED
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"media")
    result = service.submit_media(media)
    assert result.status is CaptureStatus.QUEUED
    assert not pipeline.executed


def test_explicit_non_manual_realtime_envelope_can_execute():
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


def test_process_later_forces_enqueue_under_normal_policy():
    pipeline = FakePipeline()
    service = CaptureService(pipeline, policy=CapturePolicy.for_mode(CaptureMode.NORMAL))
    result = service.submit_text("later", process_later=True)
    assert result.status is CaptureStatus.QUEUED
    assert pipeline.enqueued and not pipeline.executed


def test_paused_service_rejects_processing():
    service = CaptureService(FakePipeline(), policy=CapturePolicy.for_mode(CaptureMode.PAUSED))
    result = service.submit_text("hello")
    assert result.status is CaptureStatus.PAUSED


def test_normalized_url_and_manual_text_are_deduplicated():
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


def test_enqueue_failure_does_not_poison_deduplication():
    pipeline = FakePipeline()
    pipeline.fail_enqueue_once = True
    service = CaptureService(pipeline)
    with pytest.raises(RuntimeError):
        service.submit_text("retry enqueue")
    retry = service.submit_text("retry enqueue")
    assert retry.status is CaptureStatus.QUEUED


def test_execute_failure_does_not_poison_deduplication():
    pipeline = FakePipeline()
    pipeline.fail_execute_once = True
    service = CaptureService(pipeline, policy=CapturePolicy.for_mode(CaptureMode.NORMAL))
    envelope = CaptureEnvelope(
        capture_id="cap-execute-1",
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
def test_metadata_cannot_override_capture_contract(key):
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


def test_codex_messages_link_to_their_own_memories_and_skip_only_missing(tmp_path):
    read_model = FakeStructuredReadModel()
    sink = StructuredReadModelSink(
        read_model,
        storage_path=tmp_path,
        memory_database=FakeMemoryDatabase({"mem-report", "mem-task"}),
    )
    messages = (
        StructuredMessage("report", "assistant", "report", 0, metadata={"document_stable_id": "mem-report"}),
        StructuredMessage("error", "error", "error", 1, metadata={"document_stable_id": "mem-error"}),
        StructuredMessage("task", "task", "task", 2, metadata={"document_stable_id": "mem-task"}),
    )
    batch = ExtractionBatch(
        documents=(),
        structured_sources=(
            StructuredSource(
                "codex",
                "repo",
                "Codex",
                (
                    StructuredConversation(
                        "task-1",
                        "Codex batch",
                        messages,
                        metadata={"document_stable_id": "conversation-fallback"},
                    ),
                ),
            ),
        ),
    )
    for execution_id in ("exec-1", "exec-2"):
        result = sink.write_batch(
            batch,
            raw_snapshot=None,
            vault_results={},
            execution_id=execution_id,
            adapter_name="codex_work_report",
            adapter_version="1",
            indexing_succeeded=True,
        )
        assert result["links"] == 2
    records = read_model.bundles[0]["conversations"][0]["messages"]
    assert records[0]["memory_links"][0]["memory_id"] == "mem-report"
    assert "memory_links" not in records[1]
    assert records[2]["memory_links"][0]["memory_id"] == "mem-task"
    import copy
    b0, b1 = copy.deepcopy(read_model.bundles[0]), copy.deepcopy(read_model.bundles[1])
    b0["source"]["metadata"].pop("import_execution_id", None)
    b1["source"]["metadata"].pop("import_execution_id", None)
    assert b0 == b1, "bundles differ beyond import_execution_id"
