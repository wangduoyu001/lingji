from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.indexer.index import PEMISIndex
from src.memory import VaultLayout
from src.retrieval import MarkdownChunker, MemoryDatabase
from src.retrieval.incremental_sync import IncrementalMemorySynchronizer
from src.obsidian.memory_scope import ObsidianMemoryScope


class IncrementalIndexSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.vault = root / "vault"
        self.storage = root / "storage"
        self.layout = VaultLayout(self.vault)
        self.layout.ensure()
        self.first = self.vault / "03-Knowledge" / "first.md"
        self.second = self.vault / "04-Projects" / "second.md"
        self.first.write_text("---\nid: MEM-FIRST\nmemory_type: knowledge\n---\n# 第一条\n\n正文一。\n", encoding="utf-8")
        self.second.write_text("---\nid: MEM-SECOND\nmemory_type: project\n---\n# 第二条\n\n正文二。\n", encoding="utf-8")
        self.indexer = PEMISIndex(self.vault, self.storage)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_unchanged_files_are_not_reparsed(self):
        first_index = self.indexer.build_index()
        self.assertEqual(first_index["meta"]["total"], 2)
        self.assertTrue(self.indexer.last_sync_result["full_rebuild"])
        with patch.object(self.indexer, "_parse_md_file", wraps=self.indexer._parse_md_file) as parser:
            second_index = self.indexer.build_index()
        self.assertEqual(parser.call_count, 0)
        self.assertEqual(second_index["meta"]["sync"]["unchanged"], 2)

    def test_changed_and_removed_files_are_synchronized(self):
        self.indexer.build_index()
        self.first.write_text("---\nid: MEM-FIRST\nmemory_type: knowledge\n---\n# 第一条\n\n正文已更新。\n", encoding="utf-8")
        with patch.object(self.indexer, "_parse_md_file", wraps=self.indexer._parse_md_file) as parser:
            updated = self.indexer.build_index()
        self.assertEqual(parser.call_count, 1)
        self.assertEqual(updated["meta"]["sync"]["updated"], 1)
        self.second.unlink()
        removed = self.indexer.build_index()
        self.assertEqual(removed["meta"]["sync"]["removed"], 1)
        self.assertEqual(removed["meta"]["total"], 1)

    def test_memory_database_only_updates_changed_documents(self):
        index = self.indexer.build_index()
        database = MemoryDatabase(self.storage / "memory.db")
        syncer = IncrementalMemorySynchronizer(database)
        first = syncer.sync(index["entries"].values(), self.vault, MarkdownChunker())
        self.assertEqual(first["added"], 2)
        first_revision = database.revision
        second = syncer.sync(index["entries"].values(), self.vault, MarkdownChunker())
        self.assertEqual(second["unchanged"], 2)
        self.assertEqual(database.revision, first_revision)

        self.first.write_text("---\nid: MEM-FIRST\nmemory_type: knowledge\n---\n# 第一条\n\n更新后的检索正文。\n", encoding="utf-8")
        updated_index = self.indexer.build_index()
        updated = syncer.sync(updated_index["entries"].values(), self.vault, MarkdownChunker())
        self.assertEqual(updated["updated"], 1)
        self.second.unlink()
        removed_index = self.indexer.build_index()
        removed = syncer.sync(removed_index["entries"].values(), self.vault, MarkdownChunker())
        self.assertEqual(removed["removed"], 1)
        self.assertIsNone(database.fetch_by_path("04-Projects/second.md"))

    def test_scoped_sync_removes_memory_moved_out_of_authorized_directory(self):
        authorized = self.vault / "_LingJi" / "Memory Inbox" / "moved.md"
        authorized.parent.mkdir(parents=True, exist_ok=True)
        authorized.write_text(
            "---\nid: MEM-MOVED\nlingji_memory: true\n---\n# moved\n\nbody", encoding="utf-8"
        )
        database = MemoryDatabase(self.storage / "scoped.db")
        scope = ObsidianMemoryScope(self.vault)
        index = PEMISIndex(self.vault, self.storage)
        syncer = IncrementalMemorySynchronizer(database)
        syncer.sync(index.memory_entries(), self.vault, memory_scope=scope)
        assert database.fetch_by_path("_LingJi/Memory Inbox/moved.md") is not None

        authorized.rename(self.vault / "03-Knowledge" / "moved.md")
        (self.vault / "03-Knowledge" / "moved.md").write_text(
            "# moved out\n\nordinary note", encoding="utf-8"
        )
        external = self.storage / "chat.md"
        external.write_text("# chat\n\nchat evidence", encoding="utf-8")
        syncer.sync(index.memory_entries(), self.vault, memory_scope=scope)
        assert database.fetch_by_path("_LingJi/Memory Inbox/moved.md") is None
        database.upsert_from_entry(
            {"id": "CHAT-1", "relative_path": "source://chat/1", "title": "chat", "memory_type": "chat"},
            external,
        )
        syncer.sync(index.memory_entries(), self.vault, memory_scope=scope)
        assert database.fetch_by_path("source://chat/1") is not None


if __name__ == "__main__":
    unittest.main()
