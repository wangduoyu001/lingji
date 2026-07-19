import tempfile
import unittest
from pathlib import Path

from src.indexer.index import PEMISIndex
from src.memory import VaultLayout
from src.obsidian.frontmatter import render_frontmatter
from src.retrieval import HybridRetriever, MarkdownChunker, MemoryDatabase
from src.retrieval.hybrid import SearchFilters


class MemoryRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.vault = base / "vault"
        self.storage = base / "storage"
        self.layout = VaultLayout(self.vault)
        self.layout.ensure()
        self.database = MemoryDatabase(self.storage / "lingji_memory.db")
        self.chunker = MarkdownChunker(max_chars=240, overlap_chars=40)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _note(self, relative, memory_id, title, body, **metadata):
        path = self.vault / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        values = {
            "schema_version": 1,
            "id": memory_id,
            "title": title,
            "memory_type": "knowledge",
            "memory_tier": "archival",
            "status": "active",
            "privacy": "private",
            "importance": "medium",
            "review_status": "approved",
            "project": [],
            "tags": [],
        }
        values.update(metadata)
        path.write_text(render_frontmatter(values, body), encoding="utf-8")
        return path

    def _rebuild(self):
        indexer = PEMISIndex(self.vault, self.storage)
        indexer.build_index()
        return self.database.rebuild_from_index(indexer.get_all(), self.vault, self.chunker)

    def test_chinese_and_english_full_text_search_with_line_citation(self):
        self._note(
            "03-Knowledge/AI/retrieval.md",
            "LJ-MEM-RETRIEVAL",
            "永久记忆召回",
            "# 召回设计\n\n永久记忆必须使用全文检索和时间过滤。\n\n## 实现\n\nSQLite FTS5 提供快速 BM25 检索。\n",
            tags=["topic/memory", "topic/sqlite"],
        )
        result = self._rebuild()
        self.assertEqual(result["documents"], 1)
        self.assertGreaterEqual(result["chunks"], 2)

        chinese = self.database.search_fts("永久记忆", limit=5)
        english = self.database.search_fts("SQLite FTS5", limit=5)
        self.assertTrue(chinese)
        self.assertTrue(english)
        self.assertEqual(chinese[0]["memory_id"], "LJ-MEM-RETRIEVAL")
        self.assertGreaterEqual(chinese[0]["start_line"], 1)
        self.assertGreaterEqual(chinese[0]["end_line"], chinese[0]["start_line"])
        self.assertIn("[", chinese[0]["snippet"])

    def test_project_tag_privacy_and_temporal_filters(self):
        self._note(
            "03-Knowledge/AI/active.md",
            "LJ-MEM-ACTIVE",
            "灵机当前架构",
            "# 当前架构\n\n灵机采用单一 Obsidian 仓库和混合召回。\n",
            project=["[[04-Projects/LingJi/LingJi]]"],
            tags=["topic/lingji"],
            valid_from="2026-01-01T00:00:00+00:00",
            valid_to="2027-01-01T00:00:00+00:00",
        )
        self._note(
            "03-Knowledge/AI/expired.md",
            "LJ-MEM-EXPIRED",
            "灵机旧架构",
            "# 旧架构\n\n灵机旧架构使用多个仓库。\n",
            project=["[[04-Projects/LingJi/LingJi]]"],
            tags=["topic/lingji"],
            valid_to="2025-01-01T00:00:00+00:00",
        )
        self._note(
            "03-Knowledge/AI/restricted.md",
            "LJ-MEM-RESTRICTED",
            "受限记忆",
            "# 受限\n\n灵机受限记忆不可交给远程模型。\n",
            privacy="restricted",
            tags=["topic/lingji"],
        )
        self._rebuild()
        retriever = HybridRetriever(self.database, cache_size=8, cache_ttl_seconds=60)
        results = retriever.search(
            "灵机架构",
            limit=10,
            filters=SearchFilters(
                project="LingJi",
                tags=("topic/lingji",),
                privacy=("public", "private"),
                as_of="2026-07-19T00:00:00+00:00",
            ),
        )
        ids = {item["memory_id"] for item in results}
        self.assertIn("LJ-MEM-ACTIVE", ids)
        self.assertNotIn("LJ-MEM-EXPIRED", ids)
        self.assertNotIn("LJ-MEM-RESTRICTED", ids)

    def test_incremental_update_and_remove_change_revision(self):
        note = self._note(
            "03-Knowledge/AI/incremental.md",
            "LJ-MEM-INCREMENTAL",
            "增量索引",
            "# 初始\n\n第一版内容只包含旧关键词。\n",
        )
        self._rebuild()
        initial_revision = self.database.revision
        self.assertTrue(self.database.search_fts("旧关键词"))

        note.write_text(
            render_frontmatter(
                {
                    "schema_version": 1,
                    "id": "LJ-MEM-INCREMENTAL",
                    "title": "增量索引",
                    "memory_type": "knowledge",
                    "memory_tier": "archival",
                    "status": "active",
                    "privacy": "private",
                },
                "# 更新\n\n第二版内容包含全新召回关键词。\n",
            ),
            encoding="utf-8",
        )
        indexer = PEMISIndex(self.vault, self.storage)
        indexer.build_index()
        entry = indexer.find_by_path(note)
        self.database.upsert_from_entry(entry, note, self.chunker)
        self.assertGreater(self.database.revision, initial_revision)
        self.assertTrue(self.database.search_fts("全新召回关键词"))
        self.assertFalse(self.database.search_fts("旧关键词"))

        self.assertTrue(self.database.remove_by_path("03-Knowledge/AI/incremental.md"))
        self.assertFalse(self.database.search_fts("全新召回关键词"))
        self.assertTrue(self.database.integrity_check()["healthy"])


if __name__ == "__main__":
    unittest.main()
