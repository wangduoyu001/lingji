import tempfile
import unittest
from pathlib import Path

from src.memory.capture import InboxService
from src.memory.vault_layout import REQUIRED_FOLDERS, VaultLayout


class VaultLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "vault"
        self.layout = VaultLayout(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ensure_creates_single_vault_tree(self):
        created = self.layout.ensure()
        self.assertTrue(created)
        self.assertTrue(all((self.root / relative).is_dir() for relative in REQUIRED_FOLDERS))
        self.assertTrue(self.layout.status()["complete"])

    def test_source_routes_to_matching_inbox(self):
        path = self.layout.inbox_path("chatgpt", "对话.md")
        self.assertIn("01-Inbox/ChatGPT", path.as_posix())
        classification = self.layout.classify(path)
        self.assertTrue(classification.is_inbox)
        self.assertEqual(classification.source_type, "chatgpt")

    def test_archive_source_type_ignores_date_folders(self):
        path = self.layout.archive_path("chatgpt", "对话.md")
        classification = self.layout.classify(path)
        self.assertEqual(classification.source_type, "chatgpt")

    def test_private_is_not_indexed_by_default(self):
        private_note = self.root / "08-Private" / "Personal" / "秘密.md"
        private_note.parent.mkdir(parents=True, exist_ok=True)
        private_note.write_text("secret", encoding="utf-8")
        self.assertFalse(self.layout.should_index(private_note))
        self.assertTrue(self.layout.should_index(private_note, include_private=True))

    def test_inbox_service_writes_traceable_note(self):
        self.layout.ensure()
        result = InboxService(self.layout).create_text_item(
            "codex",
            "工作报告",
            "完成单仓库结构",
            {"project_id": "LJ-PROJECT-000001", "tags": ["灵机", "开发"]},
        )
        path = Path(result["path"])
        text = path.read_text(encoding="utf-8")
        self.assertIn("status: \"received\"", text)
        self.assertIn("project_id: \"LJ-PROJECT-000001\"", text)
        self.assertIn("完成单仓库结构", text)
        self.assertIn("01-Inbox/Codex", result["relative_path"])


if __name__ == "__main__":
    unittest.main()
