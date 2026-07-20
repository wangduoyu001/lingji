from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from .vault_layout import VaultLayout


class InboxService:
    """Create append-only inbox notes inside the single Obsidian vault."""

    def __init__(self, layout: VaultLayout):
        self.layout = layout

    def create_text_item(
        self,
        source_type: str,
        title: str,
        content: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        item_id = f"LJ-SOURCE-{now:%Y%m%d}-{uuid4().hex[:8].upper()}"
        safe_title = self.layout.sanitize_filename(title).removesuffix(".md")
        filename = f"{now:%Y%m%d-%H%M%S}-{safe_title}.md"
        path = self.layout.inbox_path(source_type, filename, now)
        payload = dict(metadata or {})
        payload.setdefault("schema_version", 1)
        payload.setdefault("id", item_id)
        payload.setdefault("title", title.strip() or "未命名内容")
        payload.setdefault("memory_type", "source")
        payload.setdefault("source_type", source_type)
        payload.setdefault("status", "received")
        payload.setdefault("privacy", "private")
        payload.setdefault("created_at", now.isoformat(timespec="seconds"))
        payload.setdefault("updated_at", now.isoformat(timespec="seconds"))
        payload.setdefault("content_hash", hashlib.sha256(content.encode("utf-8")).hexdigest())

        text = self._render_note(payload, content)
        self._atomic_write(path, text)
        return {
            "id": item_id,
            "path": str(path),
            "relative_path": self.layout.relative(path).as_posix(),
            "status": "received",
        }

    def create_reference_item(
        self,
        source_type: str,
        title: str,
        source_path: Path | str,
        note: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = Path(source_path).expanduser()
        payload = dict(metadata or {})
        payload["source_path"] = str(source)
        if source.exists() and source.is_file():
            payload["source_size"] = source.stat().st_size
            payload["source_modified_at"] = datetime.fromtimestamp(source.stat().st_mtime).isoformat(timespec="seconds")
        body = note.strip() or "该条目仅登记原始文件位置，未复制或修改原文件。"
        return self.create_text_item(source_type, title, body, payload)

    @staticmethod
    def _render_note(metadata: Mapping[str, Any], content: str) -> str:
        lines = ["---"]
        preferred_order = (
            "schema_version",
            "id",
            "title",
            "memory_type",
            "project_id",
            "tool_id",
            "source_type",
            "source_id",
            "source_path",
            "source_url",
            "status",
            "importance",
            "confidence",
            "privacy",
            "created_at",
            "updated_at",
            "content_hash",
            "tags",
            "related_ids",
            "review_status",
        )
        written: set[str] = set()
        for key in preferred_order:
            if key in metadata and metadata[key] not in (None, "", []):
                lines.extend(InboxService._yaml_lines(key, metadata[key]))
                written.add(key)
        for key in sorted(set(metadata) - written):
            if metadata[key] not in (None, "", []):
                lines.extend(InboxService._yaml_lines(key, metadata[key]))
        lines.extend(["---", "", f"# {metadata.get('title', '未命名内容')}", "", "## 原始内容", "", content.rstrip(), ""])
        return "\n".join(lines)

    @staticmethod
    def _yaml_lines(key: str, value: Any) -> list[str]:
        if isinstance(value, (list, tuple, set)):
            result = [f"{key}:"]
            result.extend(f"  - {json.dumps(item, ensure_ascii=False)}" for item in value)
            return result
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (int, float)):
            rendered = str(value)
        else:
            rendered = json.dumps(str(value), ensure_ascii=False)
        return [f"{key}: {rendered}"]

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(text, encoding="utf-8")
        temp_path.replace(path)
