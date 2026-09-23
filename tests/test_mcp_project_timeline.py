"""project_timeline MCP 工具：蒸馏层 + 记忆检索按主题聚合时间线（跨 AI 迭代视图）。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.automatic_memory.distillation import KnowledgeDistiller
from src.mcp.timeline import build_timeline


class _Settings:
    def __init__(self, memory_db_path: Path) -> None:
        self.memory_db_path = str(memory_db_path)
        self.ollama_base_url = "http://127.0.0.1:11434"
        self.distill_model = ""


def _distiller_with_one_entry(tmp_path: Path) -> KnowledgeDistiller:
    db = tmp_path / "lingji_memory.db"
    db.touch()  # _db_available 检查文件存在；存在才会触发 _ensure_schema
    distiller = KnowledgeDistiller(_Settings(db))
    distiller.list_entries(limit=1)  # 触发 _ensure_schema
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """
            INSERT INTO distilled_knowledge (
                conversation_id, source_id, title, summary, key_points_json, category,
                model, messages_digest, occurred_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "conv-1", "codex:session-abc", "嵌入模型切换",
                "确定了 qwen3-embedding 切换方案，同维度需防混库",
                '["qwen3-embedding:0.6b", "指纹守卫"]', "决策",
                "glm-4-flash", "digest-1",
                "2026-09-20T10:00:00+00:00", "2026-09-20T11:00:00+00:00", "2026-09-21T09:00:00+00:00",
            ),
        )
        conn.commit()
    return distiller


def test_list_entries_exposes_source_id(tmp_path: Path) -> None:
    distiller = _distiller_with_one_entry(tmp_path)
    items = distiller.list_entries(query="嵌入", order="occurred")["items"]
    assert items, "keyword query must hit the distilled entry"
    assert items[0]["source_id"] == "codex:session-abc"


def test_timeline_merges_and_sorts_by_time_desc() -> None:
    distilled = [
        {"occurred_at": "2026-09-20T10:00:00+00:00", "created_at": "2026-09-20T11:00:00+00:00",
         "title": "嵌入切换", "summary": "确定 qwen3 方案", "key_points": ["qwen3"],
         "category": "决策", "source_id": "codex:s1"},
    ]
    memories = [
        {"memory_id": "LJ-MEM-9", "title": "防混库守卫", "text": "同维度换模型必须重建集合",
         "memory_type": "knowledge", "updated_at": "2026-09-22T08:00:00+00:00"},
        {"memory_id": "LJ-MEM-2", "title": "早期记录", "text": "旧 bge-m3 集合",
         "memory_type": "knowledge", "updated_at": "2026-09-19T08:00:00+00:00"},
    ]
    result = build_timeline("嵌入模型", distilled, memories, limit=10, max_chars=6000)
    assert result["total_matches"] == 3
    assert result["returned"] == 3
    assert result["truncated"] is False
    times = [item["occurred_at"] for item in result["items"]]
    assert times == sorted(times, reverse=True), "timeline must be time-descending"
    kinds = [item["kind"] for item in result["items"]]
    assert kinds == ["memory", "distilled", "memory"]
    assert result["items"][1]["source_id"] == "codex:s1"
    assert result["items"][1]["key_points"] == ["qwen3"]
    assert result["items"][0]["source_id"] == "LJ-MEM-9"


def test_timeline_respects_limit_and_char_budget() -> None:
    memories = [
        {"memory_id": f"LJ-MEM-{i}", "title": f"条目 {i}",
         "text": "长" * 400, "memory_type": "knowledge",
         "updated_at": f"2026-09-{i + 1:02d}T00:00:00+00:00"}
        for i in range(9)
    ]
    result = build_timeline("主题", [], memories, limit=2, max_chars=6000)
    assert result["returned"] == 2
    assert result["total_matches"] == 9
    assert result["truncated"] is True

    squeezed = build_timeline("主题", [], memories, limit=20, max_chars=900)
    assert squeezed["truncated"] is True
    total_len = sum(len(str(item["summary"])) + len(str(item["title"])) for item in squeezed["items"])
    assert total_len <= 900, "summary budget must bound total payload"


def test_timeline_snippets_are_normalized_and_capped() -> None:
    memories = [
        {"memory_id": "M1", "title": "标题", "text": "  多  段  空白 \n 内容  " + "尾" * 300,
         "memory_type": "knowledge", "updated_at": "2026-09-01T00:00:00+00:00"},
    ]
    result = build_timeline("主题", [], memories, limit=5, max_chars=6000)
    snippet = result["items"][0]["summary"]
    assert snippet.startswith("多 段 空白 内容")
    assert len(snippet) <= 181 and snippet.endswith("…")
