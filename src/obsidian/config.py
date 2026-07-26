from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .discovery import (
    DISCOVERY_NOT_FOUND,
    discover_cli,
    resolve_vault_name,
    resolve_vault_path,
)
from .models import ObsidianCliDiscovery


@dataclass
class ObsidianCliConfig:
    cli_path: str = ""
    vault_path: str = ""
    vault_name: str = ""
    timeout: int = 15
    dry_run: bool = False
    enabled: bool = True
    cli_discovery_source: str = DISCOVERY_NOT_FOUND
    vault_discovery_source: str = DISCOVERY_NOT_FOUND

    @classmethod
    def from_sources(
        cls,
        *,
        settings: Any | None = None,
        runtime_values: Mapping[str, Any] | None = None,
        workspace_vault_path: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
        platform: str | None = None,
    ) -> "ObsidianCliConfig":
        env = os.environ if environ is None else environ
        values = runtime_values or {}
        explicit_cli = str(values.get("obsidian_cli_path") or "").strip()
        discovery = discover_cli(
            explicit_path=explicit_cli or None,
            environ=env,
            platform=platform,
        )

        if workspace_vault_path is None and settings is not None:
            workspace_vault_path = getattr(settings, "vault_path", None)
        runtime_vault_path = str(values.get("obsidian_vault_path") or "").strip()
        vault_path, vault_source = resolve_vault_path(
            workspace_vault_path=workspace_vault_path,
            runtime_vault_path=runtime_vault_path or None,
            environ=env,
        )

        timeout_value = values.get("obsidian_cli_timeout_seconds")
        if timeout_value in (None, ""):
            timeout_value = env.get("OBSIDIAN_CLI_TIMEOUT", "15")
        try:
            timeout = int(timeout_value)
        except (TypeError, ValueError):
            timeout = 15
        if timeout <= 0:
            timeout = 15

        enabled = cls._as_bool(values.get("obsidian_cli_enabled", True), default=True)
        dry_run_value = values.get("obsidian_cli_dry_run")
        if dry_run_value is None:
            dry_run_value = env.get("OBSIDIAN_CLI_DRY_RUN", "0")
        dry_run = cls._as_bool(dry_run_value, default=False)
        vault_name = resolve_vault_name(
            vault_path=vault_path,
            explicit_name=str(values.get("obsidian_vault_name") or "").strip() or None,
            environ=env,
        )

        return cls(
            cli_path=discovery.path,
            vault_path=vault_path,
            vault_name=vault_name,
            timeout=timeout,
            dry_run=dry_run,
            enabled=enabled,
            cli_discovery_source=discovery.source,
            vault_discovery_source=vault_source,
        )

    @classmethod
    def from_env(
        cls,
        *,
        workspace_vault_path: str | Path | None = None,
        runtime_vault_path: str | Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> "ObsidianCliConfig":
        env = os.environ if environ is None else environ
        discovery = cls.discover(environ=env)
        vault_path, vault_source = cls._resolve_vault_path(
            workspace_vault_path=workspace_vault_path,
            runtime_vault_path=runtime_vault_path,
            environ=env,
        )
        timeout_value = str(env.get("OBSIDIAN_CLI_TIMEOUT", "15") or "15")
        try:
            timeout = int(timeout_value)
        except (TypeError, ValueError):
            timeout = 15
        if timeout <= 0:
            timeout = 15
        return cls(
            cli_path=discovery.path,
            vault_path=vault_path,
            vault_name=cls._resolve_vault_name(vault_path=vault_path, environ=env),
            timeout=timeout,
            dry_run=cls._as_bool(env.get("OBSIDIAN_CLI_DRY_RUN", "0"), default=False),
            enabled=True,
            cli_discovery_source=discovery.source,
            vault_discovery_source=vault_source,
        )

    @classmethod
    def discover(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        platform: str | None = None,
    ) -> ObsidianCliDiscovery:
        return discover_cli(environ=environ, platform=platform)

    @classmethod
    def _detect(cls) -> str:
        return cls.discover().path

    @staticmethod
    def _resolve_vault_path(
        *,
        workspace_vault_path: str | Path | None,
        runtime_vault_path: str | Path | None,
        environ: Mapping[str, str],
    ) -> tuple[str, str]:
        return resolve_vault_path(
            workspace_vault_path=workspace_vault_path,
            runtime_vault_path=runtime_vault_path,
            environ=environ,
        )

    @staticmethod
    def _resolve_vault_name(
        *,
        vault_path: str,
        environ: Mapping[str, str] | None = None,
    ) -> str:
        return resolve_vault_name(vault_path=vault_path, environ=environ)

    def validate(self) -> list[str]:
        issues: list[str] = []
        if not self.enabled:
            return issues
        if not self.cli_path or not os.path.isfile(self.cli_path):
            issues.append(f"CLI 未找到: {self.cli_path}")
        if not self.vault_path or not os.path.isdir(self.vault_path):
            issues.append(f"Vault 路径不存在: {self.vault_path}")
        if not self.vault_name:
            issues.append("Vault 名称未设置")
        return issues

    def ok(self) -> bool:
        return bool(self.enabled and self.cli_path and os.path.isfile(self.cli_path))

    @staticmethod
    def _as_bool(value: Any, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return default


ObsidianConfig = ObsidianCliConfig
