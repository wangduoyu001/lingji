from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
PROJECT_MANIFEST_INVALID = "PROJECT_MANIFEST_INVALID"
PROJECT_UNASSIGNED = "PROJECT_UNASSIGNED"
PROJECT_PATH_INVALID = "PROJECT_PATH_INVALID"


class ProjectContextError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ProjectState(str, Enum):
    RESOLVED = "resolved"
    UNASSIGNED = "unassigned"


@dataclass(frozen=True)
class ProjectManifest:
    schema_version: int
    project_id: str
    name: str
    repository: str
    privacy: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    source_path: Path | None = None


@dataclass(frozen=True)
class GitIdentity:
    repository_root: Path | None = None
    git_common_dir: Path | None = None
    repository: str = ""
    branch: str = ""


@dataclass(frozen=True)
class ProjectResolution:
    project_id: str
    name: str
    repository: str
    branch: str
    worktree_name: str
    path_display: str
    resolution_source: str
    state: ProjectState
    privacy: str = "private"
    workspace_root: Path | None = None
    worktree_root: Path | None = None
    git_common_dir: Path | None = None
    manifest_source: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "repository": self.repository,
            "branch": self.branch,
            "worktree_name": self.worktree_name,
            "path_display": self.path_display,
            "resolution_source": self.resolution_source,
            "state": self.state.value,
        }
