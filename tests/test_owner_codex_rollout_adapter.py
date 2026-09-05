from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.extraction.adapters.codex import CodexRolloutAdapter
from src.extraction.models import ExtractionRequest


def _record(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _fixture() -> list[dict]:
    return [
        {"type": "session_meta", "payload": {"id": "sess-1", "timestamp": "2026-08-28T10:00:00Z"}},
        {"type": "turn_context", "payload": {"turn_id": "turn-1", "timestamp": "2026-08-28T10:00:01Z"}},
        {"type": "event_msg", "id": "u1", "payload": {"type": "user_message", "message": "请整理项目"}, "timestamp": "2026-08-28T10:00:02Z"},
        {"type": "response_item", "id": "a1", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "已整理项目。"}]}, "timestamp": "2026-08-28T10:00:03Z"},
        {"type": "event_msg", "id": "u1", "payload": {"type": "user_message", "message": "请整理项目"}, "timestamp": "2026-08-28T10:00:02Z"},
        {"type": "response_item", "id": "tool-1", "payload": {"type": "function_call", "name": "shell", "arguments": "secret"}, "timestamp": "2026-08-28T10:00:04Z"},
        {"type": "event_msg", "payload": {"type": "agent_reasoning", "text": "hidden reasoning"}},
        {"type": "world_state", "payload": {"cwd": "/private/secret"}},
        {"type": "base_instructions", "payload": {"text": "do not ingest"}},
    ]


def test_rollout_adapter_streams_safe_messages_and_deduplicates(tmp_path: Path):
    path = tmp_path / "rollout.jsonl"
    _record(path, _fixture())
    adapter = CodexRolloutAdapter()
    request = ExtractionRequest("job-1", "codex_rollout", input_path=path, options={"authorized_roots": [str(tmp_path)]})

    batch = adapter.extract(request)

    assert adapter.name == "codex_rollout"
    source = batch.structured_sources[0]
    conversation = source.conversations[0]
    assert conversation.external_id == "codex-rollout:conversation:sess-1"
    assert [(item.role, item.content) for item in conversation.messages] == [
        ("user", "请整理项目"),
        ("assistant", "已整理项目。"),
    ]
    assert all("secret" not in item.content for item in conversation.messages)
    assert all(item.external_id for item in conversation.messages)
    assert conversation.messages[0].metadata["content_hash"]
    assert batch.summary["messages"] == 2


def test_rollout_adapter_fails_closed_on_unknown_schema(tmp_path: Path):
    path = tmp_path / "unknown.jsonl"
    _record(path, [{"type": "something_else", "payload": {"id": "x"}}])
    adapter = CodexRolloutAdapter()
    assert not adapter.can_handle("codex_rollout", path, {})
    with pytest.raises(ValueError, match="unsupported|schema"):
        adapter.extract(ExtractionRequest("job-1", "codex_rollout", input_path=path, options={"authorized_roots": [str(tmp_path)]}))


def test_rollout_adapter_skips_oversized_records_with_bounded_reads(tmp_path: Path):
    """A >1MB record is a giant tool/context dump, never chat content.

    The record is skipped with bounded chunked reads (never buffered or
    parsed whole) while the surrounding conversation stays authoritative.
    """
    path = tmp_path / "oversized.jsonl"
    path.write_text(
        json.dumps({"type": "session_meta", "payload": {"id": "s"}, "timestamp": "2026-09-01T09:00:00Z"}) + "\n"
        + "x" * (4 * 1024 * 1024) + "\n"
        + json.dumps({"type": "event_msg", "payload": {"type": "user_message", "message": "跳过大记录后对话仍在"}, "timestamp": "2026-09-01T09:01:00Z"}) + "\n",
        encoding="utf-8",
    )
    adapter = CodexRolloutAdapter()
    assert adapter.can_handle("codex_rollout", path, {})
    batch = adapter.extract(ExtractionRequest("job-1", "codex_rollout", input_path=path, options={"authorized_roots": [str(tmp_path)]}))
    conversation = batch.structured_sources[0].conversations[0]
    assert [(item.role, item.content) for item in conversation.messages] == [
        ("user", "跳过大记录后对话仍在"),
    ]


