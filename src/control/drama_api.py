from __future__ import annotations

from typing import Any, Callable

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
    dependencies: list[Any],
    translate_error: Callable[[Exception], Exception],
) -> None:
    """Register the isolated Drama Memory surface on authenticated 8766."""

    service: DramaService | None = None

    def drama() -> DramaService:
        nonlocal service
        if service is None:
            service = DramaService(settings, memory_gateway=getattr(control, "memory_gateway", None))
        return service

    @app.get("/api/drama/status", dependencies=dependencies)
    def drama_status() -> dict[str, Any]:
        try:
            return drama().status()
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/drama/library", dependencies=dependencies)
    def drama_library(limit: int = 100, offset: int = 0) -> dict[str, Any]:
        try:
            return drama().list_dramas(limit=limit, offset=offset)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.get("/api/drama/library/{drama_id}", dependencies=dependencies)
    def drama_detail(drama_id: str) -> dict[str, Any]:
        try:
            return drama().get_drama(drama_id)
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/drama/import", dependencies=dependencies)
    def drama_import(request: DramaImportRequest) -> dict[str, Any]:
        try:
            return drama().import_script(
                request.source_path,
                title=request.title,
                force=request.force,
            )
        except Exception as exc:
            raise translate_error(exc) from exc

    @app.post("/api/drama/search", dependencies=dependencies)
    def drama_search(request: DramaSearchRequest) -> dict[str, Any]:
        try:
            return drama().search(
                request.query,
                limit=request.limit,
                drama_id=request.drama_id,
                chunk_type=request.chunk_type,
            )
        except Exception as exc:
            raise translate_error(exc) from exc
