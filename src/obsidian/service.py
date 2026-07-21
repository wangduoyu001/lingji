from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .client import ObsidianCliClient
from .config import ObsidianCliConfig
from .discovery import display_path
from .models import (
    OBSIDIAN_CLI_FAILED,
    OBSIDIAN_CLI_NOT_FOUND,
    OBSIDIAN_CLI_TIMEOUT,
    OBSIDIAN_STATE_CONFIGURATION_REQUIRED,
    OBSIDIAN_STATE_DEGRADED,
    OBSIDIAN_STATE_DISABLED,
    OBSIDIAN_STATE_HEALTHY,
    OBSIDIAN_STATE_UNAVAILABLE,
    OBSIDIAN_VAULT_NOT_CONFIGURED,
    OBSIDIAN_VAULT_NOT_FOUND,
    ObsidianCliError,
    ObsidianCliTimeout,
    ObsidianIssue,
)

OBSIDIAN_SETTING_KEYS = {
    "obsidian_cli_enabled",
    "obsidian_cli_path",
    "obsidian_vault_path",
    "obsidian_vault_name",
    "obsidian_cli_timeout_seconds",
    "obsidian_cli_dry_run",
}


class ObsidianService:
    """Workspace-aware Obsidian capability service used by 8766 and Tauri."""

    def __init__(
        self,
        settings: Any,
        *,
        runtime_settings: Any,
        state_db: Any | None = None,
        environ: Mapping[str, str] | None = None,
        platform: str | None = None,
        client_factory: type[ObsidianCliClient] = ObsidianCliClient,
    ):
        self.settings = settings
        self.runtime_settings = runtime_settings
        self.state_db = state_db
        self.environ = os.environ if environ is None else environ
        self.platform = platform or sys.platform
        self.client_factory = client_factory

    def config(self, overrides: Mapping[str, Any] | None = None) -> ObsidianCliConfig:
        values = dict(self.runtime_settings.snapshot().get("values") or {})
        if overrides:
            values.update(dict(overrides))
        return ObsidianCliConfig.from_sources(
            settings=self.settings,
            runtime_values=values,
            environ=self.environ,
            platform=self.platform,
        )

    def status(self, *, overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
        config = self.config(overrides)
        issues: list[ObsidianIssue] = []
        version: str | None = None
        state = OBSIDIAN_STATE_HEALTHY

        cli_path = Path(config.cli_path).expanduser() if config.cli_path else None
        vault_path = Path(config.vault_path).expanduser() if config.vault_path else None

        if not config.enabled:
            state = OBSIDIAN_STATE_DISABLED
        else:
            if cli_path is None:
                issues.append(ObsidianIssue(OBSIDIAN_CLI_NOT_FOUND, "Obsidian CLI 尚未配置"))
                state = OBSIDIAN_STATE_CONFIGURATION_REQUIRED
            elif not cli_path.is_file():
                issues.append(ObsidianIssue(OBSIDIAN_CLI_NOT_FOUND, "配置的 Obsidian CLI 不可用"))
                state = OBSIDIAN_STATE_UNAVAILABLE

            if vault_path is None:
                issues.append(ObsidianIssue(OBSIDIAN_VAULT_NOT_CONFIGURED, "Obsidian Vault 尚未配置"))
                if state == OBSIDIAN_STATE_HEALTHY:
                    state = OBSIDIAN_STATE_CONFIGURATION_REQUIRED
            elif not vault_path.is_dir():
                issues.append(ObsidianIssue(OBSIDIAN_VAULT_NOT_FOUND, "配置的 Obsidian Vault 不存在"))
                state = OBSIDIAN_STATE_UNAVAILABLE

            if not issues:
                try:
                    version = self.client_factory(config).get_version() or None
                except ObsidianCliTimeout:
                    issues.append(ObsidianIssue(OBSIDIAN_CLI_TIMEOUT, "Obsidian CLI 响应超时"))
                    state = OBSIDIAN_STATE_DEGRADED
                except ObsidianCliError:
                    issues.append(ObsidianIssue(OBSIDIAN_CLI_FAILED, "Obsidian CLI 状态检查失败"))
                    state = OBSIDIAN_STATE_DEGRADED
                except Exception:
                    issues.append(ObsidianIssue(OBSIDIAN_CLI_FAILED, "Obsidian CLI 状态检查失败"))
                    state = OBSIDIAN_STATE_DEGRADED

        available = state == OBSIDIAN_STATE_HEALTHY
        return {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "state": state,
            "enabled": config.enabled,
            "available": available,
            "version": version,
            "vault_name": config.vault_name or None,
            "cli_configured": bool(config.cli_path),
            "vault_configured": bool(config.vault_path),
            "cli_path_display": display_path(config.cli_path),
            "vault_path_display": display_path(config.vault_path),
            "cli_discovery_source": config.cli_discovery_source,
            "vault_discovery_source": config.vault_discovery_source,
            "timeout_seconds": config.timeout,
            "dry_run": config.dry_run,
            "capabilities": {
                "status": True,
                "read": available,
                "write": available and not config.dry_run,
                "dry_run": config.dry_run,
                "compatibility_forwarding": True,
            },
            "issues": [issue.as_dict() for issue in issues],
        }

    def validate_configuration(self, values: Mapping[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(values) - OBSIDIAN_SETTING_KEYS)
        if unknown:
            raise KeyError(f"Unknown Obsidian setting: {unknown[0]}")
        payload = self.status(overrides=values)
        payload["persisted"] = False
        if self.state_db is not None:
            self.state_db.append_event(
                "obsidian_configuration_validated",
                "obsidian",
                "runtime",
                {
                    "state": payload["state"],
                    "cli_discovery_source": payload["cli_discovery_source"],
                    "vault_discovery_source": payload["vault_discovery_source"],
                },
            )
        return payload

    def client(self) -> ObsidianCliClient:
        config = self.config()
        status = self.status()
        if status["state"] != OBSIDIAN_STATE_HEALTHY:
            issue = (status.get("issues") or [{}])[0]
            raise ObsidianCliError(
                str(issue.get("message") or "Obsidian CLI is unavailable"),
                public_message=str(issue.get("message") or "Obsidian CLI is unavailable"),
            )
        return self.client_factory(config)
