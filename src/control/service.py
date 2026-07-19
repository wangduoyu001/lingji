from __future__ import annotations

from typing import Any, Mapping

from src.health import StartupHealthChecker

from .runtime_settings import RuntimeSettingsStore


class LocalControlService:
    """Framework-neutral service used by the future FastAPI/Tauri control UI."""

    def __init__(self, settings: Any, state_db: Any | None = None):
        self.settings = settings
        self.runtime_settings = RuntimeSettingsStore(settings, state_db=state_db)
        self.health_checker = StartupHealthChecker(settings)

    def get_settings(self) -> dict[str, Any]:
        return self.runtime_settings.snapshot()

    def update_settings(
        self,
        values: Mapping[str, Any],
        *,
        actor: str = "owner",
    ) -> dict[str, Any]:
        return self.runtime_settings.update(values, actor=actor)

    def reset_settings(
        self,
        keys: list[str] | None = None,
        *,
        actor: str = "owner",
    ) -> dict[str, Any]:
        return self.runtime_settings.reset(keys, actor=actor)

    def health(self) -> dict[str, Any]:
        return self.health_checker.run()
