#!/usr/bin/env python3
"""LingJi Memory Gateway MCP server launcher.

--data-root 接打包运行时的同一套显式路径解析：环境注入必须在导入 src.config
之前完成（configure_packaged_environment 是纯 stdlib 实现）。"""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LingJi Memory Gateway MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=None,
    )
    parser.add_argument(
        "--agent",
        default=None,
        help="Default AI profile when a tool call omits agent_id",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="Absolute active-workspace data root (packaged runtime resolution)",
    )
    parser.add_argument("--workspace", default=None, choices=(None, "production", "acceptance"))
    args = parser.parse_args()

    if args.data_root:
        from run_packaged_control_api import configure_packaged_environment

        configure_packaged_environment(args.data_root, workspace=args.workspace)

    from src.config import settings
    from src.mcp_server import run_mcp_server
    from src.runtime import ensure_tcp_port_available, resolve_mcp_runtime_config

    transport = args.transport or settings.mcp_transport
    default_agent = args.agent or settings.mcp_default_agent_id
    runtime = resolve_mcp_runtime_config(settings, transport=transport)
    if runtime.transport == "streamable-http":
        ensure_tcp_port_available(runtime.host, runtime.port, service_name="LingJi MCP HTTP")
    run_mcp_server(runtime.transport, default_agent)


if __name__ == "__main__":
    main()
