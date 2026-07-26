from __future__ import annotations

import socket
from dataclasses import asdict, dataclass
from typing import Any, Mapping

_ALLOWED_MCP_TRANSPORTS = {"stdio", "streamable-http"}
_WILDCARD_HOSTS = {"", "0.0.0.0", "::"}


@dataclass(frozen=True)
class McpRuntimeConfig:
    """Resolved MCP and local runtime port contract."""

    transport: str
    host: str
    port: int
    control_host: str
    control_port: int
    compatibility_host: str
    compatibility_port: int

    @property
    def endpoint(self) -> str | None:
        if self.transport != "streamable-http":
            return None
        return f"http://{self.host}:{self.port}"

    def status(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "endpoint": self.endpoint,
            "configured": True,
            "running": None,
            "restart_required": True,
            "contract_valid": True,
            "desktop_gateway": f"http://{self.control_host}:{self.control_port}",
            "compatibility_api": f"http://{self.compatibility_host}:{self.compatibility_port}",
        }


def normalize_mcp_transport(value: Any) -> str:
    transport = str(value or "stdio").strip().lower()
    if transport not in _ALLOWED_MCP_TRANSPORTS:
        raise ValueError("MCP transport must be stdio or streamable-http")
    return transport


def resolve_mcp_runtime_config(
    settings: Any,
    runtime_values: Mapping[str, Any] | None = None,
    *,
    transport: str | None = None,
    host: str | None = None,
    port: int | None = None,
) -> McpRuntimeConfig:
    values = dict(runtime_values or {})
    config = McpRuntimeConfig(
        transport=normalize_mcp_transport(
            transport if transport is not None else values.get("mcp_transport", settings.mcp_transport)
        ),
        host=str(host if host is not None else values.get("mcp_host", settings.mcp_host)).strip(),
        port=int(port if port is not None else values.get("mcp_port", settings.mcp_port)),
        control_host=str(settings.control_api_host).strip(),
        control_port=int(settings.control_api_port),
        compatibility_host=str(getattr(settings, "compatibility_api_host", "127.0.0.1")).strip(),
        compatibility_port=int(getattr(settings, "compatibility_api_port", 8765)),
    )
    validate_runtime_port_contract(config)
    return config


def validate_runtime_port_contract(config: McpRuntimeConfig) -> None:
    for name, host, port in (
        ("MCP", config.host, config.port),
        ("Local Control API", config.control_host, config.control_port),
        ("Compatibility API", config.compatibility_host, config.compatibility_port),
    ):
        if not host:
            raise ValueError(f"{name} host must not be empty")
        if not 1024 <= int(port) <= 65535:
            raise ValueError(f"{name} port must be between 1024 and 65535")

    endpoints = (
        ("MCP", config.host, config.port),
        ("Local Control API", config.control_host, config.control_port),
        ("Compatibility API", config.compatibility_host, config.compatibility_port),
    )
    for index, (left_name, left_host, left_port) in enumerate(endpoints):
        for right_name, right_host, right_port in endpoints[index + 1 :]:
            if left_port == right_port and _hosts_overlap(left_host, right_host):
                raise ValueError(
                    f"Runtime port conflict: {left_name} and {right_name} both use "
                    f"{left_host}:{left_port}"
                )


def ensure_tcp_port_available(host: str, port: int, *, service_name: str = "MCP HTTP") -> None:
    """Fail before startup when the configured TCP bind address is unavailable."""

    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise RuntimeError(f"{service_name} host cannot be resolved: {host}:{port} ({exc})") from exc

    last_error: OSError | None = None
    for family, socktype, protocol, _, sockaddr in addresses:
        probe = socket.socket(family, socktype, protocol)
        try:
            probe.bind(sockaddr)
        except OSError as exc:
            last_error = exc
        else:
            return
        finally:
            probe.close()

    detail = f" ({last_error})" if last_error else ""
    raise RuntimeError(f"{service_name} port is unavailable: {host}:{port}{detail}")


def mcp_runtime_status(settings: Any, runtime_values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return configuration truth without pretending to know whether MCP is running."""

    try:
        return resolve_mcp_runtime_config(settings, runtime_values).status()
    except (TypeError, ValueError) as exc:
        return {
            "configured": False,
            "running": None,
            "contract_valid": False,
            "error": str(exc),
        }


def _hosts_overlap(left: str, right: str) -> bool:
    left_value = str(left or "").strip().lower()
    right_value = str(right or "").strip().lower()
    if left_value == right_value:
        return True
    return left_value in _WILDCARD_HOSTS or right_value in _WILDCARD_HOSTS
