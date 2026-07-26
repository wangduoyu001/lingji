from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.memory import VaultLayout
from src.skills import SkillRegistry


class SkillRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.vault = root / "vault"
        self.skills_root = root / "skills"
        self.layout = VaultLayout(self.vault)
        self.layout.ensure()
        self.registry = SkillRegistry(self.layout)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_register_writes_manifest_not_code_copy(self):
        source = self.skills_root / "demo" / "SKILL.md"
        source.parent.mkdir(parents=True)
        source.write_text("# Demo Skill\n\n用于测试。", encoding="utf-8")
        result = self.registry.register(
            {
                "skill_id": "demo-skill",
                "name": "Demo Skill",
                "version": "1.0.0",
                "source_path": str(source),
                "capabilities": ["search"],
                "compatible_agents": ["codex"],
            }
        )
        path = Path(result["path"])
        self.assertTrue(path.exists())
        self.assertIn("07-Assets/Skills", path.as_posix())
        text = path.read_text(encoding="utf-8")
        self.assertIn(str(source), text)
        self.assertIn("源代码和可执行实现保留在 Git", text)
        self.assertFalse((path.parent / "SKILL.md").exists())

    def test_sync_directory_reads_skill_frontmatter(self):
        source = self.skills_root / "capture-web" / "SKILL.md"
        source.parent.mkdir(parents=True)
        source.write_text(
            "---\nname: 网页采集\nversion: 2.0.0\ncapabilities:\n  - web_capture\n---\n\n# 网页采集\n\n采集网页。\n",
            encoding="utf-8",
        )
        result = self.registry.sync_directory(self.skills_root)
        self.assertEqual(result["succeeded"], 1)
        skills = self.registry.list()
        self.assertEqual(skills[0]["version"], "2.0.0")
        self.assertIn("web_capture", skills[0]["capabilities"])

    def test_owner_status_survives_resync(self):
        result = self.registry.register({"skill_id": "demo", "name": "Demo"})
        path = Path(result["path"])
        text = path.read_text(encoding="utf-8")
        text = text.replace("status: active", "status: disabled")
        text = text.replace("owner_confirmed: false", "owner_confirmed: true")
        path.write_text(text, encoding="utf-8")
        self.registry.register({"skill_id": "demo", "name": "Demo", "version": "2"})
        updated = path.read_text(encoding="utf-8")
        self.assertIn("status: disabled", updated)
        self.assertIn("owner_confirmed: true", updated)


if __name__ == "__main__":
    unittest.main()
