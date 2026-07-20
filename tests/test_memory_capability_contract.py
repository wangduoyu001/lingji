import tempfile
import unittest
from pathlib import Path

from tests.fixtures.memory_capability import (
    FUTURE_SEMANTIC_CONTRACTS,
    build_workspace_memory_fixtures,
)


class LexicalMemoryCapabilityContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        fixtures = build_workspace_memory_fixtures(Path(self.temp_dir.name))
        self.production = fixtures["production"]
        self.acceptance = fixtures["acceptance"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_memory_and_chunk_ids_remain_stable_across_rebuilds(self):
        self.production.write_memory(
            "03-Knowledge/Contracts/stable.md",
            "LJ-MEM-CONTRACT-STABLE",
            "稳定身份合同",
            "# 稳定身份\n\nStableIdentityNeedle 在重复重建后必须保持相同分块身份。\n",
        )
        self.production.rebuild()
        first = self.production.fetch("LJ-MEM-CONTRACT-STABLE")
        self.production.rebuild()
        second = self.production.fetch("LJ-MEM-CONTRACT-STABLE")

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first["memory_id"], second["memory_id"])
        self.assertEqual(
            [chunk["chunk_id"] for chunk in first["chunks"]],
            [chunk["chunk_id"] for chunk in second["chunks"]],
        )

    def test_lexical_and_chinese_fallback_return_valid_citations_without_semantic_provider(self):
        relative_path = "03-Knowledge/Contracts/search.md"
        self.production.write_memory(
            relative_path,
            "LJ-MEM-CONTRACT-SEARCH",
            "正式检索合同",
            "# 检索\n\nCapabilityNeedle 可由全文检索召回。\n\n## 中文\n\n灵机需要支持中文短词召回。\n",
        )
        self.production.rebuild()

        english = self.production.search("CapabilityNeedle")
        chinese = self.production.search("灵机")
        self.assertTrue(english)
        self.assertTrue(chinese)
        citation = english[0]["citation"]
        self.assertEqual(citation["path"], relative_path)
        self.assertIsInstance(citation["start_line"], int)
        self.assertGreaterEqual(citation["start_line"], 1)
        self.assertGreaterEqual(citation["end_line"], citation["start_line"])
        self.assertIsNone(self.production.gateway.retriever.semantic_provider)
        self.assertNotIn("semantic", english[0]["retrieval_channels"])

    def test_project_tag_privacy_agent_scope_and_current_status_filters(self):
        common = "ContractFilterNeedle"
        self.production.write_memory(
            "03-Knowledge/Contracts/target.md",
            "LJ-MEM-CONTRACT-TARGET",
            "目标合同",
            f"# 目标\n\n{common} 只属于 Alpha 项目和 contract/tag。\n",
            project=["Alpha"],
            tags=["contract/tag"],
        )
        self.production.write_memory(
            "03-Knowledge/Contracts/restricted.md",
            "LJ-MEM-CONTRACT-RESTRICTED",
            "受限合同",
            f"# 受限\n\n{common} 只允许本地代理读取。\n",
            privacy="restricted",
        )
        self.production.write_memory(
            "03-Knowledge/Contracts/scoped.md",
            "LJ-MEM-CONTRACT-SCOPED",
            "范围合同",
            f"# 范围\n\n{common} 只允许 ChatGPT。\n",
            agent_scope=["chatgpt"],
        )
        self.production.write_memory(
            "09-Archive/Contracts/archived.md",
            "LJ-MEM-CONTRACT-ARCHIVED",
            "归档合同",
            f"# 归档\n\n{common} 不应默认返回。\n",
            status="archived",
        )
        self.production.write_memory(
            "09-Archive/Contracts/superseded.md",
            "LJ-MEM-CONTRACT-SUPERSEDED",
            "被替代合同",
            f"# 被替代\n\n{common} 不应默认返回。\n",
            status="superseded",
        )
        self.production.rebuild()

        filtered = self.production.search(
            common,
            agent_id="chatgpt",
            project="Alpha",
            tags=["contract/tag"],
        )
        self.assertEqual(
            {item["memory_id"] for item in filtered},
            {"LJ-MEM-CONTRACT-TARGET"},
        )
        self.assertFalse(
            self.production.search(common, agent_id="chatgpt", project="Beta")
        )
        self.assertFalse(
            self.production.search(common, agent_id="chatgpt", tags=["missing/tag"])
        )

        remote_ids = {
            item["memory_id"]
            for item in self.production.search(common, agent_id="codex")
        }
        local_ids = {
            item["memory_id"]
            for item in self.production.search(common, agent_id="lingji-local")
        }
        chatgpt_ids = {
            item["memory_id"]
            for item in self.production.search(common, agent_id="chatgpt")
        }
        self.assertNotIn("LJ-MEM-CONTRACT-RESTRICTED", remote_ids)
        self.assertIn("LJ-MEM-CONTRACT-RESTRICTED", local_ids)
        self.assertNotIn("LJ-MEM-CONTRACT-SCOPED", remote_ids)
        self.assertIn("LJ-MEM-CONTRACT-SCOPED", chatgpt_ids)
        self.assertNotIn("LJ-MEM-CONTRACT-ARCHIVED", local_ids)
        self.assertNotIn("LJ-MEM-CONTRACT-SUPERSEDED", local_ids)

    def test_core_memory_and_context_pack_use_the_unified_gateway_contract(self):
        self.production.write_memory(
            "03-Knowledge/Core-Memory/Working-Rules/core.md",
            "LJ-MEM-CONTRACT-CORE",
            "核心能力合同",
            "# 核心合同\n\nCoreContractNeedle 必须通过统一 Gateway 读取。\n",
            memory_tier="core",
            pin_to_context=True,
            importance="critical",
        )
        self.production.write_memory(
            "03-Knowledge/Contracts/context.md",
            "LJ-MEM-CONTRACT-CONTEXT",
            "上下文合同",
            "# 上下文\n\nContextBudgetNeedle " + ("内容" * 900) + "。\n",
        )
        self.production.rebuild()

        core_ids = {item["memory_id"] for item in self.production.core()}
        pack = self.production.context_pack("ContextBudgetNeedle", max_chars=1000)
        self.assertIn("LJ-MEM-CONTRACT-CORE", core_ids)
        self.assertLessEqual(pack["used_chars"], pack["max_chars"])
        self.assertEqual(
            pack["memory_revision"],
            self.production.gateway.database.revision,
        )
        self.assertGreater(pack["memory_revision"], 0)
        self.assertTrue(pack["sections"])

    def test_production_and_acceptance_data_are_not_cross_visible(self):
        self.production.write_memory(
            "03-Knowledge/Contracts/production.md",
            "LJ-MEM-PRODUCTION-ONLY",
            "Production only",
            "# Production\n\nProductionOnlyNeedle 只能出现在 production。\n",
        )
        self.acceptance.write_memory(
            "03-Knowledge/Contracts/acceptance.md",
            "LJ-MEM-ACCEPTANCE-ONLY",
            "Acceptance only",
            "# Acceptance\n\nAcceptanceOnlyNeedle 只能出现在 acceptance。\n",
        )
        self.production.rebuild()
        self.acceptance.rebuild()

        self.assertTrue(self.production.search("ProductionOnlyNeedle"))
        self.assertFalse(self.acceptance.search("ProductionOnlyNeedle"))
        self.assertTrue(self.acceptance.search("AcceptanceOnlyNeedle"))
        self.assertFalse(self.production.search("AcceptanceOnlyNeedle"))

    def test_lexical_phase_declares_future_semantic_contracts_without_skipping(self):
        capabilities = self.production.capabilities
        self.assertTrue(capabilities["lexical_enabled"])
        self.assertFalse(capabilities["semantic_enabled"])
        self.assertFalse(capabilities["compatibility_database_required"])
        self.assertFalse(capabilities["compatibility_api_required"])
        self.assertFalse(capabilities["qdrant_required"])
        self.assertTrue(FUTURE_SEMANTIC_CONTRACTS)
        self.assertEqual(
            self.production.gateway.database.path,
            self.production.context.memory_db_path,
        )
        self.assertNotEqual(
            self.production.context.memory_db_path,
            self.acceptance.context.memory_db_path,
        )


if __name__ == "__main__":
    unittest.main()
