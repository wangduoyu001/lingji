from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.obsidian.frontmatter import atomic_write, render_frontmatter, split_frontmatter


class MemoryLifecycleService:
    """Manage candidate, core and superseded memories in the Obsidian vault."""

    def __init__(self, layout, state_db=None):
        self.layout = layout
        self.state_db = state_db

    def propose_memory(
        self,
        agent_id: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        memory_id = f"LJ-MEM-{now:%Y%m%d}-{uuid4().hex[:10].upper()}"
        safe_agent = self.layout.sanitize_filename(agent_id or "unknown").replace(".md", "")
        safe_title = self.layout.sanitize_filename(title or "未命名记忆").removesuffix(".md")
        target = (
            self.layout.root
            / "01-Inbox"
            / "AI-Memory"
            / safe_agent
            / now.strftime("%Y")
            / now.strftime("%m")
            / f"{now:%Y%m%d-%H%M%S}-{safe_title}.md"
        )
        values = dict(metadata or {})
        values.update(
            {
                "schema_version": 1,
                "id": memory_id,
                "title": title.strip() or "未命名记忆",
                "memory_type": values.get("memory_type", "knowledge"),
                "memory_tier": "candidate",
                "status": "needs_review",
                "review_status": "needs_review",
                "privacy": values.get("privacy", "private"),
                "importance": values.get("importance", "medium"),
                "confidence": values.get("confidence", ""),
                "pin_to_context": False,
                "agent_scope": values.get("agent_scope", [agent_id]),
                "proposed_by": agent_id,
                "created_at": now.isoformat(timespec="seconds"),
                "updated_at": now.isoformat(timespec="seconds"),
                "tags": self._merge_tags(values.get("tags"), ["signal/memory-candidate", "attention/review"]),
            }
        )
        body = "\n".join(
            [
                f"# {values['title']}",
                "",
                "> 这是 AI 提议的永久记忆候选，未经主人确认不会进入核心记忆。",
                "",
                "## 候选记忆",
                "",
                content.strip(),
                "",
                "## 主人审核",
                "",
                "- [ ] 内容准确",
                "- [ ] 值得长期保留",
                "- [ ] 允许加入核心上下文",
                "- 审核备注：",
                "",
            ]
        )
        atomic_write(target, render_frontmatter(values, body))
        result = {
            "id": memory_id,
            "path": str(target),
            "relative_path": self.layout.relative(target).as_posix(),
            "status": "needs_review",
            "memory_tier": "candidate",
        }
        self._event("memory_proposed", memory_id, {**result, "agent_id": agent_id})
        return result

    def promote_candidate(
        self,
        candidate_path: Path | str,
        owner_confirmed: bool,
        agent_scope: list[str] | None = None,
        recall_weight: float = 1.2,
        target_category: str = "General",
    ) -> dict[str, Any]:
        if not owner_confirmed:
            raise PermissionError("Promoting permanent memory requires explicit owner confirmation")
        source = self._resolve_candidate(candidate_path)
        original = source.read_text(encoding="utf-8-sig")
        metadata, body = split_frontmatter(original)
        if metadata.get("memory_tier") != "candidate":
            raise ValueError("Only candidate memories can be promoted")
        if metadata.get("review_status") == "rejected":
            raise ValueError("Rejected memory cannot be promoted")

        safe_category = self.layout.sanitize_filename(target_category or "General").removesuffix(".md")
        target_dir = self.layout.root / "03-Knowledge" / "Core-Memory" / safe_category
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / self.layout.sanitize_filename(source.name)
        if target.exists() and target.resolve() != source.resolve():
            target = target_dir / f"{source.stem}-{str(metadata.get('id') or '')[-8:]}.md"

        now = datetime.now().isoformat(timespec="seconds")
        metadata.update(
            {
                "memory_tier": "core",
                "status": "active",
                "review_status": "approved",
                "pin_to_context": True,
                "agent_scope": agent_scope or metadata.get("agent_scope") or ["all"],
                "recall_weight": max(float(recall_weight), 1.0),
                "promoted_at": now,
                "updated_at": now,
                "tags": self._merge_tags(
                    metadata.get("tags"),
                    ["signal/core-memory"],
                    remove={"signal/memory-candidate", "attention/review"},
                ),
            }
        )
        atomic_write(target, render_frontmatter(metadata, body))
        if source.resolve() != target.resolve():
            source.unlink()
            self._remove_empty_parents(source.parent, self.layout.root / "01-Inbox" / "AI-Memory")
        result = {
            "id": str(metadata.get("id")),
            "path": str(target),
            "relative_path": self.layout.relative(target).as_posix(),
            "status": "active",
            "memory_tier": "core",
            "pin_to_context": True,
        }
        self._event("memory_promoted", result["id"], result)
        return result

    def supersede_memory(
        self,
        memory_path: Path | str,
        superseded_by: str,
        owner_confirmed: bool,
        reason: str = "",
    ) -> dict[str, Any]:
        if not owner_confirmed:
            raise PermissionError("Superseding permanent memory requires explicit owner confirmation")
        target = self.layout.root / self.layout.relative(memory_path)
        original = target.read_text(encoding="utf-8-sig")
        metadata, body = split_frontmatter(original)
        now = datetime.now().isoformat(timespec="seconds")
        metadata.update(
            {
                "status": "superseded",
                "valid_to": now,
                "superseded_by": superseded_by,
                "pin_to_context": False,
                "updated_at": now,
            }
        )
        if reason:
            metadata["supersede_reason"] = reason
        atomic_write(target, render_frontmatter(metadata, body))
        result = {
            "id": str(metadata.get("id")),
            "relative_path": self.layout.relative(target).as_posix(),
            "status": "superseded",
            "valid_to": now,
            "superseded_by": superseded_by,
        }
        self._event("memory_superseded", result["id"], result)
        return result

    def reject_candidate(
        self,
        candidate_path: Path | str,
        owner_confirmed: bool,
        reason: str = "",
    ) -> dict[str, Any]:
        if not owner_confirmed:
            raise PermissionError("Rejecting a memory candidate requires owner confirmation")
        target = self._resolve_candidate(candidate_path)
        metadata, body = split_frontmatter(target.read_text(encoding="utf-8-sig"))
        now = datetime.now().isoformat(timespec="seconds")
        metadata.update(
            {
                "status": "rejected",
                "review_status": "rejected",
                "pin_to_context": False,
                "rejected_at": now,
                "updated_at": now,
            }
        )
        if reason:
            metadata["rejection_reason"] = reason
        atomic_write(target, render_frontmatter(metadata, body))
        result = {
            "id": str(metadata.get("id")),
            "relative_path": self.layout.relative(target).as_posix(),
            "status": "rejected",
        }
        self._event("memory_rejected", result["id"], result)
        return result

    def _resolve_candidate(self, path: Path | str) -> Path:
        relative = self.layout.relative(path)
        if relative.parts[:2] != ("01-Inbox", "AI-Memory"):
            raise PermissionError("Memory candidate must be inside 01-Inbox/AI-Memory")
        target = self.layout.root / relative
        if not target.exists():
            raise FileNotFoundError(target)
        return target

    @staticmethod
    def _merge_tags(
        existing: Any,
        additions: list[str],
        remove: set[str] | None = None,
    ) -> list[str]:
        values = existing if isinstance(existing, list) else ([existing] if existing else [])
        blocked = remove or set()
        output = []
        for value in [*values, *additions]:
            tag = str(value)
            if tag and tag not in blocked and tag not in output:
                output.append(tag)
        return output

    @staticmethod
    def _remove_empty_parents(path: Path, stop: Path) -> None:
        current = path
        while current != stop and stop in current.parents:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    def _event(self, event_type: str, memory_id: str, payload: dict[str, Any]) -> None:
        if self.state_db:
            self.state_db.append_event(event_type, "memory", memory_id, payload)
