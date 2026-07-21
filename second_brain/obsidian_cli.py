"""Deprecated compatibility facade for the formal ``src.obsidian`` package.

New product code must import from ``src.obsidian``. This module intentionally
contains no command implementation so the legacy and formal surfaces cannot
silently diverge.
"""
from __future__ import annotations

# Keep these module imports visible because old tests and downstream callers
# monkeypatch them through this compatibility module. They refer to the same
# standard-library module objects used by the formal implementation.
import os
import shutil
import subprocess
from pathlib import Path

from src.obsidian import (
    DISCOVERY_ENVIRONMENT,
    DISCOVERY_NOT_FOUND,
    DISCOVERY_PATH,
    DISCOVERY_PLATFORM_LOCATION,
    ObsidianCli,
    ObsidianCliClient,
    ObsidianCliConfig,
    ObsidianCliDiscovery,
    ObsidianCliError,
    ObsidianCliErrorResult,
    ObsidianCliNotFound,
    ObsidianCliTimeout,
    ObsidianNote,
    ObsidianVaultInfo,
    _platform_cli_candidates,
    platform_cli_candidates,
)

DEFAULT_CLI_PATHS: list[str] = [str(path) for path in platform_cli_candidates()]

__all__ = [
    "DEFAULT_CLI_PATHS",
    "DISCOVERY_ENVIRONMENT",
    "DISCOVERY_NOT_FOUND",
    "DISCOVERY_PATH",
    "DISCOVERY_PLATFORM_LOCATION",
    "ObsidianCli",
    "ObsidianCliClient",
    "ObsidianCliConfig",
    "ObsidianCliDiscovery",
    "ObsidianCliError",
    "ObsidianCliErrorResult",
    "ObsidianCliNotFound",
    "ObsidianCliTimeout",
    "ObsidianNote",
    "ObsidianVaultInfo",
    "Path",
    "_platform_cli_candidates",
]
