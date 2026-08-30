from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from src.project_memory.review_service import MemoryReviewError


class ContextRequest(BaseModel):
    agent_id: str = "codex"
    project_id: str
    query: str = ""
    session_id: str = ""
    max_chars: int | None = None
    allow_cross_project: bool = False


class ReviewAction(BaseModel):
    owner_confirmed: bool = False
    expected_content_hash: str = ""
    reason: str = ""
    content: str = ""
    title: str | None = None
    target_category: str = "General"
    valid_to: str | None = None


class OwnerMemoryRequest(BaseModel):
    title: str
    content: str
    project_ids: list[str] = Field(default_factory=list)
    memory_type: str = "knowledge"
    importance: str = "high"
    privacy: str = "private"
    tags: list[str] = Field(default_factory=list)
    owner_confirmed: bool = False


def register_project_memory_routes(app, project_context_service, memory_review_service, *, token_validator: Callable[[str], bool] | None = None):
    router = APIRouter()

    def auth(token: str | None):
        if token_validator and not token_validator(token or ""):
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})

    def guard(call):
        try:
            return call()
        except MemoryReviewError as exc:
            status = 404 if exc.code.endswith("NOT_FOUND") else 409 if exc.code in {"MEMORY_REVIEW_CONFLICT", "MEMORY_ALREADY_REVIEWED", "CORE_MEMORY_EXTERNAL_MODIFIED"} else 422
            raise HTTPException(status_code=status, detail={"code": exc.code}) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail={"code": "PROJECT_ACCESS_DENIED"}) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail={"code": "CORE_MEMORY_NOT_FOUND"}) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail={"code": "PROJECT_CONTEXT_UNAVAILABLE"}) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": str(exc)}) from exc

    @router.post("/api/context/project")
    def context(request: ContextRequest, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: project_context_service.build(request.agent_id, request.project_id, request.query, request.session_id, request.max_chars, request.allow_cross_project))

    @router.get("/api/memory/review/candidates")
    def candidates(project_id: str | None = None, agent_id: str | None = None, memory_type: str | None = None, importance: str | None = None, q: str = "", limit: int = 50, offset: int = 0, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: memory_review_service.list_candidates(project_id, agent_id, memory_type, importance, q, limit, offset))

    @router.get("/api/memory/review/candidates/{memory_id}")
    def candidate(memory_id: str, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: memory_review_service.get_candidate(memory_id))

    @router.post("/api/memory/review/candidates/{memory_id}/approve")
    def approve(memory_id: str, request: ReviewAction, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: memory_review_service.approve(memory_id, owner_confirmed=request.owner_confirmed, expected_content_hash=request.expected_content_hash, target_category=request.target_category))

    @router.post("/api/memory/review/candidates/{memory_id}/edit-approve")
    def edit_approve(memory_id: str, request: ReviewAction, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: memory_review_service.edit_and_approve(memory_id, content=request.content, title=request.title, owner_confirmed=request.owner_confirmed, expected_content_hash=request.expected_content_hash, target_category=request.target_category))

    @router.post("/api/memory/review/candidates/{memory_id}/reject")
    def reject(memory_id: str, request: ReviewAction, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: memory_review_service.reject(memory_id, owner_confirmed=request.owner_confirmed, expected_content_hash=request.expected_content_hash, reason=request.reason))

    @router.post("/api/memory/core")
    def create_core(request: OwnerMemoryRequest, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: memory_review_service.create_owner_memory(**request.model_dump()))

    @router.post("/api/memory/core/{memory_id}/archive")
    def archive(memory_id: str, request: ReviewAction, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        if not request.expected_content_hash.strip():
            raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "expected_content_hash is required"})
        return guard(lambda: memory_review_service.archive_core_memory(memory_id, owner_confirmed=request.owner_confirmed, reason=request.reason, expected_content_hash=request.expected_content_hash))

    @router.post("/api/memory/core/{memory_id}/correct")
    def correct(memory_id: str, request: ReviewAction, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: memory_review_service.correct_core_memory(memory_id, content=request.content, title=request.title, owner_confirmed=request.owner_confirmed, expected_content_hash=request.expected_content_hash, reason=request.reason))

    @router.post("/api/memory/core/{memory_id}/invalidate")
    def invalidate(memory_id: str, request: ReviewAction, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: memory_review_service.invalidate_core_memory(memory_id, owner_confirmed=request.owner_confirmed, expected_content_hash=request.expected_content_hash, reason=request.reason, valid_to=request.valid_to))

    @router.get("/api/memory/core/{memory_id}/integrity")
    def integrity(memory_id: str, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: memory_review_service.inspect_core_integrity(memory_id))

    app.include_router(router)
    return router