def test_rollout_requires_payload_session_identity_and_rejects_mixed_sessions(tmp_path: Path):
    path = tmp_path / "rollout.jsonl"
    _record(path, [
        {"type": "session_meta", "id": "top-level-must-not-count", "payload": {"id": "session-one"}},
        {"type": "session_meta", "payload": {"session_id": "session-two"}},
        {"type": "event_msg", "id": "u", "payload": {"type": "user_message", "message": "x"}, "timestamp": "2026-08-29T00:00:00Z"},
    ])
    adapter = CodexRolloutAdapter()
    with pytest.raises(ValueError, match="unsupported|session"):
        adapter.extract(ExtractionRequest("job-1", "codex_rollout", input_path=path, options={"authorized_roots": [str(tmp_path)]}))


def test_rollout_rejects_unknown_top_level_and_malformed_message_variant(tmp_path: Path):
    path = tmp_path / "rollout.jsonl"
    _record(path, [
        {"type": "session_meta", "payload": {"id": "session-one"}},
        {"type": "event_msg", "payload": {"type": "unrecognized_message", "role": "assistant", "text": "x"}, "timestamp": "2026-08-29T00:00:00Z"},
        {"type": "future_internal_event", "payload": {}},
    ])
    adapter = CodexRolloutAdapter()
    assert not adapter.can_handle("codex_rollout", path, {})


def test_rollout_deduplicates_same_content_with_different_event_ids_and_preserves_raw_identity(tmp_path: Path):
    path = tmp_path / "rollout.jsonl"
    _record(path, [
        {"type": "session_meta", "payload": {"id": "session-one"}},
        {"type": "event_msg", "id": "event-u", "payload": {"type": "user_message", "message": "same"}, "timestamp": "2026-08-29T00:00:00Z"},
        {"type": "response_item", "id": "response-u", "payload": {"type": "message", "role": "user", "content": "same"}, "timestamp": "2026-08-29T00:00:00Z"},
    ])
    batch = CodexRolloutAdapter().extract(ExtractionRequest("job-1", "codex_rollout", input_path=path, options={"authorized_roots": [str(tmp_path)]}))
    messages = batch.structured_sources[0].conversations[0].messages
    assert len(messages) == 1
    assert messages[0].raw_reference == "raw:codex_rollout/rollout.jsonl"


def test_rollout_automatic_dispatch_requires_exact_codex_root(tmp_path: Path):
    path = tmp_path / "rollout.jsonl"
    _record(path, _fixture())
    with pytest.raises(ValueError, match="root|authorized"):
        CodexRolloutAdapter().extract(ExtractionRequest(
            "job-1", "codex_rollout", input_path=path,
            payload={"source_id": "s1", "authorized_root": str(tmp_path)},
        options={"automatic_memory": True},
        ))


def test_rollout_automatic_dispatch_rejects_same_named_root_outside_effective_home(tmp_path: Path, monkeypatch):
    effective_home = tmp_path / "effective-home"
    outside_root = tmp_path / "other-home" / ".codex" / "sessions"
    path = outside_root / "rollout-outside.jsonl"
    path.parent.mkdir(parents=True)
    _record(path, _fixture())
    monkeypatch.setenv("HOME", str(effective_home))
    with pytest.raises(ValueError, match="root|authorized"):
        CodexRolloutAdapter().extract(ExtractionRequest(
            "job-1", "codex_rollout", input_path=path,
            payload={"source_id": "s1", "authorized_root": str(outside_root)},
            options={"automatic_memory": True},
        ))


