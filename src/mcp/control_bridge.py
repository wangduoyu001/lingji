"""Thin stdio bridge to the existing authenticated desktop backend.

No database, index or worker is opened by this client. Standalone development
MCP remains available through the launcher without --data-root.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable


def _request_types():
    from mcp import types
    return (types.ListToolsRequest, types.CallToolRequest,
            types.ListResourcesRequest, types.ReadResourceRequest,
            types.ListResourceTemplatesRequest, types.ListPromptsRequest,
            types.GetPromptRequest)


def register_control_bridge(app: Any, get_server: Callable, *, token: str) -> None:
    from fastapi import Depends, HTTPException
    from src.control.p2_07_api import _header_authorizer

    @app.post('/api/mcp/rpc', dependencies=[Depends(_header_authorizer(token))])
    def rpc(body: dict[str, Any]) -> dict:
        from mcp import types
        try:
            request = types.ClientRequest.model_validate(body.get('request')).root
        except ValueError as exc:
            raise HTTPException(422, 'Invalid MCP request') from exc
        if type(request) not in _request_types():
            raise HTTPException(422, 'Unsupported MCP request')
        server = get_server()

        async def dispatch():
            if isinstance(request, types.CallToolRequest):
                # Keep the connecting client's AI scope when it omits agent_id.
                tools = await server.list_tools()
                tool = next((t for t in tools if t.name == request.params.name), None)
                if tool and 'agent_id' in tool.inputSchema.get('properties', {}):
                    arguments = dict(request.params.arguments or {})
                    arguments.setdefault('agent_id', str(body.get('agent_id') or 'codex'))
                    request.params.arguments = arguments
            result = await server._mcp_server.request_handlers[type(request)](request)
            return result.model_dump(mode='json')
        # A synchronous route runs on FastAPI's worker pool, keeping UI status
        # requests responsive while existing synchronous MCP tools execute.
        return asyncio.run(dispatch())


def create_control_bridge(http: Any, *, token: str, default_agent: str):
    from mcp import types
    from mcp.server.lowlevel import Server
    bridge = Server('LingJi Memory Gateway')

    async def forward(request):
        response = await http.post(
            '/api/mcp/rpc', headers={'X-LingJi-Token': token},
            json={'request': request.model_dump(mode='json'), 'agent_id': default_agent},
        )
        response.raise_for_status()
        return types.ServerResult.model_validate(response.json())

    for request_type in _request_types():
        bridge.request_handlers[request_type] = forward
    return bridge


def run_control_bridge(data_root: str, *, default_agent: str = 'codex', port: int = 8766) -> None:
    import httpx
    from mcp.server.stdio import stdio_server

    token_path = Path(data_root).expanduser() / 'storage' / 'control_api_token'
    if not token_path.is_file():
        raise RuntimeError('请先打开灵机桌面应用，建立本地后端连接。')
    token = token_path.read_text(encoding='utf-8-sig').strip()
    if not token:
        raise RuntimeError('灵机本地后端令牌为空，请重新打开桌面应用。')

    async def serve():
        async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}',
                                     timeout=60, trust_env=False, follow_redirects=False) as http:
            bridge = create_control_bridge(http, token=token, default_agent=default_agent)
            async with stdio_server() as streams:
                await bridge.run(*streams, bridge.create_initialization_options())
    asyncio.run(serve())
