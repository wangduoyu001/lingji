from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from typing import Any, Mapping


CODEX_SESSION_NOT_FOUND = "CODEX_SESSION_NOT_FOUND"
CODEX_SESSION_ALREADY_CLOSED = "CODEX_SESSION_ALREADY_CLOSED"
CODEX_EVENT_DUPLICATE = "CODEX_EVENT_DUPLICATE"
CODEX_EVENT_INVALID = "CODEX_EVENT_INVALID"
CODEX_ARCHIVE_UNAVAILABLE = "CODEX_ARCHIVE_UNAVAILABLE"
CODEX_INGESTION_FAILED = "CODEX_INGESTION_FAILED"

_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "password",
    "secret",
    "authorization",
    "cookie",
    "private_key",
    "privatekey",
}
_SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{6,}\b", re.IGNORECASE),
    re.compile(r"\bBearer\s+[^\s,;]+", re.IGNORECASE),
    re.compile(
        r"\b(api[_-]?key|token|password|secret|authorization|cookie|private[_-]?key)\s*[:=]\s*[^\s,;]+",
        re.IGNORECASE,
    ),
)


class CodexSessionError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class CodexSessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class CodexEventType(str, Enum):
    SESSION_STARTED = "session_started"
    CHECKPOINT = "checkpoint"
    DECISION = "decision"
    TEST_RESULT = "test_result"
    BLOCKER = "blocker"
    SESSION_CLOSED = "session_closed"


@dataclass(frozen=True)
class CodexSessionEvent:
    event_id: str
    session_id: str
    project_id: str
    event_type: CodexEventType
    occurred_at: str
    sequence: int
    summary: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    content_hash: str = ""

    def with_sequence(self, sequence: int) -> "CodexSessionEvent":
        return replace(self, sequence=sequence)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["payload"] = sanitize_value(dict(self.payload))
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CodexSessionEvent":
        return cls(
            event_id=str(data.get("event_id") or ""),
            session_id=str(data.get("session_id") or ""),
            project_id=str(data.get("project_id") or ""),
            event_type=CodexEventType(str(data.get("event_type") or "checkpoint")),
            occurred_at=str(data.get("occurred_at") or ""),
            sequence=int(data.get("sequence") or 0),
            summary=str(data.get("summary") or ""),
            payload=sanitize_value(data.get("payload") or {}),
            content_hash=str(data.get("content_hash") or ""),
        )


@dataclass(frozen=True)
class CodexCheckpoint:
    event_id: str
    kind: CodexEventType
    summary: str
    changed_files: tuple[str, ...] = ()
    tests: tuple[Any, ...] = ()
    decisions: tuple[Any, ...] = ()
    blockers: tuple[Any, ...] = ()
    next_steps: tuple[Any, ...] = ()
    branch: str = ""
    commits: tuple[str, ...] = ()


@dataclass(frozen=True)
class CodexSession:
    session_id: str
    project_id: str
    project_name: str
    repository: str
    title: str
    task: str
    status: CodexSessionStatus
    created_at: str
    updated_at: str
    branch: str = ""
    worktree_name: str = ""
    external_session_id: str = ""
    ended_at: str = ""
    raw_reference: str = ""
    event_count: int = 0
    remaining_tasks: tuple[Any, ...] = ()
    memory_candidates_suggested: tuple[Any, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "repository": self.repository,
            "title": self.title,
            "task": self.task,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ended_at": self.ended_at,
            "branch": self.branch,
            "worktree_name": self.worktree_name,
            "external_session_id": self.external_session_id,
            "raw_reference": self.raw_reference,
            "event_count": self.event_count,
            "remaining_tasks": list(self.remaining_tasks),
            "memory_candidates_suggested": list(self.memory_candidates_suggested),
        }


def sanitize_value(value: Any, *, key: str = "") -> Any:
    normalized_key = re.sub(r"[^a-z0-9_]", "", str(key).lower())
    if normalized_key in _SENSITIVE_KEYS or any(item in normalized_key for item in _SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(item_key): sanitize_value(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_value(item) for item in value]
    if isinstance(value, str):
        result = value
        for pattern in _SECRET_VALUE_PATTERNS:
            result = pattern.sub(_redacted_match, result)
        return result
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def event_content_hash(
    *,
    session_id: str,
    project_id: str,
    event_type: CodexEventType,
    summary: str,
    payload: Mapping[str, Any],
) -> str:
    material = {
        "session_id": session_id,
        "project_id": project_id,
        "event_type": event_type.value,
        "summary": sanitize_value(summary),
        "payload": sanitize_value(dict(payload)),
    }
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _redacted_match(match: re.Match[str]) -> str:
    value = match.group(0)
    if value.lower().startswith("bearer"):
        return "Bearer [REDACTED]"
    if value.lower().startswith("sk-"):
        return "sk-[REDACTED]"
    key = value.split(":", 1)[0].split("=", 1)[0]
    return f"{key}=[REDACTED]"
