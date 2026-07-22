from __future__ import annotations

from .settings_governance import OwnerSettingsRegistry

RuntimeSettingsStore = OwnerSettingsRegistry

__all__ = ["RuntimeSettingsStore", "OwnerSettingsRegistry", "LocalControlService", "GovernedLocalControlService"]


def __getattr__(name: str):
    if name == "LocalControlService":
        from .service import LocalControlService

        return LocalControlService
    if name == "GovernedLocalControlService":
        from .governed_service import GovernedLocalControlService

        return GovernedLocalControlService
    raise AttributeError(name)
