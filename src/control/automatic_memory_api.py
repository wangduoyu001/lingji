from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import math
import threading
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from pydantic import BaseModel, Field

from src.automatic_memory import AuthorizationScope, SourceRegistry, discover_source_metadata
from src.automatic_memory.app_manifest import discover_app_manifest, discover_running_processes
from src.automatic_memory.checkpoint import (
    VALUE_GATE_SKIPPED_STATUS,
    append_value_gate_audit,
    read_value_gate_audit,
)
from src.automatic_memory.home import resolve_effective_home
from src.automatic_memory.job_facts import (
    association_from_status,
    resolve_job_facts,
    summarize_job_facts,
)
from src.automatic_memory.export_inbox import ensure_all_export_inboxes, ensure_export_inbox


class ExportInboxEnsureRequest(BaseModel):
    kind: str = Field(min_length=1)


# PERF_RESOURCE_ROOT_CAUSE_20260927 (A2): the Desktop shell polls these
# discovery endpoints every few seconds from several components, and every
# hit used to rescan the filesystem from scratch (pure-Python, GIL-holding).
# Scan results are cached process-wide behind a short TTL: source discovery
# is day-scale information, so a stale window of this size is invisible to
# the owner while the rescan cost drops to zero.
_DISCOVERY_CACHE_TTL_SECONDS = 60.0
_discovery_cache: dict[str, tuple[float, Any]] = {}
_discovery_cache_lock = threading.Lock()


def cached_discovery_snapshot(key: str, producer: Callable[[], Any]) -> Any:
    now = time.monotonic()
    with _discovery_cache_lock:
        hit = _discovery_cache.get(key)
        if hit is not None and now - hit[0] < _DISCOVERY_CACHE_TTL_SECONDS:
            return hit[1]
    value = producer()
    with _discovery_cache_lock:
        _discovery_cache[key] = (time.monotonic(), value)
    return value


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


