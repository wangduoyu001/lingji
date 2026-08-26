from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from src.automatic_memory.models import AuthorizationScope
from src.extraction.adapters.chatgpt import ChatGPTExportAdapter
from src.extraction.adapters.claude_desktop import ClaudeDesktopAdapter
from src.extraction.adapters.codex import CodexTranscriptAdapter
from src.extraction.adapters.generic_ai_history import GenericAIHistoryAdapter
from src.extraction.models import ExtractionRequest
from src.extraction.registry import AdapterRegistry


FIXTURES = Path(__file__).parent / "fixtures" / "automatic_memory"


def _chatgpt_conversation() -> dict:
    return {
        "id": "official-conv-1",
        "title": "Official export",
        "create_time": 1_700_000_000,
        "update_time": 1_700_000_001,
        "current_node": "node-a",
        "mapping": {
            "node-u": {
                "id": "node-u",
                "parent": None,
                "children": ["node-a"],
                "message": {
                    "id": "official-msg-1",
                    "author": {"role": "user"},
                    "create_time": 1_700_000_000,
                    "content": {"content_type": "text", "parts": ["Question"]},
                    "metadata": {},
                },
            },
            "node-a": {
                "id": "node-a",
                "parent": "node-u",
                "children": [],
                "message": {
                    "id": "official-msg-2",
                    "author": {"role": "assistant"},
                    "create_time": 1_700_000_001,
                    "content": {"content_type": "text", "parts": ["Answer"]},
                    "metadata": {},
                },
            },
        },
    }


def test_chatgpt_accepts_official_json_and_preserves_ids(tmp_path: Path):
    path = tmp_path / "conversations.json"
    path.write_text(json.dumps([_chatgpt_conversation()]), encoding="utf-8")
    adapter = ChatGPTExportAdapter()

    detection = adapter.detect(path)
    assert detection.supported is True
    batch = adapter.extract(ExtractionRequest("job", "chatgpt_export", input_path=path))

    conversation = batch.structured_sources[0].conversations[0]
    assert conversation.external_id == "official-conv-1"
    assert [message.external_id for message in conversation.messages] == [
        "official-msg-1",
        "official-msg-2",
    ]
    assert [message.metadata["node_id"] for message in conversation.messages] == [
        "node-u",
        "node-a",
    ]


def test_chatgpt_rejects_unknown_json_structure_without_guessing(tmp_path: Path):
    path = tmp_path / "not-an-export.json"
    path.write_text(json.dumps({"items": [{"id": "guess-me"}]}), encoding="utf-8")
    adapter = ChatGPTExportAdapter()

    detection = adapter.detect(path)
    assert detection.supported is False
    assert "official" in detection.reason.lower()
    with pytest.raises(ValueError, match="unsupported|official"):
        adapter.extract(ExtractionRequest("job", "chatgpt_export", input_path=path))


def test_chatgpt_rejects_zip_path_traversal(tmp_path: Path):
    path = tmp_path / "export.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../conversations.json", json.dumps([_chatgpt_conversation()]))
    detection = ChatGPTExportAdapter().detect(path)
    assert detection.supported is False


def test_codex_transcript_detects_explicit_version_and_extracts_jsonl(tmp_path: Path):
    path = tmp_path / "session.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"schema": "codex_transcript", "schema_version": "1", "type": "header"}),
                json.dumps({"type": "message", "conversation_id": "c1", "message_id": "m1", "role": "user", "content": "Question", "timestamp": "2026-08-26T04:00:00Z"}),
                json.dumps({"type": "message", "conversation_id": "c1", "message_id": "m2", "role": "assistant", "content": "Answer", "timestamp": "2026-08-26T04:00:01Z"}),
            ]
        ),
        encoding="utf-8",
    )
    adapter = CodexTranscriptAdapter()

    detection = adapter.detect_schema(path)
    assert detection == detection.__class__("codex_transcript", "1", True, detection.reason)
    batch = adapter.extract(ExtractionRequest("job", "codex_transcript", input_path=path))
    conversation = batch.structured_sources[0].conversations[0]
    assert conversation.external_id == "c1"
    assert [message.external_id for message in conversation.messages] == ["m1", "m2"]


def test_codex_transcript_unknown_schema_fails_closed(tmp_path: Path):
    path = tmp_path / "unknown.jsonl"
    path.write_text(json.dumps({"type": "message", "content": "guess"}) + "\n", encoding="utf-8")
    detection = CodexTranscriptAdapter().detect_schema(path)
    assert detection.supported is False
    with pytest.raises(ValueError, match="unsupported|schema"):
        CodexTranscriptAdapter().extract(ExtractionRequest("job", "codex_transcript", input_path=path))


@pytest.mark.parametrize("name", ["generic_ai_history.json", "generic_ai_history.jsonl", "generic_ai_history.md"])
def test_generic_history_inbox_accepts_owner_selected_formats(name: str):
    adapter = GenericAIHistoryAdapter()
    path = FIXTURES / name

    detection = adapter.detect(path)
    assert detection.supported is True
    batch = adapter.extract(ExtractionRequest("job", "generic_ai_history", input_path=path))
    assert len(batch.documents) == 1
    conversation = batch.structured_sources[0].conversations[0]
    assert conversation.external_id
    assert [message.sequence for message in conversation.messages] == list(range(len(conversation.messages)))
    assert all(message.external_id for message in conversation.messages)
    again = adapter.extract(ExtractionRequest("job-2", "generic_ai_history", input_path=path))
    assert again.documents[0].external_id == batch.documents[0].external_id


def test_generic_history_rejects_unmarked_markdown(tmp_path: Path):
    path = tmp_path / "ordinary.md"
    path.write_text("# A note\n\n## user\n\nhello", encoding="utf-8")
    detection = GenericAIHistoryAdapter().detect(path)
    assert detection.supported is False
    with pytest.raises(ValueError, match="History Inbox|unsupported"):
        GenericAIHistoryAdapter().extract(ExtractionRequest("job", "generic_ai_history", input_path=path))


def test_claude_desktop_reports_consent_or_unsupported_without_opening_storage():
    adapter = ClaudeDesktopAdapter()
    unconfirmed = AuthorizationScope("g1", ("claude_desktop",), ("/opaque",), datetime.now(), None, False)
    confirmed = AuthorizationScope("g2", ("claude_desktop",), ("/opaque",), datetime.now(), None, True)
    assert adapter.capability(unconfirmed).status == "consent_required"
    assert adapter.capability(confirmed).status == "unsupported"


def test_registry_resolves_only_supported_approved_adapter(tmp_path: Path):
    path = FIXTURES / "generic_ai_history.json"
    registry = AdapterRegistry()
    registry.register(GenericAIHistoryAdapter())
    assert registry.resolve("generic_ai_history", path).name == "generic_ai_history"
    with pytest.raises(LookupError):
        registry.resolve("generic_ai_history", tmp_path / "unknown.json")
