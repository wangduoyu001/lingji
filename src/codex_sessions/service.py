from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from src.project_context import (
    PROJECT_UNASSIGNED,
    ProjectContextError,
    ProjectResolution,
    ProjectResolver,
    ProjectState,
)

from .archive import CodexSessionArchive
from .models import (
    CODEX_EVENT_INVALID,
    CODEX_INGESTION_FAILED,
    CODEX_SESSION_ALREADY_CLOSED,
    CodexEventType,
    CodexSessionError,
    CodexSessionEvent,
    CodexSessionStatus,
    event_content_hash,
    sanitize_value,
)

logger = logging.getLogger("lingji.codex_sessions.service")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_ALLOWED_CHECKPOINTS = {
    CodexEventType.CHECKPOINT,
    CodexEventType.DECISION,
    CodexEventType.TEST_RESULT,
    CodexEventType.BLOCKER,
}
_ACTIVITY_TYPES = {
    "SESSION_STARTED",
    "PROJECT_RESOLVED",
    "CHECKPOINT_RECEIVED",
    "SOURCE_ARCHIVED",
    "CONVERSATION_INDEXED",
    "SESSION_CLOSED",
    "FAILED",
}


class CodexSessionService:
    def __init__(
        self,
        project_resolver: ProjectResolver,
        archive: CodexSessionArchive,
        pipeline: Any,
        *,
        state_db: Any | None = None,
    ):
        self.project_resolver = project_resolver
        self.archive = archive
        self.pipeline = pipeline
        self.state_db = state_db

    def resolve_project(self, workspace_path: Path | str) -> dict[str, Any]:
        resolution = self.project_resolver.resolve(workspace_path)
        self._activity(
            "PROJECT_RESOLVED",
            "project",
            resolution.project_id or "unassigned",
            {
                "project_id": resolution.project_id,
                "repository": resolution.repository,
                "state": resolution.state.value,
                "resolution_source": resolution.resolution_source,
            },
        )
        return resolution.to_public_dict()

    def list_projects(self) -> list[dict[str, Any]]:
        return self.project_resolver.list_projects()

    def start_session(
        self,
        *,
        workspace_path: Path | str,
        external_session_id: str = "",
        title: str = "",
        task: str = "",
        branch: str = "",
    ) -> dict[str, Any]:
        resolution = self.project_resolver.resolve(workspace_path)
        self._require_assigned(resolution)
        self._activity(
            "PROJECT_RESOLVED",
            "project",
            resolution.project_id,
            {
                "project_id": resolution.project_id,
                "repository": resolution.repository,
                "state": resolution.state.value,
                "resolution_source": resolution.resolution_source,
            },
        )
        session_id = self._session_id(resolution.project_id, external_session_id)
        now = self._now()
        event = self._event(
            event_id=f"{session_id}.started",
            session_id=session_id,
            project_id=resolution.project_id,
            event_type=CodexEventType.SESSION_STARTED,
            occurred_at=now,
            summary=title or task or "Codex session started",
            payload={
                "project_name": resolution.name,
                "repository": resolution.repository,
                "title": title or task or "Codex session",
                "task": task,
                "branch": branch or resolution.branch,
                "worktree_name": resolution.worktree_name,
                "external_session_id": external_session_id,
                "privacy": resolution.privacy,
                "role": "owner",
            },
        )
        append = self.archive.append(event)
        if append.added:
            self._activity(
                "SOURCE_ARCHIVED",
                "codex_session",
                session_id,
                {"session_id": session_id, "project_id": resolution.project_id},
            )
        self._ingest(session_id)
        session, _ = self.archive.get_session(session_id)
        self._activity(
            "SESSION_STARTED",
            "codex_session",
            session_id,
            {
                "session_id": session_id,
                "project_id": resolution.project_id,
                "duplicate": not append.added,
            },
        )
        return session.to_public_dict()

    def checkpoint(
        self,
        session_id: str,
        *,
        event_id: str,
        kind: str = "checkpoint",
        summary: str,
        changed_files: Any = None,
        tests: Any = None,
        decisions: Any = None,
        blockers: Any = None,
        next_steps: Any = None,
        branch: str = "",
        commits: Any = None,
    ) -> dict[str, Any]:
        session, _ = self.archive.get_session(session_id)
        self._require_active(session.status)
        event_type = self._checkpoint_type(kind)
        self._validate_event_id(event_id)
        event = self._event(
            event_id=event_id,
            session_id=session_id,
            project_id=session.project_id,
            event_type=event_type,
            occurred_at=self._now(),
            summary=summary,
            payload={
                "changed_files": self._safe_paths(changed_files),
                "tests": self._items(tests),
                "decisions": self._items(decisions),
                "blockers": self._items(blockers),
                "next_steps": self._items(next_steps),
                "branch": branch or session.branch,
                "commits": self._items(commits),
                "role": "tool" if event_type is CodexEventType.TEST_RESULT else "assistant",
            },
        )
        append = self.archive.append(event)
        if append.added:
            self._activity(
                "SOURCE_ARCHIVED",
                "codex_session",
                session_id,
                {"session_id": session_id, "project_id": session.project_id},
            )
        self._ingest(session_id)
        self._activity(
            "CHECKPOINT_RECEIVED",
            "codex_session",
            session_id,
            {
                "session_id": session_id,
                "project_id": session.project_id,
                "event_id": event_id,
                "event_type": event_type.value,
                "duplicate": not append.added,
                "duplicate_content_event_id": append.duplicate_content_event_id,
            },
        )
        return {
            "session_id": session_id,
            "project_id": session.project_id,
            "event_id": append.event.event_id,
            "sequence": append.event.sequence,
            "duplicate": not append.added,
            "duplicate_content_event_id": append.duplicate_content_event_id or None,
            "status": "active",
        }

    def close_session(
        self,
        session_id: str,
        *,
        event_id: str,
        summary: str,
        status: str = "completed",
        decisions: Any = None,
        remaining_tasks: Any = None,
    ) -> dict[str, Any]:
        session, _ = self.archive.get_session(session_id)
        self._require_active(session.status)
        self._validate_event_id(event_id)
        try:
            final_status = CodexSessionStatus(str(status))
        except ValueError as exc:
            raise CodexSessionError(
                CODEX_EVENT_INVALID,
                "Codex session close status is invalid",
                status_code=422,
            ) from exc
        if final_status is CodexSessionStatus.ACTIVE:
            raise CodexSessionError(
                CODEX_EVENT_INVALID,
                "Closed Codex sessions cannot remain active",
                status_code=422,
            )
        event = self._event(
            event_id=event_id,
            session_id=session_id,
            project_id=session.project_id,
            event_type=CodexEventType.SESSION_CLOSED,
            occurred_at=self._now(),
            summary=summary,
            payload={
                "status": final_status.value,
                "decisions": self._items(decisions),
                "remaining_tasks": self._items(remaining_tasks),
                "memory_candidates_suggested": [],
                "branch": session.branch,
                "role": "assistant",
            },
        )
        append = self.archive.append(event)
        if append.added:
            self._activity(
                "SOURCE_ARCHIVED",
                "codex_session",
                session_id,
                {"session_id": session_id, "project_id": session.project_id},
            )
        self._ingest(session_id)
        closed, _ = self.archive.get_session(session_id)
        self._activity(
            "SESSION_CLOSED",
            "codex_session",
            session_id,
            {
                "session_id": session_id,
                "project_id": session.project_id,
                "status": final_status.value,
            },
        )
        return closed.to_public_dict()

    def get_session(self, session_id: str) -> dict[str, Any]:
        session, events = self.archive.get_session(session_id)
        result = session.to_public_dict()
        result["events"] = [item.to_dict() for item in events]
        return result

    def list_sessions(
        self,
        *,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self.archive.list_sessions(
            project_id=project_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def activity(
        self,
        *,
        after_id: int = 0,
        limit: int = 100,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        selected_limit = max(min(int(limit), 500), 1)
        if self.state_db is None:
            return {"items": [], "after_id": int(after_id), "has_more": False}
        rows = self.state_db.recent_events(limit=10000)
        items = []
        for row in reversed(rows):
            event_id = int(row.get("event_id") or 0)
            if event_id <= int(after_id):
                continue
            event_type = str(row.get("event_type") or "")
            if event_type not in _ACTIVITY_TYPES:
                continue
            payload = self._payload(row.get("payload_json"))
            if project_id and str(payload.get("project_id") or "") != project_id:
                continue
            if session_id and str(payload.get("session_id") or row.get("entity_id") or "") != session_id:
                continue
            items.append(
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "project_id": str(payload.get("project_id") or ""),
                    "session_id": str(payload.get("session_id") or ""),
                    "summary": str(payload.get("summary") or ""),
                    "created_at": str(row.get("created_at") or ""),
                }
            )
        page = items[:selected_limit]
        return {
            "items": page,
            "after_id": page[-1]["event_id"] if page else int(after_id),
            "has_more": len(items) > len(page),
        }

    def _ingest(self, session_id: str) -> None:
        session, events = self.archive.get_session(session_id)
        try:
            result = self.pipeline.execute(
                "codex_session",
                payload={
                    "session": session.to_public_dict(),
                    "events": [item.to_dict() for item in events],
                    "raw_reference": session.raw_reference,
                },
                adapter_name="codex_session",
                execution_id=f"LJ-CODEX-INGEST-{hashlib.sha256((session_id + str(len(events))).encode()).hexdigest()[:12].upper()}",
            )
            structured = result.get("structured_read_model") if isinstance(result, Mapping) else None
            if isinstance(structured, Mapping) and structured.get("state") == "degraded":
                raise RuntimeError("structured ingestion degraded")
        except Exception as exc:
            logger.exception("Codex session structured ingestion failed")
            self._activity(
                "FAILED",
                "codex_session",
                session_id,
                {
                    "session_id": session_id,
                    "project_id": session.project_id,
                    "summary": "Codex session ingestion failed; see local logs",
                },
            )
            raise CodexSessionError(
                CODEX_INGESTION_FAILED,
                "Codex session ingestion failed; see local logs",
                status_code=503,
            ) from exc
        self._activity(
            "CONVERSATION_INDEXED",
            "codex_session",
            session_id,
            {"session_id": session_id, "project_id": session.project_id},
        )

    def _activity(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        if self.state_db is None:
            return
        try:
            self.state_db.append_event(
                event_type,
                entity_type,
                entity_id,
                sanitize_value(dict(payload)),
            )
        except Exception:
            logger.exception("Codex activity event write failed: %s", event_type)

    @staticmethod
    def _event(
        *,
        event_id: str,
        session_id: str,
        project_id: str,
        event_type: CodexEventType,
        occurred_at: str,
        summary: str,
        payload: Mapping[str, Any],
    ) -> CodexSessionEvent:
        safe_summary = str(sanitize_value(summary)).strip()
        safe_payload = sanitize_value(dict(payload))
        return CodexSessionEvent(
            event_id=event_id,
            session_id=session_id,
            project_id=project_id,
            event_type=event_type,
            occurred_at=occurred_at,
            sequence=0,
            summary=safe_summary,
            payload=safe_payload,
            content_hash=event_content_hash(
                session_id=session_id,
                project_id=project_id,
                event_type=event_type,
                summary=safe_summary,
                payload=safe_payload,
            ),
        )

    @staticmethod
    def _session_id(project_id: str, external_session_id: str) -> str:
        seed = f"{project_id}\0{external_session_id}" if external_session_id else f"{project_id}\0{uuid4().hex}"
        token = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20].upper()
        return f"LJ-CODEX-SESSION-{token}"

    @staticmethod
    def _checkpoint_type(value: str) -> CodexEventType:
        try:
            selected = CodexEventType(str(value or "checkpoint"))
        except ValueError as exc:
            raise CodexSessionError(
                CODEX_EVENT_INVALID,
                "Codex checkpoint kind is invalid",
                status_code=422,
            ) from exc
        if selected not in _ALLOWED_CHECKPOINTS:
            raise CodexSessionError(
                CODEX_EVENT_INVALID,
                "Codex checkpoint kind is invalid",
                status_code=422,
            )
        return selected

    @staticmethod
    def _validate_event_id(event_id: str) -> None:
        if not str(event_id or "").strip() or len(str(event_id)) > 240:
            raise CodexSessionError(
                CODEX_EVENT_INVALID,
                "Codex event_id is invalid",
                status_code=422,
            )

    @staticmethod
    def _require_active(status: CodexSessionStatus) -> None:
        if status is not CodexSessionStatus.ACTIVE:
            raise CodexSessionError(
                CODEX_SESSION_ALREADY_CLOSED,
                "Codex session is already closed",
                status_code=409,
            )

    @staticmethod
    def _require_assigned(resolution: ProjectResolution) -> None:
        if resolution.state is ProjectState.UNASSIGNED or not resolution.project_id:
            raise ProjectContextError(
                PROJECT_UNASSIGNED,
                "Project is unassigned",
                status_code=409,
            )

    @staticmethod
    def _safe_paths(value: Any) -> list[str]:
        result = []
        for item in CodexSessionService._items(value):
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
            return list(sanitize_value(value))
        return [sanitize_value(value)]

    @staticmethod
    def _payload(value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        if not value:
            return {}
        try:
            parsed = json.loads(str(value))
            return dict(parsed) if isinstance(parsed, Mapping) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
