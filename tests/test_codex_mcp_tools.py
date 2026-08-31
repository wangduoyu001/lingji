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
