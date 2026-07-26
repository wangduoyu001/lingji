from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.project_context import (
    PROJECT_MANIFEST_INVALID,
    ProjectContextError,
    ProjectRegistry,
    ProjectResolver,
    ProjectState,
    load_project_manifest,
)


def test_manifest_parses_and_parent_search_wins(tmp_path: Path):
    root = tmp_path / "repo"
    child = root / "src" / "feature"
    child.mkdir(parents=True)
    manifest = root / ".lingji" / "project.yaml"
    manifest.parent.mkdir()
    manifest.write_text(
        """schema_version: 1
project_id: LJ-PROJ-LINGJI
name: LingJi
repository: wangduoyu001/lingji
privacy: private
owner_note: local-only
""",
        encoding="utf-8",
    )
    registry = ProjectRegistry(tmp_path / "storage" / "project_registry.json")
    resolver = ProjectResolver(registry, git_runner=lambda command, cwd: "")
    result = resolver.resolve(child)
    assert result.project_id == "LJ-PROJ-LINGJI"
    assert result.resolution_source == "manifest"
    assert result.metadata["owner_note"] == "local-only"
    assert result.path_display.endswith("/…/repo")
    assert str(root) not in result.to_public_dict().values()


def test_manifest_invalid_contract_is_rejected(tmp_path: Path):
    manifest = tmp_path / "project.yaml"
    manifest.write_text(
        "schema_version: 2\nproject_id: bad\nname: X\nrepository: a/b\nprivacy: secret\n",
        encoding="utf-8",
    )
    with pytest.raises(ProjectContextError) as error:
        load_project_manifest(manifest)
    assert error.value.code == PROJECT_MANIFEST_INVALID


def test_git_worktrees_normalize_to_same_project(tmp_path: Path):
    first = tmp_path / "lingji"
    second = tmp_path / "lingji-p2-07"
    common = tmp_path / "repo.git"
    first.mkdir()
    second.mkdir()
    common.mkdir()

    def git_runner(command, cwd):
        key = tuple(command[1:])
        if key == ("rev-parse", "--show-toplevel"):
            return str(cwd)
        if key == ("rev-parse", "--git-common-dir"):
            return str(common)
        if key == ("remote", "get-url", "origin"):
            return "git@github.com:wangduoyu001/lingji.git"
        if key == ("branch", "--show-current"):
            return "work/p2-07a" if cwd == second else "main"
        raise RuntimeError

    registry = ProjectRegistry(tmp_path / "storage" / "project_registry.json")
    resolver = ProjectResolver(registry, git_runner=git_runner)
    left = resolver.resolve(first)
    right = resolver.resolve(second)
    assert left.project_id == right.project_id == "LJ-PROJ-LINGJI"
    assert right.resolution_source == "registry"
    records = registry.records()
    assert len(records) == 1
    assert len(records[0]["worktree_roots"]) == 2


def test_unconfirmed_workspace_is_unassigned(tmp_path: Path):
    workspace = tmp_path / "plain"
    workspace.mkdir()
    resolver = ProjectResolver(
        ProjectRegistry(tmp_path / "registry.json"),
        git_runner=lambda command, cwd: "",
    )
    result = resolver.resolve(workspace)
    assert result.state is ProjectState.UNASSIGNED
    assert result.project_id == ""
    assert result.resolution_source == "unassigned"


def test_registry_atomic_write_deduplicates_and_corruption_degrades(tmp_path: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    registry_path = tmp_path / "storage" / "project_registry.json"
    registry = ProjectRegistry(registry_path)
    resolver = ProjectResolver(
        registry,
        git_runner=lambda command, cwd: {
            ("git", "rev-parse", "--show-toplevel"): str(workspace),
            ("git", "rev-parse", "--git-common-dir"): str(tmp_path / "common.git"),
            ("git", "remote", "get-url", "origin"): "https://github.com/a/demo.git",
            ("git", "branch", "--show-current"): "main",
        }[tuple(command)],
    )
    resolver.resolve(workspace)
    resolver.resolve(workspace)
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert len(payload["projects"]) == 1
    assert len(payload["projects"][0]["worktree_roots"]) == 1
    assert not registry_path.with_suffix(".json.tmp").exists()
    registry_path.write_text("{broken", encoding="utf-8")
    assert registry.records() == []
