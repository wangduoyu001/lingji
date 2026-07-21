from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Mapping

from .models import ProjectResolution

logger = logging.getLogger("lingji.project_context.registry")


class ProjectRegistry:
    """Rebuildable local bindings between repositories and project IDs."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._lock = threading.RLock()

    def records(self) -> list[dict[str, Any]]:
        with self._lock:
            return self._read()

    def find(
        self,
        workspace_path: Path | str,
        *,
        git_common_dir: Path | None = None,
        repository: str = "",
    ) -> dict[str, Any] | None:
        target = Path(workspace_path).expanduser().resolve(strict=False)
        common = _path_key(git_common_dir) if git_common_dir else ""
        records = self.records()
        for record in records:
            roots = [*(record.get("workspace_roots") or []), *(record.get("worktree_roots") or [])]
            if any(_contains(root, target) for root in roots):
                return record
        if common:
            for record in records:
                if _path_key(record.get("git_common_dir")) == common:
                    return record
        normalized_repository = str(repository or "").strip().lower()
        if normalized_repository:
            matches = [
                record
                for record in records
                if str(record.get("repository") or "").strip().lower() == normalized_repository
            ]
            if len(matches) == 1:
                return matches[0]
        return None

    def upsert(
        self,
        resolution: ProjectResolution,
        *,
        workspace_root: Path | None,
        worktree_root: Path | None,
        git_common_dir: Path | None,
        last_seen_at: str,
    ) -> dict[str, Any]:
        if not resolution.project_id:
            raise ValueError("Resolved project_id is required")
        with self._lock:
            records = self._read()
            existing = next(
                (item for item in records if item.get("project_id") == resolution.project_id),
                None,
            )
            record = dict(existing or {})
            record.update(
                {
                    "project_id": resolution.project_id,
                    "name": resolution.name,
                    "repository": resolution.repository,
                    "git_common_dir": str(git_common_dir or record.get("git_common_dir") or ""),
                    "last_seen_at": last_seen_at,
                    "manifest_source": resolution.manifest_source,
                }
            )
            record["workspace_roots"] = _dedupe_paths(
                [*(record.get("workspace_roots") or []), workspace_root]
            )
            record["worktree_roots"] = _dedupe_paths(
                [*(record.get("worktree_roots") or []), worktree_root]
            )
            if existing is None:
                records.append(record)
            else:
                records[records.index(existing)] = record
            records.sort(key=lambda item: (str(item.get("project_id") or ""), str(item.get("repository") or "")))
            self._write(records)
            return record

    def public_items(self) -> list[dict[str, Any]]:
        items = []
        for record in self.records():
            roots = record.get("worktree_roots") or record.get("workspace_roots") or []
            display = path_display(roots[-1]) if roots else ""
            items.append(
                {
                    "project_id": str(record.get("project_id") or ""),
                    "name": str(record.get("name") or ""),
                    "repository": str(record.get("repository") or ""),
                    "branch": "",
                    "worktree_name": Path(str(roots[-1])).name if roots else "",
                    "path_display": display,
                    "resolution_source": "registry",
                    "state": "resolved",
                }
            )
        return items

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
            records = payload.get("projects", payload) if isinstance(payload, Mapping) else []
            if not isinstance(records, list):
                return []
            return [dict(item) for item in records if isinstance(item, Mapping)]
        except (OSError, json.JSONDecodeError):
            logger.exception("Project registry is unavailable; using an empty rebuildable registry")
            return []

    def _write(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = {"schema_version": 1, "projects": records}
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)


def path_display(value: Path | str | None) -> str:
    if not value:
        return ""
    text = str(value).replace("\\", "/").rstrip("/")
    name = text.rsplit("/", 1)[-1]
    if len(text) >= 2 and text[1] == ":":
        return f"{text[:2]}/…/{name}"
    return f"/…/{name}"


def _dedupe_paths(values: list[Any]) -> list[str]:
    result: dict[str, str] = {}
    for value in values:
        if value in (None, ""):
            continue
        path = Path(str(value)).expanduser().resolve(strict=False)
        result[_path_key(path)] = str(path)
    return [result[key] for key in sorted(result)]


def _path_key(value: Any) -> str:
    if value in (None, ""):
        return ""
    return os.path.normcase(str(Path(str(value)).expanduser().resolve(strict=False)))


def _contains(root_value: Any, target: Path) -> bool:
    if root_value in (None, ""):
        return False
    root = Path(str(root_value)).expanduser().resolve(strict=False)
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False
