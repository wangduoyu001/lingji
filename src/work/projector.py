from __future__ import annotations

from typing import Any

from .store import WorkStore


class WorkProjector:
    """Read model for Desktop views. UI should consume facts, not invent state."""

    def __init__(self, store: WorkStore):
        self.store = store

    def current_work(self, limit: int = 20) -> list[dict[str, Any]]:
        return [item.__dict__ for item in self.store.list_work(limit=limit)]

    def pending_actions(self, limit: int = 20) -> list[dict[str, Any]]:
        return [item.__dict__ for item in self.store.list_pending(limit=limit)]

    def timeline(self, work_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return [item.__dict__ for item in self.store.list_events(work_id, limit=limit)]
