from __future__ import annotations

from typing import Any, Mapping

from .service import LocalControlService
from .settings_governance import OwnerSettingsRegistry


class GovernedLocalControlService(LocalControlService):
    """Formal 8766 control service with owner-visible settings governance."""

    def __init__(self, settings: Any, state_db: Any | None = None, **kwargs: Any):
        super().__init__(settings, state_db=state_db, **kwargs)
        registry = OwnerSettingsRegistry(settings, state_db=self.state_db)
        self.runtime_settings = registry
        if hasattr(self.obsidian, "runtime_settings"):
            self.obsidian.runtime_settings = registry
        if hasattr(self.model_inventory, "runtime_settings"):
            self.model_inventory.runtime_settings = registry
        self._sync_hardware_settings()

    def get_settings(self) -> dict[str, Any]:
        return self.runtime_settings.snapshot(self._settings_capabilities())

    def preview_settings(self, values: Mapping[str, Any]) -> dict[str, Any]:
        return self.runtime_settings.preview(values, capabilities=self._settings_capabilities())

    def commit_settings(
        self,
        values: Mapping[str, Any],
        *,
        confirmation: str = "",
        actor: str = "owner",
    ) -> dict[str, Any]:
        self.runtime_settings.update(
            values,
            actor=actor,
            confirmation=confirmation,
            capabilities=self._settings_capabilities(),
        )
        self._sync_hardware_settings()
        return self.get_settings()

    def update_settings(
        self,
        values: Mapping[str, Any],
        *,
        actor: str = "owner",
    ) -> dict[str, Any]:
        return self.commit_settings(values, actor=actor)

    def reset_settings(
        self,
        keys: list[str] | None = None,
        *,
        actor: str = "owner",
    ) -> dict[str, Any]:
        self.runtime_settings.reset(keys, actor=actor)
        self._sync_hardware_settings()
        return self.get_settings()

    def _settings_capabilities(self) -> dict[str, dict[str, Any]]:
        capabilities: dict[str, dict[str, Any]] = {}
        try:
            providers = self.provider_status()
        except Exception as exc:
            providers = {}
            capabilities["provider_inventory"] = {
                "available": False,
                "reason": f"Provider inventory unavailable: {type(exc).__name__}",
            }
        for provider_id in ("faster_whisper", "paddleocr", "pyscenedetect"):
            status = dict(providers.get(provider_id) or {})
            capabilities[provider_id] = {
                "available": status.get("available"),
                "reason": status.get("last_error"),
                "optional_requirements": status.get("optional_requirements"),
            }
        try:
            obsidian = self.obsidian_status()
            capabilities["obsidian_cli"] = {
                "available": bool(obsidian.get("available")),
                "reason": "; ".join(
                    str(item.get("message") or item.get("code") or "")
                    for item in obsidian.get("issues") or []
                    if isinstance(item, Mapping)
                )
                or None,
            }
        except Exception as exc:
            capabilities["obsidian_cli"] = {
                "available": False,
                "reason": f"Obsidian status unavailable: {type(exc).__name__}",
            }
        return capabilities