class AutomaticMemoryValueGateRescanRequest(BaseModel):
    """按来源撤销入口价值预判拦截；body 可省略表示撤销全部来源。"""

    source_id: str | None = None


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

    facts = summarize_job_facts(jobs)
    completed = facts["completed"]
    imported_completed = facts["imported"]
    failed = facts["failed"]
    pending = facts["pending"]
    counts = {
        "processing_total": facts["total"],
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
    elif imported_completed:
        status = "imported"
    elif completed:
        status = "scan_completed"
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
    if jobs is not None and jobs and str(payload.get("status") or "").lower() == "completed":
        facts = summarize_job_facts(jobs)
        queued = facts["new"]
        reused = facts["reused"]
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
    "chatgpt": "ChatGPT导出记录",
    "codex_rollout": "Codex聊天记录",
    "codex_transcript": "Codex聊天记录",
    "codex": "Codex聊天记录",
    "codex_history": "Codex聊天记录",
    "history_inbox": "通用AI历史记录",
    "generic_ai_history": "通用AI历史记录",
    "obsidian": "Obsidian知识库",
}
_SCAN_ITEM_REASON_MAP = {
    ("snapshot", "recorded"): "已记录到扫描清单",
    ("queued", "waiting"): "等待进入提取队列",
    ("extracting", "processing"): "正在提取来源内容",
    ("completed", "imported"): "已导入结构化结果",
    ("completed", "reused"): "命中复用，未重复导入",
    ("completed", "failed"): "提取失败",
    ("completed", "cancelled"): "提取已取消",
    ("completed", "skipped_by_value_gate"): "入口价值预判跳过（未入队，可重扫撤销）",
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


def _manifest_item_result_and_stage(
    manifest_item: dict[str, Any] | None,
    associated_job: dict[str, Any] | None = None,
) -> tuple[str, str, bool, int | None, int | None, int | None]:
    status = str((manifest_item or {}).get("status") or "processed").lower()
    if associated_job is not None:
        return _scan_item_result_and_stage(associated_job)
    if status == "skipped_by_value_gate":
        return "completed", "skipped_by_value_gate", False, None, None, None
    if status == "reused":
        return "completed", "reused", False, None, None, None
    if status in {"queued", "retrying"}:
        return "queued", "waiting", False, None, None, None
    if status in {"processing", "running"}:
        return "extracting", "processing", False, None, None, None
    if status == "failed":
        return "completed", "failed", True, None, None, None
    if status == "cancelled":
        return "completed", "cancelled", True, None, None, None
    return "snapshot", "recorded", False, None, None, None


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
    elif queue_item is None:
        stage, result, retryable, imported_sources, imported_conversations, imported_messages = _manifest_item_result_and_stage(manifest_item)
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
            associated_jobs = []
            for manifest in registry.state_db.list_automatic_memory_scan_items(scan_id):
                association = association_from_status(manifest.get("status"))
                if association is None:
                    continue
                try:
                    associated = queue.get(association[0])
                except LookupError:
                    continue
                payload = associated.get("payload") if isinstance(associated, dict) else None
                if isinstance(payload, dict) and str(payload.get("source_id") or "") == str(manifest.get("source_id") or "") and str(payload.get("relative_path") or "") == str(manifest.get("relative_path") or ""):
                    associated_jobs.append((associated, association[1]))
            scan = registry.get_scan(scan_id)
            return resolve_job_facts(
                source_id=str(scan.source_id), direct_jobs=jobs,
                associated_jobs=associated_jobs,
            )
        except TypeError:
            return None

    def scan_items_for_scan(scan_id: str, *, limit: int, offset: int) -> dict[str, Any]:
        scan = registry.get_scan(scan_id)
        source_id = str(scan.source_id)
        source = registry.state_db.get_automatic_memory_source(source_id)
        source_kind = str((source or {}).get("kind") or "")
        manifest_items = {
            str(item.get("relative_path") or ""): item
            for item in registry.state_db.list_automatic_memory_scan_items(scan_id)
        }
        queue_items = jobs_for_scan(scan_id)
        merged: dict[str, dict[str, Any]] = {
            relative_path: {"manifest_item": manifest_item, "queue_item": None}
            for relative_path, manifest_item in manifest_items.items()
        }
        for item in queue_items or []:
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            relative_path = str(payload.get("relative_path") or "")
            if not relative_path:
                continue
            entry = merged.setdefault(
                relative_path,
                {"manifest_item": None, "queue_item": None},
            )
            entry["queue_item"] = item
        ordered = []
        for relative_path, entry in sorted(
            merged.items(), key=lambda item: (_safe_scan_item_name(item[0]), item[0])
        ):
            associated_job = entry["queue_item"]
            ordered.append(project_scan_item(
                scan_id, relative_path, source_id=source_id, source_kind=source_kind,
                manifest_item=entry["manifest_item"],
                queue_item=associated_job,
                reused=(
                    isinstance(associated_job, dict)
                    and associated_job.get("_automatic_memory_association") == "existing"
                    and isinstance(associated_job, dict)
                    and str(associated_job.get("status") or "").lower() == "completed"
                ),
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

    def _value_gate_raw_root() -> Path:
        runtime = getattr(control, "runtime", None)
        snapshot = getattr(runtime, "snapshot", None)
        raw_root = getattr(snapshot, "raw_root", None)
        if raw_root:
            return Path(str(raw_root))
        settings = getattr(control, "settings", control)
        return Path(str(getattr(settings, "storage_path", "storage"))) / "raw"

    def _value_gate_current_config() -> tuple[bool, int, int]:
        runtime = getattr(control, "runtime", None)
        runner = getattr(runtime, "runner", None)
        reader = getattr(runner, "_value_gate_config", None)
        if callable(reader):
            try:
                enabled, min_turns, min_chars = reader()
                return bool(enabled), int(min_turns), int(min_chars)
            except Exception:
                pass
        settings = getattr(control, "settings", control)
        return (
            bool(getattr(settings, "value_gate_enabled", False)),
            int(getattr(settings, "value_gate_min_turns", 2)),
            int(getattr(settings, "value_gate_min_chars", 300)),
        )

    @app.get("/api/automatic-memory/value-gate/skipped", dependencies=secured)
    def value_gate_skipped(limit: int = 50) -> dict[str, Any]:
        """被入口价值预判拦下的会话：计数 + 滚动样本（绝不静默）。"""
        enabled, min_turns, min_chars = _value_gate_current_config()
        total, entries = read_value_gate_audit(_value_gate_raw_root(), limit=limit)
        return {
            "enabled": enabled,
            "thresholds": {"min_turns": min_turns, "min_chars": min_chars},
            "total": total,
            "entries": entries,
        }

    @app.post("/api/automatic-memory/value-gate/rescan", dependencies=secured)
    def value_gate_rescan(request: AutomaticMemoryValueGateRescanRequest) -> dict[str, Any]:
        """按来源撤销入口价值预判拦截；下次扫描重新采集、按当前阈值重新判定。"""
        state_db = getattr(control, "state_db", None)
        if state_db is None:
            raise HTTPException(status_code=409, detail="state database is not composed")
        source_id = (request.source_id or "").strip() or None
        cleared = call(lambda: state_db.clear_automatic_memory_scan_items_by_status(
            VALUE_GATE_SKIPPED_STATUS, source_id=source_id
        ))
        # 审计文件追加撤销痕迹（滚动复用），历史记录不物理删除。
        append_value_gate_audit(_value_gate_raw_root(), {
            "action": "rescan_requested",
            "source_id": source_id,
            "cleared": cleared,
            "requested_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        })
        return {"cleared": cleared, "source_id": source_id}

    @app.get("/api/automatic-memory/sources", dependencies=secured)
    def list_sources() -> list[dict[str, Any]]:
        return [asdict(item) for item in registry.list_sources()]

    @app.get("/api/automatic-memory/discovered", dependencies=secured)
    def discovered_sources() -> list[dict[str, Any]]:
        settings = getattr(control, "settings", control)

        def _scan() -> list[dict[str, Any]]:
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

        return cached_discovery_snapshot("discovered", _scan)

    @app.get("/api/automatic-memory/apps", dependencies=secured)
    def installed_ai_apps() -> list[dict[str, Any]]:
        """Owner-facing manifest of locally detected AI software (read-only)."""
        settings = getattr(control, "settings", control)
        return cached_discovery_snapshot("apps", lambda: discover_app_manifest(settings))

    @app.get("/api/automatic-memory/processes", dependencies=secured)
    def running_ai_processes() -> list[dict[str, Any]]:
        """Whitelisted running AI process rows with owner-safe fields only."""
        settings = getattr(control, "settings", control)
        return cached_discovery_snapshot("processes", lambda: discover_running_processes(settings))

    @app.get("/api/automatic-memory/export-inbox", dependencies=secured)
    def export_inbox_list() -> list[dict[str, Any]]:
        """Auto-ensure and report LingJi-owned official-export receiving folders."""
        settings = getattr(control, "settings", control)
        return ensure_all_export_inboxes(settings)

    @app.post("/api/automatic-memory/export-inbox/ensure", dependencies=secured)
    def export_inbox_ensure(request: ExportInboxEnsureRequest) -> dict[str, Any]:
        settings = getattr(control, "settings", control)
        try:
            return ensure_export_inbox(settings, request.kind)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

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
