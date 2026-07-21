from __future__ import annotations

import logging
from typing import Any, Callable, Mapping

from pydantic import BaseModel, Field

from src.codex_sessions import CODEX_INGESTION_FAILED, CodexSessionError
from src.project_context import ProjectContextError
from src.sources.read_model import SourceReadModel

logger = logging.getLogger("lingji.control.codex_api")


class ProjectResolveRequest(BaseModel):
    workspace_path: str = Field(min_length=1)


class CodexSessionStartRequest(BaseModel):
    workspace_path: str = Field(min_length=1)
    external_session_id: str = ""
    title: str = ""
    task: str = ""
    branch: str = ""


class CodexCheckpointRequest(BaseModel):
    event_id: str = Field(min_length=1)
    kind: str = "checkpoint"
    summary: str = Field(min_length=1)
    changed_files: list[str] = Field(default_factory=list)
    tests: list[Any] = Field(default_factory=list)
    decisions: list[Any] = Field(default_factory=list)
    blockers: list[Any] = Field(default_factory=list)
    next_steps: list[Any] = Field(default_factory=list)
    branch: str = ""
    commits: list[str] = Field(default_factory=list)


class CodexCloseRequest(BaseModel):
    event_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    status: str = "completed"
    decisions: list[Any] = Field(default_factory=list)
    remaining_tasks: list[Any] = Field(default_factory=list)


