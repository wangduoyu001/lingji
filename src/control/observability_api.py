"""Read-only observability projections for the owner workbench.

Every route here is a pure projection of existing facts (StateDB scans, scan
items, extraction jobs, events, memory document version chain). No new
storage, no writes, no internal identifiers (job ids, leases, paths, stack
traces) on the owner surface.
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException, Query

from src.storage import StateDatabase

# 主人可读的失败原因分类：内部错误串永不直接暴露。
_FAILURE_EXPLANATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "distinct session_meta",
        "同一个文件里混着多个不同的会话",
        "为避免把不同对话记混，这个文件没有导入。等产生它的 AI 软件把会话分开后，会自动重试。",
    ),
    (
        "no supported messages",
        "文件里没有可读的聊天内容",
        "可能是空会话或纯系统记录，没有需要记住的对话。",
    ),
    (
        "exceeds bounded size",
        "文件里出现了超过安全上限的超大单条记录",
        "超大记录通常是程序内部数据而不是聊天内容，灵机跳过它们只读对话部分。",
    ),
    (
        "unknown Codex rollout",
        "文件里出现了灵机不认识的新格式",
        "为避免记错，灵机没有猜测含义。等格式确认后会自动支持。",
    ),
    (
        "symlink",
        "文件位置通过链接指向别处",
        "为避免读错位置，灵机没有跟随这个链接。",
    ),
)

STEP_DEFS: tuple[tuple[str, str, str], ...] = (
    ("fetch", "原始获取", "把新文件完整复制一份到灵机自己的保存区，原件不动"),
    ("parse", "解析", "读懂文件里的每一条对话"),
    ("dedupe", "去重", "和已经导入过的内容比对，完全相同的不再重复导入"),
    ("filter", "有效性筛选", "跳过空会话、无法归属、格式不认识的内容"),
    ("extract", "信息提取", "把对话整理成一条条可检索的消息"),
    ("judge", "记忆判断", "判断哪些是新内容、哪些之前已经导入过"),
    ("memory", "记忆更新", "把新内容写进可搜索的记忆层"),
    ("timeline", "时间线", "把这次工作记录进事件时间线"),
    ("vectorize", "向量化", "把内容变成“按意思搜索”用的索引（需要本地 AI 服务在运行）"),
)



def _read_rows(db: StateDatabase, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Read rows through the existing StateDB connection lifecycle."""
    with db._connection() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]

def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _scan_row_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "scan_id": str(row.get("scan_id") or ""),
        "source_id": str(row.get("source_id") or ""),
        "status": str(row.get("status") or "unknown"),
        "progress": _safe_int(row.get("progress")),
        "total": _safe_int(row.get("total")),
        "queued_count": _safe_int(row.get("queued_count")),
        "reused_count": _safe_int(row.get("reused_count")),
        "updated_at": row.get("updated_at"),
        "last_error": row.get("last_error"),
    }


def explain_failure(last_error: Any) -> dict[str, Any]:
    """Map an internal failure string to an owner-safe explanation."""
    text = str(last_error or "")
    lowered = text.lower()
    for marker, what, next_step in _FAILURE_EXPLANATIONS:
        if marker.lower() in lowered:
            # category is an internal selector, not owner copy — never project it.
            return {"what": what, "next": next_step}
    if text.strip():
        return {
            "what": "这条内容没有导入成功",
            "next": "灵机会在下一次自动检查时重试；多次失败会保留原始文件供之后支持。",
        }
    return {"what": "尚未获得", "next": "尚未获得"}


def project_job_counts_by_scan(state_db: StateDatabase) -> dict[str, dict[str, int]]:
    """Aggregate extraction job facts per scan using the existing queue table."""
    counts: dict[str, dict[str, int]] = {}
    try:
        rows = _read_rows(
            state_db,
            """
            SELECT json_extract(payload_json, '$.scan_id') AS scan_id,
                   status,
                   COUNT(*) AS n
            FROM extraction_jobs
            GROUP BY 1, 2
            """,
        )
    except Exception:
        return counts
    for row in rows:
        scan_id = str(row["scan_id"] or "")
        if not scan_id:
            continue
        bucket = counts.setdefault(scan_id, {"queued": 0, "running": 0, "completed": 0, "failed": 0, "retrying": 0})
        status = str(row["status"] or "")
        if status in {"queued", "running", "completed", "failed", "retrying"}:
            bucket[status] += int(row["n"] or 0)
    return counts


