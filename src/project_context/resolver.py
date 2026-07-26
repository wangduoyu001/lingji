from __future__ import annotations

import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlparse

from .manifest import find_project_manifest, load_project_manifest
from .models import (
    PROJECT_PATH_INVALID,
    GitIdentity,
    ProjectContextError,
    ProjectResolution,
    ProjectState,
)
from .registry import ProjectRegistry, path_display

logger = logging.getLogger("lingji.project_context.resolver")
GitRunner = Callable[[Sequence[str], Path], str]


class ProjectResolver:
    def __init__(self, registry: ProjectRegistry, *, git_runner: GitRunner | None = None):
        self.registry = registry
        self.git_runner = git_runner or _run_git

    def resolve(self, workspace_path: Path | str) -> ProjectResolution:
        workspace = Path(workspace_path).expanduser()
        if not workspace.exists():
            raise ProjectContextError(
                PROJECT_PATH_INVALID,
                "Project workspace path does not exist",
                status_code=422,
            )
        if workspace.is_file():
            workspace = workspace.parent
        workspace = workspace.resolve(strict=False)
        git = self._git_identity(workspace)
        manifest_path = find_project_manifest(workspace)
        if manifest_path:
            manifest = load_project_manifest(manifest_path)
            root = manifest_path.parent.parent.resolve(strict=False)
            result = ProjectResolution(
                project_id=manifest.project_id,
                name=manifest.name,
                repository=manifest.repository or git.repository,
                branch=git.branch,
                worktree_name=(git.repository_root or root).name,
                path_display=path_display(git.repository_root or root),
                resolution_source="manifest",
                state=ProjectState.RESOLVED,
                privacy=manifest.privacy,
                workspace_root=root,
                worktree_root=git.repository_root or root,
                git_common_dir=git.git_common_dir,
                manifest_source=".lingji/project.yaml",
                metadata=manifest.metadata,
            )
            self._remember(result)
            return result
        record = self.registry.find(
            workspace,
            git_common_dir=git.git_common_dir,
            repository=git.repository,
        )
        if record:
            root = git.repository_root or workspace
            result = ProjectResolution(
                project_id=str(record.get("project_id") or ""),
                name=str(record.get("name") or ""),
                repository=str(record.get("repository") or git.repository),
                branch=git.branch,
                worktree_name=root.name,
                path_display=path_display(root),
                resolution_source="registry",
                state=ProjectState.RESOLVED,
                workspace_root=workspace,
                worktree_root=root,
                git_common_dir=git.git_common_dir,
                manifest_source=str(record.get("manifest_source") or ""),
            )
            self._remember(result)
            return result
        if git.repository and git.git_common_dir is not None:
            root = git.repository_root or workspace
            name = git.repository.rsplit("/", 1)[-1]
            result = ProjectResolution(
                project_id=_project_id_from_repository(git.repository),
                name=name,
                repository=git.repository,
                branch=git.branch,
                worktree_name=root.name,
                path_display=path_display(root),
                resolution_source="git",
                state=ProjectState.RESOLVED,
                workspace_root=workspace,
                worktree_root=root,
                git_common_dir=git.git_common_dir,
            )
            self._remember(result)
            return result
        return ProjectResolution(
            project_id="",
            name="",
            repository="",
            branch=git.branch,
            worktree_name=workspace.name,
            path_display=path_display(workspace),
            resolution_source="unassigned",
            state=ProjectState.UNASSIGNED,
            workspace_root=workspace,
            worktree_root=git.repository_root,
            git_common_dir=git.git_common_dir,
        )

    def list_projects(self) -> list[dict[str, object]]:
        return self.registry.public_items()

    def _remember(self, resolution: ProjectResolution) -> None:
        self.registry.upsert(
            resolution,
            workspace_root=resolution.workspace_root,
            worktree_root=resolution.worktree_root,
            git_common_dir=resolution.git_common_dir,
            last_seen_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    def _git_identity(self, workspace: Path) -> GitIdentity:
        values: dict[str, str] = {}
        commands = {
            "repository_root": ("git", "rev-parse", "--show-toplevel"),
            "git_common_dir": ("git", "rev-parse", "--git-common-dir"),
            "repository": ("git", "remote", "get-url", "origin"),
            "branch": ("git", "branch", "--show-current"),
        }
        for key, command in commands.items():
            try:
                values[key] = self.git_runner(command, workspace).strip()
            except (OSError, subprocess.SubprocessError, RuntimeError):
                values[key] = ""
        root = Path(values["repository_root"]).expanduser().resolve(strict=False) if values["repository_root"] else None
        common = None
        if values["git_common_dir"]:
            raw_common = Path(values["git_common_dir"]).expanduser()
            common = (workspace / raw_common).resolve(strict=False) if not raw_common.is_absolute() else raw_common.resolve(strict=False)
        return GitIdentity(
            repository_root=root,
            git_common_dir=common,
            repository=normalize_repository(values["repository"]),
            branch=values["branch"],
        )


def normalize_repository(remote: str) -> str:
    value = str(remote or "").strip().replace("\\", "/")
    if not value:
        return ""
    if re.match(r"^[^@]+@[^:]+:.+$", value):
        value = value.split(":", 1)[1]
    elif "://" in value:
        parsed = urlparse(value)
        value = parsed.path
    value = value.strip("/")
    if value.endswith(".git"):
        value = value[:-4]
    parts = [part for part in value.split("/") if part]
    return "/".join(parts[-2:]) if len(parts) >= 2 else ""


def _project_id_from_repository(repository: str) -> str:
    slug = repository.rsplit("/", 1)[-1]
    token = re.sub(r"[^A-Za-z0-9]+", "-", slug).strip("-").upper()
    return f"LJ-PROJ-{token}"


def _run_git(command: Sequence[str], cwd: Path) -> str:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return completed.stdout
