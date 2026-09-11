"""Read-only observability projections for the owner workbench.

Every route here is a pure projection of existing facts (StateDB scans, scan
items, extraction jobs, events, memory document version chain). No new
storage, no writes, no internal identifiers (job ids, leases, paths, stack
traces) on the owner surface.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Query

from src.retrieval.vector_backfill import VectorBackfill
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


def project_job_result_totals(state_db: StateDatabase) -> dict[str, dict[str, int | None]]:
    """Aggregate real per-scan output totals from completed job results:
    messages extracted, memory-layer documents updated, lexical index additions."""
    totals: dict[str, dict[str, int | None]] = {}
    try:
        rows = _read_rows(
            state_db,
            """
            SELECT json_extract(payload_json, '$.scan_id') AS scan_id,
                   result_json
            FROM extraction_jobs
            WHERE status = 'completed'
            ORDER BY updated_at DESC
            """,
        )
    except Exception:
        return totals
    for row in rows:
        scan_id = str(row["scan_id"] or "")
        if not scan_id:
            continue
        try:
            result = json.loads(row["result_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            result = {}
        model = result.get("structured_read_model") or {}
        lexical = model.get("lexical_index") or {}
        bucket = totals.setdefault(
            scan_id,
            {"extracted": 0, "memory_updated": 0, "vectorize": None},
        )
        bucket["extracted"] += _safe_int(model.get("messages")) or 0
        bucket["memory_updated"] += _safe_int(lexical.get("added")) or 0
    return totals


def project_steps(
    scan: dict[str, Any],
    job_counts: dict[str, int],
    timeline_events: int | None,
    vectorized: int | None,
    *,
    extracted: int | None = None,
    memory_updated: int | None = None,
    failure_detail: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Project the nine pipeline steps with real counts only; gaps stay 尚未获得."""
    total = _safe_int(scan.get("total"))
    completed = job_counts.get("completed")
    failed = job_counts.get("failed")
    reused = _safe_int(scan.get("reused_count"))
    queued_new = _safe_int(scan.get("queued_count"))

    values: dict[str, int | None] = {
        "fetch": total,
        "parse": completed,
        "dedupe": reused,
        "filter": failed,
        "extract": extracted,
        "judge": queued_new,
        "memory": memory_updated,
        "timeline": timeline_events,
        "vectorize": vectorized,
    }
    steps: list[dict[str, Any]] = []
    for key, label, plain in STEP_DEFS:
        count = values.get(key)
        percent = None
        if count is not None and total:
            percent = max(0, min(100, round(count / total * 100)))
        step: dict[str, Any] = {
            "step": key,
            "label": label,
            "plain": plain,
            "count": count,
            "total": total,
            "percent": percent,
        }
        if key == "filter" and failed and failure_detail:
            step["failure"] = failure_detail
        steps.append(step)
    return steps


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
        totals = project_job_result_totals(db).get(scan_id, {})
        timeline = None
        try:
            rows = _read_rows(db, "SELECT COUNT(*) AS n FROM events WHERE event_type='structured_ingestion_completed'")
            timeline = int(rows[0]["n"] or 0) if rows else None
        except Exception:
            timeline = None
        steps = project_steps(
            scan,
            counts,
            timeline,
            totals.get("vectorize"),
            extracted=totals.get("extracted"),
            memory_updated=totals.get("memory_updated"),
            failure_detail=explain_failure(scan.get("last_error")) if scan.get("last_error") else None,
        )
        return {"scan_id": scan_id, "steps": steps, "failure": explain_failure(scan.get("last_error")) if scan.get("last_error") else None}

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

    @app.post("/api/observability/vectorize", dependencies=secured)
    def observability_vectorize() -> dict[str, Any]:
        """自动向量化一轮（有界）；由前端自动触发，也可手动兜底。"""
        settings = getattr(control, "settings", control)
        provider_builder = getattr(control, "build_embedding_provider", None)
        if provider_builder is None:
            from src.model_center import build_embedding_provider

            provider_builder = build_embedding_provider
        provider = provider_builder(settings)
        if provider is None:
            raise HTTPException(status_code=503, detail="embedding provider is not configured")
        backfill = VectorBackfill(settings, provider=provider)
        return backfill.run_once(limit=200)

    @app.get("/api/observability/recall", dependencies=secured)
    def observability_recall(
        q: str = Query(min_length=1),
        limit: int = Query(default=10, ge=1, le=50),
    ) -> dict[str, Any]:
        """按意思搜索你的全部对话记忆（语义召回）。"""
        settings = getattr(control, "settings", control)
        provider_builder = getattr(control, "build_embedding_provider", None)
        if provider_builder is None:
            from src.model_center import build_embedding_provider

            provider_builder = build_embedding_provider
        provider = provider_builder(settings)
        if provider is None:
            raise HTTPException(status_code=503, detail="embedding provider is not configured")
        vectors = provider.embed_many([q])
        if not vectors:
            return {"items": [], "query": q}
        from src.retrieval.vector_backfill import VectorBackfill

        backfill = VectorBackfill(settings, provider=provider)
        hits = backfill.search(vectors[0], limit=limit)
        return {"items": hits, "query": q}

    def _distiller() -> Any:
        settings = getattr(control, "settings", control)
        from src.automatic_memory.distillation import KnowledgeDistiller

        # 优先复用 runtime 持有的 daemon 实例：进度/最近云端错误才是真实值。
        runtime = getattr(control, "runtime", None)
        daemon_distiller = getattr(runtime, "_distiller", None)
        if daemon_distiller is not None:
            return daemon_distiller

        try:
            from src.control.runtime_settings import RuntimeSettingsStore

            store = RuntimeSettingsStore(settings)

            def _model_override() -> str:
                return str(store.snapshot()["values"].get("distill_model", "") or "")

            def _provider_override() -> str:
                return str(store.snapshot()["values"].get("distill_provider", "local") or "local")

            def _key_override() -> str:
                return str(store.snapshot()["values"].get("zhipu_api_key", "") or "")

            return KnowledgeDistiller(
                settings,
                model_override=_model_override,
                provider_override=_provider_override,
                api_key_override=_key_override,
            )
        except Exception:
            return KnowledgeDistiller(settings)

    @app.get("/api/observability/knowledge", dependencies=secured)
    def observability_knowledge(
        limit: int = Query(default=30, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        category: str = Query(default=""),
        q: str = Query(default=""),
        order: str = Query(default="occurred"),
    ) -> dict[str, Any]:
        """灵机自动提炼的知识要点：一句话总结 + 要点 + 分类，可搜索。"""
        distiller = _distiller()
        stats = distiller.stats()
        listing = distiller.list_entries(
            limit=limit,
            offset=offset,
            category=category or None,
            query=q or None,
            order=order if order in {"occurred", "updated"} else "occurred",
        )
        listing["stats"] = stats
        try:
            listing["distill_model"] = distiller.configured_model
        except Exception:
            listing["distill_model"] = ""
        try:
            listing["provider"] = distiller.provider
        except Exception:
            listing["provider"] = "local"
        try:
            listing["zhipu_key_set"] = bool(distiller.api_key)
        except Exception:
            listing["zhipu_key_set"] = False
        try:
            listing["progress"] = distiller.progress()
        except Exception:
            listing["progress"] = {"active": False}
        try:
            listing["models"] = distiller.installed_models()
        except Exception:
            listing["models"] = []
        return listing

    @app.post("/api/observability/knowledge/provider", dependencies=secured)
    def observability_knowledge_set_provider(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """切换提炼服务：local（本机）或 zhipu（云端 GLM-4-Flash，需 Key）。"""
        body = payload or {}
        provider = str(body.get("provider") or "local").strip().lower()
        if provider not in {"local", "zhipu"}:
            raise HTTPException(status_code=400, detail="provider must be local or zhipu")
        api_key = str(body.get("api_key") or "").strip()
        settings = getattr(control, "settings", control)
        from src.control.runtime_settings import RuntimeSettingsStore

        values: dict[str, Any] = {"distill_provider": provider}
        if api_key:
            values["zhipu_api_key"] = api_key
        if provider == "zhipu":
            snapshot = RuntimeSettingsStore(settings)
            existing_key = str(snapshot.snapshot()["values"].get("zhipu_api_key", "") or "").strip()
            if not api_key and not existing_key:
                raise HTTPException(status_code=400, detail="zhipu provider requires an api key")
        RuntimeSettingsStore(settings).update(values)
        return {"provider": provider, "zhipu_key_set": bool(api_key) or provider == "zhipu" and bool(values.get("zhipu_api_key"))}

    @app.post("/api/observability/knowledge/model", dependencies=secured)
    def observability_knowledge_set_model(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """主人切换提炼模型：只在已安装的本机模型里选，下一轮提炼立即生效。"""
        body = payload or {}
        requested = str(body.get("model") or "").strip()
        distiller = _distiller()
        installed = {str(entry["name"]) for entry in distiller.installed_models()}
        if requested and requested not in installed:
            raise HTTPException(status_code=400, detail="model is not installed locally")
        settings = getattr(control, "settings", control)
        from src.control.runtime_settings import RuntimeSettingsStore

        snapshot = RuntimeSettingsStore(settings).update({"distill_model": requested})
        return {"distill_model": snapshot["values"].get("distill_model", ""), "installed": sorted(installed)}

    @app.get("/api/observability/knowledge/{conversation_id}", dependencies=secured)
    def observability_knowledge_detail(conversation_id: str) -> dict[str, Any]:
        """单条知识要点详情：提炼结果 + 来源对话原文（追溯）。"""
        distiller = _distiller()
        listing = distiller.list_entries(limit=200, offset=0)
        entry = next((item for item in listing["items"] if item["conversation_id"] == conversation_id), None)
        settings = getattr(control, "settings", control)
        memory_db_raw = str(getattr(settings, "memory_db_path", "") or "").strip()
        if not memory_db_raw:
            storage = str(getattr(settings, "storage_path", "") or "")
            memory_db_raw = str(Path(storage) / "lingji_memory.db") if storage else ""
        messages: list[dict[str, Any]] = []
        if memory_db_raw and Path(memory_db_raw).exists():
            import sqlite3

            with sqlite3.connect(memory_db_raw) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT role, author, content, occurred_at
                    FROM message_records
                    WHERE conversation_id = ?
                    ORDER BY occurred_at ASC, sequence ASC
                    LIMIT 200
                    """,
                    (conversation_id,),
                ).fetchall()
                messages = [dict(row) for row in rows]
        return {"entry": entry, "messages": messages}

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

    @app.get("/api/observability/pipeline", dependencies=secured)
    def observability_pipeline() -> dict[str, Any]:
        """九环节各自的全量数据面板：真实计数 + 每环节明细列表。"""
        db = state_db()
        scans = list(db.list_automatic_memory_scans())
        job_counts = project_job_counts_by_scan(db)

        # 唯一文件口径：每个 relative_path 只算一次（按最新一次任务状态），
        # 避免重复核对把“获取/解析”数字越滚越大。
        try:
            job_rows = _read_rows(
                db,
                """
                SELECT json_extract(payload_json, '$.relative_path') AS rel,
                       json_extract(payload_json, '$.scan_id') AS scan_id,
                       status, updated_at, result_json
                FROM extraction_jobs
                WHERE json_extract(payload_json, '$.relative_path') != ''
                ORDER BY updated_at ASC
                """,
            )
        except Exception:
            job_rows = []
        latest_by_rel: dict[str, dict[str, Any]] = {}
        rounds_by_rel: dict[str, int] = {}
        for row in job_rows:
            rel = str(row["rel"] or "")
            if rel:
                latest_by_rel[rel] = row
                rounds_by_rel[rel] = rounds_by_rel.get(rel, 0) + 1
        unique_files = len(latest_by_rel)
        unique_completed = sum(1 for row in latest_by_rel.values() if str(row["status"]) == "completed")
        unique_failed = sum(1 for row in latest_by_rel.values() if str(row["status"]) == "failed")
        unique_pending = sum(1 for row in latest_by_rel.values() if str(row["status"]) in {"queued", "running", "retrying"})
        scan_rounds = len(scans)

        # 提炼消息/记忆更新：同一文件取最新一次 completed 结果，
        # 直接读取该任务自己的 structured_read_model.messages / lexical_index.added，
        # 绝不把整轮 scan 的合计再按文件累加（那会把数字放大几百倍）。
        extracted_total = 0
        memory_total = 0
        latest_result_by_rel: dict[str, dict[str, Any]] = {}
        for row in reversed(job_rows):
            rel = str(row["rel"] or "")
            status = str(row["status"] or "")
            if rel and status == "completed" and rel not in latest_result_by_rel:
                latest_result_by_rel[rel] = row
        extracted_total = 0
        memory_total = 0
        for rel, row in latest_result_by_rel.items():
            try:
                result = json.loads(row.get("result_json") or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            model = result.get("structured_read_model") or {}
            extracted_total += _safe_int(model.get("messages")) or 0
            lexical = model.get("lexical_index") or {}
            memory_total += _safe_int(lexical.get("added")) or 0

        # 明细列表（脱敏、白名单字段）
        failed_detail: list[dict[str, Any]] = []
        try:
            rows = _read_rows(
                db,
                """
                SELECT payload_json, last_error, updated_at FROM extraction_jobs
                WHERE status = 'failed' ORDER BY updated_at DESC LIMIT 50
                """,
            )
            for row in rows:
                try:
                    payload = json.loads(row["payload_json"] or "{}")
                except (TypeError, ValueError, json.JSONDecodeError):
                    payload = {}
                rel = str(payload.get("relative_path") or "")
                failed_detail.append({
                    "name": rel.rsplit("/", 1)[-1] if rel else "尚未获得",
                    "time": row.get("updated_at"),
                    **explain_failure(row["last_error"]),
                })
        except Exception:
            failed_detail = []

        reused_detail: list[dict[str, Any]] = []
        # 复用明细 = 同一相对路径出现过多轮 completed 任务（第二轮起即复用）
        rounds_by_rel: dict[str, int] = {}
        for row in job_rows:
            rel = str(row["rel"] or "")
            if not rel:
                continue
            rounds_by_rel[rel] = rounds_by_rel.get(rel, 0) + 1
        reused_detail = [
            {"name": rel.rsplit("/", 1)[-1], "time": latest_result_by_rel[rel].get("updated_at")}
            for rel in sorted(latest_result_by_rel)
            if rounds_by_rel.get(rel, 0) > 1
        ][:50]

        latest_scans = [
            {
                "scan_id": str(scan.get("scan_id") or ""),
                "status": str(scan.get("status") or ""),
                "total": _safe_int(scan.get("total")),
                "queued": _safe_int(scan.get("queued_count")),
                "reused": _safe_int(scan.get("reused_count")),
                "completed": job_counts.get(str(scan.get("scan_id") or ""), {}).get("completed"),
                "failed": job_counts.get(str(scan.get("scan_id") or ""), {}).get("failed"),
                "updated_at": scan.get("updated_at"),
            }
            for scan in scans[:10]
        ]

        timeline_rows: list[dict[str, Any]] = []
        try:
            timeline_rows = _read_rows(
                db,
                "SELECT created_at, event_type, entity_id, payload_json FROM events ORDER BY created_at DESC, rowid DESC LIMIT 40",
            )
        except Exception:
            timeline_rows = []

        return {
            "scan_rounds": scan_rounds,
            "pipeline": [
                {"key": "fetch", "label": "原始获取（唯一文件）", "plain": "来源里不重复的文件总数；自动检查会反复核对它们", "count": unique_files},
                {"key": "parse", "label": "解析成功", "plain": "最新一轮成功读出对话内容的文件数", "count": unique_completed},
                {"key": "pending", "label": "待处理", "plain": "还在排队等待提取的文件", "count": unique_pending or None},
                {"key": "dedupe", "label": "去重复用", "plain": "内容与已导入记录相同、跳过重复导入的文件数", "count": sum(1 for rel in latest_result_by_rel if rounds_by_rel.get(rel, 0) > 1)},
                {"key": "filter_failed", "label": "筛选拒绝", "plain": "无法安全解析或归属不明的文件", "count": unique_failed},
                {"key": "extract", "label": "提炼消息", "plain": "从对话里整理出的可检索消息条数（唯一内容）", "count": extracted_total or None},
                {"key": "memory", "label": "记忆层更新", "plain": "写进可搜索记忆层的条目数（唯一内容）", "count": memory_total or None},
                {"key": "vectorize", "label": "向量化", "plain": "按意思搜索用的索引；自动后台补算，无需操作", "count": VectorBackfill.vector_count(getattr(control, "settings", control))},
            ],
            "failed_detail": failed_detail,
            "reused_detail": reused_detail,
            "latest_scans": latest_scans,
            "timeline": [project_event(dict(row)) | {"object": str(row.get("entity_id") or "")[:24]} for row in timeline_rows],
        }

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
