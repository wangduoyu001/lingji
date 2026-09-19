import asyncio

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mcp import types
from mcp.server.fastmcp import FastMCP

from src.mcp.control_bridge import create_control_bridge, register_control_bridge


def test_bridge_preserves_tool_output_agent_and_authentication():
    shared = FastMCP('shared')
    @shared.tool()
    def recall(query: str, agent_id: str = 'lingji-local') -> dict[str, str]:
        return {'query': query, 'agent_id': agent_id}
    @shared.resource('lingji://test')
    def resource() -> str:
        return 'existing resource'
    @shared.prompt()
    def context(task: str) -> str:
        return task
    app = FastAPI()
    constructed = []
    def get_server():
        constructed.append(True)
        return shared
    register_control_bridge(app, get_server, token='local-secret')
    request = {'request': {'method': 'tools/list'}}
    assert TestClient(app).post('/api/mcp/rpc', json=request).status_code == 401
    assert constructed == []

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://127.0.0.1') as http:
            bridge = create_control_bridge(http, token='local-secret', default_agent='codex')
            async def dispatch(payload):
                parsed = types.ClientRequest.model_validate(payload).root
                return (await bridge.request_handlers[type(parsed)](parsed)).root
            listed = await dispatch({'method':'tools/list'})
            assert [t.name for t in listed.tools] == ['recall']
            result = await dispatch({'method':'tools/call','params':{'name':'recall','arguments':{'query':'精准'}}})
            assert not result.isError
            assert result.structuredContent == {'query':'精准','agent_id':'codex'}
            invalid = await dispatch({'method':'tools/call','params':{'name':'recall','arguments':{}}})
            assert invalid.isError
            resources = await dispatch({'method':'resources/list'})
            assert len(resources.resources) == 1
            body = await dispatch({'method':'resources/read','params':{'uri':'lingji://test'}})
            assert body.contents[0].text == 'existing resource'
            prompts = await dispatch({'method':'prompts/list'})
            assert len(prompts.prompts) == 1
            prompt = await dispatch({'method':'prompts/get','params':{'name':'context','arguments':{'task':'hello'}}})
            assert prompt.messages[0].content.text == 'hello'
    asyncio.run(exercise())
