from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.config import Settings
from src.memory.auto_promotion import (
    EVENT_TYPE,
    AutoMemoryPromotionPipeline,
    verify_auto_promotion_chain,
)
from src.memory.lifecycle import MemoryLifecycleService
from src.memory.vault_layout import VaultLayout
from src.storage.state_db import StateDatabase


def _memory_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE distilled_knowledge (
                conversation_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_points_json TEXT NOT NULL,
                category TEXT NOT NULL,
                model TEXT NOT NULL,
                messages_digest TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                revision INTEGER NOT NULL DEFAULT 1,
                occurred_at TEXT,
                status TEXT NOT NULL DEFAULT 'ready',
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                confidence REAL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _seed(
    path: Path,
    conversation_id: str,
    title: str,
    summary: str,
    points: list[str],
    *,
    category: str = "技术",
    confidence: float | None = 0.95,
    revision: int = 1,
    status: str = "ready",
    occurred_at: str = "2026-09-22T08:00:00",
) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            INSERT INTO distilled_knowledge (
                conversation_id, source_id, title, summary, key_points_json, category,
                model, messages_digest, message_count, revision, occurred_at,
                status, last_error, created_at, updated_at, confidence
            ) VALUES (?, 'src', ?, ?, ?, ?, 'test-model', 'digest', 3, ?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                conversation_id,
                title,
                summary,
                json.dumps(points, ensure_ascii=False),
                category,
                revision,
                occurred_at,
                status,
                occurred_at,
                occurred_at,
                confidence,
            ),
        )
        conn.commit()
    finally:
        conn.close()


class AutoPromotionPipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.vault = root / "vault"
        self.memory_db = root / "memory.db"
        _memory_db(self.memory_db)
        self.settings = Settings(
            _env_file=None,
            vault_dir=str(self.vault),
            storage_dir=str(root / "storage"),
        )
        self.state_db = StateDatabase(root / "state.db")
        self.lifecycle = MemoryLifecycleService(VaultLayout(self.vault), self.state_db)
        self.overrides: dict[str, any] = {"auto_promote_enabled": True}
        self.now = datetime(2026, 9, 22, 12, 0, 0)
        self.sync_calls: list[int] = []
        self.pipeline = AutoMemoryPromotionPipeline(
            settings=self.settings,
            lifecycle=self.lifecycle,
            state_db=self.state_db,
            memory_db_path=self.memory_db,
            semantic_similarity=lambda text, document: 0.10,
            setting_reader=self.overrides.get,
            post_promotion_sync=lambda: self.sync_calls.append(1) or {"added": 1},
            now=lambda: self.now,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _decisions(self) -> list[dict]:
        output: list[dict] = []
        for row in self.state_db.recent_events(limit=1000):
            if row.get("event_type") != EVENT_TYPE:
                continue
            payload = json.loads(str(row.get("payload_json") or "{}"))
            if isinstance(payload, dict):
                output.append(payload)
        return output

    def _core_files(self) -> list[Path]:
        core = self.vault / "03-Knowledge" / "Core-Memory"
        return sorted(core.rglob("*.md")) if core.exists() else []

    def _evolving_files(self) -> list[Path]:
        evolving = self.vault / "03-Knowledge" / "Evolving"
        return sorted(evolving.rglob("*.md")) if evolving.exists() else []

    # ------------------------------------------------------- 开关与零写入
    def test_disabled_switch_writes_nothing(self):
        self.overrides["auto_promote_enabled"] = False
        _seed(
            self.memory_db,
            "conv-1",
            "部署方案定稿",
            "确定用方案 A 部署生产环境。",
            ["方案 A 为生产部署方案"],
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(self._decisions(), [])
        self.assertEqual(self._core_files(), [])
        self.assertEqual(self._evolving_files(), [])

    # ----------------------------------------------------------- 晋升正路
    def test_qualified_row_promotes_to_core_memory(self):
        _seed(
            self.memory_db,
            "conv-1",
            "部署方案定稿",
            "确定用方案 A 部署生产环境。",
            ["方案 A 为生产部署方案", "部署窗口是周五凌晨"],
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["promoted"], 1)
        core = self._core_files()
        self.assertEqual(len(core), 1)
        text = core[0].read_text(encoding="utf-8-sig")
        self.assertIn("方案 A 为生产部署方案", text)
        self.assertIn("memory_tier: core", text)
        # 晋升文件 frontmatter 必须自带来源链（2026-09-30 P1 修复）：来源撤销
        # 时授权过滤要靠 relationships.automatic_memory_source_id 管辖派生层。
        self.assertIn("automatic_memory_source_id: src", text)
        decisions = self._decisions()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["outcome"], "promoted")
        self.assertTrue(verify_auto_promotion_chain(decisions))
        # 晋升后触发投影同步，结果并入 summary。
        self.assertEqual(len(self.sync_calls), 1)
        self.assertEqual(result.get("projection_sync"), {"added": 1})

    def test_promoted_core_memory_is_visible_to_ai_agents(self):
        """晋升 = 批准进 Core Memory，scope 必须对 AI 可见（2026-09-30 真实召回标定）。

        缺陷史：propose 阶段写入 agent_scope=["lingji-auto"]（管线内部身份，
        AIProfileRegistry 无此 profile），promote 沿用后 74 条 core 知识对
        codex/zcode 全部不可见。
        """
        _seed(
            self.memory_db,
            "conv-scope",
            "ZCode 快照增量导出方案",
            "增量快照按会话自包含导出并用水位线去重。",
            ["水位线在 storage/automatic_memory_watermarks"],
        )
        self.pipeline.run_once()
        core = self._core_files()
        self.assertEqual(len(core), 1)
        text = core[0].read_text(encoding="utf-8-sig")
        # agent_scope 必须是全域可见；proposed_by 保留 lingji-auto（提议者审计字段）。
        self.assertIn("agent_scope:\n- all", text)

    def test_no_promotion_skips_projection_sync(self):
        _seed(
            self.memory_db,
            "conv-2",
            "周末出游计划",
            "商量了周末出游的备选地点。",
            ["备选地点包括海边和山区"],
            category="其他",
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["evolving"], 1)
        self.assertEqual(self.sync_calls, [])
        self.assertNotIn("projection_sync", result)

    # ------------------------------------------------------- 门槛各分支
    def test_category_not_whitelisted_goes_evolving(self):
        _seed(
            self.memory_db,
            "conv-2",
            "周末出游计划",
            "商量了周末出游的备选地点。",
            ["备选地点包括海边和山区"],
            category="其他",
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["evolving"], 1)
        self.assertEqual(self._core_files(), [])
        evolving = self._evolving_files()
        self.assertEqual(len(evolving), 1)
        text = evolving[0].read_text(encoding="utf-8-sig")
        self.assertIn("category_not_whitelisted", text)
        self.assertIn("2026-09-22T12:00:00", text)

    def test_low_confidence_goes_evolving(self):
        _seed(
            self.memory_db,
            "conv-3",
            "临时调试参数",
            "调试时改过超时时间。",
            ["超时时间临时改成了 60 秒"],
            confidence=0.50,
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["evolving"], 1)
        self.assertEqual(self._decisions()[0]["reasons"], ["confidence_below_threshold"])

    def test_missing_confidence_goes_evolving(self):
        _seed(
            self.memory_db,
            "conv-4",
            "历史遗留结论",
            "旧版本提炼行没有置信度。",
            ["旧格式行"],
            confidence=None,
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["evolving"], 1)
        self.assertIn("confidence_missing", self._decisions()[0]["reasons"])

    def test_notification_like_title_goes_evolving(self):
        _seed(
            self.memory_db,
            "conv-5",
            "晨间简报任务失败",
            "简报任务一次运行失败。",
            ["失败原因待查"],
            confidence=0.95,
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["evolving"], 1)
        self.assertIn("notification_like", self._decisions()[0]["reasons"])

    # ------------------------------------------------------------- 去重
    def test_full_text_duplicate_is_recorded_without_writes(self):
        _seed(
            self.memory_db,
            "conv-1",
            "部署方案定稿",
            "确定用方案 A 部署生产环境。",
            ["方案 A 为生产部署方案"],
        )
        self.pipeline.run_once()
        self.assertEqual(len(self._core_files()), 1)
        _seed(
            self.memory_db,
            "conv-2",
            "部署方案定稿（重复记录）",
            "确定用方案 A 部署生产环境。",
            ["方案 A 为生产部署方案"],
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["duplicate"], 1)
        self.assertEqual(len(self._core_files()), 1)
        outcomes = [item["outcome"] for item in self._decisions()]
        self.assertEqual(outcomes, ["duplicate", "promoted"])

    def test_semantic_duplicate_blocks_promotion(self):
        _seed(
            self.memory_db,
            "conv-1",
            "部署方案定稿",
            "确定用方案 A 部署生产环境。",
            ["方案 A 为生产部署方案"],
        )
        self.pipeline.run_once()
        self.pipeline.semantic_similarity = lambda text, document: 0.99
        _seed(
            self.memory_db,
            "conv-3",
            "生产部署方案的最终决定",
            "生产环境部署采用方案 A。",
            ["方案 A 是生产部署方案"],
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["duplicate"], 1)
        self.assertEqual(len(self._core_files()), 1)

    # ------------------------------------------------------------- 冲突
    def test_title_conflict_goes_evolving(self):
        _seed(
            self.memory_db,
            "conv-1",
            "部署方案定稿",
            "确定用方案 A 部署生产环境。",
            ["方案 A 为生产部署方案"],
        )
        self.pipeline.run_once()
        _seed(
            self.memory_db,
            "conv-2",
            "部署方案定稿",
            "改用方案 B 部署生产环境。",
            ["方案 B 取代方案 A"],
        )
        result = self.pipeline.run_once()
        self.assertEqual(result["evolving"], 1)
        self.assertEqual(len(self._core_files()), 1, "冲突行不得晋升，既有 Core 不增不改")
        decisions = self._decisions()
        self.assertEqual(decisions[0]["reasons"], ["title_conflict"])
        self.assertTrue(verify_auto_promotion_chain(decisions))

    # ------------------------------------------------------------- 上限
    def test_daily_limit_caps_promotions(self):
        self.overrides["auto_promote_daily_limit"] = 1
        for index in range(2):
            _seed(
                self.memory_db,
                f"conv-cap-{index}",
                f"独立结论{index}号",
                f"第{index}条独立确定的事实。",
                [f"事实{index}"],
            )
        result = self.pipeline.run_once()
        self.assertEqual(result["promoted"], 1)
        self.assertTrue(result["capped"])

    # ------------------------------------------------- 幂等与 revision 迭代
    def test_same_revision_is_not_reprocessed(self):
        _seed(
            self.memory_db,
            "conv-1",
            "部署方案定稿",
            "确定用方案 A 部署生产环境。",
            ["方案 A 为生产部署方案"],
        )
        self.pipeline.run_once()
        self.pipeline.run_once()
        self.assertEqual(len(self._decisions()), 1)

    def test_decided_rows_do_not_exhaust_batch_limit(self):
        """真机回归：最老的已决行不得占满每轮 limit 名额导致管线空转。"""
        for index in range(3):
            _seed(
                self.memory_db,
                f"conv-limit-{index}",
                f"独立结论{index}号",
                f"第{index}条独立确定的事实。",
                [f"事实{index}"],
                occurred_at=f"2026-09-2{index}T08:00:00",
            )
        first = self.pipeline.run_once(limit=2)
        self.assertEqual(first["processed"], 2)
        # 第二轮：前两条已决，limit=2 的名额必须轮到第三条。
        second = self.pipeline.run_once(limit=2)
        self.assertEqual(second["processed"], 1)
        self.assertEqual(len(self._decisions()), 3)
        # 全部决后：零处理但不报错。
        third = self.pipeline.run_once(limit=2)
        self.assertEqual(third["processed"], 0)

    def test_revision_bump_is_reprocessed_and_graduates_evolving(self):
        _seed(
            self.memory_db,
            "conv-1",
            "临时调试参数",
            "调试时改过超时时间。",
            ["超时时间临时改成了 60 秒"],
            confidence=0.50,
        )
        self.pipeline.run_once()
        evolving = self._evolving_files()
        self.assertEqual(len(evolving), 1)
        self.assertIn("status: evolving", evolving[0].read_text(encoding="utf-8-sig"))
        # 同一 conversation  revision 升级且达到门槛：再次处理并毕业。
        conn = sqlite3.connect(str(self.memory_db))
        try:
            conn.execute(
                "UPDATE distilled_knowledge SET revision = 2, confidence = 0.97, summary = ? WHERE conversation_id = 'conv-1'",
                ("已验证：超时时间调整为 60 秒并写入配置。",),
            )
            conn.commit()
        finally:
            conn.close()
        result = self.pipeline.run_once()
        self.assertEqual(result["promoted"], 1)
        evolving_text = evolving[0].read_text(encoding="utf-8-sig")
        self.assertIn("status: graduated", evolving_text)
        self.assertIn("graduated:conv-1", evolving_text)

    # ------------------------------------------------------------ 审计链
    def test_audit_chain_verifies_and_detects_tamper(self):
        for index in range(3):
            _seed(
                self.memory_db,
                f"conv-audit-{index}",
                f"审计样本{index}",
                f"审计样本{index}的确定性结论。",
                [f"结论{index}"],
            )
        self.pipeline.run_once()
        decisions = self._decisions()
        self.assertEqual(len(decisions), 3)
        self.assertTrue(verify_auto_promotion_chain(decisions))
        tampered = [dict(item) for item in decisions]
        tampered[1]["outcome"] = "rejected"
        self.assertFalse(verify_auto_promotion_chain(tampered))


if __name__ == "__main__":
    unittest.main()
