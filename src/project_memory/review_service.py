from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.obsidian.frontmatter import atomic_write, content_hash, render_frontmatter, split_frontmatter


class MemoryReviewError(RuntimeError):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


class MemoryReviewService:
    """Owner review facade over the existing MemoryLifecycleService."""

    def __init__(self, lifecycle, *, database=None, index_sync: Callable[[Path], Any] | None = None, state_db=None):
        self.lifecycle = lifecycle
        self.layout = lifecycle.layout
        self.database = database
        self.index_sync = index_sync
        self.state_db = state_db or getattr(lifecycle, "state_db", None)

    def list_candidates(self, project_id: str | None = None, agent_id: str | None = None, memory_type: str | None = None, importance: str | None = None, q: str = "", limit: int = 50, offset: int = 0) -> dict[str, Any]:
        items = []
        for path in self._candidate_paths():
            record = self._read_candidate(path, include_content=False)
            if project_id and project_id not in record["project_ids"]:
                continue
            if agent_id and record["proposed_by"] != agent_id:
                continue
            if memory_type and record["memory_type"] != memory_type:
                continue
            if importance and record["importance"] != importance:
                continue
            if q and q.lower() not in (record["title"] + " " + record["content_preview"]).lower():
                continue
            items.append(record)
        items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        start = max(int(offset), 0)
        size = min(max(int(limit), 1), 200)
        return {"items": items[start:start + size], "total": len(items), "limit": size, "offset": start}

    def get_candidate(self, memory_id: str) -> dict[str, Any]:
        path = self._find_candidate(memory_id)
        return self._read_candidate(path, include_content=True)

    def approve(self, memory_id: str, *, owner_confirmed: bool, expected_content_hash: str, target_category: str = "General", agent_scope: list[str] | None = None) -> dict[str, Any]:
        if not owner_confirmed:
            raise MemoryReviewError("MEMORY_APPROVAL_REQUIRED")
        source = self._find_candidate(memory_id)
        self._require_hash(source, expected_content_hash)
        result = self.lifecycle.promote_candidate(source, True, agent_scope=agent_scope, target_category=target_category)
        target = self.layout.root / result["relative_path"]
        metadata, body = split_frontmatter(target.read_text(encoding="utf-8-sig"))
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        approved_hash = content_hash(body)
        metadata.update({"approved_hash": approved_hash, "approved_at": now, "approved_by": "owner", "review_status": "approved", "status": "active", "pin_to_context": True, "updated_at": now})
        atomic_write(target, render_frontmatter(metadata, body))
        self._sync(target)
        payload = {**result, "approved_hash": approved_hash, "approved_at": now, "approved_by": "owner"}
        self._event("memory_owner_approved", memory_id, payload)
        return payload

    def edit_and_approve(self, memory_id: str, *, content: str, expected_content_hash: str, owner_confirmed: bool, title: str | None = None, target_category: str = "General") -> dict[str, Any]:
        source = self._find_candidate(memory_id)
        self._require_hash(source, expected_content_hash)
        metadata, body = split_frontmatter(source.read_text(encoding="utf-8-sig"))
        if title is not None:
            metadata["title"] = title.strip() or metadata.get("title")
        metadata["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        new_body = self._replace_candidate_content(body, content)
        atomic_write(source, render_frontmatter(metadata, new_body))
        return self.approve(memory_id, owner_confirmed=owner_confirmed, expected_content_hash=content_hash(source.read_text(encoding="utf-8-sig")), target_category=target_category)

    def reject(self, memory_id: str, *, owner_confirmed: bool, expected_content_hash: str, reason: str) -> dict[str, Any]:
        if not owner_confirmed:
            raise MemoryReviewError("MEMORY_APPROVAL_REQUIRED")
        if not reason.strip():
            raise ValueError("rejection reason is required")
        source = self._find_candidate(memory_id)
        self._require_hash(source, expected_content_hash)
        result = self.lifecycle.reject_candidate(source, True, reason=reason.strip())
        self._event("memory_owner_rejected", memory_id, {**result, "reason": reason.strip()})
        return result

    def create_owner_memory(self, *, title: str, content: str, project_ids: list[str], memory_type: str = "knowledge", importance: str = "high", privacy: str = "private", tags: list[str] | None = None, owner_confirmed: bool = True) -> dict[str, Any]:
        if not owner_confirmed:
            raise MemoryReviewError("MEMORY_APPROVAL_REQUIRED")
        candidate = self.lifecycle.propose_memory("owner_manual", title, content, {"project": list(project_ids), "project_ids": list(project_ids), "memory_type": memory_type, "importance": importance, "privacy": privacy, "tags": list(tags or []) + ["source/owner-manual"], "agent_scope": ["all"]})
        path = self.layout.root / candidate["relative_path"]
        return self.approve(candidate["id"], owner_confirmed=True, expected_content_hash=content_hash(path.read_text(encoding="utf-8-sig")))

    def correct_core_memory(self, memory_id: str, *, content: str, expected_content_hash: str, owner_confirmed: bool, reason: str, title: str | None = None) -> dict[str, Any]:
        """Create a new owner-confirmed version while retaining the old one."""
        if not owner_confirmed:
            raise MemoryReviewError("MEMORY_APPROVAL_REQUIRED")
        if not content.strip():
            raise ValueError("content is required")
        if not reason.strip():
            raise ValueError("reason is required")
        source = self._find_core(memory_id)
        self._require_hash(source, expected_content_hash)
        metadata, _ = split_frontmatter(source.read_text(encoding="utf-8-sig"))
        category = source.parent.name or "General"
        candidate = self.lifecycle.propose_memory(
            "owner_correction",
            title or str(metadata.get("title") or "修正后的记忆"),
            content,
            {
                "project_ids": self._list(metadata.get("project_ids") or metadata.get("project")),
                "memory_type": metadata.get("memory_type", "knowledge"),
                "importance": metadata.get("importance", "medium"),
                "privacy": metadata.get("privacy", "private"),
                "tags": self._list(metadata.get("tags")),
            },
        )
        candidate_path = self.layout.root / candidate["relative_path"]
        approved = self.approve(
            candidate["id"],
            owner_confirmed=True,
            expected_content_hash=content_hash(candidate_path.read_text(encoding="utf-8-sig")),
            target_category=category,
        )
        superseded = self.lifecycle.supersede_memory(source, approved["id"], True, reason=reason.strip())
        result = {**approved, "superseded_id": memory_id, "superseded": superseded}
        self._event("memory_owner_corrected", memory_id, result)
        return result

    def invalidate_core_memory(self, memory_id: str, *, expected_content_hash: str, owner_confirmed: bool, reason: str, valid_to: str | None = None) -> dict[str, Any]:
        if not owner_confirmed:
            raise MemoryReviewError("MEMORY_APPROVAL_REQUIRED")
        if not reason.strip():
            raise ValueError("reason is required")
        source = self._find_core(memory_id)
        self._require_hash(source, expected_content_hash)
        metadata, body = split_frontmatter(source.read_text(encoding="utf-8-sig"))
        now = valid_to or datetime.now(timezone.utc).isoformat(timespec="seconds")
        metadata.update({"status": "invalidated", "valid_to": now, "invalidating_reason": reason.strip(), "pin_to_context": False, "updated_at": now})
        atomic_write(source, render_frontmatter(metadata, body))
        self._sync(source)
        result = {"id": memory_id, "relative_path": self.layout.relative(source).as_posix(), "status": "invalidated", "valid_to": now, "reason": reason.strip()}
        self._event("memory_owner_invalidated", memory_id, result)
        return result

    def archive_core_memory(self, memory_id: str, *, owner_confirmed: bool, reason: str, expected_content_hash: str = "") -> dict[str, Any]:
        if not owner_confirmed:
            raise MemoryReviewError("MEMORY_APPROVAL_REQUIRED")
        path = self._find_core(memory_id)
        if expected_content_hash:
            self._require_hash(path, expected_content_hash)
        metadata, body = split_frontmatter(path.read_text(encoding="utf-8-sig"))
        if str(metadata.get("status") or "") == "archived":
            raise MemoryReviewError("MEMORY_ALREADY_REVIEWED")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        metadata.update({"status": "archived", "pin_to_context": False, "archived_at": now, "archive_reason": reason.strip(), "updated_at": now})
        atomic_write(path, render_frontmatter(metadata, body))
        self._sync(path)
        result = {"id": memory_id, "relative_path": self.layout.relative(path).as_posix(), "status": "archived", "archived_at": now}
        self._event("core_memory_archived", memory_id, result)
        return result

    def inspect_core_integrity(self, memory_id: str) -> dict[str, Any]:
        from .integrity import CoreMemoryIntegrityService
        return CoreMemoryIntegrityService(self.layout).inspect(memory_id)

    def _candidate_paths(self):
        root = self.layout.root / "01-Inbox" / "AI-Memory"
        return root.rglob("*.md") if root.exists() else ()

    def _find_candidate(self, memory_id: str) -> Path:
        for path in self._candidate_paths():
            metadata, _ = split_frontmatter(path.read_text(encoding="utf-8-sig"))
            if str(metadata.get("id") or "") == memory_id:
                if metadata.get("memory_tier") != "candidate" or metadata.get("review_status") != "needs_review":
                    raise MemoryReviewError("MEMORY_ALREADY_REVIEWED")
                return path
        raise MemoryReviewError("MEMORY_CANDIDATE_NOT_FOUND")

    def _find_core(self, memory_id: str) -> Path:
        root = self.layout.root / "03-Knowledge" / "Core-Memory"
        for path in root.rglob("*.md") if root.exists() else ():
            metadata, _ = split_frontmatter(path.read_text(encoding="utf-8-sig"))
            if str(metadata.get("id") or "") == memory_id:
                return path
        raise MemoryReviewError("CORE_MEMORY_NOT_FOUND")

    def _read_candidate(self, path: Path, *, include_content: bool) -> dict[str, Any]:
        raw = path.read_text(encoding="utf-8-sig")
        metadata, body = split_frontmatter(raw)
        content = self._candidate_content(body)
        result = {
            "memory_id": str(metadata.get("id") or ""), "title": str(metadata.get("title") or path.stem),
            "content_preview": content[:500], "project_ids": self._list(metadata.get("project_ids") or metadata.get("project")),
            "proposed_by": str(metadata.get("proposed_by") or ""), "memory_type": str(metadata.get("memory_type") or "knowledge"),
            "importance": str(metadata.get("importance") or ""), "confidence": metadata.get("confidence"),
            "created_at": str(metadata.get("created_at") or ""), "source_refs": self._list(metadata.get("source_refs") or metadata.get("sources")),
            "current_hash": content_hash(raw), "relative_path": self.layout.relative(path).as_posix(), "similar_core": self._similar_core(str(metadata.get("title") or "")),
        }
        if include_content:
            result["content"] = content
        return result

    def _similar_core(self, title: str):
        if not self.database or not title:
            return []
        values = self.database.list_core_memories(limit=20)
        words = {word.lower() for word in title.split() if len(word) > 1}
        return [{"memory_id": item.get("memory_id"), "title": item.get("title")} for item in values if words & {word.lower() for word in str(item.get("title") or "").split()}][:5]

    @staticmethod
    def _list(value):
        if value in (None, ""):
            return []
        return list(value) if isinstance(value, (list, tuple, set)) else [value]

    @staticmethod
    def _candidate_content(body: str) -> str:
        marker = "## 候选记忆"
        review = "## 主人审核"
        value = body.split(marker, 1)[1] if marker in body else body
        return value.split(review, 1)[0].strip()

    @staticmethod
    def _replace_candidate_content(body: str, content: str) -> str:
        before = body.split("## 候选记忆", 1)[0] if "## 候选记忆" in body else ""
        after = body.split("## 主人审核", 1)[1] if "## 主人审核" in body else ""
        return f"{before.rstrip()}\n\n## 候选记忆\n\n{content.strip()}\n\n## 主人审核\n{after.lstrip()}"

    @staticmethod
    def _require_hash(path: Path, expected: str):
        current = content_hash(path.read_text(encoding="utf-8-sig"))
        if not expected or current != expected:
            raise MemoryReviewError("MEMORY_REVIEW_CONFLICT")

    def _sync(self, path: Path):
        if self.index_sync:
            self.index_sync(path)

    def _event(self, event_type: str, memory_id: str, payload: dict[str, Any]):
        if self.state_db:
            self.state_db.append_event(event_type, "memory_review", memory_id, payload)
