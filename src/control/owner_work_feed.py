from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePath
from typing import Any, Iterable, Mapping

_ACTIVE_QUEUE_STATES = {"queued", "leased", "running", "retrying"}
_REVIEW_STATES = {"pending", "pending_review", "needs_review", "awaiting_review", "candidate"}

_SOURCE_LABELS = {
    "chatgpt_export": "ChatGPT 历史",
    "codex_report": "Codex 工作记录",
    "media": "媒体资料",
    "web": "网页资料",
    "text": "文本资料",
    "file": "本地文件",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _safe_relative_path(value: Any) -> str | None:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw or raw.startswith("/") or ":/" in raw or raw.startswith("~/"):
        return None
    parts = [part for part in raw.split("/") if part not in {"", ".", ".."}]
    return "/".join(parts) if parts else None


def _safe_filename(value: Any) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw:
        return ""
    return PurePath(raw).name[:160]


def _source_label(source_type: Any) -> str:
    key = str(source_type or "").strip().lower()
    return _SOURCE_LABELS.get(key, key or "知识库资料")


def _job_time(job: Mapping[str, Any]) -> str:
    return str(job.get("completed_at") or job.get("updated_at") or job.get("created_at") or "")


def _job_title(job: Mapping[str, Any]) -> str:
    payload = _mapping(job.get("payload"))
    title = str(payload.get("title") or "").strip()
    if title:
        return title[:180]
    filename = _safe_filename(job.get("input_path"))
    return filename or _source_label(job.get("source_type"))


def _result_links(job: Mapping[str, Any]) -> set[str]:
    result = _mapping(job.get("result"))
    links: set[str] = set()
    for bucket in ("created", "updated", "skipped"):
        for item in _items(result.get(bucket)):
            relative = _safe_relative_path(item.get("relative_path"))
            if relative:
                links.add(relative)
    for path in result.get("paths") or []:
        relative = _safe_relative_path(path)
        if relative:
            links.add(relative)
    return links


def _result_action(job: Mapping[str, Any]) -> tuple[str, str, str, bool, str | None]:
    """Return stage key, stage label, completed action, owner requirement and next step."""

    status = str(job.get("status") or "unknown").lower()
    result = _mapping(job.get("result"))

    if status == "queued":
        return "intake", "等待处理", "已进入处理队列", False, "灵机会自动开始解析，你现在不用操作"
    if status in {"leased", "running"}:
        return "parse", "正在处理", "正在解析和整理这份资料", False, "灵机会继续自动处理，你现在不用操作"
    if status == "retrying":
        return "parse", "自动重试", "上一次处理未完成，已进入自动重试", False, "灵机会继续重试，你现在不用做技术处理"
    if status == "failed":
        return "issue", "处理未完成", "自动重试已结束，失败原因已保留", False, "这份资料暂未完成，可到任务记录查看原因"
    if status == "cancelled":
        return "stopped", "已停止", "处理任务已取消", False, "不会继续处理，除非你重新提交"
    if status == "completed":
        created = len(_items(result.get("created")))
        updated = len(_items(result.get("updated")))
        skipped = len(_items(result.get("skipped")))
        details = []
        if created:
            details.append(f"新增 {created} 条")
        if updated:
            details.append(f"更新 {updated} 条")
        if skipped:
            details.append(f"跳过 {skipped} 条重复内容")
        suffix = f"（{'，'.join(details)}）" if details else ""
        indexed = result.get("indexed")
        if indexed is True:
            return "retrieve", "已完成，可取回", f"已完成收纳、解析并更新索引{suffix}", False, "已经可以检索，你现在不用操作"
        if indexed is False:
            return "index", "索引待恢复", f"已完成收纳和解析，但索引同步未成功{suffix}", False, "正文已保留，可在高级工具查看索引状态"
        return "complete", "已处理", f"已完成收纳和解析{suffix}", False, "资料已进入知识库，你现在不用操作"
    return "unknown", "状态待确认", "已经记录这份资料，但当前处理状态尚未确认", False, "灵机会继续刷新状态"


def _review_action(memory: Mapping[str, Any]) -> tuple[bool, str | None]:
    review = str(memory.get("review_status") or "").strip().lower()
    if review in _REVIEW_STATES:
        return True, "需要你确认这条候选是否保留"
    return False, None


def _memory_item(memory: Mapping[str, Any], job: Mapping[str, Any] | None) -> dict[str, Any]:
    relative = _safe_relative_path(memory.get("relative_path"))
    title = str(memory.get("title") or "").strip()
    if not title and job is not None:
        title = _job_title(job)
    if not title:
        title = _safe_filename(relative) or str(memory.get("memory_id") or "资料")

    owner_required, owner_label = _review_action(memory)
    if job is not None:
        stage, stage_label, done, job_owner_required, next_step = _result_action(job)
        owner_required = owner_required or job_owner_required
    else:
        stage, stage_label = "memory", "已进入知识库"
        done = "这份资料已经进入灵机知识库"
        next_step = "现在不用你操作，可直接在记忆中查看"

    if owner_required:
        stage, stage_label = "confirm", "等你确认"
        next_step = owner_label or "需要你确认后才能继续"

    source_type = str(job.get("source_type") or "") if job else ""
    occurred_at = (
        _job_time(job)
        if job is not None
        else str(memory.get("modified_at") or memory.get("updated_at") or "")
    )
    return {
        "id": str(memory.get("memory_id") or relative or title),
        "memory_id": str(memory.get("memory_id") or "") or None,
        "title": title[:180],
        "source": _source_label(source_type),
        "source_type": source_type or None,
        "relative_path": relative,
        "memory_type": str(memory.get("memory_type") or "") or None,
        "stage": stage,
        "stage_label": stage_label,
        "status": str(job.get("status") or memory.get("status") or "unknown") if job else str(memory.get("status") or "unknown"),
        "done": done,
        "next_step": next_step,
        "owner_action_required": owner_required,
        "owner_action_label": owner_label,
        "occurred_at": occurred_at or None,
    }


def _job_only_item(job: Mapping[str, Any]) -> dict[str, Any]:
    stage, stage_label, done, owner_required, next_step = _result_action(job)
    return {
        "id": str(job.get("job_id") or _job_title(job)),
        "memory_id": None,
        "title": _job_title(job),
        "source": _source_label(job.get("source_type")),
        "source_type": str(job.get("source_type") or "") or None,
        "relative_path": None,
        "memory_type": None,
        "stage": stage,
        "stage_label": stage_label,
        "status": str(job.get("status") or "unknown"),
        "done": done,
        "next_step": next_step,
        "owner_action_required": owner_required,
        "owner_action_label": None,
        "occurred_at": _job_time(job) or None,
    }


def _activity(event: Mapping[str, Any]) -> dict[str, Any] | None:
    event_type = str(event.get("event_type") or "").strip()
    payload = _mapping(event.get("payload"))
    known = {
        "capture_submitted": ("已接收新资料", "资料已进入自动处理流程", "active"),
        "capture_duplicate": ("发现重复资料并跳过", "没有创建重复任务或重复记忆", "done"),
        "capture_job_retried": ("失败任务已自动重试", "原失败记录仍保留", "active"),
        "capture_job_cancelled": ("资料处理任务已停止", "历史记录仍保留", "waiting"),
        "extraction_document_created": ("已创建一条知识记录", "新资料已写入知识库", "done"),
        "extraction_document_updated": ("已更新一条知识记录", "已有资料已按最新内容更新", "done"),
        "extraction_document_skipped": ("重复内容已跳过", "没有重复写入知识库", "done"),
        "autopilot_repair": ("已自动修复运行问题", "修复后已经重新检查", "done"),
        "autopilot_cycle_failed": ("自动巡检暂时失败", "系统会在下一轮继续检查", "issue"),
    }
    if event_type not in known:
        return None
    title, detail, tone = known[event_type]
    source_type = payload.get("source_type")
    if event_type == "capture_submitted" and source_type:
        title = f"已接收{_source_label(source_type)}"
    return {
        "id": str(event.get("event_id") or f"{event_type}:{event.get('created_at') or ''}"),
        "title": title,
        "detail": detail,
        "tone": tone,
        "occurred_at": str(event.get("created_at") or "") or None,
    }


def build_owner_work_feed(
    *,
    memories: Iterable[Mapping[str, Any]] | None,
    jobs: Iterable[Mapping[str, Any]] | None,
    events: Iterable[Mapping[str, Any]] | None = None,
    expected_documents: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Build a read-only owner view from existing facts without creating a second source of truth."""

    selected_limit = max(min(int(limit), 50), 1)
    memory_rows = [dict(item) for item in (memories or []) if isinstance(item, Mapping)]
    job_rows = [dict(item) for item in (jobs or []) if isinstance(item, Mapping)]
    job_rows.sort(key=_job_time, reverse=True)

    by_relative: dict[str, dict[str, Any]] = {}
    for job in job_rows:
        for relative in _result_links(job):
            by_relative.setdefault(relative, job)

    feed: list[dict[str, Any]] = []
    matched_jobs: set[str] = set()
    for memory in memory_rows:
        relative = _safe_relative_path(memory.get("relative_path"))
        job = by_relative.get(relative or "")
        if job is not None and job.get("job_id"):
            matched_jobs.add(str(job["job_id"]))
        feed.append(_memory_item(memory, job))

    for job in job_rows:
        job_id = str(job.get("job_id") or "")
        if job_id and job_id in matched_jobs:
            continue
        status = str(job.get("status") or "").lower()
        if status in _ACTIVE_QUEUE_STATES or status in {"failed", "completed", "cancelled"}:
            feed.append(_job_only_item(job))

    feed.sort(key=lambda item: str(item.get("occurred_at") or ""), reverse=True)
    feed = feed[:selected_limit]

    expected = int(expected_documents) if isinstance(expected_documents, int) else None
    details_state = "ready"
    details_message = ""
    if expected is not None and expected > 0 and not memory_rows:
        details_state = "unavailable"
        details_message = f"系统统计到 {expected} 份资料，但当前无法读取具体明细。灵机不会用一个数字代替资料列表。"

    owner_count = sum(1 for item in feed if item["owner_action_required"])
    active_count = sum(1 for item in feed if str(item["status"]).lower() in _ACTIVE_QUEUE_STATES)
    issue_count = sum(1 for item in feed if item["stage"] == "issue")
    activity = [entry for event in (events or []) if isinstance(event, Mapping) if (entry := _activity(event))]

    return {
        "schema_version": 1,
        "as_of": _now(),
        "state": "degraded" if details_state == "unavailable" else "ready",
        "details_state": details_state,
        "details_message": details_message,
        "summary": {
            "visible_items": len(feed),
            "expected_documents": expected,
            "needs_owner": owner_count,
            "active": active_count,
            "issues": issue_count,
        },
        "items": feed,
        "recent_activity": activity[:8],
    }
