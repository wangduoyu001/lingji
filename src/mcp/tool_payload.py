"""Single-copy MCP tool payload emission.

mcp 1.29.1 会把带 dict 返回注解的工具载荷同时序列化进 content（indent=2 文本）
与 structuredContent，协议层双份、AI 侧 token 翻倍。工具函数必须改为返回显式
CallToolResult 并移除 dict 返回注解（否则 outputSchema 校验拒绝该结构），
使线上载荷只有一份紧凑 JSON（2026-09-29 同版本端到端探针实测）。
"""
from __future__ import annotations

import json
from typing import Any


def tool_result(payload: Any):
    """Wrap a tool payload into one compact TextContent CallToolResult."""
    from mcp.types import CallToolResult, TextContent

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, default=str))],
        isError=False,
    )
