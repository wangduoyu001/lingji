from __future__ import annotations

import logging
from typing import Any, Callable

from pydantic import BaseModel, Field

from src.codex_sessions import CODEX_INGESTION_FAILED, CodexSessionError
from src.project_context import ProjectContextError

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


def register_codex_routes(
    app: Any,
    codex_service: Any,
    token_validator: Callable[..., Any],
) -> None:
    """Register P2-07A routes without coupling them to LocalControlService."""

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

    @app.post("/api/codex/projects/resolve", dependencies=secured)
    def resolve_project(request: ProjectResolveRequest) -> dict[str, Any]:
        try:
            return codex_service.resolve_project(request.workspace_path)
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/codex/projects", dependencies=secured)
    def list_projects() -> list[dict[str, Any]]:
        try:
            return codex_service.list_projects()
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/codex/current", dependencies=secured)
    def current_project(
        workspace_path: str = Query(min_length=1),
    ) -> dict[str, Any]:
        try:
            return codex_service.resolve_project(workspace_path)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/codex/sessions/start", dependencies=secured)
    def start_session(request: CodexSessionStartRequest) -> dict[str, Any]:
        try:
            return codex_service.start_session(**request.model_dump())
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
            return codex_service.close_session(session_id, **request.model_dump())
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/codex/sessions", dependencies=secured)
    def list_sessions(
        project_id: str | None = Query(default=None),
        status: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            return codex_service.list_sessions(
                project_id=project_id,
                status=status,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/codex/sessions/{session_id}", dependencies=secured)
    def get_session(session_id: str) -> dict[str, Any]:
        try:
            return codex_service.get_session(session_id)
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
            return codex_service.activity(
                after_id=after_id,
                limit=limit,
                project_id=project_id,
                session_id=session_id,
            )
        except Exception as exc:
            raise translate(exc) from exc
