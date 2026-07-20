import tempfile
import unittest
from pathlib import Path

from src.gateway import AIProfileRegistry, MemoryGateway
from src.indexer.index import PEMISIndex
from src.memory import MemoryLifecycleService, PermanentMemoryObsidianManager, VaultLayout
from src.retrieval import HybridRetriever, MarkdownChunker, MemoryDatabase
from src.retrieval.context_pack import ContextPackBuilder
from src.storage import StateDatabase


class PermanentMemoryGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.vault = base / "vault"
        self.storage = base / "storage"
        self.layout = VaultLayout(self.vault)
        self.layout.ensure()
        self.state_db = StateDatabase(self.storage / "state.db")
        self.database = MemoryDatabase(self.storage / "memory.db")
        self.chunker = MarkdownChunker(max_chars=500, overlap_chars=60)
        self.retriever = HybridRetriever(self.database, cache_size=16, cache_ttl_seconds=60)
        self.lifecycle = MemoryLifecycleService(self.layout, self.state_db)
        self.gateway = MemoryGateway(
            self.database,
            self.retriever,
            ContextPackBuilder(self.database, self.retriever),
            self.lifecycle,
            profiles=AIProfileRegistry(),
            state_db=self.state_db,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _rebuild(self):
        indexer = PEMISIndex(self.vault, self.storage)
        indexer.build_index()
        return self.gateway.rebuild(indexer.get_all(), self.vault, self.chunker)

    def test_ai_can_propose_but_cannot_directly_promote_core_memory(self):
        candidate = self.gateway.propose_memory(
            "chatgpt",
            "用户偏好简洁代码",
            "用户偏好简洁、可维护、避免反复重构的代码。",
            {"importance": "high", "tags": ["domain/ai"]},
        )
        self.assertEqual(candidate["memory_tier"], "candidate")
        self.assertIn("01-Inbox/AI-Memory/chatgpt", candidate["relative_path"])
        with self.assertRaises(PermissionError):
            self.lifecycle.promote_candidate(candidate["path"], owner_confirmed=False)

        promoted = self.lifecycle.promote_candidate(
            candidate["path"],
            owner_confirmed=True,
            agent_scope=["all"],
            target_category="Preferences",
        )
        self.assertEqual(promoted["memory_tier"], "core")
        self.assertTrue(promoted["pin_to_context"])
        self.assertIn("03-Knowledge/Core-Memory/Preferences", promoted["relative_path"])
        self.assertFalse(Path(candidate["path"]).exists())
        promoted_text = Path(promoted["path"]).read_text(encoding="utf-8")
        self.assertIn("已由主人确认", promoted_text)
        self.assertNotIn("## 主人审核", promoted_text)

    def test_remote_ai_cannot_create_or_read_restricted_memory(self):
        with self.assertRaises(PermissionError):
            self.gateway.propose_memory(
                "chatgpt",
                "受限身份信息",
                "这条内容只允许本地模型读取。",
                {"privacy": "restricted"},
            )
        local = self.gateway.propose_memory(
            "ollama",
            "本地受限信息",
            "这条内容只允许本地模型读取。",
            {"privacy": "restricted"},
        )
        self._rebuild()
        self.assertIsNotNone(
            self.gateway.fetch_memory("ollama", relative_path=local["relative_path"])
        )
        with self.assertRaises(PermissionError):
            self.gateway.fetch_memory("chatgpt", relative_path=local["relative_path"])

    def test_context_pack_puts_core_memory_first_and_respects_budget(self):
        candidate = self.gateway.propose_memory(
            "codex",
            "代码开发原则",
            "所有功能先理解需求再开发，代码保持简洁并配套测试文档。",
            {"importance": "critical"},
        )
        self.lifecycle.promote_candidate(
            candidate["path"],
            owner_confirmed=True,
            agent_scope=["codex", "chatgpt"],
            recall_weight=1.5,
            target_category="Working-Rules",
        )
        source = self.layout.root / "03-Knowledge" / "Technology" / "sqlite.md"
        source.write_text(
            "---\nid: LJ-SOURCE-SQLITE\nmemory_type: knowledge\nmemory_tier: archival\nstatus: active\nprivacy: private\n---\n\n# SQLite检索\n\nFTS5 用于快速全文搜索，WAL 用于增强并发读取稳定性。\n",
            encoding="utf-8",
        )
        self._rebuild()
        pack = self.gateway.build_context_pack(
            "codex",
            query="SQLite 全文检索",
            project=None,
            max_chars=1200,
        )
        self.assertTrue(pack["sections"])
        self.assertEqual(pack["sections"][0]["kind"], "core_memory")
        self.assertLessEqual(pack["used_chars"], 1200)
        self.assertIn("来源：", pack["markdown"])
        self.assertIn("代码开发原则", pack["markdown"])

    def test_agent_scope_hides_core_memory_from_other_ai(self):
        candidate = self.gateway.propose_memory(
            "chatgpt",
            "只给ChatGPT的规则",
            "这条规则只应发送给 ChatGPT。",
        )
        self.lifecycle.promote_candidate(
            candidate["path"],
            owner_confirmed=True,
            agent_scope=["chatgpt"],
            target_category="Constraints",
        )
        self._rebuild()
        chatgpt = self.gateway.get_core_memory("chatgpt")
        codex = self.gateway.get_core_memory("codex")
        self.assertEqual(len(chatgpt["memories"]), 1)
        self.assertEqual(len(codex["memories"]), 0)

    def test_permanent_memory_obsidian_ui_is_generated(self):
        manager = PermanentMemoryObsidianManager(self.layout)
        result = manager.ensure()
        expected = self.vault / "00-System" / "Bases" / "Permanent Memory.base"
        self.assertTrue(expected.exists())
        self.assertTrue((self.vault / "00-System" / "Permanent-Memory.md").exists())
        self.assertTrue((self.vault / "00-System" / "Templates" / "核心记忆模板.md").exists())
        self.assertTrue(result["created"] or result["skipped"])


if __name__ == "__main__":
    unittest.main()
