"""ZCode 活库按会话增量导出（写放大治理，主人 2026-09-29）。

此前每次变化整库拷贝 ~186MB；本套件钉死三件事：
1. 增量导出自包含且与生产适配器 schema 完全兼容；
2. 水位线语义：无新消息不产出、只带触过的会话、回滚即超集（崩安全）；
3. checkpoint 接线：zcode_session 走增量、其他来源行为不变、无新消息零写入。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.automatic_memory.checkpoint import SnapshotJobRunner
from src.automatic_memory.incremental import (
    export_increment,
    load_watermark,
    save_watermark,
)
from src.automatic_memory.models import AuthorizationScope
from src.automatic_memory.snapshot import ConsistentSnapshot
from src.automatic_memory.source_registry import SourceRegistry
from src.extraction.adapters.zcode_session import ZcodeSessionAdapter
from src.extraction.models import ExtractionRequest
from src.extraction.queue import SQLiteExtractionQueue
from src.storage.state_db import StateDatabase


def _build_live_db(path: Path, sessions: list[str]) -> int:
    """构造与生产同构的活库样本，返回 max(message.rowid)。"""
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE session (
            id TEXT PRIMARY KEY, project_id TEXT, workspace_id TEXT, parent_id TEXT,
            slug TEXT, directory TEXT, path TEXT, title TEXT, version TEXT,
            share_url TEXT, time_created INTEGER, time_updated INTEGER
        );
        CREATE TABLE message (
            id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER,
            time_updated INTEGER, data TEXT, sequence INTEGER
        );
        CREATE TABLE part (
            id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT,
            time_created INTEGER, time_updated INTEGER, data TEXT, sequence INTEGER
        );
        """
    )
    clock = 1790000000000
    rid = 0
    for s_index, session_id in enumerate(sessions):
        conn.execute(
            "INSERT INTO session (id, project_id, directory, title, time_created, time_updated) VALUES (?,?,?,?,?,?)",
            (session_id, "proj", "/tmp/proj", f"会话{session_id[:6]}", clock, clock),
        )
        for m_index in range(3):
            rid += 1
            message_id = f"msg-{session_id[-4:]}-{m_index}"
            role = "user" if m_index % 2 == 0 else "assistant"
            conn.execute(
                "INSERT INTO message (id, session_id, time_created, time_updated, data, sequence) VALUES (?,?,?,?,?,?)",
                (
                    message_id,
                    session_id,
                    clock + m_index,
                    clock + m_index,
                    json.dumps({"role": role, "time": {"created": clock + m_index}}),
                    m_index,
                ),
            )
            conn.execute(
                "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data, sequence) VALUES (?,?,?,?,?,?,?)",
                (
                    f"part-{message_id}",
                    message_id,
                    session_id,
                    clock + m_index,
                    clock + m_index,
                    json.dumps({"type": "text", "text": f"会话{session_id[:6]}消息{m_index}"}),
                    1,
                ),
            )
        clock += 10000
    conn.commit()
    conn.close()
    return rid


def _extract(path: Path):
    adapter = ZcodeSessionAdapter()
    request = ExtractionRequest(
        job_id="job-test",
        source_type="zcode_session",
        input_path=path,
        payload={},
    )
    assert adapter.can_handle("zcode_session", path, {})
    return adapter.extract(request)


def test_export_increment_is_selfcontained_and_adapter_compatible(tmp_path: Path) -> None:
    live = tmp_path / "db.sqlite"
    _build_live_db(live, ["sess-aaaa", "sess-bbbb"])
    watermark = load_watermark(tmp_path, "src-1")
    assert watermark == 0

    export = export_increment(live, watermark, tmp_path / "increment.sqlite")
    assert export is not None
    assert export.sessions == 2
    assert export.messages == 6
    assert export.watermark == 6

    batch = _extract(export.path)
    conversations = list(batch.structured_sources[0].conversations)
    assert {item.external_id for item in conversations} == {"sess-aaaa", "sess-bbbb"}
    for conversation in conversations:
        assert len(conversation.messages) == 3
        assert "消息" in conversation.messages[0].content


