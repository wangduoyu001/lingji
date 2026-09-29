"""Per-session incremental export for the ZCode CLI database.

写放大治理（主人 2026-09-29：大量硬盘写入必须优化）。此前 ZCode 活库每变化
一次就整库拷贝一份（~186MB/次，重会话日 2GB+），而单个周期真正新增的往往
只有几条消息。本模块用只读 WAL 连接导出「自水位线以来有新消息的会话」
（整个会话自包含），写成与生产适配器 schema 完全一致的小型 SQLite 增量库，
下游 ``ZcodeSessionAdapter`` 零改动直接消费。

崩溃安全：水位线只在增量文件完成 raw 落位并入队后才由调用方提交；任何一步
失败，下一轮导出的是上一轮的超集，提取按内容哈希幂等，绝不丢数据。文本部
件（type="text"）之外的部分（工具输出等）不导出——适配器只读文本部件。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_BYTES = 512 * 1024 * 1024

_SESSION_SCHEMA = """
CREATE TABLE session (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    directory TEXT,
    title TEXT,
    time_created INTEGER,
    time_updated INTEGER
)
"""

_MESSAGE_SCHEMA = """
CREATE TABLE message (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    time_created INTEGER,
    time_updated INTEGER,
    data TEXT,
    sequence INTEGER
)
"""

_PART_SCHEMA = """
CREATE TABLE part (
    id TEXT PRIMARY KEY,
    message_id TEXT,
    data TEXT,
    sequence INTEGER
)
"""


@dataclass(frozen=True)
class IncrementExport:
    path: Path
    watermark: int
    sessions: int
    messages: int
    bytes_written: int


def watermark_path(storage_path: Path, source_id: str) -> Path:
    return Path(storage_path) / "automatic_memory_watermarks" / f"{source_id}.json"


def load_watermark(storage_path: Path, source_id: str) -> int:
    path = watermark_path(storage_path, source_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return max(int(payload.get("watermark") or 0), 0)
    except (OSError, ValueError, TypeError):
        return 0


def save_watermark(storage_path: Path, source_id: str, watermark: int) -> None:
    path = watermark_path(storage_path, source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".json.tmp")
    temp.write_text(
        json.dumps({"watermark": int(watermark)}, ensure_ascii=False),
        encoding="utf-8",
    )
    temp.replace(path)


def export_increment(
    db_path: Path,
    watermark: int,
    out_path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> IncrementExport | None:
    """导出自 ``watermark`` 以来有新消息的会话为自包含 SQLite 增量库。

    返回 ``None`` 表示没有新消息（无需采集）。超过 ``max_bytes`` 时抛
    ``ValueError``，调用方回退整库快照路径，绝不截断数据。
    """
    live = sqlite3.connect(
        f"file:{Path(db_path).as_uri()[len('file:'):]}?mode=ro", uri=True, timeout=15
    )
    live.row_factory = sqlite3.Row
    try:
        live.execute("PRAGMA query_only=1")
        rows = live.execute(
            """
            SELECT m.rowid AS rid, m.id AS message_id, m.session_id AS session_id
            FROM message m
            WHERE m.rowid > ?
            ORDER BY m.rowid ASC
            """,
            (int(watermark),),
        ).fetchall()
        if not rows:
            return None
        new_watermark = int(rows[-1]["rid"])
        touched: list[str] = []
        seen: set[str] = set()
        for row in rows:
            session_id = str(row["session_id"] or "")
            if session_id and session_id not in seen:
                seen.add(session_id)
                touched.append(session_id)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        temp = out_path.with_name(out_path.name + ".build")
        if temp.exists():
            temp.unlink()
        increment = sqlite3.connect(str(temp))
        increment.row_factory = sqlite3.Row
        try:
            increment.execute(_SESSION_SCHEMA)
            increment.execute(_MESSAGE_SCHEMA)
            increment.execute(_PART_SCHEMA)
            message_count = 0
            for session_id in touched:
                session_row = live.execute(
                    """
                    SELECT id, project_id, directory, title, time_created, time_updated
                    FROM session WHERE id = ?
                    """,
                    (session_id,),
                ).fetchone()
                if session_row is not None:
                    increment.execute(
                        "INSERT INTO session (id, project_id, directory, title, time_created, time_updated) VALUES (?,?,?,?,?,?)",
                        (
                            session_row["id"],
                            session_row["project_id"],
                            session_row["directory"],
                            session_row["title"],
                            session_row["time_created"],
                            session_row["time_updated"],
                        ),
                    )
                messages = live.execute(
                    """
                    SELECT id, session_id, time_created, time_updated, data, sequence
                    FROM message WHERE session_id = ? ORDER BY rowid ASC
                    """,
                    (session_id,),
                ).fetchall()
                for message in messages:
                    increment.execute(
                        "INSERT INTO message (id, session_id, time_created, time_updated, data, sequence) VALUES (?,?,?,?,?,?)",
                        (
                            message["id"],
                            message["session_id"],
                            message["time_created"],
                            message["time_updated"],
                            message["data"],
                            message["sequence"],
                        ),
                    )
                    message_count += 1
                parts = live.execute(
                    """
                    SELECT p.id AS part_id, p.message_id AS message_id, p.data AS data, p.sequence AS sequence
                    FROM part p JOIN message m ON p.message_id = m.id
                    WHERE m.session_id = ? AND json_extract(p.data, '$.type') = 'text'
                    ORDER BY p.id ASC
                    """,
                    (session_id,),
                ).fetchall()
                for part in parts:
                    increment.execute(
                        "INSERT INTO part (id, message_id, data, sequence) VALUES (?,?,?,?)",
                        (part["part_id"], part["message_id"], part["data"], part["sequence"]),
                    )
            increment.commit()
        finally:
            increment.close()

        size = temp.stat().st_size
        if size > int(max_bytes):
            temp.unlink(missing_ok=True)
            raise ValueError(
                f"zcode increment exceeds size limit ({size}/{int(max_bytes)} bytes)"
            )
        temp.replace(out_path)
        return IncrementExport(
            path=Path(out_path),
            watermark=new_watermark,
            sessions=len(touched),
            messages=message_count,
            bytes_written=size,
        )
    finally:
        live.close()
