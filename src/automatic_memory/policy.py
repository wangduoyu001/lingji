"""Platform-aware policy for automatic-memory event admission."""

from __future__ import annotations

import sys


def resolve_event_watcher_enabled(
    configured: bool | None,
    *,
    platform_name: str | None = None,
) -> bool:
    """Resolve event admission with an injectable platform value.

    Darwin defaults to the safe periodic fallback. Other platforms retain the
    historical event-watcher default unless configuration explicitly overrides
    it.
    """
    if configured is not None:
        return bool(configured)
    current_platform = str(platform_name or sys.platform).strip().lower()
    return current_platform != "darwin"
