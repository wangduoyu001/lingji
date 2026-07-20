from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml


class FrontmatterError(ValueError):
    pass


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    normalized = text.lstrip("\ufeff")
    if not normalized.startswith("---\n"):
        return {}, normalized
    end = normalized.find("\n---", 4)
    if end == -1:
        raise FrontmatterError("Frontmatter is missing the closing delimiter")
    yaml_text = normalized[4:end]
    body_start = end + 4
    if body_start < len(normalized) and normalized[body_start] == "\n":
        body_start += 1
    metadata = yaml.safe_load(yaml_text) or {}
    if not isinstance(metadata, dict):
        raise FrontmatterError("Frontmatter root must be a mapping")
    return metadata, normalized[body_start:]


def render_frontmatter(metadata: dict[str, Any], body: str) -> str:
    yaml_text = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    ).rstrip()
    body = body.lstrip("\n")
    return f"---\n{yaml_text}\n---\n\n{body.rstrip()}\n"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
