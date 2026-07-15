from __future__ import annotations

from second_brain.db import Database
from second_brain.memory.service import MemoryService


RULE_MARKERS = ("必须", "不要", "以后", "从现在开始", "以这个为准", "不再使用", "改成")
DECISION_MARKERS = ("最终决定", "确定", "采用", "选择", "就按")
PREFERENCE_MARKERS = ("我喜欢", "我不喜欢", "我希望", "我的习惯")
TASK_MARKERS = ("待办", "下一步", "需要做", "记得")


class DistillationService:
    """Creates review candidates. It never auto-activates model guesses."""

    def __init__(self, database: Database, memories: MemoryService):
        self.database = database
        self.memories = memories

    def distill(self, conversation_id: str | None = None, source_id: str | None = None) -> list[dict]:
        clauses = ["msg.role='user'"]
        params: list[str] = []
        if conversation_id:
            clauses.append("msg.conversation_id=?")
            params.append(conversation_id)
        if source_id:
            clauses.append("c.source_id=?")
            params.append(source_id)
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""SELECT msg.content, c.project_id, p.name AS project, c.source_id
                FROM messages msg
                JOIN conversations c ON c.id=msg.conversation_id
                LEFT JOIN projects p ON p.id=c.project_id
                WHERE {' AND '.join(clauses)} ORDER BY msg.ordinal""",
                params,
            ).fetchall()
        candidates: list[dict] = []
        for row in rows:
            for text in self._segments(row["content"]):
                memory_type = self._classify(text)
                if memory_type is None:
                    continue
                memory, created = self.memories.create(
                    memory_type=memory_type,
                    title=text[:60],
                    content=text,
                    project=row["project"] or "global",
                    status="pending",
                    importance=0.7,
                    confidence=0.7,
                    source_id=row["source_id"],
                    source_excerpt=text,
                )
                if created:
                    candidates.append(memory)
        return candidates

    @staticmethod
    def _segments(content: str) -> list[str]:
        normalized = content.replace("。", "。\n").replace("；", "；\n")
        return [line.strip(" -\t") for line in normalized.splitlines() if 8 <= len(line.strip()) <= 1000]

    @staticmethod
    def _classify(text: str) -> str | None:
        if any(marker in text for marker in RULE_MARKERS):
            return "RULE"
        if any(marker in text for marker in DECISION_MARKERS):
            return "DECISION"
        if any(marker in text for marker in PREFERENCE_MARKERS):
            return "PREFERENCE"
        if any(marker in text for marker in TASK_MARKERS):
            return "TASK"
        return None
