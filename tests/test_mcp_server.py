from __future__ import annotations

import os
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import Settings
from src.runtime import (
    McpRuntimeConfig,
    ensure_tcp_port_available,
    mcp_runtime_status,
    resolve_mcp_runtime_config,
    validate_runtime_port_contract,
)


class McpPortContractTests(unittest.TestCase):
    def settings(self, **overrides):
        return Settings(_env_file=None, **overrides)

    def test_default_port_contract_is_distinct(self):
        settings = self.settings()
        runtime = resolve_mcp_runtime_config(settings)
        self.assertEqual(runtime.transport, "stdio")
        self.assertEqual(runtime.compatibility_port, 8765)
        self.assertEqual(runtime.control_port, 8766)
        self.assertEqual(runtime.port, 8767)
        self.assertIsNone(runtime.endpoint)

    def test_http_endpoint_uses_dedicated_port(self):
        runtime = resolve_mcp_runtime_config(self.settings(), transport="streamable-http")
        self.assertEqual(runtime.endpoint, "http://127.0.0.1:8767")

    def test_environment_can_override_mcp_port(self):
        with patch.dict(os.environ, {"MCP_PORT": "9876"}, clear=False):
            settings = Settings(_env_file=None)
        self.assertEqual(settings.mcp_port, 9876)

    def test_runtime_override_can_change_mcp_transport_and_port(self):
        runtime = resolve_mcp_runtime_config(
            self.settings(),
            {"mcp_transport": "streamable-http", "mcp_port": 9988},
        )
        self.assertEqual(runtime.transport, "streamable-http")
        self.assertEqual(runtime.port, 9988)

    def test_conflicting_ports_are_rejected(self):
        config = McpRuntimeConfig(
            transport="streamable-http",
            host="127.0.0.1",
            port=8766,
            control_host="127.0.0.1",
            control_port=8766,
            compatibility_host="127.0.0.1",
            compatibility_port=8765,
        )
        with self.assertRaisesRegex(ValueError, "Runtime port conflict"):
            validate_runtime_port_contract(config)

    def test_occupied_port_returns_clear_error(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        with self.assertRaisesRegex(RuntimeError, f"127.0.0.1:{port}"):
            ensure_tcp_port_available("127.0.0.1", port, service_name="LingJi MCP HTTP")

    def test_status_does_not_claim_process_is_running(self):
        status = mcp_runtime_status(self.settings())
        self.assertTrue(status["configured"])
        self.assertTrue(status["contract_valid"])
        self.assertIsNone(status["running"])
        self.assertEqual(status["desktop_gateway"], "http://127.0.0.1:8766")
        self.assertEqual(status["compatibility_api"], "http://127.0.0.1:8765")

    def test_tauri_defaults_only_to_control_api(self):
        root = Path(__file__).resolve().parents[1]
        api_source = (root / "desktop" / "lingji-control" / "src" / "api.ts").read_text(encoding="utf-8")
        tauri_source = (
            root / "desktop" / "lingji-control" / "src-tauri" / "src" / "main.rs"
        ).read_text(encoding="utf-8")
        for source in (api_source, tauri_source):
            self.assertIn("127.0.0.1:8766", source)
            self.assertNotIn("127.0.0.1:8765", source)
            self.assertNotIn("127.0.0.1:8767", source)


if __name__ == "__main__":
    unittest.main()
