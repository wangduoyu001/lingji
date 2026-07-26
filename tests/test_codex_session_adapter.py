from __future__ import annotations

from src.extraction.adapters.codex_session import CodexSessionAdapter
from src.extraction.models import ExtractionRequest


def test_codex_session_maps_only_structured_source_without_obsidian_document():
    adapter = CodexSessionAdapter()
    batch = adapter.extract(ExtractionRequest(
        job_id="EXEC-1", source_type="codex_session", adapter_name="codex_session",
        payload={
            "raw_reference": "raw:codex/sessions/LJ-PROJ-LINGJI/S1.jsonl",
            "session": {
                "session_id": "S1", "project_id": "LJ-PROJ-LINGJI",
                "project_name": "LingJi", "repository": "wangduoyu001/lingji",
                "title": "Build resolver", "status": "active",
                "created_at": "2026-07-21T00:00:00+00:00",
                "branch": "work/p2-07a", "worktree_name": "lingji-p2-07",
            },
            "events": [{
                "event_id": "E1", "session_id": "S1", "project_id": "LJ-PROJ-LINGJI",
                "event_type": "checkpoint", "occurred_at": "2026-07-21T00:01:00+00:00",
                "sequence": 2, "summary": "Tests passed",
                "payload": {
                    "changed_files": [r"D:\code\lingji\src\x.py", "tests/test_x.py"],
                    "tests": {"status": "passed"}, "token": "secret-token",
                },
                "content_hash": "abc",
            }],
        },
    ))
    assert batch.documents == ()
    assert len(batch.structured_sources) == 1
    source = batch.structured_sources[0]
    assert source.source_type == "codex_session"
    assert source.external_id == "codex:LJ-PROJ-LINGJI"
    assert source.projects == ("LJ-PROJ-LINGJI",)
    assert source.agent_scope == ("codex", "lingji-local")
    conversation = source.conversations[0]
    assert conversation.external_id == "S1"
    assert conversation.participants == ("owner", "codex")
    message = conversation.messages[0]
    assert message.external_id == "E1"
    assert message.role == "assistant"
    assert message.raw_reference == "raw:codex/sessions/LJ-PROJ-LINGJI/S1.jsonl"
    assert message.projects == ("LJ-PROJ-LINGJI",)
    assert message.metadata["changed_files"] == ["x.py", "tests/test_x.py"]
    assert "secret-token" not in message.content
