from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.automatic_memory import AuthorizationScope, SourceRegistry


class AutomaticMemoryAuthorizationRequest(BaseModel):
    grant_id: str = Field(min_length=1)
    source_kinds: list[str] = Field(min_length=1)
    roots: list[str] = Field(min_length=1)
    granted_at: datetime
    expires_at: datetime | None = None
    owner_confirmed: bool = False
    kind: str = Field(min_length=1)
    root: str = Field(min_length=1)


class AutomaticMemorySourceRequest(BaseModel):
    source_id: str = Field(min_length=1)


class AutomaticMemoryScanRequest(BaseModel):
    source_id: str = Field(min_length=1)


class AutomaticMemoryScanActionRequest(BaseModel):
    scan_id: str = Field(min_length=1)


def register_automatic_memory_routes(
    app: Any, control: Any, secured: list[Any]
) -> None:
    """Expose source metadata and scan controls through the existing 8766 auth."""
    from dataclasses import asdict
    from fastapi import HTTPException

    registry: SourceRegistry | None = getattr(control, "automatic_memory_registry", None)
    if registry is None:
        state_db = getattr(control, "state_db", None)
        # Lightweight control doubles used by unrelated API tests do not own
        # the production state boundary; leave their app surface unchanged.
        if state_db is None:
            return
        registry = SourceRegistry(state_db)
        try:
            control.automatic_memory_registry = registry
        except Exception:
            pass

    def call(operation):
        try:
            return operation()
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/automatic-memory/authorize", dependencies=secured)
    def authorize_source(request: AutomaticMemoryAuthorizationRequest) -> dict[str, Any]:
        scope = AuthorizationScope(
            grant_id=request.grant_id,
            source_kinds=tuple(request.source_kinds),
            roots=tuple(request.roots),
            granted_at=request.granted_at,
            expires_at=request.expires_at,
            owner_confirmed=request.owner_confirmed,
        )
        result = call(lambda: registry.register(scope, request.kind, request.root))
        return asdict(result)

    @app.post("/api/automatic-memory/revoke", dependencies=secured)
    def revoke_source(request: AutomaticMemorySourceRequest) -> dict[str, Any]:
        result = call(lambda: registry.revoke(request.source_id))
        return asdict(result)

    @app.post("/api/automatic-memory/scan", dependencies=secured)
    def start_scan(request: AutomaticMemoryScanRequest) -> dict[str, Any]:
        result = call(lambda: registry.start_scan(request.source_id))
        return asdict(result)

    @app.post("/api/automatic-memory/pause", dependencies=secured)
    def pause_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        result = call(lambda: registry.pause_scan(request.scan_id))
        return asdict(result)

    @app.post("/api/automatic-memory/retry", dependencies=secured)
    def retry_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        result = call(lambda: registry.retry_scan(request.scan_id))
        return asdict(result)

    @app.get("/api/automatic-memory/sources", dependencies=secured)
    def list_sources() -> list[dict[str, Any]]:
        return [asdict(item) for item in registry.list_sources()]

    @app.get("/api/automatic-memory/scans/{scan_id}", dependencies=secured)
    def get_scan(scan_id: str) -> dict[str, Any]:
        result = call(lambda: registry.get_scan(scan_id))
        return asdict(result)
