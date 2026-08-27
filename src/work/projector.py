from __future__ import annotations

from typing import Any

from .store import WorkStore


class WorkProjector:
    """Read model for Desktop views. UI should consume facts, not invent state."""

    def __init__(self, store: WorkStore):
        self.store = store

    @staticmethod
    def _dump(value: Any) -> dict[str, Any] | None:
        return dict(value.__dict__) if value is not None else None

    def fact(self, work_id: str) -> dict[str, Any]:
        self.store.reconcile_extraction_jobs()
        if self.store.get_work(work_id) is None:
            raise LookupError(f"work not found: {work_id}")
        outcome = self.store.get_outcome(work_id)
        return {
            "work": self._dump(self.store.get_work(work_id)),
            "events": [dict(item.__dict__) for item in self.store.list_events(work_id)],
            "outcome": self._dump(outcome),
            "next_action": self._dump(self.store.get_next_action(work_id)),
            "pending_actions": [dict(item.__dict__) for item in self.store.list_pending(work_id=work_id)],
            "failure": self._dump(self.store.get_failure(work_id)) if outcome and outcome.status == "failed" else None,
        }

    def current_fact(self) -> dict[str, Any]:
        self.store.reconcile_extraction_jobs()
        work = self.store.list_work(limit=1)
        return self.fact(work[0].work_id) if work else {"work": None, "events": [], "outcome": None, "next_action": None, "pending_actions": [], "failure": None}

    def current_work(self) -> dict[str, Any]:
        return self.current_fact()

    def pending_actions(self, limit: int = 20) -> dict[str, Any]:
        self.store.reconcile_extraction_jobs()
        return {"pending_actions": [dict(item.__dict__) for item in self.store.list_pending(limit=limit)]}

    @staticmethod
    def _friendly_summary(fact: dict[str, Any]) -> dict[str, Any]:
        work = fact.get("work") or {}
        outcome = fact.get("outcome") or {}
        next_action = fact.get("next_action") or {}
        pending = fact.get("pending_actions") or []
        status = str(outcome.get("status") or work.get("status") or "")
        phase = {
            "pending": "等待处理",
            "accepted": "已接收",
            "running": "处理中",
            "retrying": "重试中",
            "completed": "已完成",
            "success": "已完成",
            "failed": "处理失败",
        }.get(status)
        result = {
            "completed": "成功",
            "success": "成功",
            "failed": "失败",
        }.get(str(outcome.get("status") or ""))
        actor = next_action.get("actor") or (pending[0].get("actor") if pending else None)
        return {
            "phase": phase,
            "result": result,
            "time": work.get("updated_at") or outcome.get("created_at") or work.get("created_at"),
            "source": "已关联来源" if work.get("source_id") else None,
            "next_actor": {"owner": "主人", "system": "灵机"}.get(str(actor), None) if actor else None,
        }

    def history(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        if int(limit) < 1 or int(limit) > 100 or int(offset) < 0:
            raise ValueError("limit must be between 1 and 100 and offset must not be negative")
        self.store.reconcile_extraction_jobs()
        works = self.store.list_work(limit=int(limit), offset=int(offset))
        items: list[dict[str, Any]] = []
        for work in works:
            fact = self.fact(work.work_id)
            fact["summary"] = self._friendly_summary(fact)
            items.append(fact)
        total = self.store.count_work()
        return {"items": items, "limit": int(limit), "offset": int(offset), "total": total, "has_more": int(offset) + len(items) < total}

    def resolve_pending(self, action_id: str) -> dict[str, Any]:
        action = self.store.resolve_pending_action(action_id)
        return {"action_id": action.action_id, "work_id": action.work_id, "resolved": action.resolved}

    def timeline(self, work_id: str, limit: int = 100) -> dict[str, Any]:
        fact = self.fact(work_id)
        fact["events"] = [dict(item.__dict__) for item in self.store.list_events(work_id, limit=limit, ascending=True)]
        return fact
