import asyncio

from src.mcp.project_context_tools import register_project_context_tools


class MCP:
    def __init__(self): self.fn = None
    def tool(self, name):
        def wrap(fn): self.fn = fn; return fn
        return wrap
class Service:
    def build(self, **kwargs): return kwargs


def test_codex_tool_forces_scope():
    mcp = MCP(); register_project_context_tools(mcp, Service(), lambda: "lingji-local")
    result = asyncio.run(mcp.fn("P", "task"))
    assert result["agent_id"] == "codex"
    assert result["allow_cross_project"] is False
