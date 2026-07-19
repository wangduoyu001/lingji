import tempfile
import unittest
from pathlib import Path

from src.indexer.index import PEMISIndex
from src.memory import InboxService, VaultLayout
from src.obsidian.frontmatter import render_frontmatter


class SingleVaultIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.vault = base / "vault"
        self.storage = base / "storage"
        self.layout = VaultLayout(self.vault)
        self.layout.ensure()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_index_records_folder_and_source_metadata(self):
        item = InboxService(self.layout).create_text_item(
            "chatgpt",
            "灵机架构",
            "这是一条足够长的原始内容，用于验证索引摘要和来源路径能够被正确保存。",
            {"project_id": "LJ-PROJECT-000001"},
        )
        indexer = PEMISIndex(self.vault, self.storage)
        indexer.build_index()
        entry = indexer.find_by_path(item["path"])
        self.assertIsNotNone(entry)
        self.assertEqual(entry["source_type"], "chatgpt")
        self.assertEqual(entry["project_id"], "LJ-PROJECT-000001")
        self.assertEqual(entry["project"], ["LJ-PROJECT-000001"])
        self.assertTrue(entry["is_inbox"])
        self.assertEqual(entry["top_level"], "01-Inbox")

    def test_index_keeps_typed_obsidian_relations(self):
        note = self.vault / "03-Knowledge" / "AI" / "relations.md"
        note.write_text(
            render_frontmatter(
                {
                    "schema_version": 1,
                    "id": "LJ-NOTE-REL",
                    "memory_type": "knowledge",
                    "project": ["[[04-Projects/LingJi/LingJi]]"],
                    "people": ["[[06-Entities/People/主人]]"],
                    "tools": ["[[06-Entities/Tools/Obsidian]]"],
                    "sources": ["[[02-Sources/Documents/source]]"],
                    "related": ["[[03-Knowledge/AI/other]]"],
                    "tags": ["domain/ai", "topic/obsidian"],
                },
                "# 关系测试\n\n这是一条用于验证类型化关系索引的知识笔记。\n",
            ),
            encoding="utf-8",
        )
        indexer = PEMISIndex(self.vault, self.storage)
        indexer.build_index()
        entry = indexer.get_entry("LJ-NOTE-REL")
        self.assertEqual(entry["project"], ["[[04-Projects/LingJi/LingJi]]"])
        self.assertEqual(entry["people"], ["[[06-Entities/People/主人]]"])
        self.assertEqual(entry["tools"], ["[[06-Entities/Tools/Obsidian]]"])
        self.assertEqual(entry["sources"], ["[[02-Sources/Documents/source]]"])
        self.assertEqual(entry["tags"], ["domain/ai", "topic/obsidian"])

    def test_private_folder_is_excluded_from_default_index(self):
        note = self.vault / "08-Private" / "Personal" / "private.md"
        note.write_text("# 私密\n\n不应进入默认索引。", encoding="utf-8")
        indexer = PEMISIndex(self.vault, self.storage, include_private=False)
        indexer.build_index()
        self.assertIsNone(indexer.find_by_path(note))

    def test_incremental_remove_uses_relative_path_not_only_filename(self):
        item = InboxService(self.layout).create_text_item("codex", "报告", "一份开发工作报告内容。")
        indexer = PEMISIndex(self.vault, self.storage)
        indexer.build_index()
        self.assertTrue(indexer.incremental_remove(item["path"]))
        self.assertIsNone(indexer.find_by_path(item["path"]))


if __name__ == "__main__":
    unittest.main()
