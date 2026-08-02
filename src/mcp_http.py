from __future__ import annotations

import os
import socket
import threading
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable

ASGIApp = Callable[
    [dict[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]],
    Awaitable[Any],
]


class BearerTokenMiddleware:
    """Minimal ASGI bearer-token guard for the loopback MCP endpoint."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = str(token or "")

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[Any]],
    ) -> None:
        if scope.get("type") != "http" or not self.token:
            await self.app(scope, receive, send)
            return
        headers = {
            bytes(key).lower(): bytes(value)
            for key, value in scope.get("headers") or []
        }
        supplied = headers.get(b"authorization", b"").decode(
            "latin-1", errors="ignore"
        )
        expected = f"Bearer {self.token}"
        if hmac_compare(supplied, expected):
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


def hmac_compare(supplied: str, expected: str) -> bool:
    import hmac

    return hmac.compare_digest(supplied, expected)


def create_authenticated_mcp_app(
    *,
    token: str,
    agent_id: str = "lingji-local",
    gateway: Any | None = None,
) -> ASGIApp:
    """Create one shared owner-memory MCP application behind local authentication."""

    from src.mcp_server import create_mcp_server

    server = create_mcp_server(gateway=gateway, default_agent_id=agent_id)
    app = server.streamable_http_app()
    return BearerTokenMiddleware(app, token)


def _assert_port_available(host: str, port: int) -> None:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            probe.bind((host, int(port)))
        except OSError as exc:
            raise RuntimeError(
                f"LingJi MCP port {host}:{port} is already owned by another process"
            ) from exc


def _memory_runtime_root(settings: Any) -> Path:
    configured = str(os.environ.get("LINGJI_OWNER_DATA_ROOT") or "").strip()
    if configured:
        return Path(configured).expanduser().resolve(strict=False)
    storage = Path(settings.storage_path).expanduser().resolve(strict=False)
    return storage.parent if storage.name.casefold() == "storage" else storage


def _publish_statistics_until_stopped(
    gateway: Any,
    stop: threading.Event,
    *,
    interval_seconds: float = 5.0,
) -> None:
    while not stop.wait(max(float(interval_seconds), 1.0)):
        gateway.publish_statistics()


def run_authenticated_mcp_http(
    *,
    token: str,
    host: str = "127.0.0.1",
    port: int = 8767,
    agent_id: str = "lingji-local",
) -> None:
    normalized_host = str(host).strip().lower()
    if normalized_host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("LingJi MCP HTTP may only bind to loopback")
    if not token:
        raise ValueError("LingJi MCP HTTP token is required")

    _assert_port_available(host, int(port))

    import uvicorn

    from src.config import settings
    from src.gateway.bootstrap import build_memory_gateway
    from src.runtime import MemoryOwnerLock

    root = _memory_runtime_root(settings)
    instance_id = str(
        os.environ.get("LINGJI_RUNTIME_INSTANCE_ID")
        or uuid.uuid4()
    )
    workspace = str(
        os.environ.get("LINGJI_WORKSPACE")
        or getattr(settings, "workspace_name", "unknown")
        or "unknown"
    )
    owner_lock = MemoryOwnerLock(
        root / "runtime" / "memory-owner.lock",
        owner="packaged_mcp_http",
        instance_id=instance_id,
        workspace=workspace,
        timeout_seconds=15.0,
    ).acquire()
    gateway = None
    publisher_stop = threading.Event()
    publisher: threading.Thread | None = None
    try:
        os.environ["LINGJI_MEMORY_STATUS_PRODUCER"] = "mcp"
        os.environ["LINGJI_MEMORY_STATUS_INSTANCE_ID"] = instance_id
        gateway = build_memory_gateway(settings)
        gateway.publish_statistics()
        publisher = threading.Thread(
            target=_publish_statistics_until_stopped,
            args=(gateway, publisher_stop),
            name="lingji-memory-status-publisher",
            daemon=True,
        )
        publisher.start()
        app = create_authenticated_mcp_app(
            token=token,
            agent_id=agent_id,
            gateway=gateway,
        )
        uvicorn.run(
            app,
            host=host,
            port=int(port),
            log_level="warning",
            access_log=False,
        )
    finally:
        publisher_stop.set()
        if publisher is not None:
            publisher.join(timeout=2.0)
        if gateway is not None:
            gateway.publish_statistics()
            gateway.close()
        owner_lock.release()
