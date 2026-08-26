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
from src.extraction.base import ExtractionAdapter
from src.extraction.models import ExtractionBatch, ExtractionRequest
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
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


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_conversation",
        "duplicate_message",
        "missing_message_id",
        "missing_content",
        "invalid_role",
        "invalid_timestamp",
    ],
)
def test_chatgpt_rejects_duplicate_or_damaged_records(tmp_path: Path, mutation: str):
    first = _chatgpt_conversation()
    if mutation == "duplicate_conversation":
        payload = [first, json.loads(json.dumps(first))]
    else:
        payload = [first]
        message = first["mapping"]["node-a"]["message"]
        if mutation == "duplicate_message":
            first["mapping"]["node-u"]["message"]["id"] = message["id"]
        elif mutation == "missing_message_id":
            message.pop("id")
        elif mutation == "missing_content":
            message.pop("content")
        elif mutation == "invalid_role":
            message["author"]["role"] = "alien"
        else:
            message["create_time"] = "not-a-time"
    path = tmp_path / "conversations.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    adapter = ChatGPTExportAdapter()
    assert adapter.detect(path).supported is False
    with pytest.raises(ValueError):
        adapter.extract(ExtractionRequest("job", "chatgpt_export", input_path=path))


@pytest.mark.parametrize("members", [["nested/conversations.json"], ["conversations.json", "conversations.json"]])
def test_chatgpt_zip_requires_one_official_root_member(tmp_path: Path, members: list[str]):
    path = tmp_path / "export.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, json.dumps([_chatgpt_conversation()]))
    assert ChatGPTExportAdapter().detect(path).supported is False


def test_chatgpt_rejects_invalid_zip_encoding(tmp_path: Path):
    path = tmp_path / "export.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("conversations.json", b"\xff\xfe")
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
    batch = adapter.extract(ExtractionRequest("job", "codex_transcript", input_path=path, options={"authorized_roots": [str(tmp_path)]}))
    conversation = batch.structured_sources[0].conversations[0]
    assert conversation.external_id.endswith(":conversation:c1")
    assert [message.external_id.split(":")[-1] for message in conversation.messages] == ["m1", "m2"]


def test_codex_transcript_unknown_schema_fails_closed(tmp_path: Path):
    path = tmp_path / "unknown.jsonl"
    path.write_text(json.dumps({"type": "message", "content": "guess"}) + "\n", encoding="utf-8")
    detection = CodexTranscriptAdapter().detect_schema(path)
    assert detection.supported is False
    with pytest.raises(ValueError, match="unsupported|schema"):
        CodexTranscriptAdapter().extract(ExtractionRequest("job", "codex_transcript", input_path=path))


def test_unknown_codex_schema_is_recorded_by_existing_extraction_queue(tmp_path: Path):
    path = tmp_path / "unknown.jsonl"
    path.write_text(json.dumps({"schema": "future", "schema_version": "99"}) + "\n", encoding="utf-8")

    class Sink:
        def preserve_raw(self, input_path, source_type):
            del input_path, source_type
            return {}

        def write_batch(self, batch, *, adapter_name, adapter_version, raw_snapshot):
            del batch, adapter_name, adapter_version, raw_snapshot
            return {}

    queue = SQLiteExtractionQueue(tmp_path / "queue.db")
    registry = AdapterRegistry()
    registry.register(CodexTranscriptAdapter())
    pipeline = ExtractionPipeline(queue, registry, Sink())
    job = queue.enqueue("codex_transcript", input_path=path, adapter_name="codex_transcript", max_attempts=1)
    outcome = pipeline.process_job(job["job_id"])
    assert outcome["job"]["status"] == "failed"
    assert "unsupported" in outcome["job"]["last_error"].lower() or "approved" in outcome["job"]["last_error"].lower()


def test_codex_rejects_sensitive_ancestor_and_symlink_ancestor(tmp_path: Path):
    sensitive = tmp_path / "private" / "session.jsonl"
    sensitive.parent.mkdir()
    sensitive.write_text('{"schema":"codex_transcript","schema_version":"1","type":"header"}\n', encoding="utf-8")
    adapter = CodexTranscriptAdapter()
    assert adapter.detect_schema(sensitive).supported is False

    real = tmp_path / "real"
    real.mkdir()
    target = real / "session.jsonl"
    target.write_text('{"schema":"codex_transcript","schema_version":"1","type":"header"}\n', encoding="utf-8")
    link = tmp_path / "linked"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    assert adapter.detect_schema(link / "session.jsonl").supported is False


