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
from src.retrieval.temporal import TemporalQuery, parse_instant
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

    def test_naive_query_and_record_instants_fail_closed(self):
        self.assertIsNone(parse_instant("2026-01-01T00:00:00"))
        self.assertFalse(TemporalQuery.from_values("as_of", "2026-01-01T00:00:00").valid)
        self.note("03-Knowledge/naive.md", "naive", "无时区", "无时区内容。", valid_from="2026-01-01T00:00:00")
        self.rebuild()
        self.assertEqual(HybridRetriever(self.db).search("无时区", filters=SearchFilters(mode="as_of", as_of="2026-01-02T00:00:00Z")), [])

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
        self.assertIn("citation", results[0]["why"])
        self.assertIn("source_refs", results[0]["why"])

        self.note("03-Knowledge/expired.md", "expired", "过期决定", "权威决定。", status="superseded", superseded_by="high", sources=["msg-old"], valid_from="2025-01-01T00:00:00Z", valid_to="2026-01-01T00:00:00Z")
        self.rebuild()
        explained = HybridRetriever(self.db).search("权威决定", filters=SearchFilters(mode="why"))
        excluded = explained[0]["why"]["excluded_candidates"]
        self.assertTrue(any(item["memory_id"] == "expired" and item["reason"].startswith("status_") for item in excluded))
        expired_explanation = next(item for item in excluded if item["memory_id"] == "expired")
        self.assertIn("msg-old", expired_explanation["citation"]["source_refs"])

    def test_lower_authority_conflict_cannot_displace_current_winner(self):
        self.note("03-Knowledge/high.md", "high", "当前决定", "同一项目决定内容。", authority="user_explicit", conflict_key="architecture", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/low.md", "low", "较新决定", "同一项目决定内容。", authority="old_chat_inference", conflict_key="architecture", valid_from="2026-02-01T00:00:00Z")
        self.rebuild()
        current = HybridRetriever(self.db).search("决定内容", filters=SearchFilters(mode="current"))
        self.assertEqual({item["memory_id"] for item in current}, {"high"})
        history = HybridRetriever(self.db).search("决定内容", filters=SearchFilters(mode="history"))
        self.assertEqual({item["memory_id"] for item in history}, {"high", "low"})

    def test_unrelated_same_project_memories_are_not_hidden_by_authority(self):
        self.note("03-Knowledge/one.md", "one", "偏好一", "同一项目的偏好一。", authority="user_explicit", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/two.md", "two", "偏好二", "同一项目的偏好二。", authority="old_chat_inference", valid_from="2026-02-01T00:00:00Z")
        self.rebuild()
        current = HybridRetriever(self.db).search("偏好", filters=SearchFilters(mode="current"))
        self.assertEqual({item["memory_id"] for item in current}, {"one", "two"})
        why = HybridRetriever(self.db).search("偏好", filters=SearchFilters(mode="why"))
        self.assertFalse(any(item["why"]["conflict"] for item in why))

    def test_project_refresh_is_idempotent_and_keeps_old_evidence(self):
        self.note("03-Knowledge/old.md", "old", "旧项目决定", "旧方案。", authority="current_project_authority", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/new.md", "new", "新项目决定", "新方案。", authority="current_project_authority", valid_from="2026-02-01T00:00:00Z")
        self.rebuild()
        first = self.db.refresh_project_decision("old", "new", reason="项目已切换")
        second = self.db.refresh_project_decision("old", "new", reason="项目已切换")
        self.assertEqual(first["status"], "superseded")
        self.assertEqual(second["status"], "superseded")
        old = self.db.fetch_memory("old")
        self.assertTrue(old and old["superseded_by"] == "new")
        self.assertEqual(old["valid_to"], "2026-02-01T00:00:00Z")
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

    def test_default_current_cache_key_is_stable_but_explicit_as_of_varies(self):
        first = SearchFilters().normalized()
        second = SearchFilters().normalized()
        self.assertIsNone(first.as_of)
        self.assertIsNone(second.as_of)
        self.assertNotEqual(SearchFilters(mode="as_of", as_of="2026-01-01T00:00:00Z").normalized().as_of, SearchFilters(mode="as_of", as_of="2026-01-02T00:00:00Z").normalized().as_of)

    def test_why_exclusions_are_scoped_per_result(self):
        self.note("03-Knowledge/a-new.md", "a-new", "主题A当前", "决定 A 现在方案。", authority="user_explicit", conflict_key="topic-a", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/a-old.md", "a-old", "主题A旧版", "决定 A 旧方案。", authority="old_chat_inference", conflict_key="topic-a", valid_from="2025-01-01T00:00:00Z")
        self.note("03-Knowledge/b-new.md", "b-new", "主题B当前", "决定 B 现在方案。", authority="user_explicit", conflict_key="topic-b", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/b-old.md", "b-old", "主题B旧版", "决定 B 旧方案。", authority="old_chat_inference", conflict_key="topic-b", valid_from="2025-01-01T00:00:00Z")
        self.note("03-Knowledge/c-current.md", "c-current", "无冲突主题", "决定 C 独立方案。", authority="verified_source", valid_from="2026-01-01T00:00:00Z")
        self.rebuild()
        results = HybridRetriever(self.db).search("决定 方案", limit=10, filters=SearchFilters(mode="why"))
        by_id = {item["memory_id"]: item["why"] for item in results}
        self.assertTrue(by_id["a-new"]["conflict"])
        self.assertEqual({item["memory_id"] for item in by_id["a-new"]["excluded_candidates"]}, {"a-old"})
        self.assertTrue(by_id["b-new"]["conflict"])
        self.assertEqual({item["memory_id"] for item in by_id["b-new"]["excluded_candidates"]}, {"b-old"})
        self.assertFalse(by_id["c-current"]["conflict"])
        self.assertNotIn("b-old", {item["memory_id"] for item in by_id["c-current"]["excluded_candidates"]})

    def test_invalid_temporal_mode_fails_closed(self):
        self.note("03-Knowledge/valid.md", "valid", "有效内容", "有效检索内容。", valid_from="2026-01-01T00:00:00Z")
        self.rebuild()
        invalid = SearchFilters(mode="not-a-mode")
        self.assertFalse(invalid.normalized().valid)
        self.assertEqual(HybridRetriever(self.db).search("有效", filters=invalid), [])

    def test_why_excluded_candidates_keep_project_and_memory_type_scope(self):
        self.note("03-Knowledge/a-current.md", "a-current", "项目A当前", "同一范围决定方案。", project=["Project A"], memory_type="knowledge", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/b-old.md", "b-old", "项目B历史", "同一范围决定方案。", project=["Project B"], memory_type="knowledge", sources=["project-b-source"], status="superseded", valid_from="2025-01-01T00:00:00Z", valid_to="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/decision-old.md", "decision-old", "决策历史", "同一范围决定方案。", project=["Project A"], memory_type="decision", sources=["decision-source"], status="superseded", valid_from="2025-01-01T00:00:00Z", valid_to="2026-01-01T00:00:00Z")
        self.rebuild()
        results = HybridRetriever(self.db).search(
            "决定 方案",
            limit=10,
            filters=SearchFilters(mode="why", project="Project A", memory_types=("knowledge",)),
        )
        self.assertTrue(results)
        excluded = results[0]["why"]["excluded_candidates"]
        excluded_ids = {item["memory_id"] for item in excluded}
        self.assertNotIn("b-old", excluded_ids)
        self.assertNotIn("decision-old", excluded_ids)
        self.assertNotIn("project-b-source", {source for item in excluded for source in item["citation"]["source_refs"]})

    def test_semantic_candidates_fail_closed_on_memory_type_and_privacy(self):
        self.note("03-Knowledge/restricted.md", "restricted", "决策私密", "不应被公开知识检索召回。", memory_type="decision", privacy="private", valid_from="2026-01-01T00:00:00Z")
        self.rebuild()

        class Provider:
            def search(self, query, limit, filters=None):
                chunk = self_outer.db.fetch_memory("restricted")["chunks"][0]["chunk_id"]
                return [{"chunk_id": chunk, "memory_id": "restricted", "score": 1.0}]

        self_outer = self
        retriever = HybridRetriever(self.db, semantic_provider=Provider())
        self.assertEqual(
            retriever.search(
                "公开知识",
                filters=SearchFilters(memory_types=("knowledge",), privacy=("public",)),
            ),
            [],
        )

    def test_why_same_conflict_key_isolated_by_project(self):
        self.note("03-Knowledge/a-new.md", "a-new", "项目A当前", "共享主题决定方案。", project=["Project A"], conflict_key="shared-topic", authority="user_explicit", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/a-old.md", "a-old", "项目A旧版", "共享主题决定方案。", project=["Project A"], conflict_key="shared-topic", authority="old_chat_inference", valid_from="2025-01-01T00:00:00Z")
        self.note("03-Knowledge/b-new.md", "b-new", "项目B当前", "共享主题决定方案。", project=["Project B"], conflict_key="shared-topic", authority="user_explicit", valid_from="2026-01-01T00:00:00Z")
        self.note("03-Knowledge/b-old.md", "b-old", "项目B旧版", "共享主题决定方案。", project=["Project B"], conflict_key="shared-topic", authority="old_chat_inference", valid_from="2025-01-01T00:00:00Z")
        self.rebuild()
        results = HybridRetriever(self.db).search("共享主题 方案", limit=10, filters=SearchFilters(mode="why"))
        by_id = {item["memory_id"]: item["why"] for item in results}
        self.assertEqual({item["memory_id"] for item in by_id["a-new"]["excluded_candidates"]}, {"a-old"})
        self.assertEqual({item["memory_id"] for item in by_id["b-new"]["excluded_candidates"]}, {"b-old"})


if __name__ == "__main__":
    unittest.main()
