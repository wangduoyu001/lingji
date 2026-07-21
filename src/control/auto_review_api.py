from __future__ import annotations

import hmac
from typing import Any

from pydantic import BaseModel, Field

from src.auto_review.application import AutoReviewApplicationService


class AutoReviewEvaluateRequest(BaseModel):
    candidate: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    use_ai: bool | None = None


class AutoReviewFeedbackRequest(BaseModel):
    decision_id: str
    outcome: str
    notes: str = ""


class AutoReviewAuditVerifyRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


def register_auto_review_routes(app: Any, settings: Any, control: Any, *, token: str) -> None:
    """Register authenticated OFF/SHADOW routes. No execution route exists."""

    from fastapi import Depends, Header, HTTPException, Query

    def authorize(x_lingji_token: str | None = Header(default=None)) -> None:
        if token and not hmac.compare_digest(str(x_lingji_token or ""), token):
            raise HTTPException(status_code=401, detail="Invalid local control token")

    def runtime() -> AutoReviewApplicationService:
        cached = getattr(control, "auto_review_runtime", None)
        if cached is None:
            cached = AutoReviewApplicationService(
                state_db=control.state_db,
                app_settings=settings,
                model_inventory=lambda: control.model_inventory.inventory(force=False),
            )
            control.auto_review_runtime = cached
        return cached

    def translate(exc: Exception) -> HTTPException:
        if isinstance(exc, LookupError):
            return HTTPException(status_code=404, detail=str(exc))
        if isinstance(exc, PermissionError):
            return HTTPException(status_code=403, detail=str(exc))
        return HTTPException(status_code=422, detail=str(exc))

    secured = [Depends(authorize)]

    @app.get("/api/auto-review/status", dependencies=secured)
    def auto_review_status() -> dict[str, Any]:
        try:
            return runtime().status()
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/auto-review/decisions", dependencies=secured)
    def auto_review_decisions(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
        items = runtime().decisions(limit=limit)
        return {"items": items, "total": len(items), "limit": limit}

    @app.get("/api/auto-review/decisions/{decision_id}", dependencies=secured)
    def auto_review_decision(decision_id: str) -> dict[str, Any]:
        try:
            return runtime().decision(decision_id)
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/auto-review/metrics", dependencies=secured)
    def auto_review_metrics() -> dict[str, Any]:
        return runtime().metrics()

    @app.post("/api/auto-review/evaluate/{subject_id}", dependencies=secured)
    def auto_review_evaluate(subject_id: str, request: AutoReviewEvaluateRequest) -> dict[str, Any]:
        try:
            candidate = dict(request.candidate)
            supplied = str(candidate.get("memory_id") or candidate.get("id") or "").strip()
            if supplied and supplied != subject_id:
                raise ValueError("subject_id does not match candidate memory_id")
            candidate["memory_id"] = subject_id
            return runtime().evaluate(candidate, request.context, use_ai=request.use_ai)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/auto-review/feedback", dependencies=secured)
    def auto_review_feedback(request: AutoReviewFeedbackRequest) -> dict[str, Any]:
        try:
            return runtime().feedback(
                request.decision_id,
                outcome=request.outcome,
                notes=request.notes,
            )
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/auto-review/audit/verify", dependencies=secured)
    def auto_review_audit_verify(request: AutoReviewAuditVerifyRequest) -> dict[str, Any]:
        return runtime().verify(request.payload)
