from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from src.codex_sessions import sanitize_value

from ..base import ExtractionAdapter
from ..models import (
    ExtractionBatch,
    ExtractionRequest,
    StructuredConversation,
    StructuredMessage,
    StructuredSource,
)

_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


class CodexSessionAdapter(ExtractionAdapter):
    name = "codex_session"
    version = "1.0.0"
    source_types = ("codex_session",)

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        del input_path
        return source_type in self.source_types and isinstance(payload.get("session"), Mapping)

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        session = sanitize_value(dict(request.payload.get("session") or {}))
        events = [
            sanitize_value(dict(item))
            for item in (request.payload.get("events") or [])
            if isinstance(item, Mapping)
        ]
        project_id = str(session.get("project_id") or "")
        session_id = str(session.get("session_id") or "")
        if not project_id or not session_id:
            raise ValueError("Codex session project_id and session_id are required")
        raw_reference = str(
            request.payload.get("raw_reference")
            or session.get("raw_reference")
            or f"raw:codex/sessions/{project_id}/{session_id}.jsonl"
        )
        messages = tuple(self._message(item, raw_reference) for item in sorted(events, key=self._sequence))
        conversation = StructuredConversation(
            external_id=session_id,
            title=str(session.get("title") or session.get("task") or "Codex session"),
            messages=messages,
            started_at=str(session.get("created_at") or ""),
            ended_at=str(session.get("ended_at") or ""),
            participants=("owner", "codex"),
            privacy=str(session.get("privacy") or "private"),
            projects=(project_id,),
            agent_scope=("codex", "lingji-local"),
            metadata={
                "branch": str(session.get("branch") or ""),
                "raw_reference": raw_reference,
                "worktree_name": str(session.get("worktree_name") or ""),
                "status": str(session.get("status") or "active"),
                "external_session_id": str(session.get("external_session_id") or ""),
                "message_count": len(messages),
            },
        )
        source = StructuredSource(
            source_type="codex_session",
            external_id=f"codex:{project_id}",
            display_name=f"Codex · {str(session.get('project_name') or project_id)}",
            conversations=(conversation,),
            privacy=str(session.get("privacy") or "private"),
            projects=(project_id,),
            agent_scope=("codex", "lingji-local"),
            status="active",
            metadata={
                "repository": str(session.get("repository") or ""),
                "raw_reference": raw_reference,
                "adapter_name": self.name,
                "adapter_version": self.version,
            },
        )
        return ExtractionBatch(
            documents=(),
            structured_sources=(source,),
            summary={
                "project_id": project_id,
                "session_id": session_id,
                "events": len(messages),
                "raw_reference": raw_reference,
            },
        )

    def _message(self, event: Mapping[str, Any], raw_reference: str) -> StructuredMessage:
        event_type = str(event.get("event_type") or "checkpoint")
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        metadata = {
            "checkpoint_kind": event_type,
            "branch": str(payload.get("branch") or ""),
            "worktree_name": str(payload.get("worktree_name") or ""),
            "changed_files": self._safe_paths(payload.get("changed_files")),
            "commits": self._items(payload.get("commits")),
            "test_status": self._test_status(payload.get("tests")),
            "blockers": self._items(payload.get("blockers")),
            "content_hash": str(event.get("content_hash") or ""),
        }
        return StructuredMessage(
            external_id=str(event.get("event_id") or ""),
            role=self._role(event_type, payload),
            author=str(payload.get("author") or "codex"),
            occurred_at=str(event.get("occurred_at") or ""),
            sequence=int(event.get("sequence") or 0),
            content=self._content(str(event.get("summary") or ""), payload),
            projects=(str(event.get("project_id") or ""),),
            agent_scope=("codex", "lingji-local"),
            raw_reference=raw_reference,
            metadata=metadata,
        )

    @staticmethod
    def _content(summary: str, payload: Mapping[str, Any]) -> str:
        parts = [summary.strip()] if summary.strip() else []
        for key in (
            "changed_files",
            "tests",
            "decisions",
            "blockers",
            "next_steps",
            "commits",
            "remaining_tasks",
        ):
            value = payload.get(key)
            if value not in (None, "", [], (), {}):
                parts.append(f"{key}: {json.dumps(value, ensure_ascii=False, sort_keys=True)}")
        return "\n".join(parts) or "Codex session event"

    @staticmethod
    def _role(event_type: str, payload: Mapping[str, Any]) -> str:
        explicit = str(payload.get("role") or "").lower()
        if explicit in {"owner", "assistant", "tool", "system"}:
            return explicit
        return {
            "session_started": "owner",
            "checkpoint": "assistant",
            "decision": "assistant",
            "test_result": "tool",
            "blocker": "assistant",
            "session_closed": "assistant",
        }.get(event_type, "system")

    @staticmethod
    def _sequence(event: Mapping[str, Any]) -> tuple[int, str]:
        return int(event.get("sequence") or 0), str(event.get("event_id") or "")

    @classmethod
    def _safe_paths(cls, value: Any) -> list[str]:
        result = []
        for item in cls._items(value):
            text = str(item).replace("\\", "/")
            if text.startswith("/") or _WINDOWS_ABSOLUTE.match(text):
                text = text.rstrip("/").rsplit("/", 1)[-1]
            result.append(text)
        return result

    @staticmethod
    def _items(value: Any) -> list[Any]:
        if value in (None, "", [], (), {}):
            return []
        if isinstance(value, (list, tuple, set)):
            return [sanitize_value(item) for item in value]
        return [sanitize_value(value)]

    @staticmethod
    def _test_status(value: Any) -> str:
        if isinstance(value, Mapping):
            return str(value.get("status") or value.get("result") or "")
        if isinstance(value, str):
            return value[:120]
        return ""
