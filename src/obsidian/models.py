from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

OBSIDIAN_STATE_HEALTHY = "healthy"
OBSIDIAN_STATE_UNAVAILABLE = "unavailable"
OBSIDIAN_STATE_CONFIGURATION_REQUIRED = "configuration_required"
OBSIDIAN_STATE_DISABLED = "disabled"
OBSIDIAN_STATE_DEGRADED = "degraded"

OBSIDIAN_CLI_NOT_FOUND = "OBSIDIAN_CLI_NOT_FOUND"
OBSIDIAN_CLI_TIMEOUT = "OBSIDIAN_CLI_TIMEOUT"
OBSIDIAN_CLI_FAILED = "OBSIDIAN_CLI_FAILED"
OBSIDIAN_VAULT_NOT_CONFIGURED = "OBSIDIAN_VAULT_NOT_CONFIGURED"
OBSIDIAN_VAULT_NOT_FOUND = "OBSIDIAN_VAULT_NOT_FOUND"
OBSIDIAN_PATH_OUTSIDE_WORKSPACE = "OBSIDIAN_PATH_OUTSIDE_WORKSPACE"
OBSIDIAN_WRITE_VERIFICATION_FAILED = "OBSIDIAN_WRITE_VERIFICATION_FAILED"


@dataclass(frozen=True)
class ObsidianCliDiscovery:
    path: str = ""
    source: str = "not_found"


@dataclass
class ObsidianNote:
    path: str = ""
    content: str = ""
    vault: str = ""
    title: str = ""
    tags: list[str] = field(default_factory=list)
    frontmatter: dict[str, Any] = field(default_factory=dict)
    modified_at: str = ""


@dataclass
class ObsidianVaultInfo:
    name: str = ""
    path: str = ""
    file_count: int = 0
    folder_count: int = 0
    size: str = ""


@dataclass(frozen=True)
class ObsidianIssue:
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class ObsidianCliError(Exception):
    code = OBSIDIAN_CLI_FAILED

    def __init__(
        self,
        message: str,
        command: str = "",
        rc: int = -1,
        err: str = "",
        *,
        public_message: str | None = None,
    ):
        super().__init__(message)
        self.command = command
        self.returncode = rc
        self.stderr = err
        self.public_message = public_message or message


class ObsidianCliNotFound(ObsidianCliError):
    code = OBSIDIAN_CLI_NOT_FOUND


class ObsidianCliTimeout(ObsidianCliError):
    code = OBSIDIAN_CLI_TIMEOUT


class ObsidianCliErrorResult(ObsidianCliError):
    code = OBSIDIAN_CLI_FAILED
