"""Regression tests for the evidence-layer value gate (主人 2026-09-28 拍板).

价值门从 intake 延伸到证据入库：轮数与字数双低且无价值信号的会话，其证据
不物化；已物化的在下一轮 sync 归档（invalidating_reason=
value_gate_below_floor）。红线：证据行与 FTS 全文保留绝不物理删除；阈值
放宽后同一内容寻址文档经 status 漂移自动重新激活；一切计数进返回值。
"""

from __future__ import annotations

import json
from pathlib import Path

from src.retrieval.memory_db import MemoryDatabase

_GATE_OFF = {"enabled": False, "min_turns": 2, "min_chars": 300}
_GATE_ON = {"enabled": True, "min_turns": 2, "min_chars": 300}


def _seed_conversation(
    db: MemoryDatabase,
    *,
    source_id: str,
    conversation_id: str,
    messages: list[str],
    source_status: str = "active",
) -> None:
    with db._connection() as conn:
        conn.execute(
            """
            INSERT INTO source_records(source_id, external_id, display_name, source_type, status, content_hash, created_at, updated_at)
            VALUES (?, ?, ?, 'generic_ai_history', ?, 'seed-hash', '2026-09-27T00:00:00Z', '2026-09-27T00:00:00Z')
            ON CONFLICT(source_id) DO UPDATE SET status = excluded.status
            """,
            (source_id, source_id, f"来源 {source_id}", source_status),
        )
        conn.execute(
            """
            INSERT INTO conversation_records(conversation_id, external_id, source_id, title, content_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'seed-hash', '2026-09-27T00:00:00Z', '2026-09-27T00:00:00Z')
            ON CONFLICT(conversation_id) DO UPDATE SET title = excluded.title
            """,
            (conversation_id, conversation_id, source_id, f"会话 {conversation_id}"),
        )
        for index, content in enumerate(messages):
            message_id = f"{conversation_id}-m{index}"
            conn.execute(
                """
                INSERT INTO message_records(
                    message_id, conversation_id, source_id, external_id, role, author,
                    occurred_at, sequence, content, content_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'user', '', '2026-09-27T00:00:00Z', ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET content = excluded.content,
                    content_hash = excluded.content_hash, updated_at = excluded.updated_at
                """,
                (
                    message_id,
                    conversation_id,
                    source_id,
                    message_id,
                    index,
                    content,
                    db._content_fallback_hash(content),
                    "2026-09-27T00:00:00Z",
                    "2026-09-27T00:00:00Z",
                ),
            )
        conn.commit()


def _db(tmp_path: Path) -> MemoryDatabase:
    # read model 的 source/conversation/message 表与 memory_db 的投影表在
    # 同一个库（生产布局）；构造 SourceReadModel 触发其 schema 初始化。
    from src.sources.read_model import SourceReadModel

    path = tmp_path / "lingji_memory.db"
    SourceReadModel(path)
    return MemoryDatabase(path)


def _active_evidence_ids(db: MemoryDatabase) -> set[str]:
    with db._connection() as conn:
        return {
            str(row[0])
            for row in conn.execute(
                "SELECT memory_id FROM memory_documents "
                "WHERE memory_type = 'structured_evidence' AND status = 'active'"
            )
        }


def test_low_value_session_never_materializes(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed_conversation(db, source_id="src-a", conversation_id="conv-tiny", messages=["你好"])
    result = db.sync_structured_evidence(value_gate=_GATE_ON)
    assert result["added"] == 0
    assert result["value_gate_conversations"] == 1
    assert result["value_gate_skipped_messages"] == 1
    assert _active_evidence_ids(db) == set()


def test_value_signal_session_survives(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed_conversation(
        db,
        source_id="src-a",
        conversation_id="conv-signal",
        messages=["拍板：部署方案 A，今天上线"],
    )
    result = db.sync_structured_evidence(value_gate=_GATE_ON)
    assert result["added"] == 1
    assert result["value_gate_conversations"] == 0


def test_long_session_survives_even_without_signals(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed_conversation(
        db,
        source_id="src-a",
        conversation_id="conv-long",
        messages=["字" * 200, "字" * 200],
    )
    result = db.sync_structured_evidence(value_gate=_GATE_ON)
    assert result["added"] == 2
    assert result["value_gate_conversations"] == 0


def test_already_materialized_low_value_evidence_is_archived_not_deleted(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed_conversation(db, source_id="src-a", conversation_id="conv-tiny", messages=["你好"])
    db.sync_structured_evidence(value_gate=_GATE_OFF)  # 先在门禁关闭下物化
    active_before = _active_evidence_ids(db)
    assert len(active_before) == 1

    result = db.sync_structured_evidence(value_gate=_GATE_ON)
    assert result["value_gate_archived"] == 1
    assert _active_evidence_ids(db) == set()
    with db._connection() as conn:
        row = conn.execute(
            "SELECT status, relationships_json FROM memory_documents WHERE memory_id = ?",
            (next(iter(active_before)),),
        ).fetchone()
    assert str(row["status"]) == "archived"
    assert "value_gate_below_floor" in str(row["relationships_json"])
    # FTS 全文保留：证据行没有被物理删除。
    with db._connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM memory_documents WHERE memory_id = ?",
            (next(iter(active_before)),),
        ).fetchone()[0]
    assert count == 1


def test_relaxed_threshold_reactivates_archived_evidence(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed_conversation(db, source_id="src-a", conversation_id="conv-tiny", messages=["你好"])
    db.sync_structured_evidence(value_gate=_GATE_ON)
    assert _active_evidence_ids(db) == set()
    relaxed = {"enabled": True, "min_turns": 1, "min_chars": 1}
    result = db.sync_structured_evidence(value_gate=relaxed)
    assert result["added"] == 1
    assert len(_active_evidence_ids(db)) == 1


def test_gate_off_keeps_legacy_full_materialization(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed_conversation(db, source_id="src-a", conversation_id="conv-tiny", messages=["你好"])
    result = db.sync_structured_evidence(value_gate=_GATE_OFF)
    assert result["added"] == 1
    assert result["value_gate_conversations"] == 0
    assert result["value_gate_archived"] == 0


def test_counts_meta_reflects_active_only(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _seed_conversation(db, source_id="src-a", conversation_id="conv-tiny", messages=["你好"])
    db.sync_structured_evidence(value_gate=_GATE_OFF)
    _seed_conversation(db, source_id="src-b", conversation_id="conv-tiny-2", messages=["早"])
    db.sync_structured_evidence(value_gate=_GATE_ON)  # 归档 src-a 会话证据
    with db._connection() as conn:
        documents = int(conn.execute(
            "SELECT value FROM memory_meta WHERE key = 'structured_evidence_document_count'"
        ).fetchone()[0])
        archived = conn.execute(
            "SELECT COUNT(*) FROM memory_documents "
            "WHERE memory_type = 'structured_evidence' AND status = 'archived'"
        ).fetchone()[0]
    assert documents + archived >= 1
    assert documents == len(_active_evidence_ids(db)), "count meta 必须是 active 口径"
