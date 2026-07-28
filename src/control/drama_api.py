from __future__ import annotations

import hmac
import sqlite3
from typing import Any

from pydantic import BaseModel, Field

from src.plugins.drama_intelligence import DramaService


class DramaImportRequest(BaseModel):
    source_path: str
    title: str | None = None
    force: bool = False


class DramaSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)
    drama_id: str | None = None
    chunk_type: str | None = None


def register_drama_routes(
    app: Any,
    settings: Any,
    control: Any,
    *,
    token: str = "",
) -> None:
    """Register the isolated Drama Memory surface on authenticated 8766."""

    try:
        from fastapi import Depends, Header, HTTPException, Query
    except ImportError as exc:  # pragma: no cover - startup dependency contract
        raise RuntimeError("Install requirements-ui.txt before registering Drama routes") from exc

    service: DramaService | None = None

    def authorize(x_lingji_token: str | None = Header(default=None)) -> None:
        if token and not hmac.compare_digest(str(x_lingji_token or ""), token):
            raise HTTPException(status_code=401, detail="Invalid local control token")

    def translate(exc: Exception) -> HTTPException:
        if isinstance(exc, LookupError):
            return HTTPException(status_code=404, detail=str(exc))
        if isinstance(exc, FileNotFoundError):
            return HTTPException(status_code=404, detail=str(exc))
        if isinstance(exc, PermissionError):
            return HTTPException(status_code=403, detail=str(exc))
        if isinstance(exc, sqlite3.Error):
            return HTTPException(status_code=503, detail="Drama read model is unavailable")
        return HTTPException(status_code=422, detail=str(exc))

    def drama() -> DramaService:
        nonlocal service
        if service is None:
            service = DramaService(settings, memory_gateway=getattr(control, "memory_gateway", None))
        return service

    secured = [Depends(authorize)]

    @app.get("/api/drama/status", dependencies=secured)
    def drama_status() -> dict[str, Any]:
        try:
            return drama().status()
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/drama/library", dependencies=secured)
    def drama_library(
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        try:
            return drama().list_dramas(limit=limit, offset=offset)
        except Exception as exc:
            raise translate(exc) from exc

    @app.get("/api/drama/library/{drama_id}", dependencies=secured)
    def drama_detail(drama_id: str) -> dict[str, Any]:
        try:
            return drama().get_drama(drama_id)
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/drama/import", dependencies=secured)
    def drama_import(request: DramaImportRequest) -> dict[str, Any]:
        try:
            return drama().import_script(
                request.source_path,
                title=request.title,
                force=request.force,
            )
        except Exception as exc:
            raise translate(exc) from exc

    @app.post("/api/drama/search", dependencies=secured)
    def drama_search(request: DramaSearchRequest) -> dict[str, Any]:
        try:
            return drama().search(
                request.query,
                limit=request.limit,
                drama_id=request.drama_id,
                chunk_type=request.chunk_type,
            )
        except Exception as exc:
            raise translate(exc) from exc