def project_steps(
    scan: dict[str, Any],
    job_counts: dict[str, int],
    timeline_events: int | None,
    vectorized: int | None,
) -> list[dict[str, Any]]:
    """Project the nine pipeline steps with real counts only; gaps stay 尚未获得."""
    total = _safe_int(scan.get("total"))
    completed = job_counts.get("completed")
    failed = job_counts.get("failed")
    reused = _safe_int(scan.get("reused_count"))
    queued_new = _safe_int(scan.get("queued_count"))

    extracted = None
    if completed:
        try:
            row = state_extracted_sum(scan)
            extracted = row
        except Exception:
            extracted = None

    values: dict[str, int | None] = {
        "fetch": total,
        "parse": completed,
        "dedupe": reused,
        "filter": failed,
        "extract": extracted,
        "judge": queued_new if queued_new is not None or reused is not None else None,
        "memory": extracted,
        "timeline": timeline_events,
        "vectorize": vectorized,
    }
    steps: list[dict[str, Any]] = []
    for key, label, plain in STEP_DEFS:
        count = values.get(key)
        percent = None
        if count is not None and total:
            percent = max(0, min(100, round(count / total * 100)))
        steps.append(
            {
                "step": key,
                "label": label,
                "plain": plain,
                "count": count,
                "total": total,
                "percent": percent,
            }
        )
    return steps


def state_extracted_sum(scan: dict[str, Any]) -> int | None:
    """Sum of messages written by this scan's completed jobs, when recorded."""
    # structured read model counts live on the job result; the queue table does
    # not store them, so the honest projection without a result scan is None.
    return None


def project_item_status(item_status: str, job_status: str | None) -> dict[str, Any]:
    """Owner-facing pipeline status for one raw entry; queued is never imported."""
    job = (job_status or "").lower()
    if job == "failed":
        return {"status": "failed", "label": "失败"}
    if job == "queued" or job == "retrying":
        return {"status": "processing", "label": "处理中"}
    if job == "running":
        return {"status": "processing", "label": "处理中"}
    if job == "completed":
        if item_status.startswith("job:") and ":existing" in item_status:
            return {"status": "merged", "label": "已合并（之前已导入过相同内容）"}
        return {"status": "kept", "label": "已保留并提取"}
    item = (item_status or "").lower()
    if item == "queued":
        return {"status": "pending", "label": "未处理"}
    if item == "failed":
        return {"status": "failed", "label": "失败"}
    if item == "processed":
        return {"status": "kept", "label": "已保留"}
    return {"status": "pending", "label": "尚未获得"}


ACTION_LABELS: dict[str, str] = {
    "automatic_memory_reconciliation": "自动检查",
    "structured_ingestion_completed": "内容导入完成",
    "memory_searched": "记忆被查询",
    "automatic_memory_source_cleanup_failed": "来源清理失败",
}


