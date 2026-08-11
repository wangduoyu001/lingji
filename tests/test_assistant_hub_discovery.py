from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from src.assistant_hub import AiAssistantDiscoveryService


class AiAssistantDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.local_app_data = self.root / "local"
        self.home.mkdir(parents=True)
        self.local_app_data.mkdir(parents=True)

    def test_scan_reports_truthful_support_without_reading_content(self) -> None:
        codex = self.home / ".codex" / "sessions"
        codex.mkdir(parents=True)
        (codex / "session.jsonl").write_text("SECRET_CODEX_CONTENT", encoding="utf-8")

        claude_projects = self.home / ".claude" / "projects" / "project-a"
        claude_projects.mkdir(parents=True)
        (self.home / ".claude" / "CLAUDE.md").write_text("SECRET_CLAUDE_MEMORY", encoding="utf-8")
        (claude_projects / "session.jsonl").write_text("SECRET_CLAUDE_CONTENT", encoding="utf-8")

        workbuddy = self.local_app_data / "Programs" / "WorkBuddy"
        workbuddy.mkdir(parents=True)

        payload = AiAssistantDiscoveryService(
            home=self.home,
            env={"LOCALAPPDATA": str(self.local_app_data)},
            platform_name="windows",
            workspace="acceptance",
        ).scan()

        self.assertEqual(payload["workspace"], "acceptance")
        self.assertTrue(payload["safety"]["read_only"])
        self.assertFalse(payload["safety"]["content_read"])
        self.assertFalse(payload["safety"]["automatic_core_memory_write"])
        self.assertTrue(payload["safety"]["review_required_for_permanent_memory"])

        assistants = {item["id"]: item for item in payload["assistants"]}
        self.assertEqual(set(assistants), {"chatgpt", "codex", "claude_code", "workbuddy"})
        self.assertEqual(assistants["codex"]["detection_state"], "detected")
        self.assertEqual(assistants["codex"]["candidate_count"], 1)
        self.assertIn("~/.codex", assistants["codex"]["discovered_paths"])
        self.assertEqual(assistants["claude_code"]["detection_state"], "detected")
        self.assertTrue(assistants["claude_code"]["capabilities"]["user_memory_detected"])
        self.assertEqual(assistants["workbuddy"]["detection_state"], "detected")

        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("SECRET_CODEX_CONTENT", encoded)
        self.assertNotIn("SECRET_CLAUDE_MEMORY", encoded)
        self.assertNotIn("SECRET_CLAUDE_CONTENT", encoded)

    def test_scan_handles_missing_tools_without_claiming_connection(self) -> None:
        payload = AiAssistantDiscoveryService(
            home=self.home,
            env={"LOCALAPPDATA": str(self.local_app_data)},
            platform_name="windows",
            workspace="production",
        ).scan()
        assistants = {item["id"]: item for item in payload["assistants"]}
        for assistant_id in ("codex", "claude_code", "workbuddy"):
            self.assertEqual(assistants[assistant_id]["detection_state"], "not_found")
            self.assertNotEqual(assistants[assistant_id]["connection_state"], "connected")

    def test_codex_home_override_is_supported_and_redacted(self) -> None:
        custom = self.root / "custom-codex"
        custom.mkdir()
        (custom / "report.json").write_text("{}", encoding="utf-8")

        payload = AiAssistantDiscoveryService(
            home=self.home,
            env={"CODEX_HOME": str(custom), "LOCALAPPDATA": str(self.local_app_data)},
            platform_name="windows",
        ).scan()
        codex = next(item for item in payload["assistants"] if item["id"] == "codex")
        self.assertEqual(codex["candidate_count"], 1)
        self.assertEqual(codex["discovered_paths"], ["<local>/custom-codex"])
        self.assertNotIn(str(self.root), json.dumps(codex))

    def test_explicit_empty_environment_does_not_inherit_host_codex_home(self) -> None:
        host_codex_home = self.root / "host-codex"
        host_codex_home.mkdir()
        (host_codex_home / "report.json").write_text("{}", encoding="utf-8")

        previous = os.environ.get("CODEX_HOME")
        os.environ["CODEX_HOME"] = str(host_codex_home)
        try:
            payload = AiAssistantDiscoveryService(home=self.home, env={}, platform_name="windows").scan()
        finally:
            if previous is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = previous

        codex = next(item for item in payload["assistants"] if item["id"] == "codex")
        self.assertEqual(codex["detection_state"], "not_found")


if __name__ == "__main__":
    unittest.main()
