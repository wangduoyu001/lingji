from __future__ import annotations

import hmac
from typing import Any

from pydantic import BaseModel, Field


class SettingsPreviewRequest(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class SettingsCommitRequest(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    confirmation: str = ""


def register_settings_governance_routes(app: Any, control: Any, *, token: str) -> None:
    """Register settings preview/commit routes without replacing legacy low-risk PATCH."""

    from fastapi import Depends, Header, HTTPException

    def authorize(x_lingji_token: str | None = Header(default=None)) -> None:
        if token and not hmac.compare_digest(str(x_lingji_token or ""), token):
            raise HTTPException(status_code=401, detail="Invalid local control token")

    def translate(exc: Exception) -> HTTPException:
        if isinstance(exc, PermissionError):
            return HTTPException(status_code=403, detail=str(exc))
        if isinstance(exc, KeyError):
            return HTTPException(status_code=404, detail=str(exc))
        return HTTPException(status_code=422, detail=str(exc))

    secured = [Depends(authorize)]

    @app.post("/api/settings/preview", dependencies=secured)
    def preview_settings(request: SettingsPreviewRequest) -> dict[str, Any]:
        try:
            return control.preview_settings(request.values)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/settings/commit", dependencies=secured)
    def commit_settings(request: SettingsCommitRequest) -> dict[str, Any]:
        try:
            return control.commit_settings(
                request.values,
                confirmation=request.confirmation,
                actor="local_ui",
            )
        except Exception as exc:
            raise translate(exc) from exc
