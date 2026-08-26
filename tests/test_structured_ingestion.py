from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.extraction.adapters.chatgpt import ChatGPTExportAdapter
from src.extraction.base import ExtractionAdapter
from src.extraction.models import (
    ExtractedDocument,
    ExtractionBatch,
    ExtractionRequest,
    StructuredConversation,
    StructuredMessage,
    StructuredSource,
)
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.structured_sink import StructuredReadModelSink
from src.retrieval import MemoryDatabase
from src.sources import SourceReadModel
from src.storage import StateDatabase


class FakeReadModel:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.bundles = []

    def upsert_bundle(self, bundle):
        if self.fail:
            raise RuntimeError(r"D:\Users\Secret\lingji_memory.db is locked")
        self.bundles.append(bundle)
        conversations = bundle["conversations"]
        messages = [message for conversation in conversations for message in conversation["messages"]]
        links = [link for message in messages for link in message.get("memory_links", [])]
        return {
            "sources": 1,
            "conversations": len(conversations),
            "messages": len(messages),
            "links": len(links),
        }


class FakeMemoryDatabase:
    def __init__(self, existing=()):
        self.existing = set(existing)

    def fetch_memory(self, memory_id, include_chunks=True):
        del include_chunks
        return {"memory_id": memory_id} if memory_id in self.existing else None


class FakeAdapter(ExtractionAdapter):
    name = "fake_structured"
    version = "1.0"
    source_types = ("fake",)

    def __init__(self, batch: ExtractionBatch, order: list[str]):
        self.batch = batch
        self.order = order

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        del request
        self.order.append("adapter")
        return self.batch


class FakeVaultSink:
    def __init__(self, order: list[str], document_id: str):
        self.order = order
        self.document_id = document_id

    def preserve_raw(self, input_path, source_type):
        del input_path, source_type
        self.order.append("raw")
        return {}

    def write_batch(self, batch, *, adapter_name, adapter_version, raw_snapshot):
        del adapter_name, adapter_version, raw_snapshot
        self.order.append("vault")
        return {
            "documents": len(batch.documents),
            "created": [
                {
                    "id": self.document_id,
                    "relative_path": "02-Sources/fake/document.md",
                }
            ],
            "updated": [],
            "skipped": [],
            "paths": ["02-Sources/fake/document.md"],
            "warnings": list(batch.warnings),
            "summary": dict(batch.summary),
            "raw_snapshot": {},
        }


class TrackingStructuredSink(StructuredReadModelSink):
    def __init__(self, *args, order: list[str], **kwargs):
        super().__init__(*args, **kwargs)
        self.order = order

    def write_batch(self, *args, **kwargs):
        self.order.append("structured")
        return super().write_batch(*args, **kwargs)


class FailingStateDatabase:
    def append_event(self, event_type, entity_type, entity_id, payload):
        del event_type, entity_type, entity_id, payload
        raise RuntimeError(r"D:\Users\Secret\lingji_state.db is locked")


