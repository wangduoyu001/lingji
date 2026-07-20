from pathlib import Path

from src.extraction.adapters.codex import CodexWorkReportAdapter
from src.extraction.adapters.media import MediaExtractionAdapter
from src.extraction.adapters.web import WebCaptureAdapter
from src.extraction.models import ExtractionBatch, ExtractionRequest, StructuredSource
from src.extraction.registry import AdapterRegistry


def _registered(adapter, *, structured_fallback=True):
    registry = AdapterRegistry()
    registry.register(adapter, structured_fallback=structured_fallback)
    return registry.get(adapter.name)


def test_registry_default_does_not_wrap_unknown_adapter():
    class UnknownAdapter:
        name = "unknown"
        version = "1"
        source_types = ("unknown",)

        def can_handle(self, source_type, input_path, payload):
            return source_type == "unknown"

        def extract(self, request):
            return ExtractionBatch(documents=())

    original = UnknownAdapter()
    registry = AdapterRegistry()
    registry.register(original)
    assert registry.get("unknown") is original


def test_codex_adapter_emits_structured_source_without_changing_markdown():
    adapter = _registered(CodexWorkReportAdapter())
    batch = adapter.extract(
        ExtractionRequest(
            job_id="job",
            source_type="codex",
            payload={
                "task_id": "task-1",
                "execution_id": "exec-1",
                "project_id": "lingji",
                "summary": "implemented capture foundation",
                "repository": "wangduoyu001/lingji",
                "errors": ["none"],
                "decisions": ["keep contracts explicit"],
                "next_tasks": ["review"],
            },
        )
    )
    assert batch.documents[0].body.startswith("# ")
    source = batch.structured_sources[0]
    assert source.source_type == "codex"
    assert source.conversations[0].external_id == "task-1"
    assert len(source.conversations[0].messages) == len(batch.documents)
    assert {
        message.metadata["document_stable_id"]
        for message in source.conversations[0].messages
    } == {document.stable_id for document in batch.documents}


def test_web_adapter_emits_structured_source_and_keeps_document_body():
    adapter = _registered(WebCaptureAdapter())
    batch = adapter.extract(
        ExtractionRequest(
            job_id="job",
            source_type="web",
            payload={
                "url": "https://example.com/article?utm_source=test",
                "title": "Article",
                "text": "正文",
                "capture_method": "browser_extension",
            },
        )
    )
    assert "正文" in batch.documents[0].body
    source = batch.structured_sources[0]
    assert source.conversations[0].messages[0].content == batch.documents[0].body
    assert source.conversations[0].messages[0].metadata["capture_method"] == "browser_extension"


def test_media_adapter_emits_structured_source_without_exposing_input_path_in_contract(tmp_path, monkeypatch):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"small-media")
    raw_adapter = MediaExtractionAdapter(tmp_path / "storage")
    monkeypatch.setattr(raw_adapter, "_probe", lambda path, options, warnings: {})
    monkeypatch.setattr(raw_adapter, "_derive", lambda path, media_hash, media_kind, options, warnings: {})
    adapter = _registered(raw_adapter)
    batch = adapter.extract(
        ExtractionRequest(
            job_id="job",
            source_type="media",
            input_path=media,
            payload={"title": "Clip", "transcript": "spoken words"},
        )
    )
    assert batch.documents[0].body.startswith("# Clip")
    source = batch.structured_sources[0]
    message = source.conversations[0].messages[0]
    assert source.source_type == "video"
    assert str(tmp_path) not in message.content
    assert str(tmp_path) not in str(message.metadata)


def test_existing_structured_output_is_not_replaced_when_fallback_enabled():
    class AlreadyStructured:
        name = "already"
        version = "1"
        source_types = ("already",)

        def can_handle(self, source_type, input_path, payload):
            return source_type == "already"

        def extract(self, request):
            source = StructuredSource("already", "id", "Already", ())
            return ExtractionBatch(documents=(), structured_sources=(source,))

    adapter = _registered(AlreadyStructured(), structured_fallback=True)
    batch = adapter.extract(ExtractionRequest(job_id="job", source_type="already"))
    assert batch.structured_sources[0].external_id == "id"
