from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from src.obsidian.frontmatter import atomic_write, render_frontmatter, split_frontmatter


class SkillRegistry:
    """Human-readable skill registry.

    Skill implementation code remains in Git or its original package. Obsidian is
    the control plane for discovery, status, compatibility, documentation and
    verification evidence, not a second copy of executable source code.
    """

    OWNER_FIELDS = {
        "status",
        "review_status",
        "owner_confirmed",
        "importance",
        "tags",
        "project",
        "notes",
    }

    def __init__(self, layout, state_db=None):
        self.layout = layout
        self.state_db = state_db
        self.root = layout.root / "07-Assets" / "Skills"
        self.root.mkdir(parents=True, exist_ok=True)

    def register(self, manifest: Mapping[str, Any]) -> dict[str, Any]:
        data = dict(manifest)
        skill_id = self._skill_id(data)
        name = str(data.get("name") or data.get("title") or skill_id).strip()
        now = datetime.now().isoformat(timespec="seconds")
        source_path = str(data.get("source_path") or "")
        source_hash = self._source_hash(Path(source_path)) if source_path else ""
        metadata = {
            "schema_version": 1,
            "id": f"LJ-SKILL-{skill_id}",
            "skill_id": skill_id,
            "title": name,
            "memory_type": "skill",
            "status": str(data.get("status") or "active"),
            "review_status": str(data.get("review_status") or "needs_review"),
            "owner_confirmed": bool(data.get("owner_confirmed", False)),
            "version": str(data.get("version") or "unknown"),
            "source_path": source_path,
            "source_hash": source_hash,
            "repository": str(data.get("repository") or ""),
            "entrypoint": str(data.get("entrypoint") or ""),
            "runtime": str(data.get("runtime") or ""),
            "capabilities": self._list(data.get("capabilities")),
            "triggers": self._list(data.get("triggers")),
            "dependencies": self._list(data.get("dependencies")),
            "compatible_agents": self._list(data.get("compatible_agents")),
            "tests": self._list(data.get("tests")),
            "last_verified_at": str(data.get("last_verified_at") or ""),
            "project": self._list(data.get("project") or data.get("project_id")),
            "tags": self._list(data.get("tags")) or ["domain/ai", "topic/skill"],
            "privacy": str(data.get("privacy") or "private"),
            "created_at": str(data.get("created_at") or now),
            "updated_at": now,
            "lingji_managed": True,
        }
        body = self._render_body(name, data)
        target = self.root / f"{skill_id}.md"
        if target.exists():
            existing_text = target.read_text(encoding="utf-8-sig")
            existing_metadata, existing_body = split_frontmatter(existing_text)
            for key in self.OWNER_FIELDS:
                if key in existing_metadata:
                    metadata[key] = existing_metadata[key]
            manual = self._manual_notes(existing_body)
            if manual:
                body = body.replace("<!-- LINGJI:SKILL-NOTES -->", manual)
            rendered = render_frontmatter(metadata, body)
            if rendered == existing_text:
                action = "skipped"
            else:
                atomic_write(target, rendered)
                action = "updated"
        else:
            atomic_write(target, render_frontmatter(metadata, body))
            action = "created"
        result = {
            "action": action,
            "skill_id": skill_id,
            "path": str(target),
            "relative_path": self.layout.relative(target).as_posix(),
            "source_hash": source_hash,
        }
        self._event("skill_registered", skill_id, result)
        return result

    def sync_directory(self, root: Path | str, limit: int = 500) -> dict[str, Any]:
        base = Path(root).expanduser()
        if not base.exists():
            raise FileNotFoundError(base)
        files = sorted(base.rglob("SKILL.md"))[: max(int(limit), 1)]
        results = []
        errors = []
        for path in files:
            try:
                metadata, body = split_frontmatter(path.read_text(encoding="utf-8-sig"))
                title = self._first_heading(body) or path.parent.name
                manifest = {
                    **metadata,
                    "name": metadata.get("name") or title,
                    "skill_id": metadata.get("skill_id") or path.parent.name,
                    "source_path": str(path),
                    "description": metadata.get("description") or self._first_paragraph(body),
                }
                results.append(self.register(manifest))
            except Exception as exc:
                errors.append({"path": str(path), "error": str(exc)[:1000]})
        return {
            "root": str(base),
            "found": len(files),
            "succeeded": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }

    def list(self, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        results = []
        for path in sorted(self.root.glob("*.md")):
            try:
                metadata, _ = split_frontmatter(path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            if status and str(metadata.get("status") or "") != status:
                continue
            results.append({**metadata, "relative_path": self.layout.relative(path).as_posix()})
            if len(results) >= max(int(limit), 1):
                break
        return results

    def get(self, skill_id: str) -> dict[str, Any] | None:
        normalized = self._safe_id(skill_id)
        path = self.root / f"{normalized}.md"
        if not path.exists():
            return None
        metadata, body = split_frontmatter(path.read_text(encoding="utf-8-sig"))
        return {**metadata, "body": body, "relative_path": self.layout.relative(path).as_posix()}

    def status(self) -> dict[str, Any]:
        skills = self.list(limit=10_000)
        counts: dict[str, int] = {}
        for item in skills:
            state = str(item.get("status") or "unknown")
            counts[state] = counts.get(state, 0) + 1
        return {"total": len(skills), "by_status": counts, "root": str(self.root)}

    @classmethod
    def _skill_id(cls, data: Mapping[str, Any]) -> str:
        raw = str(data.get("skill_id") or data.get("id") or data.get("name") or "").strip()
        if not raw:
            raw = hashlib.sha256(
                json.dumps(dict(data), ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:16]
        return cls._safe_id(raw)

    @staticmethod
    def _safe_id(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-.").lower()
        return cleaned[:100] or "unknown-skill"

    @staticmethod
    def _list(value: Any) -> list[Any]:
        if value in (None, "", []):
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _source_hash(path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _first_heading(body: str) -> str:
        for line in body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    @staticmethod
    def _first_paragraph(body: str) -> str:
        for block in re.split(r"\n\s*\n", body):
            value = block.strip()
            if value and not value.startswith("#"):
                return value[:500]
        return ""

    @staticmethod
    def _manual_notes(body: str) -> str:
        marker = "<!-- LINGJI:SKILL-NOTES -->"
        index = body.find(marker)
        return body[index:] if index >= 0 else ""

    @staticmethod
    def _render_body(name: str, data: Mapping[str, Any]) -> str:
        description = str(data.get("description") or "").strip()
        usage = str(data.get("usage") or data.get("instructions") or "").strip()
        return (
            f"# {name}\n\n"
            "## 定位\n\n"
            f"{description or '待补充。'}\n\n"
            "## 使用方式\n\n"
            f"{usage or '以 source_path 指向的 SKILL.md 或仓库文档为准。'}\n\n"
            "## 验证与维护\n\n"
            "- 源代码和可执行实现保留在 Git 或原安装目录。\n"
            "- Obsidian 只管理说明、状态、触发条件、依赖、测试证据和关联项目。\n"
            "- 修改技能实现后必须更新版本并重新验证。\n\n"
            "<!-- LINGJI:SKILL-NOTES -->\n\n"
            "## 人工备注\n\n"
        )

    def _event(self, event_type: str, entity_id: str, payload: Any) -> None:
        if self.state_db:
            self.state_db.append_event(event_type, "skill", entity_id, payload)
