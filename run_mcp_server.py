#!/usr/bin/env python3
import argparse

from src.config import settings
from src.mcp_server import run_mcp_server


def main():
    parser = argparse.ArgumentParser(description="Run the LingJi Memory Gateway MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=settings.mcp_transport,
    )
    parser.add_argument(
        "--agent",
        default=settings.mcp_default_agent_id,
        help="Default AI profile when a tool call omits agent_id",
    )
    args = parser.parse_args()
    run_mcp_server(args.transport, args.agent)


if __name__ == "__main__":
    main()
