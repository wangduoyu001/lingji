from __future__ import annotations

import sqlite3
from typing import Any


def register_work_routes(app: Any, control: Any, secured: list[Any]) -> None:
    """Register work fact read-model routes.

    The routes intentionally depend on LocalControlService so Desktop and other
    clients consume the same work facts instead of rebuilding state locally.
    """

    from fastapi import HTTPException, Query

    def safe(call: Any) -> Any:
        try:
            return call()
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="work fact not found") from exc
        except sqlite3.Error as exc:
            raise HTTPException(status_code=503, detail={"code": "WORK_FACT_UNAVAILABLE", "message": "Work Fact is temporarily unavailable"}) from exc

    @app.get('/api/work/current', dependencies=secured)
    def current_work() -> dict[str, Any]:
        return safe(control.current_work)

    @app.get('/api/work/pending-actions', dependencies=secured)
    def pending_actions() -> dict[str, Any]:
        return safe(control.pending_actions)

    @app.get('/api/work/history', dependencies=secured)
    def work_history(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        return safe(lambda: control.work_history(limit=limit, offset=offset))

    @app.get('/api/work/timeline/{work_id}', dependencies=secured)
    def work_timeline(work_id: str) -> dict[str, Any]:
        return safe(lambda: control.work_timeline(work_id))

    @app.post('/api/work/pending-actions/{action_id}/resolve', dependencies=secured)
    def resolve_pending(action_id: str) -> dict[str, Any]:
        return safe(lambda: control.resolve_pending(action_id))
