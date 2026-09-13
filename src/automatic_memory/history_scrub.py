"""历史数据清洗：对脱敏功能上线前入库的存量内容重跑脱敏（主人红线）。

清洗范围：message_records.content、conversation_records.title、
distilled_knowledge.summary/key_points_json。随后重建结构化证据投影
（记忆块+FTS），并按调用方指示删除受影响消息的向量点（回填自动重嵌入）。

幂等：重复执行第二遍 0 变更。
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.extraction.privacy import PrivacyClassifier


@dataclass
class ScrubReport:
    messages_changed: int = 0
    titles_changed: int = 0
    distilled_changed: int = 0
    changed_message_ids: list[str] | None = None


class HistoryScrubber:
    def __init__(self, settings: Any):
        self.memory_db_path = Path(str(getattr(settings, "memory_db_path", "") or ""))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.memory_db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def scrub(self, batch: int = 500) -> ScrubReport:
        if not self.memory_db_path.exists():
            return ScrubReport()
        redactor = PrivacyClassifier()
        report = ScrubReport(changed_message_ids=[])
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            # 1) 消息正文
            changed: list[tuple[str, str]] = []
            for row in conn.execute(
                "SELECT message_id, content FROM message_records ORDER BY message_id"
            ).fetchall():
                clean = redactor.redact(str(row["content"] or ""))
                if clean != str(row["content"] or ""):
                    changed.append((str(row["message_id"]), clean))
                    if len(changed) >= max(batch, 1):
                        conn.executemany(
                            "UPDATE message_records SET content = ? WHERE message_id = ?",
                            [(clean, mid) for mid, clean in changed],
                        )
                        report.changed_message_ids.extend(mid for mid, _ in changed)
                        report.messages_changed += len(changed)
                        changed = []
            if changed:
                conn.executemany(
                    "UPDATE message_records SET content = ? WHERE message_id = ?",
                    [(clean, mid) for mid, clean in changed],
                )
                report.changed_message_ids.extend(mid for mid, _ in changed)
                report.messages_changed += len(changed)

            # 2) 会话标题
            for row in conn.execute(
                "SELECT conversation_id, title FROM conversation_records"
            ).fetchall():
                clean = redactor.redact(str(row["title"] or ""))
                if clean != str(row["title"] or ""):
                    conn.execute(
                        "UPDATE conversation_records SET title = ? WHERE conversation_id = ?",
                        (clean, str(row["conversation_id"])),
                    )
                    report.titles_changed += 1

            # 3) 提炼产物（总结 + 要点）
            for row in conn.execute(
                "SELECT conversation_id, summary, key_points_json FROM distilled_knowledge"
            ).fetchall():
                summary = redactor.redact(str(row["summary"] or ""))
                try:
                    points = json.loads(str(row["key_points_json"] or "[]"))
                except json.JSONDecodeError:
                    points = []
                clean_points = [redactor.redact(str(point)) for point in points]
                clean_json = json.dumps(clean_points, ensure_ascii=False)
                if summary != str(row["summary"] or "") or clean_json != str(row["key_points_json"] or ""):
                    conn.execute(
                        "UPDATE distilled_knowledge SET summary = ?, key_points_json = ? WHERE conversation_id = ?",
                        (summary, clean_json, str(row["conversation_id"])),
                    )
                    report.distilled_changed += 1
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()
        return report
