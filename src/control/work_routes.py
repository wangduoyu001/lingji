from __future__ import annotations

from typing import Any, Callable


def register_work_routes(
    app: Any,
    control: Any,
    secured: list[Any],
    *,
    translate_error: Callable[[Exception], Exception] | None = None,
) -> None:
    """Register the canonical owner-facing Work Fact read API on 8766."""

    def guarded(call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            return call()
        except Exception as exc:
            if translate_error is not None:
                raise translate_error(exc) from exc
            raise

    @app.get("/api/work/current", dependencies=secured)
    def current_work() -> dict[str, Any]:
        return guarded(control.current_work)

    @app.get("/api/work/recent", dependencies=secured)
    def recent_work(limit: int = 20) -> dict[str, Any]:
        return guarded(lambda: control.recent_work(limit=limit))

    @app.get("/api/work/pending-actions", dependencies=secured)
    def pending_actions(limit: int = 20) -> dict[str, Any]:
        return guarded(lambda: control.pending_actions(limit=limit))

    @app.get("/api/work/timeline/{work_id}", dependencies=secured)
    def work_timeline(work_id: str, limit: int = 100) -> dict[str, Any]:
        return guarded(lambda: control.work_timeline(work_id, limit=limit))

    # Dynamic route intentionally comes after the static work routes above.
    @app.get("/api/work/{work_id}", dependencies=secured)
    def work_detail(work_id: str) -> dict[str, Any]:
        return guarded(lambda: control.work_detail(work_id))