def test_rollout_automatic_dispatch_requires_matching_durable_raw_snapshot(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    root = home / ".codex" / "sessions"
    source_path = root / "rollout-source.jsonl"
    raw_path = tmp_path / "raw" / "durable-object"
    source_path.parent.mkdir(parents=True)
    _record(source_path, _fixture())
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(source_path.read_bytes())
    monkeypatch.setenv("HOME", str(home))
    with pytest.raises(ValueError, match="raw|snapshot|provenance"):
        CodexRolloutAdapter().extract(ExtractionRequest(
            "job-1", "codex_rollout", input_path=source_path,
            payload={
                "source_id": "s1", "authorized_root": str(root),
                "effective_home": str(home), "raw_id": "a" * 64,
                "raw_path": str(raw_path),
            }, options={"automatic_memory": True},
        ))


def test_rollout_adapter_accepts_new_codex_variants_and_extracts_agent_messages(tmp_path: Path):
    """Codex 26.825.x emits new telemetry/tool variants plus agent_message carriers.

    Recognized non-message variants must be skipped; agent_message must be
    extracted as the assistant message; truly unknown types still fail closed.
    """
    path = tmp_path / "rollout-new.jsonl"
    _record(path, [
        {"type": "session_meta", "payload": {"id": "thread-new", "session_id": "origin-old", "timestamp": "2026-09-01T09:00:00Z"}},
        {"type": "compacted", "payload": {"message": "context compacted summary"}},
        {"type": "inter_agent_communication_metadata", "payload": {"peer": "sub-agent"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "帮我排期"}, "timestamp": "2026-09-01T09:01:00Z"},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {"total": 100}}, "timestamp": "2026-09-01T09:01:10Z"},
        {"type": "event_msg", "payload": {"type": "task_started", "task": "t"}, "timestamp": "2026-09-01T09:01:11Z"},
        {"type": "event_msg", "payload": {"type": "item_completed", "item": {"id": "i"}}, "timestamp": "2026-09-01T09:01:12Z"},
        {"type": "event_msg", "payload": {"type": "mcp_tool_call_end", "call": "c"}, "timestamp": "2026-09-01T09:01:13Z"},
        {"type": "event_msg", "payload": {"type": "thread_settings_applied"}, "timestamp": "2026-09-01T09:01:14Z"},
        {"type": "event_msg", "payload": {"type": "patch_apply_end"}, "timestamp": "2026-09-01T09:01:15Z"},
        {"type": "event_msg", "payload": {"type": "sub_agent_activity"}, "timestamp": "2026-09-01T09:01:16Z"},
        {"type": "event_msg", "payload": {"type": "web_search_end"}, "timestamp": "2026-09-01T09:01:17Z"},
        {"type": "event_msg", "payload": {"type": "turn_aborted"}, "timestamp": "2026-09-01T09:01:18Z"},
        {"type": "event_msg", "payload": {"type": "context_compacted"}, "timestamp": "2026-09-01T09:01:19Z"},
        {"type": "event_msg", "payload": {"type": "agent_message", "message": "已排好下周发布计划。"}, "timestamp": "2026-09-01T09:02:00Z"},
        {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "tool"}, "timestamp": "2026-09-01T09:02:10Z"},
        {"type": "response_item", "payload": {"type": "custom_tool_call_output", "output": "ok"}, "timestamp": "2026-09-01T09:02:11Z"},
        {"type": "response_item", "payload": {"type": "agent_message", "author": "assistant", "content": [{"type": "output_text", "text": "这是新版助手回复。"}]}, "timestamp": "2026-09-01T09:02:20Z"},
        {"type": "event_msg", "payload": {"type": "task_complete"}, "timestamp": "2026-09-01T09:02:30Z"},
    ])
    adapter = CodexRolloutAdapter()
    assert adapter.can_handle("codex_rollout", path, {}), "new Codex variants must pass schema detection"
    batch = adapter.extract(ExtractionRequest("job-2", "codex_rollout", input_path=path, options={"authorized_roots": [str(tmp_path)]}))
    conversation = batch.structured_sources[0].conversations[0]
    assert conversation.external_id.endswith("thread-new"), "new-format thread id must be the conversation identity"
    roles = [(item.role, item.content) for item in conversation.messages]
    assert ("user", "帮我排期") in roles
    assert ("assistant", "已排好下周发布计划。") in roles, "event agent_message must be extracted as assistant"
    assert ("assistant", "这是新版助手回复。") in roles, "response_item agent_message must be extracted as assistant"
    assert all("secret" not in item.content for item in conversation.messages)


def test_rollout_adapter_still_fails_closed_on_truly_unknown_variant(tmp_path: Path):
    path = tmp_path / "rollout-unknown-variant.jsonl"
    _record(path, [
        {"type": "session_meta", "payload": {"id": "sess-u", "timestamp": "2026-09-01T09:00:00Z"}},
        {"type": "event_msg", "payload": {"type": "brand_new_future_variant"}, "timestamp": "2026-09-01T09:01:00Z"},
    ])
    adapter = CodexRolloutAdapter()
    assert not adapter.can_handle("codex_rollout", path, {}), "unknown future variants must keep failing closed"