def _as_items(value: Any) -> list[Any]:
    if value in (None, "", [], (), {}):
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def _session_view(value: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(value)
    events = [dict(event) for event in item.get("events") or [] if isinstance(event, Mapping)]
    checkpoint_events = [
        event for event in events
        if str(event.get("event_type") or "") not in {"session_started", "session_closed"}
    ]
    decisions: list[Any] = []
    tests: list[Any] = []
    blockers: list[Any] = []
    next_steps: list[Any] = []
    completed: list[str] = []
    for event in checkpoint_events:
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        decisions.extend(_as_items(payload.get("decisions")))
        tests.extend(_as_items(payload.get("tests")))
        blockers.extend(_as_items(payload.get("blockers")))
        next_steps.extend(_as_items(payload.get("next_steps")))
        summary = str(event.get("summary") or "").strip()
        if summary:
            completed.append(summary)
    project_id = str(item.get("project_id") or "")
    session_id = str(item.get("session_id") or "")
    source_ids: list[str] = []
    conversation_ids: list[str] = []
    if project_id and session_id:
        source_id = SourceReadModel.stable_id("source", "codex_session", f"codex:{project_id}")
        source_ids = [source_id]
        conversation_ids = [SourceReadModel.stable_id("conversation", source_id, session_id)]
    last_event = events[-1] if events else {}
    last_checkpoint = checkpoint_events[-1] if checkpoint_events else None
    projected = {
        key: value
        for key, value in item.items()
        if key not in {"events", "raw_reference", "workspace_path", "git_common_dir"}
    }
    projected.update(
        started_at=str(item.get("started_at") or item.get("created_at") or ""),
        checkpoint_count=len(checkpoint_events) if events else max(int(item.get("event_count") or 0) - 1, 0),
        last_checkpoint_at=str((last_checkpoint or {}).get("occurred_at") or ""),
        summary=str(last_event.get("summary") or item.get("summary") or item.get("title") or ""),
        goal=str(item.get("goal") or item.get("task") or ""),
        completed=completed,
        decisions=decisions,
        tests=tests,
        blockers=blockers,
        next_steps=next_steps or _as_items(item.get("remaining_tasks")),
        source_ids=source_ids,
        conversation_ids=conversation_ids,
    )
    return projected


def _activity_view(value: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(value)
    stage = str(item.get("stage") or item.get("event_type") or "")
    return {
        **item,
        "stage": stage,
        "occurred_at": str(item.get("occurred_at") or item.get("created_at") or ""),
        "status": str(item.get("status") or ("failed" if stage == "FAILED" else "active")),
    }


def register_codex_routes(
    app: Any,
    codex_service: Any,
    token_validator: Callable[..., Any],
) -> None:
    """Register P2-07A routes with stable, sanitized Desktop projections."""

    from fastapi import Depends, HTTPException, Query

    secured = [Depends(token_validator)]

    def translate(exc: Exception) -> HTTPException:
        if isinstance(exc, (CodexSessionError, ProjectContextError)):
            return HTTPException(
                status_code=exc.status_code,
                detail={"code": exc.code, "message": exc.message},
            )
        logger.exception("Codex API request failed")
        return HTTPException(
            status_code=503,
            detail={
                "code": CODEX_INGESTION_FAILED,
                "message": "Codex session service unavailable; see local logs",
            },
        )

    def project_page() -> dict[str, Any]:
        items = list(codex_service.list_projects() or [])
        return {
            "items": items,
            "pagination": {"limit": len(items), "offset": 0, "total": len(items), "has_more": False},
        }

    @app.post("/api/codex/projects/resolve", dependencies=secured)
    def resolve_project(request: ProjectResolveRequest) -> dict[str, Any]:
        try:
            return codex_service.resolve_project(request.workspace_path)
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/codex/projects", dependencies=secured)
    def list_projects() -> dict[str, Any]:
        try:
            return project_page()
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/codex/current", dependencies=secured)
    def current_project(
        workspace_path: str | None = Query(default=None),
    ) -> dict[str, Any]:
        try:
            projects = project_page()["items"]
            if workspace_path:
                project = codex_service.resolve_project(workspace_path)
            else:
                project = projects[0] if projects else None
            page = codex_service.list_sessions(limit=1, offset=0)
            raw_session = (page.get("items") or [None])[0]
            session = None
            if isinstance(raw_session, Mapping):
                session = _session_view(codex_service.get_session(str(raw_session.get("session_id") or "")))
                matching = next(
                    (item for item in projects if item.get("project_id") == session.get("project_id")),
                    None,
                )
                project = matching or project
            return {
                "project": project,
                "session": session,
                "mcp_state": "available",
                "obsidian_state": None,
                "memory_index_state": None,
                "last_checkpoint_at": session.get("last_checkpoint_at") if session else None,
                "pending_review_count": None,
                "activity": None,
            }
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/codex/sessions/start", dependencies=secured)
    def start_session(request: CodexSessionStartRequest) -> dict[str, Any]:
        try:
            return _session_view(codex_service.start_session(**request.model_dump()))
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/codex/sessions/{session_id}/checkpoint", dependencies=secured)
    def checkpoint(session_id: str, request: CodexCheckpointRequest) -> dict[str, Any]:
        try:
            return codex_service.checkpoint(session_id, **request.model_dump())
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/codex/sessions/{session_id}/close", dependencies=secured)
    def close_session(session_id: str, request: CodexCloseRequest) -> dict[str, Any]:
        try:
            return _session_view(codex_service.close_session(session_id, **request.model_dump()))
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/codex/sessions", dependencies=secured)
    def list_sessions(
        project_id: str | None = Query(default=None),
        status: str | None = Query(default=None),
        q: str = Query(default=""),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            raw_page = codex_service.list_sessions(
                project_id=project_id,
                status=status,
                limit=200 if q else limit,
                offset=0 if q else offset,
            )
            raw_items = list(raw_page.get("items") or [])
            if q:
                needle = q.casefold()
                raw_items = [
                    item for item in raw_items
                    if needle in " ".join(
                        str(item.get(key) or "")
                        for key in ("session_id", "title", "task", "project_name", "branch", "status")
                    ).casefold()
                ]
                total = len(raw_items)
                raw_items = raw_items[offset: offset + limit]
                pagination = {"limit": limit, "offset": offset, "total": total, "has_more": offset + len(raw_items) < total}
            else:
                pagination = dict(raw_page.get("pagination") or {})
            items = [
                _session_view(codex_service.get_session(str(item.get("session_id") or "")))
                for item in raw_items
            ]
            return {"items": items, "pagination": pagination}
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/codex/sessions/{session_id}", dependencies=secured)
    def get_session(session_id: str) -> dict[str, Any]:
        try:
            return _session_view(codex_service.get_session(session_id))
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/activity", dependencies=secured)
    def activity(
        after_id: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        project_id: str | None = Query(default=None),
        session_id: str | None = Query(default=None),
    ) -> dict[str, Any]:
        try:
            result = codex_service.activity(
                after_id=after_id,
                limit=limit,
                project_id=project_id,
                session_id=session_id,
            )
            return {**result, "items": [_activity_view(item) for item in result.get("items") or []]}
        except Exception as exc:
            raise translate(exc) from exc
