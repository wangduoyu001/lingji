from __future__ import annotations

from datetime import datetime
import math
import os
from dataclasses import asdict, is_dataclass
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


_SCAN_DTO_FIELDS = (
    "scan_id", "source_id", "work_id", "status", "cursor", "progress", "total",
    "last_error", "recovery_token", "source_sentinel", "lease_id",
    "lease_owner_pid", "lease_owner_thread", "lease_owner_instance",
    "lease_heartbeat_at", "lease_expires_at", "attempt",
    "scheduler_lease_id", "scheduler_lease_owner",
    "scheduler_lease_heartbeat_at", "scheduler_lease_expires_at", "updated_at",
    "queued", "reused", "counts_present", "complete", "errors", "discovered",
    "unchanged", "next_action",
)


def project_scan_dto(scan: Any) -> dict[str, Any]:
    """Project every scan response from the same nullable evidence contract."""
    payload = asdict(scan) if is_dataclass(scan) else dict(scan)
    presence_was_declared = "counts_present" in payload
    declared = set(payload.get("counts_present") or ())

    def normalize_count(name: str) -> int | None:
        value = payload.get(name)
        persisted_name = f"{name}_count"
        if value is None and persisted_name in payload:
            value = payload.get(persisted_name)
        if not isinstance(value, int) or isinstance(value, bool):
            return None
        # Older model/dict callers used zero as a default.  Only accept that
        # value when the current DTO declares presence or the persisted
        # nullable column itself supplied it.
        if value == 0 and presence_was_declared and name not in declared:
            return None
        if value == 0 and not presence_was_declared and persisted_name not in payload:
            return None
        return value

    queued = normalize_count("queued")
    reused = normalize_count("reused")
    result = {key: payload.get(key) for key in _SCAN_DTO_FIELDS}
    result["queued"] = queued
    result["reused"] = reused
    result["counts_present"] = [
        key for key, value in (("queued", queued), ("reused", reused))
        if value is not None
    ]
    # A scan's work fact uses this same stable identity.  Derive it at the
    # projector boundary so action, list, summary, and detail responses cannot
    # drift into different UI-local identifiers.
    if not result.get("work_id") and result.get("scan_id"):
        result["work_id"] = f"automatic-memory:{result['scan_id']}"
    if "errors" in payload:
        result["errors"] = list(payload.get("errors") or ())
    return result


