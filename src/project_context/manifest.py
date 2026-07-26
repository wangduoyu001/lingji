from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

from .models import PROJECT_MANIFEST_INVALID, ProjectContextError, ProjectManifest

_FORMAL_FIELDS = {"schema_version", "project_id", "name", "repository", "privacy"}
_PRIVACY = {"public", "private", "restricted"}


def find_project_manifest(workspace_path: Path | str) -> Path | None:
    path = Path(workspace_path).expanduser()
    if path.is_file():
        path = path.parent
    path = path.resolve(strict=False)
    for current in (path, *path.parents):
        candidate = current / ".lingji" / "project.yaml"
        if candidate.is_file():
            return candidate
    return None


def load_project_manifest(path: Path | str) -> ProjectManifest:
    source = Path(path).expanduser()
    try:
        raw = source.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ProjectContextError(
            PROJECT_MANIFEST_INVALID,
            "Project manifest could not be read",
            status_code=422,
        ) from exc
    try:
        data = _load_yaml_mapping(raw)
        schema_version = int(data.get("schema_version"))
        project_id = str(data.get("project_id") or "").strip()
        name = str(data.get("name") or "").strip()
        repository = str(data.get("repository") or "").strip()
        privacy = str(data.get("privacy") or "").strip().lower()
    except (TypeError, ValueError) as exc:
        raise ProjectContextError(
            PROJECT_MANIFEST_INVALID,
            "Project manifest contains invalid field types",
            status_code=422,
        ) from exc
    if schema_version != 1:
        raise ProjectContextError(
            PROJECT_MANIFEST_INVALID,
            "Project manifest schema_version must equal 1",
            status_code=422,
        )
    if not project_id or not project_id.startswith("LJ-PROJ-"):
        raise ProjectContextError(
            PROJECT_MANIFEST_INVALID,
            "Project manifest project_id must start with LJ-PROJ-",
            status_code=422,
        )
    if privacy not in _PRIVACY:
        raise ProjectContextError(
            PROJECT_MANIFEST_INVALID,
            "Project manifest privacy must be public, private or restricted",
            status_code=422,
        )
    if not name:
        name = project_id.removeprefix("LJ-PROJ-").replace("-", " ").title()
    metadata = {key: value for key, value in data.items() if key not in _FORMAL_FIELDS}
    return ProjectManifest(
        schema_version=schema_version,
        project_id=project_id,
        name=name,
        repository=repository,
        privacy=privacy,
        metadata=metadata,
        source_path=source.resolve(strict=False),
    )


def _load_yaml_mapping(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    if yaml is not None:
        loaded = yaml.safe_load(text)
        if not isinstance(loaded, Mapping):
            raise ValueError("manifest must be an object")
        return dict(loaded)
    result: dict[str, Any] = {}
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if raw_line[:1].isspace():
            raise ValueError(f"nested YAML requires PyYAML at line {line_number}")
        if ":" not in line:
            raise ValueError(f"invalid YAML line {line_number}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"missing key at line {line_number}")
        result[key] = _scalar(raw_value.strip())
    return result


def _scalar(value: str) -> Any:
    if not value:
        return ""
    lowered = value.lower()
    if lowered in {"null", "none", "~"}:
        return None
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value[:1] in {'"', "'", "[", "{"}:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return value.strip('"\'')
    try:
        return int(value)
    except ValueError:
        return value
