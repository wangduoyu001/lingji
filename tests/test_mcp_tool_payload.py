"""线上载荷单份化回归：dict 返回注解的工具在 mcp 1.29.1 下会被 SDK 同时
序列化进 content 与 structuredContent（协议层双份）。工具函数改为返回显式
CallToolResult 后，走真实低层 handler 验证只有一份紧凑 JSON 文本。
"""
from __future__ import annotations

import asyncio
import json

from mcp import types
from mcp.server.fastmcp import FastMCP

from src.mcp.tool_payload import tool_result
from src.mcp_server import register_codex_mcp_tools


class FakeService:
    def resolve_project(self, workspace_path):
        return {"project_id": "P", "workspace": workspace_path, "备注": "值" * 10}


def _call_tool(mcp: FastMCP, name: str, arguments: dict) -> types.CallToolResult:
    request = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(name=name, arguments=arguments),
    )
    handler = mcp._mcp_server.request_handlers[types.CallToolRequest]
    server_result = asyncio.run(handler(request))
    return server_result.root


def test_tool_result_wraps_payload_into_single_compact_text():
    payload = {"project_id": "P", "记录": "值" * 10}
    result = tool_result(payload)
    assert result.isError is False
    assert result.structuredContent is None
    assert len(result.content) == 1
    text = result.content[0].text
    assert json.loads(text) == payload
    assert "\n" not in text  # 紧凑序列化，无 indent 空白膨胀


def test_registered_tool_carries_single_copy_over_lowlevel_handler():
    mcp = FastMCP("probe")
    register_codex_mcp_tools(mcp, FakeService())
    call = _call_tool(mcp, "lingji_resolve_project", {"workspace_path": "D:/code/lingji"})
    assert call.isError is False
    # 双份回归断言：structuredContent 必须缺席，content 只有 1 个文本块
    assert call.structuredContent is None
    assert len(call.content) == 1
    payload = json.loads(call.content[0].text)
    assert payload["project_id"] == "P"
    assert payload["workspace"] == "D:/code/lingji"
