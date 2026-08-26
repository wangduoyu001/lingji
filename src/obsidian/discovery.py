from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path, PureWindowsPath
from typing import Mapping

from .models import ObsidianCliDiscovery
from .memory_scope import ObsidianMemoryScope, ObsidianMemoryDecision

DISCOVERY_RUNTIME_SETTINGS = "runtime_settings"
DISCOVERY_WORKSPACE = "workspace"
DISCOVERY_ENVIRONMENT = "environment"
DISCOVERY_PATH = "path"
DISCOVERY_PLATFORM_LOCATION = "platform_location"
DISCOVERY_NOT_FOUND = "not_found"


def platform_cli_candidates(
    *,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    """Return platform-standard CLI locations without machine-specific paths."""

    env = os.environ if environ is None else environ
    current = (platform or sys.platform).lower()
    candidates: list[Path] = []

    if current.startswith("win"):
        for variable in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
            root = str(env.get(variable, "") or "").strip()
            if not root:
                continue
            base = Path(root).expanduser()
            if variable == "LOCALAPPDATA":
                candidates.append(base / "Programs" / "Obsidian" / "Obsidian.com")
            candidates.append(base / "Obsidian" / "Obsidian.com")
    elif current == "darwin":
        candidates.extend(
            [
                Path("/Applications/Obsidian.app/Contents/MacOS/Obsidian"),
                Path.home() / "Applications/Obsidian.app/Contents/MacOS/Obsidian",
            ]
        )
    else:
        candidates.extend(
            [
                Path.home() / ".local/bin/obsidian",
                Path("/usr/local/bin/obsidian"),
                Path("/usr/bin/obsidian"),
            ]
        )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return tuple(unique)


def discover_cli(
    *,
    explicit_path: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> ObsidianCliDiscovery:
    """Resolve CLI path using runtime, environment, PATH, then platform locations."""

    env = os.environ if environ is None else environ
    runtime_path = str(explicit_path or "").strip()
    if runtime_path:
        return ObsidianCliDiscovery(str(Path(runtime_path).expanduser()), DISCOVERY_RUNTIME_SETTINGS)

    environment_path = str(env.get("OBSIDIAN_CLI_PATH", "") or "").strip()
    if environment_path:
        return ObsidianCliDiscovery(
            str(Path(environment_path).expanduser()),
            DISCOVERY_ENVIRONMENT,
        )

    search_path = str(env.get("PATH", "") or "")
    for executable in ("Obsidian.com", "obsidian"):
        resolved = shutil.which(executable, path=search_path)
        if resolved:
            return ObsidianCliDiscovery(str(Path(resolved).expanduser()), DISCOVERY_PATH)

    for candidate in platform_cli_candidates(platform=platform, environ=env):
        if candidate.is_file():
            return ObsidianCliDiscovery(str(candidate), DISCOVERY_PLATFORM_LOCATION)
    return ObsidianCliDiscovery()


def resolve_vault_path(
    *,
    workspace_vault_path: str | Path | None,
    runtime_vault_path: str | Path | None,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """Resolve Vault while preserving Workspace as the authority."""

    env = os.environ if environ is None else environ
    for value, source in (
        (workspace_vault_path, DISCOVERY_WORKSPACE),
        (runtime_vault_path, DISCOVERY_RUNTIME_SETTINGS),
        (env.get("OBSIDIAN_VAULT_PATH"), DISCOVERY_ENVIRONMENT),
        (env.get("SECOND_BRAIN_OBSIDIAN_DIR"), DISCOVERY_ENVIRONMENT),
    ):
        text = str(value or "").strip()
        if text:
            return str(Path(text).expanduser()), source
    return "", DISCOVERY_NOT_FOUND


def resolve_vault_name(
    *,
    vault_path: str,
    explicit_name: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    env = os.environ if environ is None else environ
    configured = str(explicit_name or "").strip()
    if configured:
        return configured
    environment_name = str(env.get("OBSIDIAN_VAULT_NAME", "") or "").strip()
    if environment_name:
        return environment_name
    if vault_path:
        name = PureWindowsPath(vault_path).name if "\\" in vault_path else Path(vault_path).name
        if name:
            return name
    return "本地知识库"


def display_path(value: str | Path | None) -> str:
    """Return a useful local display without exposing a complete absolute path."""

    text = str(value or "").strip()
    if not text:
        return ""
    parts = (
        list(PureWindowsPath(text).parts)
        if "\\" in text
        else list(Path(text).parts)
    )
    useful = [part for part in parts if part not in {"/", "\\"}]
    if not useful:
        return ""
    tail = useful[-2:]
    return ("…/" if len(useful) > len(tail) else "") + "/".join(tail)


def discover_memory_paths(vault_path: str | Path) -> tuple[ObsidianMemoryDecision, ...]:
    """Discover only automatic-memory-authorized Markdown files."""
    return ObsidianMemoryScope(vault_path).iter_markdown()


# Compatibility alias used by the old module and its tests.
_platform_cli_candidates = platform_cli_candidates
