"""跨 AI 时间线聚合：同一主题的蒸馏要点 + 记忆检索按时间归并。

主人需求（2026-09-23）：多个 AI 在同一项目的不同时间结论要能整理到一起迭代。
蒸馏层（distilled_knowledge，含 conversation 发生时间）与记忆层（memory_documents，
含 updated_at）各自按关键词取回后，这里做纯函数归并：按时间排序、带来源标注、
token 受控（每条截断 + 总量上限）。
"""

from __future__ import annotations

from typing import Any

_DISTILLED_SNIPPET_CHARS = 220
_MEMORY_SNIPPET_CHARS = 180

TIMELINE_ITEM_FIELDS = (
    "occurred_at",
    "kind",
    "title",
    "summary",
    "source",
    "source_id",
    "category",
    "memory_type",
)


def build_timeline(
    topic: str,
    distilled_entries: list[dict[str, Any]],
    memory_results: list[dict[str, Any]],
    *,
    limit: int = 20,
    max_chars: int = 6000,
) -> dict[str, Any]:
    """归并两个来源为按时间倒序的时间线；不写任何数据。"""
    items: list[dict[str, Any]] = []
    for entry in distilled_entries:
        occurred = str(entry.get("occurred_at") or entry.get("created_at") or "")
        items.append(
            {
                "occurred_at": occurred,
                "kind": "distilled",
                "title": str(entry.get("title") or "")[:120],
                "summary": _snippet(entry.get("summary"), _DISTILLED_SNIPPET_CHARS),
                "source": "distilled_knowledge",
                "source_id": str(entry.get("source_id") or ""),
                "category": str(entry.get("category") or ""),
                "memory_type": "",
                "_key_points": [
                    str(point) for point in (entry.get("key_points") or [])[:3] if str(point).strip()
                ],
            }
        )
    for result in memory_results:
        items.append(
            {
                "occurred_at": str(result.get("updated_at") or ""),
                "kind": "memory",
                "title": str(result.get("title") or "")[:120],
                "summary": _snippet(
                    result.get("text") or result.get("heading"), _MEMORY_SNIPPET_CHARS
                ),
                "source": "memory_index",
                "source_id": str(result.get("memory_id") or ""),
                "category": "",
                "memory_type": str(result.get("memory_type") or ""),
            }
        )
    items.sort(key=lambda item: item.get("occurred_at") or "", reverse=True)

    total = len(items)
    bounded: list[dict[str, Any]] = []
    used = 0
    truncated = False
    for item in items:
        if len(bounded) >= max(int(limit), 1):
            truncated = True
            break
        payload = {key: item.get(key, "") for key in TIMELINE_ITEM_FIELDS}
        key_points = item.get("_key_points") or []
        if key_points:
            payload["key_points"] = key_points
        cost = len(str(payload.get("summary") or "")) + len(str(payload.get("title") or "")) + 80
        if bounded and used + cost > max(int(max_chars), 200):
            truncated = True
            break
        used += cost
        bounded.append(payload)
    return {
        "topic": str(topic or ""),
        "items": bounded,
        "total_matches": total,
        "returned": len(bounded),
        "truncated": truncated,
        "detail_hint": "use fetch_memory(memory_id) for full content of a memory item",
    }


def _snippet(value: Any, cap: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= cap:
        return text
    return text[: max(cap - 1, 0)] + "…"


__all__ = ["build_timeline"]
