from __future__ import annotations

import inspect
import json


def _payload(result):
    return json.loads(result.content[0].text)


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(function):
            self.tools[function.__name__] = function
            return function
        return decorator


class FakeService:
    def resolve_project(self, workspace_path):
        return {"project_id": "P", "workspace": workspace_path}

    def start_session(self, **kwargs):
        return {"session_id": "S", **kwargs}

    def checkpoint(self, session_id, **kwargs):
        return {"session_id": session_id, **kwargs}

    def close_session(self, session_id, **kwargs):
        return {"session_id": session_id, **kwargs}


def test_codex_mcp_tools_exist_and_do_not_expose_core_memory_writes():
    from src.mcp_server import register_codex_mcp_tools

    mcp = FakeMCP()
    service = FakeService()
    register_codex_mcp_tools(mcp, service)
    assert set(mcp.tools) == {
        "lingji_resolve_project", "lingji_start_session", "lingji_checkpoint", "lingji_close_session",
    }
    assert not any("core_memory" in name or "vault" in name for name in mcp.tools)
    assert _payload(mcp.tools["lingji_resolve_project"]("D:/code/lingji"))["project_id"] == "P"
    assert _payload(mcp.tools["lingji_start_session"]("D:/code/lingji", "C1"))["session_id"] == "S"
    checkpoint = mcp.tools["lingji_checkpoint"](
        "S", "E1", "checkpoint", "summary", changed_files=["src/x.py"]
    )
    assert _payload(checkpoint)["event_id"] == "E1"
    closed = mcp.tools["lingji_close_session"]("S", "E2", "done")
    assert _payload(closed)["status"] == "completed"
    for function in mcp.tools.values():
        parameters = set(inspect.signature(function).parameters)
        assert "vault_path" not in parameters
        assert "core_memory" not in parameters


def test_slim_search_results_keeps_agent_fields_and_drops_metadata():
    from src.mcp_server import slim_search_results

    payload = {
        "query": "薏仁",
        "agent_id": "codex",
        "memory_revision": 1313,
        "results": [
            {
                "memory_id": "LJ-EVIDENCE-1",
                "chunk_id": "LJ-CHUNK-1",
                "relative_path": "__structured__/evidence/LJ-EVIDENCE-1.md",
                "title": "工作日志",
                "heading": "复检结论",
                "text": "薏仁台词命中",
                "memory_type": "structured_evidence",
                "memory_tier": "evidence",
                "status": "active",
                "review_status": "evidence",
                "privacy": "private",
                "recall_weight": 1.0,
                "content_hash": "abc",
                "score": 0.57,
                "updated_at": "2026-09-19T21:00:00",
                "tags": ["a"],
                "relationships": {"decisions": []},
            }
        ],
    }
    slimmed = slim_search_results(payload)
    assert slimmed["query"] == "薏仁"
    assert "fetch_memory" in slimmed["detail_hint"]
    row = slimmed["results"][0]
    for key in ("memory_id", "title", "heading", "text", "memory_type", "memory_tier", "score", "updated_at"):
        assert key in row
    for key in ("chunk_id", "relative_path", "status", "review_status", "privacy", "recall_weight", "content_hash", "tags", "relationships"):
        assert key not in row
    # 原始 payload 不被就地修改
    assert "chunk_id" in payload["results"][0]


def test_slim_search_results_passes_through_unexpected_shapes():
    from src.mcp_server import slim_search_results

    assert slim_search_results(None) is None
    assert slim_search_results(["not", "a", "dict"]) == ["not", "a", "dict"]
    no_results = {"query": "x", "results": None}
    assert slim_search_results(no_results) is no_results
    mixed = {"results": [{"memory_id": "LJ-1"}, "opaque-string"]}
    slimmed = slim_search_results(mixed)
    assert slimmed["results"][1] == "opaque-string"
    assert slimmed["results"][0] == {"memory_id": "LJ-1"}


def test_slim_search_results_keeps_citation_contract_and_drops_verbose_fields():
    from src.mcp_server import slim_search_results

    payload = {
        "results": [
            {
                "memory_id": "LJ-EVIDENCE-1",
                "title": "结论",
                "text": "正文",
                "citation": {
                    "path": "__structured__/evidence/LJ-EVIDENCE-1.md",
                    "message_id": "LJ-MSG-1",
                    "content_hash": "hash1",
                    "raw_reference": "raw:zcode/cli/db/db.sqlite#sess/m",
                    "heading": "正文",
                    "start_line": 1,
                    "end_line": 1,
                    "sequence": 459,
                    "conversation_external_id": "codex-rollout:conversation:01abc",
                    "source_external_id": "codex-rollout:src-xyz",
                },
            }
        ]
    }
    slimmed = slim_search_results(payload)
    citation = slimmed["results"][0]["citation"]
    for key in ("path", "message_id", "content_hash", "raw_reference"):
        assert key in citation
    for key in ("heading", "start_line", "end_line", "sequence", "conversation_external_id", "source_external_id"):
        assert key not in citation


def test_slim_recent_changes_projects_memory_rows_and_truncates_events():
    from src.mcp_server import slim_recent_changes

    payload = {
        "agent_id": "zcode",
        "memory_revision": 9,
        "memories": [
            {
                "memory_id": "LJ-EVIDENCE-1",
                "relative_path": "__structured__/evidence/a.md",
                "title": "结论",
                "memory_type": "structured_evidence",
                "memory_tier": "evidence",
                "status": "active",
                "updated_at": "2026-09-29T12:21:17",
                "agent_scope": ["codex"],
                "tags": ["a", "b"],
                "privacy": "private",
                "recall_weight": 1.0,
                "relationships": {"author": "codex", "raw_reference": "/x"},
            }
        ],
        "events": [
            {
                "event_id": 1,
                "event_type": "memory_searched",
                "entity_type": "memory_gateway",
                "entity_id": "zcode",
                "created_at": "2026-09-29T12:35:47",
                "payload_json": "x" * 400,
            }
        ],
    }
    slimmed = slim_recent_changes(payload)
    row = slimmed["memories"][0]
    for key in ("memory_id", "relative_path", "title", "memory_type", "memory_tier", "updated_at", "agent_scope", "tags"):
        assert key in row
    for key in ("relationships", "privacy", "recall_weight", "content_hash"):
        assert key not in row
    event = slimmed["events"][0]
    assert event["payload_json"].endswith("…")
    assert len(event["payload_json"]) == 241
    assert event["event_type"] == "memory_searched"
    assert "detail_hint" in slimmed
    # 原始 payload 不被就地修改
    assert "relationships" in payload["memories"][0]


def test_slim_recent_changes_passes_through_unexpected_shapes():
    from src.mcp_server import slim_recent_changes

    assert slim_recent_changes(None) is None
    assert slim_recent_changes(["not", "a", "dict"]) == ["not", "a", "dict"]
    bare = {"agent_id": "zcode"}
    assert slim_recent_changes(bare)["detail_hint"]