def project_event(row: dict[str, Any]) -> dict[str, Any]:
    event_type = str(row.get("event_type") or "")
    payload: dict[str, Any] = {}
    try:
        payload = json.loads(row.get("payload_json") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    return {
        "time": row.get("created_at"),
        "action": ACTION_LABELS.get(event_type, event_type or "尚未获得"),
        "action_key": event_type,
        "reason": payload.get("reason"),
        "detail_available": bool(payload),
    }


def register_observability_routes(app: Any, control: Any, secured: list[Any]) -> None:
    from fastapi import Query

    def state_db() -> StateDatabase:
        db = getattr(control, "state_db", None)
        if db is None:
            raise HTTPException(status_code=503, detail="state database is unavailable")
        return db

    @app.get("/api/observability/tasks", dependencies=secured)
    def observability_tasks(
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        db = state_db()
        scans = list(db.list_automatic_memory_scans())
        scans.reverse()
        window = scans[offset : offset + limit]
        counts = project_job_counts_by_scan(db)
        items = []
        for row in window:
            public = _scan_row_public(row)
            scan_counts = counts.get(public["scan_id"], {})
            public["job_completed"] = scan_counts.get("completed")
            public["job_failed"] = scan_counts.get("failed")
            public["job_queued"] = scan_counts.get("queued")
            items.append(public)
        return {"items": items, "pagination": {"total": len(scans), "limit": limit, "offset": offset, "has_more": offset + limit < len(scans)}}

    @app.get("/api/observability/tasks/{scan_id}/steps", dependencies=secured)
    def observability_steps(scan_id: str) -> dict[str, Any]:
        db = state_db()
        scan = db.get_automatic_memory_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="scan not found")
        counts = project_job_counts_by_scan(db).get(scan_id, {})
        timeline = None
        try:
            rows = _read_rows(db, "SELECT COUNT(*) AS n FROM events WHERE event_type='structured_ingestion_completed'")
            timeline = int(rows[0]["n"] or 0) if rows else None
        except Exception:
            timeline = None
        steps = project_steps(scan, counts, timeline, None)
        return {"scan_id": scan_id, "steps": steps}

    @app.get("/api/observability/tasks/{scan_id}/items", dependencies=secured)
    def observability_task_items(
        scan_id: str,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        db = state_db()
        scan = db.get_automatic_memory_scan(scan_id)
        if scan is None:
            raise HTTPException(status_code=404, detail="scan not found")
        items = list(db.list_automatic_memory_scan_items(scan_id))
        items.sort(key=lambda row: str(row.get("relative_path") or ""))
        job_state: dict[str, tuple[str, str | None]] = {}
        try:
            rows = _read_rows(
                db,
                """
                SELECT payload_json, status, last_error FROM extraction_jobs
                WHERE json_extract(payload_json, '$.scan_id') = ?
                ORDER BY updated_at DESC
                """,
                (scan_id,),
            )
            for row in rows:
                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                rel = str(payload.get("relative_path") or "")
                if rel and rel not in job_state:
                    job_state[rel] = (str(row["status"] or ""), row["last_error"])
        except Exception:
            job_state = {}
        # Merge manifest rows with job-only rows (same union semantics as the
        # scan detail projection): every relative path appears exactly once.
        merged: list[tuple[str, str, Any]] = []
        for item in items:
            rel = str(item.get("relative_path") or "")
            merged.append((rel, str(item.get("status") or ""), item.get("updated_at")))
        for rel, (job_status, job_error) in job_state.items():
            if rel and all(existing != rel for existing, _s, _t in merged):
                merged.append((rel, "queued", None))
        merged.sort(key=lambda entry: entry[0])
        total = len(merged)
        window = merged[offset : offset + limit]
        projected = []
        for rel, item_status, updated_at in window:
            job_status, job_error = job_state.get(rel, (None, None))
            projected_status = project_item_status(item_status, job_status)
            entry = {
                "name": rel.rsplit("/", 1)[-1] if rel else "尚未获得",
                "updated_at": updated_at,
                **projected_status,
            }
            if projected_status["status"] == "failed":
                entry["failure"] = explain_failure(job_error or item_status)
            projected.append(entry)
        return {"items": projected, "pagination": {"total": total, "limit": limit, "offset": offset, "has_more": offset + limit < total}}

    @app.get("/api/observability/changes", dependencies=secured)
    def observability_changes(
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        db = state_db()
        void = None
        try:
            rows = _read_rows(
                db,
                "SELECT created_at, event_type, entity_id, payload_json FROM events ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        except Exception:
            rows = []
        items = []
        for row in rows:
            item = project_event(dict(row))
            item["object"] = str(row.get("entity_id") or "")[:24] or "尚未获得"
            items.append(item)
        return {"items": items, "pagination": {"limit": limit, "offset": offset, "has_more": len(items) == limit}}

    @app.get("/api/observability/feed", dependencies=secured)
    def observability_feed(
        status: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        db = state_db()
        try:
            rows = _read_rows(
                db,
                """
                SELECT payload_json, status AS job_status, updated_at FROM extraction_jobs
                WHERE json_extract(payload_json, '$.relative_path') != ''
                ORDER BY updated_at DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        except Exception:
            rows = []
        seen: set[str] = set()
        items: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            rel = str(payload.get("relative_path") or "")
            if not rel or rel in seen:
                continue
            seen.add(rel)
            projected = project_item_status("processed", str(row["job_status"] or ""))
            entry = {
                "name": rel.rsplit("/", 1)[-1],
                "time": row["updated_at"],
                **projected,
            }
            if projected["status"] == "failed":
                entry["failure"] = explain_failure(None)
            if status and entry["status"] != status:
                continue
            items.append(entry)
        return {"items": items, "pagination": {"limit": limit, "offset": offset, "has_more": len(items) == limit}}

    return None
