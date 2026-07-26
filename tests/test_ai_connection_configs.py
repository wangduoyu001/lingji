import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_ai_connection_configs import generate_configs


class AIConnectionConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.project = self.base / "lingji"
        self.project.mkdir()
        (self.project / "run_mcp_server.py").write_text("# entry\n", encoding="utf-8")
        self.output = self.base / "connections"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generates_configs_without_modifying_external_settings(self):
        files = generate_configs(self.output, self.project, "python")
        self.assertEqual(len(files), 9)
        self.assertTrue((self.output / "codex-config.toml").exists())
        self.assertFalse((self.project / ".codex" / "config.toml").exists())

    def test_codex_claude_and_gemini_use_distinct_agent_profiles(self):
        codex = (self.output / "codex-config.toml")
        if not codex.exists():
            generate_configs(self.output, self.project, "python")
        codex_text = codex.read_text(encoding="utf-8")
        claude_text = (self.output / "claude-command.txt").read_text(encoding="utf-8")
        gemini = json.loads((self.output / "gemini-settings.json").read_text(encoding="utf-8"))
        self.assertIn('"--agent", "codex"', codex_text)
        self.assertIn("--agent claude", claude_text)
        self.assertIn("gemini", gemini["mcpServers"]["lingji-memory"]["args"])
        self.assertFalse(gemini["mcpServers"]["lingji-memory"]["trust"])

    def test_openai_remote_template_does_not_expose_localhost(self):
        generate_configs(self.output, self.project, "python")
        payload = json.loads((self.output / "openai-remote-mcp-tool.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["server_url"].startswith("https://"))
        self.assertNotIn("127.0.0.1", payload["server_url"])
        self.assertTrue(payload["allowed_tools"]["read_only"])
        self.assertNotIn("propose_memory", payload["allowed_tools"]["tool_names"])

    def test_direct_client_modes_preserve_privacy_boundary(self):
        generate_configs(self.output, self.project, "python")
        payload = json.loads((self.output / "direct-clients.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["ollama"]["can_read_restricted"])
        self.assertNotIn("can_read_restricted", payload["deepseek"])
        self.assertEqual(payload["deepseek"]["adapter"], "AIContextAdapter.generic_prompt")


if __name__ == "__main__":
    unittest.main()
