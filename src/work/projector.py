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
        return {
            "work": self._dump(self.store.get_work(work_id)),
            "events": [dict(item.__dict__) for item in self.store.list_events(work_id)],
            "outcome": self._dump(self.store.get_outcome(work_id)),
            "next_action": self._dump(self.store.get_next_action(work_id)),
            "pending_actions": [dict(item.__dict__) for item in self.store.list_pending(work_id=work_id)],
            "failure": self._dump(self.store.get_failure(work_id)),
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

    def timeline(self, work_id: str, limit: int = 100) -> dict[str, Any]:
        fact = self.fact(work_id)
        fact["events"] = [dict(item.__dict__) for item in self.store.list_events(work_id, limit=limit)]
        return fact
