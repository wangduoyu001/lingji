"""Platform-aware policy for automatic-memory event admission."""

from __future__ import annotations

import platform


_USE_SYSTEM_PLATFORM = object()
_EVENT_WATCHER_PLATFORMS = frozenset({"windows", "win32", "linux"})


def resolve_event_watcher_enabled(
    configured: bool | None,
    *,
    platform_name: str | None | object = _USE_SYSTEM_PLATFORM,
) -> bool:
    """Resolve event admission with an injectable platform value.

    Darwin defaults to the safe periodic fallback. Other platforms retain the
    historical event-watcher default unless configuration explicitly overrides
    it.
    """
    if configured is not None:
        return bool(configured)
    if platform_name is _USE_SYSTEM_PLATFORM:
        platform_name = platform.system()
    current_platform = str(platform_name).strip().lower()
    if current_platform == "darwin":
        return False
    if current_platform in _EVENT_WATCHER_PLATFORMS:
        return True
    # Unknown or malformed platform values fail closed to the safer mode.
    return False
