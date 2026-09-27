"""Regression tests for the evidence retrieval channel (3.2.1, 2026-09-27).

structured_evidence 是溯源证据，之前与真知识混排导致 99.8% 的证据淹没
knowledge。分通道后：memory 通道（knowledge 等）优先，evidence 通道殿后
并带 retrieval_channel 标签；证据永不丢弃，仍可引用与展开原文。
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.memory import VaultLayout
from src.retrieval import HybridRetriever, MarkdownChunker, MemoryDatabase
from src.indexer.index import PEMISIndex
from src.obsidian.frontmatter import render_frontmatter


class EvidenceChannelTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.vault = base / "vault"
        self.storage = base / "storage"
        VaultLayout(self.vault).ensure()
        self.database = MemoryDatabase(self.storage / "lingji_memory.db")
        self.chunker = MarkdownChunker(max_chars=240, overlap_chars=40)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _seed_knowledge(self) -> None:
        path = self.vault / "03-Knowledge" / "AI" / "deploy.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        values = {
            "schema_version": 1,
            "id": "LJ-MEM-DEPLOY",
            "title": "部署结论",
            "memory_type": "knowledge",
            "memory_tier": "archival",
            "status": "active",
            "privacy": "private",
            "importance": "high",
            "review_status": "approved",
            "project": [],
            "tags": [],
        }
        path.write_text(
            render_frontmatter(values, "灵机部署采用 pyinstaller 打包与回填队列。"), encoding="utf-8"
        )
        indexer = PEMISIndex(self.vault, self.storage)
        indexer.build_index()
        self.database.rebuild_from_index(indexer.get_all(), self.vault, self.chunker)

    def _seed_evidence(self, memory_id: str, body: str) -> None:
        entry = {
            "id": memory_id,
            "relative_path": f"__structured__/evidence/{memory_id}.md",
            "title": f"证据 {memory_id}",
            "memory_type": "structured_evidence",
            "memory_tier": "evidence",
            "status": "active",
            "review_status": "evidence",
            "privacy": "private",
            "project": [],
            "tags": ["structured-evidence"],
            "content_hash": f"hash-{memory_id}",
            "modified_at": "2026-09-27T00:00:00Z",
            "sources": ["src-test"],
            "authority": "old_chat_inference",
            "evidence_refs": [memory_id],
        }
        chunks = self.chunker.chunk(memory_id, f"[user] {body}")
        with self.database._connection() as connection:
            self.database._upsert_document(connection, entry, chunks)
            connection.commit()

    def _retriever(self) -> HybridRetriever:
        return HybridRetriever(self.database)

    def test_knowledge_ranks_above_evidence_with_channel_tags(self) -> None:
        self._seed_knowledge()
        # 证据命中同一主题且唯一词频更高，裸分数排序下它会压过 knowledge。
        self._seed_evidence(
            "LJ-EVIDENCE-DEPLOY-1",
            "灵机部署采用 pyinstaller 打包与回填队列，部署部署部署 deploy deploy。",
        )
        results = self._retriever().search("灵机部署 pyinstaller", limit=5)
        self.assertTrue(results)
        channels = [str(item.get("retrieval_channel")) for item in results]
        self.assertIn("memory", channels)
        self.assertIn("evidence", channels)
        self.assertEqual(channels.index("memory"), 0, "memory 通道必须排在 evidence 之前")
        ids = [str(item.get("memory_id")) for item in results]
        self.assertEqual(ids[0], "LJ-MEM-DEPLOY")

    def test_evidence_only_results_survive_with_channel_tag(self) -> None:
        self._seed_evidence(
            "LJ-EVIDENCE-UNIQUE-7",
            "独一无二的主题词 quantum-entangle-sync 出现在这段对话里。",
        )
        results = self._retriever().search("quantum-entangle-sync", limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["retrieval_channel"], "evidence")
        self.assertTrue(results[0].get("citation"), "证据必须继续携带可验证引用")


if __name__ == "__main__":
    unittest.main()
