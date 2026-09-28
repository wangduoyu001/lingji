"""Regression tests for the no-key-content distillation skip (主人 2026-09-28 原则).

不为记忆而记忆：模型按提示词明确返回空产出时，会话落 ``no_key_content``
终态出队（不重试、不计失败），消息数变化后自动复活重新提炼。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.automatic_memory.distillation import KnowledgeDistiller

from tests.test_automatic_memory_distillation import (
    _OllamaHandler,
    _distiller,
    _seed_memory_db,
    ollama_server,  # noqa: F401  (fixture)
)

_DEFAULT_PAYLOAD = dict(_OllamaHandler.payload)


@pytest.fixture(autouse=True)
def _restore_stub_payload():
    """payload 是类属性：用后必须恢复，否则污染同进程的后续测试文件。"""
    yield
    _OllamaHandler.payload = dict(_DEFAULT_PAYLOAD)


def _row(path: Path, conversation_id: str) -> sqlite3.Row:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "SELECT * FROM distilled_knowledge WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
    finally:
        conn.close()


def test_empty_yield_lands_terminal_state_and_stops_retrying(tmp_path, ollama_server):
    _OllamaHandler.payload = {"summary": "", "key_points": [], "category": "其他"}
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    distiller = _distiller(tmp_path, ollama_server)

    result = distiller.run_once(limit=10)

    assert result["status"] == "ok"
    assert result["distilled"] == 0
    assert result["skipped_no_key_content"] == 2
    row = _row(memory_db, "conv-1")
    assert str(row["status"]) == "no_key_content"
    assert str(row["messages_digest"]) != "", "终态行必须记录内容指纹以支撑复活"
    # 下一轮不再重试同一会话（无 pending、无模型调用）。
    again = distiller.run_once(limit=10)
    assert again["distilled"] == 0
    assert again["pending"] == 0


def test_new_messages_revive_a_skipped_conversation(tmp_path, ollama_server):
    _OllamaHandler.payload = {"summary": "", "key_points": [], "category": "其他"}
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    distiller = _distiller(tmp_path, ollama_server)
    distiller.run_once(limit=10)
    assert _row(memory_db, "conv-1")["status"] == "no_key_content"

    # 会话出现新消息：message_count 变化必须让它复活，且这次有关键内容就入库。
    conn = sqlite3.connect(str(memory_db))
    conn.execute(
        "INSERT INTO message_records(message_id, conversation_id, role, content, content_hash, occurred_at)"
        " VALUES ('conv-1-new', 'conv-1', 'user', '拍板：上线方案 A', 'revive-hash', '2026-09-28T00:00:00Z')"
    )
    conn.execute(
        "UPDATE conversation_records SET message_count = message_count + 1 WHERE conversation_id = 'conv-1'"
    )
    conn.commit()
    conn.close()

    _OllamaHandler.payload = {
        "summary": "拍板上线方案 A",
        "key_points": ["方案 A 已拍板上线"],
        "category": "决策",
    }
    result = distiller.run_once(limit=10)
    assert result["distilled"] == 1
    row = _row(memory_db, "conv-1")
    assert str(row["status"]) == "ready"
    assert "方案 A" in str(row["summary"])


def test_summary_with_empty_points_still_lands(tmp_path, ollama_server):
    # summary 非空但要点为空：有一句话结论就算产出，不得误跳过。
    _OllamaHandler.payload = {"summary": "确认了部署窗口", "key_points": [], "category": "决策"}
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    distiller = _distiller(tmp_path, ollama_server)

    result = distiller.run_once(limit=10)

    assert result["distilled"] == 2
    assert result["skipped_no_key_content"] == 0
    assert str(_row(memory_db, "conv-1")["status"]) == "ready"


def test_unparseable_output_still_counts_as_failure(tmp_path, ollama_server):
    # 解析失败≠合法空产出：失败语义保持，会话保留重试资格。
    _OllamaHandler.payload = {"nonsense": True}
    memory_db = tmp_path / "lingji_memory.db"
    _seed_memory_db(memory_db)
    distiller = _distiller(tmp_path, ollama_server)

    result = distiller.run_once(limit=10)

    assert result["failed"] == 2
    assert result["skipped_no_key_content"] == 0
    assert str(_row(memory_db, "conv-1")["status"]) == "failed"
