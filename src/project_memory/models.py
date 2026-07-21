from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ProjectContextPack:
    agent_id: str
    project_id: str
    session_id: str = ""
    max_chars: int = 18000
    core_memories: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    active_tasks: list[dict[str, Any]] = field(default_factory=list)
    recent_sessions: list[dict[str, Any]] = field(default_factory=list)
    related_messages: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    markdown: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema_version"] = 1
        payload["used_chars"] = len(self.markdown)
        return payload


def stable_citation(item: dict[str, Any]) -> dict[str, str] | None:
    citation = {
        key: str(item.get(key) or "")
        for key in ("memory_id", "source_id", "conversation_id", "message_id", "relative_path")
    }
    return citation if any(citation.values()) else None