def _structured_batch(*, document_id: str = "LJ-CHATGPT-conv-1") -> ExtractionBatch:
    return ExtractionBatch(
        documents=(
            ExtractedDocument(
                stable_id=document_id,
                title="Structured test",
                body="Vault body",
                source_type="chatgpt",
            ),
        ),
        structured_sources=(
            StructuredSource(
                source_type="chatgpt",
                external_id="account-1",
                display_name="ChatGPT",
                projects=("LingJi",),
                conversations=(
                    StructuredConversation(
                        external_id="conv-1",
                        title="Structured test",
                        messages=(
                            StructuredMessage(
                                external_id="node-1",
                                role="user",
                                author="owner",
                                content="hello from the structured message",
                                sequence=0,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def _chatgpt_fixture(path: Path) -> Path:
    payload = [
        {
            "id": "conv-1",
            "title": "Structured test",
            "create_time": 100,
            "update_time": 200,
            "current_node": "node-2",
            "mapping": {
                "node-2": {
                    "parent": "node-1",
                    "message": {
                        "id": "node-2-message",
                        "author": {"role": "assistant", "name": "ChatGPT"},
                        "create_time": 102,
                        "content": {"parts": ["answer"]},
                        "metadata": {"model_slug": "gpt-test"},
                    },
                },
                "node-1": {
                    "parent": "",
                    "message": {
                        "id": "node-1-message",
                        "author": {"role": "user", "name": "owner"},
                        "create_time": 101,
                        "content": {"parts": ["question"]},
                        "metadata": {"attachments": [{"id": "file-1", "name": "a.txt"}]},
                    },
                },
                "branch": {
                    "parent": "node-1",
                    "message": {
                        "id": "branch-message",
                        "author": {"role": "assistant"},
                        "create_time": 103,
                        "content": {"parts": ["branch answer"]},
                        "metadata": {"model_slug": "gpt-branch"},
                    },
                },
            },
        }
    ]
    target = path / "conversations.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def _pipeline(
    root: Path,
    *,
    order: list[str],
    batch: ExtractionBatch,
    on_documents_written=None,
):
    memory_database = MemoryDatabase(root / "lingji_memory.db")
    read_model = SourceReadModel(memory_database)
    state_db = StateDatabase(root / "lingji_state.db")
    structured_sink = TrackingStructuredSink(
        read_model,
        storage_path=root / "storage",
        state_db=state_db,
        memory_database=memory_database,
        order=order,
    )
    registry = AdapterRegistry()
    registry.register(FakeAdapter(batch, order))
    pipeline = ExtractionPipeline(
        SQLiteExtractionQueue(root / "queue.db"),
        registry,
        FakeVaultSink(order, batch.documents[0].stable_id),
        structured_sink=structured_sink,
        on_documents_written=on_documents_written,
    )
    return pipeline, read_model, state_db


def test_transport_models_are_backward_compatible_and_frozen():
    batch = ExtractionBatch(documents=())
    assert batch.structured_sources == ()
    with pytest.raises(FrozenInstanceError):
        batch.documents = ()


def test_chatgpt_emits_document_and_structured_conversation_in_one_pass(tmp_path):
    export = _chatgpt_fixture(tmp_path)
    request = ExtractionRequest(
        job_id="job-1",
        source_type="chatgpt",
        input_path=export,
        options={
            "source_external_id": "account-42",
            "source_display_name": "Primary ChatGPT",
            "privacy_scan": False,
        },
    )

    batch = ChatGPTExportAdapter().extract(request)

    assert len(batch.documents) == 1
    source = batch.structured_sources[0]
    conversation = source.conversations[0]
    assert source.external_id == "account-42"
    assert source.display_name == "Primary ChatGPT"
    assert conversation.external_id == "conv-1"
    assert conversation.metadata["document_stable_id"] == batch.documents[0].stable_id
    assert [message.external_id for message in conversation.messages] == [
        "node-1-message",
        "node-2-message",
        "branch-message",
    ]
    assert [message.sequence for message in conversation.messages] == [0, 1, 2]
    assert conversation.messages[1].metadata["model"] == "gpt-test"
    assert conversation.messages[2].metadata["is_branch"] is True


def test_chatgpt_conversation_warning_is_stable_and_does_not_leak_path(
    tmp_path, monkeypatch
):
    export = _chatgpt_fixture(tmp_path)
    adapter = ChatGPTExportAdapter()

    def fail_conversation(conversation):
        raise RuntimeError(
            rf"{conversation['id']}: D:\Users\Secret\conversations.json contains private details"
        )

    monkeypatch.setattr(adapter, "_normalize_conversation", fail_conversation)
    batch = adapter.extract(
        ExtractionRequest(
            job_id="job-warning",
            source_type="chatgpt",
            input_path=export,
            options={"privacy_scan": False},
        )
    )

    assert batch.warnings == (
        "conv-1: conversation extraction failed; see local logs",
    )
    warning = batch.warnings[0]
    assert "D:\\" not in warning
    assert "Users" not in warning
    assert "conversations.json" not in warning
    assert "private details" not in warning


def test_structured_sink_writes_safe_references_and_is_idempotency_ready(tmp_path):
    storage = tmp_path / "storage"
    raw_path = storage / "raw" / "chatgpt" / "sha" / "conversations.json"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text("[]", encoding="utf-8")
    read_model = FakeReadModel()
    memory_id = "LJ-CHATGPT-conv-1"
    sink = StructuredReadModelSink(
        read_model,
        storage_path=storage,
        memory_database=FakeMemoryDatabase({memory_id}),
    )
    batch = _structured_batch(document_id=memory_id)
    conversation = batch.structured_sources[0].conversations[0]
    batch = ExtractionBatch(
        documents=batch.documents,
        structured_sources=(
            StructuredSource(
                source_type="chatgpt",
                external_id="account",
                display_name="ChatGPT",
                conversations=(
                    StructuredConversation(
                        external_id=conversation.external_id,
                        title=conversation.title,
                        messages=conversation.messages,
                        metadata={"document_stable_id": memory_id},
                    ),
                ),
            ),
        ),
    )
    vault_results = {
        "created": [
            {
                "id": memory_id,
                "path": str(tmp_path / "vault" / "note.md"),
                "relative_path": "07-Sources/chatgpt/note.md",
            }
        ],
        "updated": [],
        "skipped": [],
    }

    first = sink.write_batch(
        batch,
        raw_snapshot={
            "raw_path": str(raw_path),
            "sha256": "sha",
            "kind": "file",
            "size": 2,
        },
        vault_results=vault_results,
        execution_id="exec-1",
        adapter_name="chatgpt_export",
        adapter_version="1.2.0",
        indexing_succeeded=True,
    )
    second = sink.write_batch(
        batch,
        raw_snapshot={"raw_path": str(raw_path), "sha256": "sha", "kind": "file", "size": 2},
        vault_results=vault_results,
        execution_id="exec-2",
        adapter_name="chatgpt_export",
        adapter_version="1.2.0",
        indexing_succeeded=True,
    )

    assert first["state"] == second["state"] == "written"
    assert first["links"] == 1
    bundle = read_model.bundles[0]
    assert bundle["source"]["raw_reference"] == "raw:chatgpt/sha/conversations.json"
    assert bundle["source"]["vault_reference"] == "vault:07-Sources/chatgpt/note.md"
    serialized = json.dumps(bundle)
    assert str(tmp_path) not in serialized


def test_real_sqlite_structured_write_is_idempotent_and_audited():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        memory_database = MemoryDatabase(root / "lingji_memory.db")
        read_model = SourceReadModel(memory_database)
        state_db = StateDatabase(root / "lingji_state.db")
        sink = StructuredReadModelSink(
            read_model,
            storage_path=root / "storage",
            state_db=state_db,
            memory_database=memory_database,
        )
        batch = _structured_batch()

        for _ in range(2):
            result = sink.write_batch(
                batch,
                raw_snapshot=None,
                vault_results={
                    "created": [
                        {
                            "id": batch.documents[0].stable_id,
                            "relative_path": "02-Sources/chatgpt/document.md",
                        }
                    ]
                },
                execution_id="exec-real",
                adapter_name="chatgpt_export",
                adapter_version="1.2.0",
                indexing_succeeded=False,
            )
            assert result["state"] == "written"

        stats = read_model.stats()
        assert stats["sources"] == 1
        assert stats["conversations"] == 1
        assert stats["messages"] == 1
        message_id = read_model.list_messages()["items"][0]["message_id"]
        detail = read_model.get_message(message_id, include_content=True)
        assert detail["content"] == "hello from the structured message"

        event = state_db.recent_events(limit=1)[0]
        assert event["event_type"] == "structured_ingestion_completed"
        assert event["entity_type"] == "structured_ingestion"
        assert event["entity_id"] == "exec-real"
        payload = json.loads(event["payload_json"])
        assert payload["state"] == "written"
        assert str(root) not in json.dumps(payload)


def test_audit_event_failure_does_not_break_structured_write(tmp_path):
    memory_database = MemoryDatabase(tmp_path / "lingji_memory.db")
    read_model = SourceReadModel(memory_database)
    sink = StructuredReadModelSink(
        read_model,
        storage_path=tmp_path / "storage",
        state_db=FailingStateDatabase(),
        memory_database=memory_database,
    )

    result = sink.write_batch(
        _structured_batch(),
        raw_snapshot=None,
        vault_results={},
        execution_id="exec-event-failure",
        adapter_name="chatgpt_export",
        adapter_version="1.2.0",
        indexing_succeeded=False,
    )

    assert result["state"] == "written"
    assert read_model.stats()["messages"] == 1


def test_pipeline_order_is_vault_then_index_callback_then_structured_sink(tmp_path):
    order: list[str] = []

    def index_callback(response):
        assert response["documents"] == 1
        order.append("index")

    pipeline, read_model, _ = _pipeline(
        tmp_path,
        order=order,
        batch=_structured_batch(),
        on_documents_written=index_callback,
    )

    response = pipeline.execute("fake", execution_id="exec-order")

    assert order == ["raw", "adapter", "vault", "index", "structured"]
    assert response["indexed"] is True
    assert response["structured_read_model"]["state"] == "written"
    assert read_model.stats()["messages"] == 1


def test_index_failure_is_sanitized_and_does_not_rollback_structured_data(tmp_path):
    order: list[str] = []

    def failing_index_callback(response):
        assert response["documents"] == 1
        order.append("index")
        raise RuntimeError(r"D:\Users\Secret\lingji_memory.db is locked")

    pipeline, read_model, state_db = _pipeline(
        tmp_path,
        order=order,
        batch=_structured_batch(),
        on_documents_written=failing_index_callback,
    )

    response = pipeline.execute("fake", execution_id="exec-index-failure")

    assert order == ["raw", "adapter", "vault", "index", "structured"]
    assert response["documents"] == 1
    assert response["created"]
    assert response["indexed"] is False
    assert response["index_error"] == (
        "Post-extraction index synchronization failed; see local logs"
    )
    for forbidden in ("D:\\", "Users", "lingji_memory.db"):
        assert forbidden not in response["index_error"]
    assert response["structured_read_model"]["state"] == "written"
    assert read_model.stats()["sources"] == 1
    assert read_model.stats()["conversations"] == 1
    assert read_model.stats()["messages"] == 1
    event = state_db.recent_events(limit=1)[0]
    assert event["event_type"] == "structured_ingestion_completed"
    assert event["entity_type"] == "structured_ingestion"
    assert event["entity_id"] == "exec-index-failure"


def test_missing_memory_skips_link_without_losing_messages(tmp_path):
    read_model = FakeReadModel()
    sink = StructuredReadModelSink(
        read_model,
        storage_path=tmp_path,
        memory_database=FakeMemoryDatabase(),
    )
    batch = ExtractionBatch(
        documents=(),
        structured_sources=(
            StructuredSource(
                source_type="chatgpt",
                external_id="account",
                display_name="ChatGPT",
                conversations=(
                    StructuredConversation(
                        external_id="conv",
                        title="t",
                        messages=(StructuredMessage("node", "user", "hello", 0),),
                        metadata={"document_stable_id": "missing"},
                    ),
                ),
            ),
        ),
    )

    result = sink.write_batch(
        batch,
        raw_snapshot=None,
        vault_results={},
        execution_id="exec",
        adapter_name="chatgpt_export",
        adapter_version="1.2.0",
        indexing_succeeded=False,
    )

    assert result["state"] == "written"
    assert result["messages"] == 1
    assert result["links"] == 0
    assert result["warnings"]


def test_empty_and_failure_states_are_safe(tmp_path):
    empty = StructuredReadModelSink(FakeReadModel(), storage_path=tmp_path).write_batch(
        ExtractionBatch(documents=()),
        raw_snapshot=None,
        vault_results={},
        execution_id="exec",
        adapter_name="none",
        adapter_version="1",
        indexing_succeeded=True,
    )
    assert empty["state"] == "not_applicable"

    source = StructuredSource(
        source_type="chatgpt",
        external_id="account",
        display_name="ChatGPT",
        conversations=(),
    )
    failed = StructuredReadModelSink(FakeReadModel(fail=True), storage_path=tmp_path).write_batch(
        ExtractionBatch(documents=(), structured_sources=(source,)),
        raw_snapshot=None,
        vault_results={},
        execution_id="exec",
        adapter_name="chatgpt_export",
        adapter_version="1.2.0",
        indexing_succeeded=True,
    )
    assert failed["state"] == "degraded"
    assert failed["warnings"] == [
        "structured read model write failed; see local logs"
    ]
    serialized = " ".join(failed["warnings"])
    for forbidden in ("D:\\", "Users", "lingji_memory.db"):
        assert forbidden not in serialized
