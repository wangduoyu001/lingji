from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .models import (
    CODEX_ARCHIVE_UNAVAILABLE,
    CODEX_SESSION_NOT_FOUND,
    CodexSession,
    CodexSessionError,
    CodexSessionEvent,
    CodexSessionStatus,
)

logger = logging.getLogger("lingji.codex_sessions.archive")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class AppendResult:
    event: CodexSessionEvent
    added: bool
    duplicate_event_id: bool = False
    duplicate_content_event_id: str = ""


class CodexSessionArchive:
    """The single raw JSONL fact source for Codex session events."""

    def __init__(self, storage_path: Path | str):
        self.storage_path = Path(storage_path)
        self.root = self.storage_path / "raw" / "codex" / "sessions"
        self._locks_guard = threading.RLock()
        self._locks: dict[str, threading.RLock] = {}

    def raw_reference(self, project_id: str, session_id: str) -> str:
        self._validate_id(project_id)
        self._validate_id(session_id)
        return f"raw:codex/sessions/{project_id}/{session_id}.jsonl"

    def append(self, event: CodexSessionEvent) -> AppendResult:
        path = self._path(event.project_id, event.session_id)
        lock = self._lock_for(path)
        with lock:
            events = self._read_path(path)
            for existing in events:
                if existing.event_id == event.event_id:
                    return AppendResult(existing, added=False, duplicate_event_id=True)
            sequence = max((item.sequence for item in events), default=0) + 1
            normalized = event.with_sequence(sequence)
            duplicate_content = next(
                (item.event_id for item in events if item.content_hash == normalized.content_hash),
                "",
            )
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(json.dumps(normalized.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                logger.exception("Codex session archive append failed")
                raise CodexSessionError(
                    CODEX_ARCHIVE_UNAVAILABLE,
                    "Codex session archive is unavailable; see local logs",
                    status_code=503,
                ) from exc
            return AppendResult(
                normalized,
                added=True,
                duplicate_content_event_id=duplicate_content,
            )

    def read_events(self, project_id: str, session_id: str) -> list[CodexSessionEvent]:
        return self._read_path(self._path(project_id, session_id))

    def get_session(self, session_id: str) -> tuple[CodexSession, list[CodexSessionEvent]]:
        path = self._find_session_path(session_id)
        events = self._read_path(path)
        if not events:
            raise CodexSessionError(
                CODEX_SESSION_NOT_FOUND,
                "Codex session not found",
                status_code=404,
            )
        return self._session_from_events(events), events

    def list_sessions(
        self,
        *,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        selected_limit = max(min(int(limit), 200), 1)
        selected_offset = max(int(offset), 0)
        paths: Iterable[Path]
        if project_id:
            self._validate_id(project_id)
            paths = (self.root / project_id).glob("*.jsonl") if (self.root / project_id).exists() else ()
        else:
            paths = self.root.glob("*/*.jsonl") if self.root.exists() else ()
        sessions: list[CodexSession] = []
        for path in paths:
            events = self._read_path(path)
            if not events:
                continue
            session = self._session_from_events(events)
            if status and session.status.value != status:
                continue
            sessions.append(session)
        sessions.sort(key=lambda item: (item.updated_at, item.session_id), reverse=True)
        page = sessions[selected_offset : selected_offset + selected_limit]
        return {
            "items": [item.to_public_dict() for item in page],
            "pagination": {
                "limit": selected_limit,
                "offset": selected_offset,
                "total": len(sessions),
                "has_more": selected_offset + len(page) < len(sessions),
            },
        }

    def _session_from_events(self, events: list[CodexSessionEvent]) -> CodexSession:
        started = next(
            (item for item in events if item.event_type.value == "session_started"),
            events[0],
        )
        closed = next(
            (item for item in reversed(events) if item.event_type.value == "session_closed"),
            None,
        )
        payload = dict(started.payload)
        close_payload = dict(closed.payload) if closed else {}
        status_value = str(close_payload.get("status") or "active")
        try:
            status = CodexSessionStatus(status_value)
        except ValueError:
            status = CodexSessionStatus.FAILED
        return CodexSession(
            session_id=started.session_id,
            project_id=started.project_id,
            project_name=str(payload.get("project_name") or ""),
            repository=str(payload.get("repository") or ""),
            title=str(payload.get("title") or started.summary or "Codex session"),
            task=str(payload.get("task") or ""),
            status=status,
            created_at=started.occurred_at,
            updated_at=events[-1].occurred_at,
            branch=str(payload.get("branch") or close_payload.get("branch") or ""),
            worktree_name=str(payload.get("worktree_name") or ""),
            external_session_id=str(payload.get("external_session_id") or ""),
            ended_at=closed.occurred_at if closed else "",
            raw_reference=self.raw_reference(started.project_id, started.session_id),
            event_count=len(events),
            remaining_tasks=tuple(close_payload.get("remaining_tasks") or ()),
            memory_candidates_suggested=tuple(
                close_payload.get("memory_candidates_suggested") or ()
            ),
        )

    def _find_session_path(self, session_id: str) -> Path:
        self._validate_id(session_id)
        if self.root.exists():
            matches = list(self.root.glob(f"*/{session_id}.jsonl"))
            if matches:
                return matches[0]
        raise CodexSessionError(
            CODEX_SESSION_NOT_FOUND,
            "Codex session not found",
            status_code=404,
        )

    def _read_path(self, path: Path) -> list[CodexSessionEvent]:
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except OSError as exc:
            logger.exception("Codex session archive read failed")
            raise CodexSessionError(
                CODEX_ARCHIVE_UNAVAILABLE,
                "Codex session archive is unavailable; see local logs",
                status_code=503,
            ) from exc
        events: list[CodexSessionEvent] = []
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    events.append(CodexSessionEvent.from_dict(data))
            except (json.JSONDecodeError, TypeError, ValueError):
                if index == len(lines) - 1:
                    logger.warning("Ignoring incomplete final Codex session archive line")
                    break
                logger.warning("Ignoring invalid Codex session archive line %s", index + 1)
        events.sort(key=lambda item: (item.sequence, item.occurred_at, item.event_id))
        return events

    def _path(self, project_id: str, session_id: str) -> Path:
        self._validate_id(project_id)
        self._validate_id(session_id)
        return self.root / project_id / f"{session_id}.jsonl"

    @staticmethod
    def _validate_id(value: str) -> None:
        if not value or not _SAFE_ID.fullmatch(value):
            raise ValueError("Codex archive identifier is invalid")

    def _lock_for(self, path: Path) -> threading.RLock:
        key = str(path.resolve(strict=False))
        with self._locks_guard:
            return self._locks.setdefault(key, threading.RLock())
