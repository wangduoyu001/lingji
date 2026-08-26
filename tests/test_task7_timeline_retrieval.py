import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.gateway import AIProfileRegistry, MemoryGateway
from src.indexer.index import PEMISIndex
from src.memory import VaultLayout
from src.obsidian.frontmatter import render_frontmatter
from src.retrieval import HybridRetriever, MarkdownChunker, MemoryDatabase
from src.retrieval.context_pack import ContextPackBuilder, ContextPackRequest
from src.retrieval.hybrid import SearchFilters
from src.storage import StateDatabase


class TimelineRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.vault = root / "vault"
        self.storage = root / "storage"
        self.layout = VaultLayout(self.vault)
        self.layout.ensure()
        self.db = MemoryDatabase(self.storage / "memory.db")

    def tearDown(self):
        self.tmp.cleanup()

    def note(self, rel, mid, title, text, **metadata):
        path = self.vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        values = {
            "id": mid, "title": title, "memory_type": "knowledge",
            "memory_tier": metadata.pop("memory_tier", "archival"),
            "status": metadata.pop("status", "active"),
            "privacy": "private", "review_status": "approved",
            "project": ["LingJi"], "tags": ["timeline"],
        }
        values.update(metadata)
        path.write_text(render_frontmatter(values, text), encoding="utf-8")

    def rebuild(self):
        indexer = PEMISIndex(self.vault, self.storage)
        indexer.build_index()
        return self.db.rebuild_from_index(indexer.get_all(), self.vault, MarkdownChunker())

    def test_current_history_as_of_and_malformed_fail_closed(self):
        self.note("03-Knowledge/old.md", "old", "旧决定", "采用旧架构。", valid_from="2025-01-01T00:00:00Z", valid_to="2026-01-01T00:00:00Z", status="superseded", superseded_by="new")
        self.note("03-Knowledge/new.md", "new", "新决定", "采用新架构。", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/bad.md", "bad", "损坏时间", "不应泄漏。", valid_from="not-a-time")
        self.rebuild()
        retriever = HybridRetriever(self.db)
        self.assertEqual({r["memory_id"] for r in retriever.search("架构", filters=SearchFilters())}, {"new"})
        self.assertEqual({r["memory_id"] for r in retriever.search("架构", filters=SearchFilters(mode="history"))}, {"old", "new"})
        past = retriever.search("架构", filters=SearchFilters(mode="as_of", as_of="2025-06-01T00:00:00+00:00"))
        self.assertEqual({r["memory_id"] for r in past}, {"old"})
        self.assertEqual(retriever.search("损坏", filters=SearchFilters(mode="as_of", as_of="2026-01-01T00:00:00Z")), [])

    def test_offset_timestamps_use_instants_and_half_open_boundary(self):
        self.note("03-Knowledge/offset.md", "offset", "偏移时间", "偏移边界证据。", valid_from="2026-01-01T08:00:00+08:00", valid_to="2026-01-02T08:00:00+08:00")
        self.rebuild()
        retriever = HybridRetriever(self.db)
        self.assertTrue(retriever.search("边界", filters=SearchFilters(mode="as_of", as_of="2026-01-01T00:00:00Z")))
        self.assertEqual(retriever.search("边界", filters=SearchFilters(mode="as_of", as_of="2026-01-02T00:00:00Z")), [])

    def test_semantic_only_stale_candidate_is_post_filtered_and_receives_contract(self):
        self.note("03-Knowledge/stale.md", "stale", "旧语义", "语义索引中的旧内容。", status="superseded", valid_to="2025-01-01T00:00:00Z")
        self.rebuild()

        class Provider:
            def __init__(self):
                self.filters = None

            def search(self, query, limit, filters=None):
                self.filters = filters
                return [{"chunk_id": self_outer.db.fetch_memory("stale")["chunks"][0]["chunk_id"], "memory_id": "stale", "score": 1.0}]

        self_outer = self
        provider = Provider()
        results = HybridRetriever(self.db, semantic_provider=provider).search("旧内容", filters=SearchFilters(mode="current"))
        self.assertEqual(results, [])
        self.assertEqual(provider.filters["mode"], "current")
        self.assertTrue(provider.filters["as_of"])

    def test_why_exposes_authority_citation_and_exclusion_reason(self):
        self.note("03-Knowledge/high.md", "high", "权威决定", "高权威决定。", authority="user_explicit", sources=["msg-high"], valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/low.md", "low", "低权威决定", "低权威决定。", authority="old_chat_inference", sources=["msg-low"], valid_from="2027-01-01T00:00:00Z")
        self.rebuild()
        results = HybridRetriever(self.db).search("决定", filters=SearchFilters(mode="why"))
        self.assertTrue(results)
        self.assertTrue(all(item.get("why") for item in results))
        self.assertIn("authority", results[0]["why"])
        self.assertIn("citation", results[0])
        self.assertIn("source_refs", results[0]["why"])

    def test_project_refresh_is_idempotent_and_keeps_old_evidence(self):
        self.note("03-Knowledge/old.md", "old", "旧项目决定", "旧方案。", authority="user_explicit", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/new.md", "new", "新项目决定", "新方案。", authority="current_project_authority", valid_from="2026-02-01T00:00:00Z")
        self.rebuild()
        first = self.db.refresh_project_decision("old", "new", reason="项目已切换")
        second = self.db.refresh_project_decision("old", "new", reason="项目已切换")
        self.assertEqual(first["status"], "superseded")
        self.assertEqual(second["status"], "superseded")
        old = self.db.fetch_memory("old")
        self.assertTrue(old and old["superseded_by"] == "new")
        self.assertTrue((self.vault / "03-Knowledge/old.md").exists())

    def test_gateway_and_context_preserve_temporal_mode(self):
        self.note("03-Knowledge/current.md", "current", "当前", "当前时间线内容。", valid_from="2026-01-01T00:00:00Z")
        self.rebuild()
        gateway = MemoryGateway(self.db, HybridRetriever(self.db), ContextPackBuilder(self.db, HybridRetriever(self.db)), object(), profiles=AIProfileRegistry(), state_db=StateDatabase(self.storage / "state.db"))
        result = gateway.search_memory("chatgpt", "时间线", mode="history", as_of="2026-01-01T00:00:00Z")
        self.assertEqual(result["query_mode"], "history")
        pack = gateway.build_context_pack("chatgpt", query="时间线", mode="as_of", as_of="2026-01-01T00:00:00Z")
        self.assertEqual(pack["request"]["mode"], "as_of")
        self.assertLessEqual(len(pack["markdown"]), 12000)


if __name__ == "__main__":
    unittest.main()
