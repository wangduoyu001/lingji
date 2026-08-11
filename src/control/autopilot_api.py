from __future__ import annotations

import hmac
from typing import Any


def register_autopilot_routes(app: Any, engine: Any, *, token: str) -> None:
    """Expose read-only Autopilot state through the authenticated local control API."""

    from fastapi import Depends, Header, HTTPException

    def authorize(x_lingji_token: str | None = Header(default=None)) -> None:
        if token and not hmac.compare_digest(str(x_lingji_token or ""), token):
            raise HTTPException(status_code=401, detail="Invalid local control token")

    secured = [Depends(authorize)]

    @app.get("/api/autopilot/status", dependencies=secured)
    def autopilot_status() -> dict[str, Any]:
        return engine.status()
