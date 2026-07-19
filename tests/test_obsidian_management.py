import tempfile
import unittest
from pathlib import Path

import yaml

from src.memory.vault_layout import VaultLayout
from src.obsidian.frontmatter import render_frontmatter, split_frontmatter
from src.obsidian.management import (
    DocumentManager,
    ManualCommandService,
    ObsidianInteractionManager,
)
from src.storage.state_db import StateDatabase


class ObsidianManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp_dir.name) / "vault"
        self.layout = VaultLayout(self.vault)
        self.layout.ensure()
        self.documents = DocumentManager(self.layout)
        self.state_db = StateDatabase(Path(self.temp_dir.name) / "state.db")
        self.commands = ManualCommandService(self.layout, self.documents, self.state_db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _note(self, relative, metadata=None, body="# Note\n"):
        path = self.vault / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        values = {
            "schema_version": 1,
            "id": "LJ-NOTE-1",
            "memory_type": "knowledge",
            "status": "active",
            "tags": [],
        }
        values.update(metadata or {})
        path.write_text(render_frontmatter(values, body), encoding="utf-8")
        return path

    def test_interaction_manager_creates_valid_bases_and_guides(self):
        result = ObsidianInteractionManager(self.layout).ensure()
        self.assertGreaterEqual(len(result["created"]), 10)
        bases = list((self.vault / "00-System" / "Bases").glob("*.base"))
        self.assertEqual(len(bases), 9)
        for base in bases:
            parsed = yaml.safe_load(base.read_text(encoding="utf-8"))
            self.assertIn("filters", parsed)
            self.assertIn("views", parsed)
        self.assertTrue((self.vault / "00-System" / "Home.md").exists())
        self.assertTrue((self.vault / "00-System" / "Tag-Dictionary.md").exists())

    def test_managed_generator_preserves_user_owned_files(self):
        path = self.vault / "00-System" / "Home.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# 我自己写的首页\n", encoding="utf-8")
        result = ObsidianInteractionManager(self.layout).ensure()
        self.assertIn("00-System/Home.md", result["skipped"])
        self.assertEqual(path.read_text(encoding="utf-8"), "# 我自己写的首页\n")

    def test_tag_normalization_and_limit(self):
        note = self._note("03-Knowledge/AI/tag-test.md")
        tags = self.documents.add_tags(note, ["#Domain/AI", "topic/Obsidian", "带 空格"])
        self.assertEqual(tags, ["domain/ai", "topic/obsidian", "带-空格"])
        with self.assertRaises(ValueError):
            self.documents.add_tags(note, [f"topic/{index}" for index in range(20)])

    def test_private_notes_require_explicit_authorization(self):
        private = self._note("08-Private/Personal/secret.md")
        with self.assertRaises(PermissionError):
            self.documents.add_tags(private, ["attention/review"])

    def test_protected_identity_cannot_be_changed(self):
        note = self._note("03-Knowledge/AI/protected.md")
        with self.assertRaises(PermissionError):
            self.documents.set_properties(note, {"id": "changed"})

    def test_link_command_creates_bidirectional_relationship(self):
        source = self._note("04-Projects/LingJi/project.md", {"memory_type": "project"})
        target = self._note("03-Knowledge/AI/knowledge.md", {"id": "LJ-NOTE-2"})
        command_path = self.vault / "00-System" / "Commands" / "Queue" / "link.md"
        command_path.parent.mkdir(parents=True, exist_ok=True)
        command = {
            "schema_version": 1,
            "id": "LJ-COMMAND-1",
            "memory_type": "command",
            "status": "queued",
            "command_type": "link_note",
            "target_path": self.layout.relative(source).as_posix(),
            "related_path": self.layout.relative(target).as_posix(),
            "relation_field": "related",
            "bidirectional": True,
        }
        command_path.write_text(render_frontmatter(command, "# Link command\n"), encoding="utf-8")

        result = self.commands.process_pending()
        self.assertEqual(result, {"processed": 1, "succeeded": 1, "failed": 0})

        source_meta, _ = split_frontmatter(source.read_text(encoding="utf-8"))
        target_meta, _ = split_frontmatter(target.read_text(encoding="utf-8"))
        self.assertIn("[[03-Knowledge/AI/knowledge]]", source_meta["related"])
        self.assertIn("[[04-Projects/LingJi/project]]", target_meta["related"])
        command_meta, _ = split_frontmatter(command_path.read_text(encoding="utf-8"))
        self.assertEqual(command_meta["status"], "done")

    def test_unknown_command_fails_without_modifying_target(self):
        target = self._note("03-Knowledge/AI/target.md")
        before = target.read_text(encoding="utf-8")
        command_path = self.vault / "00-System" / "Commands" / "Queue" / "bad.md"
        command_path.parent.mkdir(parents=True, exist_ok=True)
        command_path.write_text(
            render_frontmatter(
                {
                    "memory_type": "command",
                    "status": "queued",
                    "command_type": "delete_note",
                    "target_path": self.layout.relative(target).as_posix(),
                },
                "# Forbidden command\n",
            ),
            encoding="utf-8",
        )
        result = self.commands.process_pending()
        self.assertEqual(result["failed"], 1)
        self.assertEqual(target.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
