from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import math
from dataclasses import asdict, is_dataclass
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, Field

from src.automatic_memory import AuthorizationScope, SourceRegistry, discover_source_metadata
from src.automatic_memory.home import resolve_effective_home


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
    "unchanged", "next_action", "processing_status", "processing_total",
    "processing_completed", "processing_failed", "processing_pending",
    "processing_counts_present",
)


def project_scan_processing(scan: Any, jobs: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Project extraction progress without treating scan admission as import."""
    payload = asdict(scan) if is_dataclass(scan) else dict(scan)
    scan_status = str(payload.get("status") or "").lower()
    unknown = {
        "processing_status": "scanning" if scan_status in {"running", "paused"} else "scan_completed",
        "processing_total": None,
        "processing_completed": None,
        "processing_failed": None,
        "processing_pending": None,
        "processing_counts_present": [],
    }
    if scan_status in {"failed", "cancelled"}:
        return {**unknown, "processing_status": "failed"}
    if scan_status != "completed":
        return unknown
    if jobs is None:
        return unknown

    statuses = [str(item.get("status") or "unknown").lower() for item in jobs]
    completed = sum(status == "completed" for status in statuses)
    failed = sum(status in {"failed", "cancelled"} for status in statuses)
    pending = sum(status not in {"completed", "failed", "cancelled"} for status in statuses)
    counts = {
        "processing_total": len(jobs),
        "processing_completed": completed,
        "processing_failed": failed,
        "processing_pending": pending,
        "processing_counts_present": [
            "processing_total", "processing_completed", "processing_failed", "processing_pending"
        ],
    }
    if pending:
        status = "processing"
    elif completed and failed:
        status = "partial_failure"
    elif failed:
        status = "failed"
    elif completed:
        status = "imported"
    else:
        total = payload.get("total")
        queued = payload.get("queued_count", payload.get("queued"))
        reused = payload.get("reused_count", payload.get("reused"))
        if total == 0:
            status = "empty"
        elif isinstance(total, int) and total > 0 and queued == 0 and reused == 0:
            status = "unsupported_format"
        else:
            status = "scan_completed"
    return {"processing_status": status, **counts}


def project_scan_dto(scan: Any, jobs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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
    result.update(project_scan_processing(payload, jobs))
    return result


_SCAN_ITEM_NAME_FALLBACK = "无法安全显示名称"
_SCAN_ITEM_SOURCE_LABELS = {
    "chatgpt_export": "ChatGPT导出记录",
    "codex_rollout": "Codex聊天记录",
    "codex_transcript": "Codex聊天记录",
    "codex": "Codex聊天记录",
    "codex_history": "Codex聊天记录",
}
_SCAN_ITEM_REASON_MAP = {
    ("snapshot", "recorded"): "已记录到扫描清单",
    ("queued", "waiting"): "等待进入提取队列",
    ("extracting", "processing"): "正在提取来源内容",
    ("completed", "imported"): "已导入结构化结果",
    ("completed", "reused"): "命中复用，未重复导入",
    ("completed", "failed"): "提取失败",
    ("completed", "cancelled"): "提取已取消",
}


def _scan_item_id(scan_id: str, relative_path: str) -> str:
    return hashlib.sha256(f"{scan_id}\0{relative_path}".encode("utf-8")).hexdigest()


def _scan_item_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _latest_scan_item_timestamp(*values: Any) -> str | None:
    latest_value = None
    latest_timestamp: datetime | None = None
    for value in values:
        timestamp = _scan_item_timestamp(value)
        if timestamp is None:
            continue
        if latest_timestamp is None or timestamp > latest_timestamp:
            latest_timestamp = timestamp
            latest_value = str(value)
    return latest_value


def _normalized_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def _safe_scan_item_name(relative_path: Any) -> str:
    raw = str(relative_path or "")
    if not raw:
        return _SCAN_ITEM_NAME_FALLBACK
    if any(ord(char) < 32 or ord(char) == 127 for char in raw):
        return _SCAN_ITEM_NAME_FALLBACK
    path = PurePosixPath(raw)
    if path.is_absolute():
        return _SCAN_ITEM_NAME_FALLBACK
    if any(part in {"", ".", ".."} for part in path.parts):
        return _SCAN_ITEM_NAME_FALLBACK
    if path.as_posix() != raw:
        return _SCAN_ITEM_NAME_FALLBACK
    first = path.parts[0] if path.parts else ""
    if ":" in first:
        return _SCAN_ITEM_NAME_FALLBACK
    lowered = raw.lower()
    if any(marker in lowered for marker in ("secret", "token", "password", "passwd", "credential", "cookie", ".env", "apikey", "api_key")):
        return _SCAN_ITEM_NAME_FALLBACK
    if any(part.startswith(".") and part not in {".", ".."} for part in path.parts):
        return _SCAN_ITEM_NAME_FALLBACK
    return raw


def _scan_item_counts(queue_result: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    structured = queue_result.get("structured_read_model")
    if not isinstance(structured, dict):
        return None, None, None
    return (
        _normalized_int(structured.get("sources")),
        _normalized_int(structured.get("conversations")),
        _normalized_int(structured.get("messages")),
    )


def _scan_item_result_and_stage(
    queue_item: dict[str, Any] | None,
) -> tuple[str, str, bool, int | None, int | None, int | None]:
    if queue_item is None:
        return "snapshot", "recorded", False, None, None, None

    status = str(queue_item.get("status") or "").lower()
    queue_result = queue_item.get("result") if isinstance(queue_item.get("result"), dict) else {}
    if status in {"queued", "retrying"}:
        return "queued", "waiting", False, None, None, None
    if status == "running":
        return "extracting", "processing", False, None, None, None
    if status == "cancelled":
        return "completed", "cancelled", True, None, None, None
    if status == "failed":
        return "completed", "failed", True, None, None, None
    if status == "completed":
        imported_sources, imported_conversations, imported_messages = _scan_item_counts(queue_result)
        if any(value is not None for value in (imported_sources, imported_conversations, imported_messages)):
            return "completed", "imported", False, imported_sources, imported_conversations, imported_messages
        if _normalized_int(queue_result.get("reused")) is not None or _normalized_int(queue_result.get("reused_count")) is not None:
            return "completed", "reused", False, None, None, None
        return "completed", "imported", False, None, None, None
    return "queued", "waiting", False, None, None, None


def project_scan_item(
    scan_id: str,
    relative_path: str,
    *,
    source_id: str = "",
    source_kind: str = "",
    manifest_item: dict[str, Any] | None = None,
    queue_item: dict[str, Any] | None = None,
    reused: bool = False,
) -> dict[str, Any]:
    payload = queue_item.get("payload") if isinstance(queue_item, dict) and isinstance(queue_item.get("payload"), dict) else {}
    item_source_id = ""
    if manifest_item is not None:
        item_source_id = str(manifest_item.get("source_id") or "")
    if not item_source_id:
        item_source_id = str(payload.get("source_id") or "")
    ownership_ok = bool(item_source_id and item_source_id == str(source_id))
    if reused:
        stage, result, retryable = "completed", "reused", False
        imported_sources = imported_conversations = imported_messages = None
    else:
        stage, result, retryable, imported_sources, imported_conversations, imported_messages = _scan_item_result_and_stage(queue_item)
    updated_at = _latest_scan_item_timestamp(
        manifest_item.get("updated_at") if manifest_item else None,
        queue_item.get("updated_at") if queue_item else None,
    )
    reason = _SCAN_ITEM_REASON_MAP.get((stage, result), "状态已更新")
    return {
        "item_id": _scan_item_id(scan_id, relative_path),
        "name": _safe_scan_item_name(relative_path) if ownership_ok else _SCAN_ITEM_NAME_FALLBACK,
        "source": _SCAN_ITEM_SOURCE_LABELS.get(str(source_kind), "已授权来源"),
        "stage": stage,
        "result": result,
        "reason": reason,
        "updated_at": updated_at,
        "retryable": retryable,
        "imported_sources": imported_sources,
        "imported_conversations": imported_conversations,
        "imported_messages": imported_messages,
    }


def register_automatic_memory_routes(
    app: Any, control: Any, secured: list[Any]
) -> None:
    """Expose source metadata and scan controls through the existing 8766 auth."""
    from fastapi import HTTPException, Query

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

    def jobs_for_scan(scan_id: str) -> list[dict[str, Any]] | None:
        runtime = getattr(control, "runtime", None)
        queue = getattr(runtime, "queue", None) or getattr(control, "queue", None)
        if queue is None or not hasattr(queue, "list_page"):
            return None
        try:
            jobs: list[dict[str, Any]] = []
            offset = 0
            page_size = 100
            while True:
                page = queue.list_page(
                    source_type="automatic_memory_snapshot",
                    scan_id=scan_id,
                    limit=page_size,
                    offset=offset,
                )
                jobs.extend(page)
                if len(page) < page_size:
                    break
                offset += page_size
            return jobs
        except TypeError:
            jobs = []
            offset = 0
            page_size = 100
            while True:
                page = queue.list_page(
                    source_type="automatic_memory_snapshot",
                    limit=page_size,
                    offset=offset,
                )
                jobs.extend(
                    item for item in page
                    if str((item.get("payload") or {}).get("scan_id") or "") == scan_id
                )
                if len(page) < page_size:
                    break
                offset += page_size
            return jobs

    def scan_items_for_scan(scan_id: str, *, limit: int, offset: int) -> dict[str, Any]:
        scan = registry.get_scan(scan_id)
        source_id = str(scan.source_id)
        source = registry.state_db.get_automatic_memory_source(source_id)
        source_kind = str((source or {}).get("kind") or "")
        manifest_items = {
            str(item.get("relative_path") or ""): item
            for item in registry.state_db.list_automatic_memory_scan_items(scan_id)
        }
        queue_items = jobs_for_scan(scan_id) or []
        merged: dict[str, dict[str, Any]] = {
            relative_path: {"manifest_item": manifest_item, "queue_item": None}
            for relative_path, manifest_item in manifest_items.items()
        }
        def newest(current: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
            if current is None:
                return candidate
            current_key = (_scan_item_timestamp(current.get("updated_at")) or datetime.min.replace(tzinfo=timezone.utc), str(current.get("job_id") or ""))
            candidate_key = (_scan_item_timestamp(candidate.get("updated_at")) or datetime.min.replace(tzinfo=timezone.utc), str(candidate.get("job_id") or ""))
            return candidate if candidate_key > current_key else current

        for item in queue_items:
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            relative_path = str(payload.get("relative_path") or "")
            if not relative_path:
                continue
            entry = merged.setdefault(
                relative_path,
                {"manifest_item": None, "queue_item": None},
            )
            entry["queue_item"] = newest(entry["queue_item"], item)
        runtime = getattr(control, "runtime", None)
        queue = getattr(runtime, "queue", None) or getattr(control, "queue", None)
        ordered = []
        for relative_path, entry in sorted(
            merged.items(), key=lambda item: (_safe_scan_item_name(item[0]), item[0])
        ):
            reuse_item = None
            if entry["queue_item"] is None and entry["manifest_item"] and queue is not None:
                lookup = getattr(queue, "list_snapshot_identity", None)
                if lookup is not None:
                    manifest = entry["manifest_item"]
                    candidates = lookup(
                        source_id=source_id,
                        relative_path=relative_path,
                        sha256=manifest.get("sha256"),
                    )
                    if not candidates and manifest.get("sha256") is None:
                        candidates = lookup(source_id=source_id, relative_path=relative_path)
                    reuse_item = candidates[0] if candidates else None
            ordered.append(project_scan_item(
                scan_id, relative_path, source_id=source_id, source_kind=source_kind,
                manifest_item=entry["manifest_item"],
                queue_item=entry["queue_item"] or reuse_item,
                reused=reuse_item is not None,
            ))
        total = len(ordered)
        page_items = ordered[offset : offset + limit]
        return {
            "items": page_items,
            "items_pagination": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "has_more": offset + limit < total,
            },
        }

    def project(scan: Any) -> dict[str, Any]:
        payload = asdict(scan) if is_dataclass(scan) else dict(scan)
        scan_id = str(payload.get("scan_id") or "")
        return project_scan_dto(payload, jobs_for_scan(scan_id) if scan_id else None)

    @app.post("/api/automatic-memory/authorize", dependencies=secured)
    def authorize_source(request: AutomaticMemoryAuthorizationRequest) -> dict[str, Any]:
        settings = getattr(control, "settings", control)
        configured_env = getattr(settings, "environ", None)
        effective_home = resolve_effective_home(settings, configured_env)
        scope = AuthorizationScope(
            grant_id=request.grant_id,
            source_kinds=tuple(request.source_kinds),
            roots=tuple(request.roots),
            granted_at=request.granted_at,
            expires_at=request.expires_at,
            owner_confirmed=request.owner_confirmed,
            effective_home=str(effective_home),
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
                projected = project(registry.get_scan(str(result["scan_id"])))
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
        return project(result)

    @app.post("/api/automatic-memory/pause", dependencies=secured)
    def pause_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        result = call(lambda: registry.pause_scan(request.scan_id))
        return project(result)

    @app.post("/api/automatic-memory/retry", dependencies=secured)
    def retry_scan(request: AutomaticMemoryScanActionRequest) -> dict[str, Any]:
        result = call(lambda: registry.retry_scan(request.scan_id))
        return project(result)

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
            project(item)
            for item in registry.state_db.list_automatic_memory_scans()[: min(max(int(limit), 1), 200)]
        ]

    @app.get("/api/automatic-memory/summary", dependencies=secured)
    def scan_summary() -> dict[str, Any]:
        scans = registry.state_db.list_automatic_memory_scans()
        counts: dict[str, int] = {}
        for scan in scans:
            status = str(scan.get("status") or "unknown")
            counts[status] = counts.get(status, 0) + 1
        latest = project(scans[0]) if scans else None
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
    def get_scan(
        scan_id: str,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        result = call(lambda: registry.get_scan(scan_id))
        payload = project(result)
        payload.update(scan_items_for_scan(scan_id, limit=limit, offset=offset))
        return payload
