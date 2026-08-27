from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.automatic_memory import AuthorizationScope, SourceRegistry, discover_source_metadata


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


class AutomaticMemoryRuntimeActionRequest(BaseModel):
    confirmation: bool = True


def register_automatic_memory_routes(
    app: Any, control: Any, secured: list[Any]
) -> None:
    """Expose source metadata and scan controls through the existing 8766 auth."""
    from dataclasses import asdict, is_dataclass
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
        runtime = getattr(control, "runtime", None)
        if runtime is None:
            raise HTTPException(status_code=409, detail="automatic-memory runtime is not composed")
        result = call(lambda: runtime.scan_now(request.source_id))
        return asdict(result) if is_dataclass(result) else dict(result)

    @app.post("/api/automatic-memory/pause", dependencies=secured)
    def pause_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        result = call(lambda: registry.pause_scan(request.scan_id))
        return asdict(result)

    @app.post("/api/automatic-memory/retry", dependencies=secured)
    def retry_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        result = call(lambda: registry.retry_scan(request.scan_id))
        return asdict(result)

    @app.post("/api/automatic-memory/resume", dependencies=secured)
    def resume_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        # Resume is the durable retry transition for a paused scan.
        result = call(lambda: registry.retry_scan(request.scan_id))
        return asdict(result)

    @app.get("/api/automatic-memory/sources", dependencies=secured)
    def list_sources() -> list[dict[str, Any]]:
        return [asdict(item) for item in registry.list_sources()]

    @app.get("/api/automatic-memory/discovered", dependencies=secured)
    def discovered_sources() -> list[dict[str, Any]]:
        settings = getattr(control, "settings", control)
        return [asdict(item) for item in discover_source_metadata(settings)]

    @app.get("/api/automatic-memory/scans", dependencies=secured)
    def list_scans(limit: int = 50) -> list[dict[str, Any]]:
        return [dict(item) for item in registry.state_db.list_automatic_memory_scans()[: min(max(int(limit), 1), 200)]]

    @app.get("/api/automatic-memory/summary", dependencies=secured)
    def scan_summary() -> dict[str, Any]:
        scans = registry.state_db.list_automatic_memory_scans()
        counts: dict[str, int] = {}
        for scan in scans:
            status = str(scan.get("status") or "unknown")
            counts[status] = counts.get(status, 0) + 1
        latest = scans[0] if scans else None
        return {
            "counts": counts,
            "total": len(scans),
            "latest": dict(latest) if latest else None,
            "progress": {
                "current": int((latest or {}).get("progress") or 0),
                "total": (latest or {}).get("total"),
            },
            "last_error": (latest or {}).get("last_error"),
            "next_action": "retry failed scan" if latest and latest.get("status") == "failed" else "wait for watcher or scheduled reconciliation",
        }

    @app.get("/api/automatic-memory/runtime", dependencies=secured)
    def runtime_status() -> dict[str, Any]:
        runtime = getattr(control, "runtime", None)
        if runtime is None:
            return {
                "state": "stopped",
                "running": False,
                "paused": False,
                "scheduler_heartbeat_at": None,
                "scheduler_heartbeat_age": None,
                "scheduler_heartbeat_reason": (
                    "unavailable: automatic-memory runtime is not composed"
                ),
                "scheduler_heartbeat_instance": None,
                "scheduler_heartbeat_generation": None,
                "scheduler_heartbeat_state": None,
                "scheduler_heartbeat_last_error": None,
                "worker_state": None,
                "authorized_watcher_count": None,
                "last_global_error": None,
            }
        return dict(runtime.status())

    @app.post("/api/automatic-memory/pause-runtime", dependencies=secured)
    def pause_runtime(request: AutomaticMemoryRuntimeActionRequest) -> dict[str, Any]:
        del request
        runtime = getattr(control, "runtime", None)
        if runtime is None:
            raise HTTPException(status_code=409, detail="automatic-memory runtime is not composed")
        return dict(runtime.pause())

    @app.post("/api/automatic-memory/resume-runtime", dependencies=secured)
    def resume_runtime(request: AutomaticMemoryRuntimeActionRequest) -> dict[str, Any]:
        del request
        runtime = getattr(control, "runtime", None)
        if runtime is None:
            raise HTTPException(status_code=409, detail="automatic-memory runtime is not composed")
        return dict(runtime.resume())

    @app.get("/api/automatic-memory/scans/{scan_id}", dependencies=secured)
    def get_scan(scan_id: str) -> dict[str, Any]:
        result = call(lambda: registry.get_scan(scan_id))
        return asdict(result)
