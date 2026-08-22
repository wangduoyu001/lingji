from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import WorkItem
from .store import WorkStore

ACTIVE_WORK_STATUSES = ("pending", "accepted", "running")
FINISHED_WORK_STATUSES = ("completed", "failed", "skipped")


class WorkProjector:
    """Canonical owner-facing read model derived only from WorkStore facts."""

    def __init__(self, store: WorkStore):
        self.store = store

    @staticmethod
    def _serialize(value: Any) -> dict[str, Any] | None:
        return asdict(value) if value is not None else None

    def _detail(self, work: WorkItem, *, event_limit: int = 100) -> dict[str, Any]:
        return {
            "work": asdict(work),
            "events": [asdict(item) for item in self.store.list_events(work.work_id, limit=event_limit)],
            "outcome": self._serialize(self.store.get_outcome(work.work_id)),
            "next_action": self._serialize(self.store.get_next_action(work.work_id)),
            "pending_actions": [
                asdict(item)
                for item in self.store.list_pending(
                    work_id=work.work_id,
                    include_resolved=False,
                    limit=100,
                )
            ],
        }

    def current_work(self, *, event_limit: int = 100) -> dict[str, Any]:
        items = self.store.list_work(limit=1, statuses=ACTIVE_WORK_STATUSES)
        if not items:
            return {
                "work": None,
                "events": [],
                "outcome": None,
                "next_action": None,
                "pending_actions": [],
            }
        return self._detail(items[0], event_limit=event_limit)

    def recent_work(self, *, limit: int = 20) -> dict[str, Any]:
        items = self.store.list_work(limit=limit, statuses=FINISHED_WORK_STATUSES)
        return {"work_items": [asdict(item) for item in items]}

    def work_detail(self, work_id: str, *, event_limit: int = 100) -> dict[str, Any]:
        work = self.store.get_work(work_id)
        if work is None:
            raise LookupError(f"Unknown work item: {work_id}")
        return self._detail(work, event_limit=event_limit)

    def pending_actions(self, *, limit: int = 20) -> dict[str, Any]:
        return {
            "pending_actions": [
                asdict(item)
                for item in self.store.list_pending(
                    limit=limit,
                    include_resolved=False,
                )
            ]
        }

    def timeline(self, work_id: str, *, limit: int = 100) -> dict[str, Any]:
        if self.store.get_work(work_id) is None:
            raise LookupError(f"Unknown work item: {work_id}")
        return {
            "work_id": work_id,
            "events": [asdict(item) for item in self.store.list_events(work_id, limit=limit)],
        }