def test_export_watermark_none_for_unchanged_then_delta(tmp_path: Path) -> None:
    live = tmp_path / "db.sqlite"
    max_rowid = _build_live_db(live, ["sess-cccc"])
    first = export_increment(live, 0, tmp_path / "inc-1.sqlite")
    assert first is not None and first.watermark == max_rowid

    # 无新消息：None，不产生任何文件
    assert export_increment(live, max_rowid, tmp_path / "inc-2.sqlite") is None

    # 旧会话追加消息：增量自包含整个会话（含旧消息），提取投影稳定
    conn = sqlite3.connect(str(live))
    conn.execute(
        "INSERT INTO message (id, session_id, time_created, time_updated, data, sequence) VALUES (?,?,?,?,?,?)",
        ("msg-cccc-new", "sess-cccc", 1790000100000, 1790000100000, json.dumps({"role": "user"}), 9),
    )
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data, sequence) VALUES (?,?,?,?,?,?,?)",
        ("part-msg-cccc-new", "msg-cccc-new", "sess-cccc", 1790000100000, 1790000100000, json.dumps({"type": "text", "text": "新消息"}), 1),
    )
    conn.commit()
    conn.close()

    second = export_increment(live, max_rowid, tmp_path / "inc-3.sqlite")
    assert second is not None and second.sessions == 1
    batch = _extract(second.path)
    conversation = batch.structured_sources[0].conversations[0]
    assert conversation.external_id == "sess-cccc"
    assert len(conversation.messages) == 4, "增量必须自包含整个会话，投影序列才稳定"


def test_watermark_rollback_yields_superset(tmp_path: Path) -> None:
    live = tmp_path / "db.sqlite"
    max_rowid = _build_live_db(live, ["sess-dddd"])
    first = export_increment(live, 0, tmp_path / "inc-1.sqlite")
    assert first is not None

    # 模拟崩溃：raw 已落位但水位线回滚 → 重导出为超集，不丢数据
    save_watermark(tmp_path, "src-1", first.watermark)
    save_watermark(tmp_path, "src-1", 0)
    assert load_watermark(tmp_path, "src-1") == 0

    again = export_increment(live, 0, tmp_path / "inc-2.sqlite")
    assert again is not None and again.messages == first.messages
    assert _extract(again.path).structured_sources[0].conversations


def _register_zcode_source(tmp_path: Path, root: Path):
    state = StateDatabase(tmp_path / "lingji_state.db")
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-zcode-inc",
            source_kinds=("generic_file",),
            roots=(str(root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_file",
        str(root),
    )
    # 测试捷径：注册后把 kind 改为 zcode_session（生产由发现层负责）。
    with sqlite3.connect(str(state.path)) as conn:
        conn.execute(
            "UPDATE automatic_memory_sources SET kind = 'zcode_session' WHERE source_id = ?",
            (source.source_id,),
        )
        conn.commit()
    return state, registry, source


def test_checkpoint_runner_uses_increment_and_zero_writes_when_unchanged(
    tmp_path: Path,
) -> None:
    root = tmp_path / "authorized"
    root.mkdir()
    live_db = root / "db.sqlite"
    max_rowid = _build_live_db(live_db, ["sess-eeee", "sess-ffff"])
    state, registry, source = _register_zcode_source(tmp_path, root)
    raw_root = tmp_path / "storage" / "raw"
    snapshot = ConsistentSnapshot(registry, raw_root)
    queue = SQLiteExtractionQueue(tmp_path / "lingji_state.db")
    runner = SnapshotJobRunner(
        snapshot,
        queue,
        state,
        path_provider=lambda scan, src: [root / "db.sqlite"],
        value_gate_enabled=False,
    )

    scan = registry.start_scan(source.source_id)
    runner.run(scan.scan_id)

    raw_files = [item for item in raw_root.iterdir() if item.is_file()]
    assert raw_files, "增量必须落位 raw"
    # 内容级断言：raw 产物是只含触达会话的小库（而非整库副本）
    for item in raw_files:
        assert item.read_bytes()[:16] == b"SQLite format 3\x00"
        conn = sqlite3.connect(str(item))
        session_count = int(conn.execute("SELECT COUNT(*) FROM session").fetchone()[0])
        message_count = int(conn.execute("SELECT COUNT(*) FROM message").fetchone()[0])
        conn.close()
        assert session_count == 2 and message_count == 6, "增量必须只包含触达会话"
    assert load_watermark(raw_root.parent, source.source_id) == max_rowid
    assert _queued_pending_jobs(state) >= 1

    jobs_before = _queued_pending_jobs(state)
    scan2 = registry.start_scan(source.source_id)
    runner.run(scan2.scan_id)
    assert _queued_pending_jobs(state) == jobs_before, "无新消息的第二轮必须零入队"
    statuses = _scan_item_statuses_for(state, scan2.scan_id)
    assert "no_increment" in statuses, "无新消息必须显式记为 no_increment，不得伪装 queued"


def _queued_pending_jobs(state: StateDatabase) -> int:
    with sqlite3.connect(str(state.path)) as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM extraction_jobs WHERE status IN ('queued','completed')"
            ).fetchone()[0]
        )


def _scan_item_statuses_for(state: StateDatabase, scan_id: str) -> list[str]:
    with sqlite3.connect(str(state.path)) as conn:
        return [
            str(row[0])
            for row in conn.execute(
                "SELECT status FROM automatic_memory_scan_items WHERE scan_id = ?",
                (scan_id,),
            )
        ]
