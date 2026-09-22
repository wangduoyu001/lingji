from __future__ import annotations

import inspect


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
    assert mcp.tools["lingji_resolve_project"]("D:/code/lingji")["project_id"] == "P"
    assert mcp.tools["lingji_start_session"]("D:/code/lingji", "C1")["session_id"] == "S"
    checkpoint = mcp.tools["lingji_checkpoint"](
        "S", "E1", "checkpoint", "summary", changed_files=["src/x.py"]
    )
    assert checkpoint["event_id"] == "E1"
    closed = mcp.tools["lingji_close_session"]("S", "E2", "done")
    assert closed["status"] == "completed"
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
