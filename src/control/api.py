from __future__ import annotations

import hmac
from typing import Any

from pydantic import BaseModel, Field

from .service import LocalControlService


class SettingsPatch(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class SettingsReset(BaseModel):
    keys: list[str] | None = None


def create_control_app(
    settings: Any,
    *,
    service: LocalControlService | None = None,
    token: str = "",
):
    """Create the localhost-only FastAPI app used by the future Tauri UI."""

    try:
        from fastapi import Depends, FastAPI, Header, HTTPException
    except ImportError as exc:
        raise RuntimeError("Install requirements-ui.txt to run the local control API") from exc

    control = service or LocalControlService(settings)
    app = FastAPI(title="LingJi Local Control API", version="0.1.0")

    def authorize(x_lingji_token: str | None = Header(default=None)) -> None:
        if token and not hmac.compare_digest(str(x_lingji_token or ""), token):
            raise HTTPException(status_code=401, detail="Invalid local control token")

    @app.get("/api/health", dependencies=[Depends(authorize)])
    def health() -> dict[str, Any]:
        return control.health()

    @app.get("/api/settings", dependencies=[Depends(authorize)])
    def get_settings() -> dict[str, Any]:
        return control.get_settings()

    @app.patch("/api/settings", dependencies=[Depends(authorize)])
    def update_settings(request: SettingsPatch) -> dict[str, Any]:
        try:
            return control.update_settings(request.values, actor="local_ui")
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/settings/reset", dependencies=[Depends(authorize)])
    def reset_settings(request: SettingsReset) -> dict[str, Any]:
        return control.reset_settings(request.keys, actor="local_ui")

    return app
