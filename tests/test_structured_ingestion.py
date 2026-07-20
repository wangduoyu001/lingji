from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from src.extraction.adapters.chatgpt import ChatGPTExportAdapter
from src.extraction.models import (
    ExtractedDocument,
    ExtractionBatch,
    ExtractionRequest,
    StructuredConversation,
    StructuredMessage,
    StructuredSource,
)
from src.extraction.structured_sink import StructuredReadModelSink


class FakeReadModel:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.bundles = []

    def upsert_bundle(self, bundle):
        if self.fail:
            raise RuntimeError("/private/user/lingji_memory.db is locked")
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
                        "author": {"role": "assistant", "name": "ChatGPT"},
                        "create_time": 102,
                        "content": {"parts": ["answer"]},
                        "metadata": {"model_slug": "gpt-test"},
                    },
                },
                "node-1": {
                    "parent": "",
                    "message": {
                        "author": {"role": "user", "name": "owner"},
                        "create_time": 101,
                        "content": {"parts": ["question"]},
                        "metadata": {"attachments": [{"id": "file-1", "name": "a.txt"}]},
                    },
                },
                "branch": {
                    "parent": "node-1",
                    "message": {
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
        "node-1",
        "node-2",
        "branch",
    ]
    assert [message.sequence for message in conversation.messages] == [0, 1, 2]
    assert conversation.messages[1].metadata["model"] == "gpt-test"
    assert conversation.messages[2].metadata["is_branch"] is True


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
    batch = ExtractionBatch(
        documents=(
            ExtractedDocument(
                stable_id=memory_id,
                title="t",
                body="b",
                source_type="chatgpt",
            ),
        ),
        structured_sources=(
            StructuredSource(
                source_type="chatgpt",
                external_id="account",
                display_name="ChatGPT",
                conversations=(
                    StructuredConversation(
                        external_id="conv-1",
                        title="t",
                        messages=(
                            StructuredMessage(
                                external_id="node-1",
                                role="user",
                                content="hello",
                                sequence=0,
                            ),
                        ),
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
    assert str(tmp_path) not in " ".join(failed["warnings"])