def register_automatic_memory_routes(
    app: Any, control: Any, secured: list[Any]
) -> None:
    """Expose source metadata and scan controls through the existing 8766 auth."""
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
        settings = getattr(control, "settings", control)
        effective_home = getattr(settings, "home_dir", None)
        if effective_home is None:
            configured_env = getattr(settings, "environ", None)
            effective_home = (configured_env if configured_env is not None else os.environ).get("HOME")
        scope = AuthorizationScope(
            grant_id=request.grant_id,
            source_kinds=tuple(request.source_kinds),
            roots=tuple(request.roots),
            granted_at=request.granted_at,
            expires_at=request.expires_at,
            owner_confirmed=request.owner_confirmed,
            effective_home=str(effective_home) if effective_home else None,
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
        if isinstance(result, dict) and result.get("scan_id"):
            # scan_now returns a reconciliation report; the durable scan row
            # is the sole count-evidence authority for action responses.
            try:
                projected = project_scan_dto(registry.get_scan(str(result["scan_id"])))
                projected["work_id"] = result.get("work_id") or f"automatic-memory:{result['scan_id']}"
                # A report can be intentionally non-admitting (for example an
                # expired source) and therefore have no durable scan row.  When
                # a row exists, retain the action outcome fields as well so the
                # action response does not turn a real failure into a neutral
                # scan snapshot.
                for key in ("complete", "errors", "discovered", "unchanged", "next_action"):
                    if key in result:
                        projected[key] = result[key]
                return projected
            except LookupError:
                # Lightweight control doubles may return a report identity
                # without owning the registry row; preserve that compatibility
                # while real runtimes always take the durable branch above.
                return project_scan_dto(result)
        return project_scan_dto(result)

    @app.post("/api/automatic-memory/pause", dependencies=secured)
    def pause_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        result = call(lambda: registry.pause_scan(request.scan_id))
        return project_scan_dto(result)

    @app.post("/api/automatic-memory/retry", dependencies=secured)
    def retry_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        result = call(lambda: registry.retry_scan(request.scan_id))
        return project_scan_dto(result)

    @app.post("/api/automatic-memory/resume", dependencies=secured)
    def resume_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        # Resume is the durable retry transition for a paused scan.
        result = call(lambda: registry.retry_scan(request.scan_id))
        return project_scan_dto(result)

    @app.get("/api/automatic-memory/sources", dependencies=secured)
    def list_sources() -> list[dict[str, Any]]:
        return [asdict(item) for item in registry.list_sources()]

    @app.get("/api/automatic-memory/discovered", dependencies=secured)
    def discovered_sources() -> list[dict[str, Any]]:
        settings = getattr(control, "settings", control)
        result: list[dict[str, Any]] = []
        for item in discover_source_metadata(settings):
            payload = asdict(item)
            # Keep owner actions explicit and machine-readable.  The API does
            # not authorize anything here; the POST route remains the sole
            # authorization boundary.
            if item.kind == "codex_rollout":
                payload["owner_action"] = {
                    "kind": "authorize",
                    "label": "允许接管 Codex",
                    "source_kind": "codex_rollout",
                }
            elif item.kind == "chatgpt_export":
                payload["owner_action"] = {
                    "kind": "select_official_export",
                    "label": "选择官方导出目录",
                    "source_kind": "chatgpt_export",
                }
            result.append(payload)
        return result

    @app.get("/api/automatic-memory/scans", dependencies=secured)
    def list_scans(limit: int = 50) -> list[dict[str, Any]]:
        return [
            project_scan_dto(item)
            for item in registry.state_db.list_automatic_memory_scans()[: min(max(int(limit), 1), 200)]
        ]

    @app.get("/api/automatic-memory/summary", dependencies=secured)
    def scan_summary() -> dict[str, Any]:
        scans = registry.state_db.list_automatic_memory_scans()
        counts: dict[str, int] = {}
        for scan in scans:
            status = str(scan.get("status") or "unknown")
            counts[status] = counts.get(status, 0) + 1
        latest = project_scan_dto(scans[0]) if scans else None
        runtime = getattr(control, "runtime", None)
        scheduler = getattr(runtime, "scheduler", None)
        periodic = getattr(scheduler, "automation_mode", None) == "periodic_reconciliation"
        interval = getattr(scheduler, "next_reconciliation_seconds", None)
        try:
            interval = float(interval) if interval is not None else None
            if interval is not None and (not math.isfinite(interval) or interval <= 0):
                interval = None
        except (TypeError, ValueError):
            interval = None
        if interval is None:
            next_action = "wait for scheduled reconciliation (interval unavailable)" if periodic else "wait for watcher or scheduled reconciliation"
        else:
            minutes = interval / 60.0
            minutes_label = str(int(minutes)) if minutes.is_integer() else f"{minutes:.1f}"
            next_action = f"wait for scheduled reconciliation (at most {minutes_label} minutes)" if periodic else "wait for watcher or scheduled reconciliation"
        return {
            "counts": counts,
            "total": len(scans),
            "latest": latest,
            "progress": {
                "current": int((latest or {}).get("progress") or 0),
                "total": (latest or {}).get("total"),
            },
            "last_error": (latest or {}).get("last_error"),
            "next_action": "retry failed scan" if latest and latest.get("status") == "failed" else next_action,
            "reconciliation_interval_seconds": interval,
            "max_change_detection_delay_seconds": interval,
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
                "automation_mode": None,
                "event_watcher_enabled": None,
                "next_reconciliation_seconds": None,
                "reconciliation_interval_seconds": None,
                "max_change_detection_delay_seconds": None,
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
        return project_scan_dto(result)