def test_codex_requires_canonical_authorized_root(tmp_path: Path):
    path = tmp_path / "session.jsonl"
    path.write_text(
        '{"schema":"codex_transcript","schema_version":"1","type":"header"}\n'
        '{"type":"message","conversation_id":"c","message_id":"m","role":"user","content":"x","timestamp":"2026-08-26T04:00:00Z"}\n',
        encoding="utf-8",
    )
    request = ExtractionRequest("job", "codex_transcript", input_path=path, options={"authorized_roots": [str(tmp_path / "elsewhere")]})
    with pytest.raises(ValueError, match="authorized|root"):
        CodexTranscriptAdapter().extract(request)


def test_codex_rejects_duplicate_message_and_bad_time_order(tmp_path: Path):
    path = tmp_path / "session.jsonl"
    header = {"schema": "codex_transcript", "schema_version": "1", "type": "header"}
    rows = [
        {"type": "message", "conversation_id": "c", "message_id": "m", "role": "user", "content": "x", "timestamp": "2026-08-26T04:00:01Z"},
        {"type": "message", "conversation_id": "c", "message_id": "m", "role": "assistant", "content": "y", "timestamp": "2026-08-26T04:00:00Z"},
    ]
    path.write_text("\n".join(json.dumps(item) for item in [header, *rows]), encoding="utf-8")
    adapter = CodexTranscriptAdapter()
    assert adapter.detect_schema(path).supported is False

    rows[1]["message_id"] = "m2"
    rows[0]["timestamp"] = "2026-08-26T04:00:00"
    path.write_text("\n".join(json.dumps(item) for item in [header, *rows]), encoding="utf-8")
    assert adapter.detect_schema(path).supported is False


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


def test_generic_history_rejects_duplicate_ids_and_non_utc_time(tmp_path: Path):
    payload = json.loads((FIXTURES / "generic_ai_history.json").read_text(encoding="utf-8"))
    payload["conversations"].append(json.loads(json.dumps(payload["conversations"][0])))
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    adapter = GenericAIHistoryAdapter()
    assert adapter.detect(path).supported is False

    payload["conversations"] = [payload["conversations"][0]]
    payload["conversations"][0]["messages"][1]["message_id"] = payload["conversations"][0]["messages"][0]["message_id"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert adapter.detect(path).supported is False

    payload["conversations"][0]["messages"][1]["message_id"] = "m2"
    payload["conversations"][0]["messages"][0]["timestamp"] = "2026-08-26T01:00:00"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert adapter.detect(path).supported is False


def test_generic_history_rejects_markdown_unknown_boundary(tmp_path: Path):
    path = tmp_path / "boundary.md"
    path.write_text(
        "---\nhistory_inbox: true\nschema: lingji.history.inbox\nschema_version: '1'\nconversation_id: c\ntitle: T\n---\n\n"
        "## user | 2026-08-26T01:00:00Z | m1\n\nhello\n\n## unrelated heading\n\nnot a message\n",
        encoding="utf-8",
    )
    assert GenericAIHistoryAdapter().detect(path).supported is False


def test_generic_history_external_ids_are_scoped_and_stable():
    adapter = GenericAIHistoryAdapter()
    path = FIXTURES / "generic_ai_history.json"
    first = adapter.extract(ExtractionRequest("job", "generic_ai_history", input_path=path))
    second = adapter.extract(ExtractionRequest("job2", "generic_ai_history", input_path=path))
    conversation = first.structured_sources[0].conversations[0]
    assert conversation.external_id != "inbox-conv-1"
    assert conversation.external_id == second.structured_sources[0].conversations[0].external_id
    assert conversation.messages[0].external_id != "inbox-msg-1"


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


def test_registry_does_not_resolve_unapproved_task3_adapter():
    class Unapproved(ExtractionAdapter):
        name = "unapproved"
        version = "1"
        source_types = ("generic_ai_history",)

        def can_handle(self, source_type, input_path, payload):
            return source_type == "generic_ai_history"

        def extract(self, request):
            del request
            return ExtractionBatch(documents=())

    registry = AdapterRegistry()
    registry.register(Unapproved())
    with pytest.raises(LookupError, match="approved"):
        registry.resolve("generic_ai_history", FIXTURES / "generic_ai_history.json")
