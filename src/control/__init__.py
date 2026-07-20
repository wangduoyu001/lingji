from __future__ import annotations

from .runtime_settings import RuntimeSettingsStore

__all__ = ["RuntimeSettingsStore", "LocalControlService"]


def __getattr__(name: str):
    if name == "LocalControlService":
        from .service import LocalControlService

        return LocalControlService
    raise AttributeError(name)
