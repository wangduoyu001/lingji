"""Resolve the home directory used by automatic-memory boundaries."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

try:
    import pwd
except ImportError:  # pragma: no cover - Windows compatibility
    pwd = None  # type: ignore[assignment]


def resolve_effective_home(settings: object | None = None, env: Mapping[str, str] | None = None) -> Path:
    """Resolve configured home first, then explicit env, then OS identity."""
    supplied = None
    if settings is not None:
        supplied = getattr(settings, "home_dir", None) or getattr(settings, "user_home", None)
    if supplied:
        return Path(str(supplied)).expanduser().resolve(strict=False)
    values = os.environ if env is None else env
    if values.get("HOME"):
        return Path(values["HOME"]).expanduser().resolve(strict=False)
    if pwd is not None:
        try:
            return Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=False)
        except (KeyError, OSError):
            pass
    return Path.home().resolve(strict=False)


__all__ = ["resolve_effective_home"]
