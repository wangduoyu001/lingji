from __future__ import annotations

import hmac
from typing import Any, Awaitable, Callable

ASGIApp = Callable[[dict[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]], Awaitable[Any]]


class BearerTokenMiddleware:
    """Minimal ASGI bearer-token guard for the loopback MCP endpoint."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = str(token or "")

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Awaitable[Any]], send: Callable[..., Awaitable[Any]]) -> None:
        if scope.get("type") != "http" or not self.token:
            await self.app(scope, receive, send)
            return
        headers = {
            bytes(key).lower(): bytes(value)
            for key, value in scope.get("headers") or []
        }
        supplied = headers.get(b"authorization", b"").decode("latin-1", errors="ignore")
        expected = f"Bearer {self.token}"
        if hmac.compare_digest(supplied, expected):
            await self.app(scope, receive, send)
            return
        body = b'{"error":"unauthorized"}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def create_authenticated_mcp_app(*, token: str, agent_id: str = "lingji-local") -> ASGIApp:
    """Create one shared owner-memory MCP application behind local authentication."""

    from src.mcp_server import create_mcp_server

    server = create_mcp_server(default_agent_id=agent_id)
    app = server.streamable_http_app()
    return BearerTokenMiddleware(app, token)


def run_authenticated_mcp_http(
    *,
    token: str,
    host: str = "127.0.0.1",
    port: int = 8767,
    agent_id: str = "lingji-local",
) -> None:
    if str(host).strip().lower() not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("LingJi MCP HTTP may only bind to loopback")
    if not token:
        raise ValueError("LingJi MCP HTTP token is required")

    import uvicorn

    app = create_authenticated_mcp_app(token=token, agent_id=agent_id)
    uvicorn.run(
        app,
        host=host,
        port=int(port),
        log_level="warning",
        access_log=False,
    )
