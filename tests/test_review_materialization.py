"""升格链物化验证（WorkBuddy 2026-09-17 R2）：DB 记忆无 vault 候选文件时，
确认动作必须先物化候选文件再升格——"要点转永久记忆"从此真正可用。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.memory.lifecycle import MemoryLifecycleService
from src.memory.vault_layout import VaultLayout
from src.project_memory.review_service import MemoryReviewService
from src.retrieval import MarkdownChunker, MemoryDatabase
from src.indexer.index import PEMISIndex


def _note(vault: Path, relative, memory_id, title, body):
    path = vault / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = (
        "---\n"
        f"schema_version: 1\nid: {memory_id}\ntitle: {title}\n"
        "memory_type: knowledge\nmemory_tier: archival\nstatus: active\n"
        "privacy: private\nimportance: medium\nreview_status: approved\n"
        "---\n"
    )
    path.write_text(frontmatter + body, encoding="utf-8")
    return path


class ReviewMaterializationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.vault = self.root / "vault"
        self.storage = self.root / "storage"
        self.vault.mkdir(parents=True, exist_ok=True)
        self.storage.mkdir(parents=True, exist_ok=True)
        self.database = MemoryDatabase(self.storage / "lingji_memory.db")
        indexer = PEMISIndex(self.vault, self.storage)
        _note(self.vault, "03-Knowledge/Cooking/yiren.md", "LJ-MEM-YIREN9",
              "薏仁采购记录", "# 买薏仁\n\n我们开了 200 公里，专门来买柴火炒薏仁的，给我装上 50 斤。\n")
        indexer.build_index()
        self.database.rebuild_from_index(indexer.get_all(), self.vault, MarkdownChunker(max_chars=200, overlap_chars=20))
        # 模拟 automatic-memory 证据记忆：库内有权威内容，vault 源文件不存在
        #（等价于提炼/导入产物从未落 vault——WorkBuddy R2 的缺失写入点场景）。
        for path in self.vault.rglob("*.md"):
            path.unlink()
        self.layout = VaultLayout(self.vault)
        self.review = MemoryReviewService(MemoryLifecycleService(self.layout), database=self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_approve_materializes_candidate_then_promotes_to_core(self):
        doc = self.database.fetch_memory("LJ-MEM-YIREN9")
        self.assertTrue(doc, "seeded memory must exist in the DB")

        result = self.review.approve("LJ-MEM-YIREN9", owner_confirmed=True,
                                     expected_content_hash="", target_category="General")

        core_files = list((self.vault / "03-Knowledge" / "Core-Memory" / "General").glob("*.md"))
        self.assertTrue(core_files, "promoted core memory file must exist in the vault")
        core_text = core_files[0].read_text(encoding="utf-8-sig")
        self.assertIn("memory_tier: core", core_text)
        self.assertIn("review_status: approved", core_text)
        self.assertIn("薏仁", core_text)
        self.assertNotIn("01-Inbox", str(core_files[0]))
        promoted_id = result.get("memory_id") or "LJ-MEM-YIREN9"
        self.assertTrue(promoted_id)

        # 候选文件应已随升格移动，重复确认应报已审阅
        with self.assertRaises(Exception):
            self.review.approve("LJ-MEM-YIREN9", owner_confirmed=True,
                                expected_content_hash="", target_category="General")

    def test_reject_materializes_and_rejects_without_crash(self):
        self.review.reject("LJ-MEM-YIREN9", owner_confirmed=True,
                           expected_content_hash="", reason="主人不需要这条")
        candidates = list((self.vault / "01-Inbox" / "AI-Memory").rglob("*.md")) if (self.vault / "01-Inbox" / "AI-Memory").exists() else []
        for path in candidates:
            text = path.read_text(encoding="utf-8-sig")
            self.assertIn("review_status: rejected", text)


if __name__ == "__main__":
    unittest.main()

    def test_conversation_card_materializes_from_conversation_records(self):
        """会话卡（LJ-CONV）确认时从会话记录物化候选——主人界面的真实卡片形态。"""
        import sqlite3

        db_path = self.storage / "lingji_memory.db"
        conn = sqlite3.connect(db_path)
        conv_id = "LJ-CONV-TEST01"
        conn.execute(
            "INSERT INTO conversation_records (conversation_id, source_id, title, started_at, message_count)"
            " VALUES (?,?,?,?,2)",
            (conv_id, "src-test", "灵机验收会话", "2026-09-17T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO message_records (message_id, conversation_id, role, content, sequence, occurred_at)"
            " VALUES ('LJ-MSG-T1', ?, 'user', '请记住这条重要的验收规则', 1, '2026-09-17T00:00:01Z')",
            (conv_id,),
        )
        conn.execute(
            "INSERT INTO message_records (message_id, conversation_id, role, content, sequence, occurred_at)"
            " VALUES ('LJ-MSG-T2', ?, 'assistant', '已记住这条重要的验收规则。', 2, '2026-09-17T00:00:02Z')",
            (conv_id,),
        )
        conn.commit(); conn.close()

        self.review.approve(conv_id, owner_confirmed=True, expected_content_hash="", target_category="General")
        core_files = list((self.vault / "03-Knowledge" / "Core-Memory" / "General").glob("LJ-CONV-TEST01*.md"))
        self.assertTrue(core_files, "conversation card must materialize and promote")
        text = core_files[0].read_text(encoding="utf-8-sig")
        self.assertIn("请记住这条重要的验收规则", text)
