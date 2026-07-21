from __future__ import annotations

from pathlib import Path

from src.obsidian.frontmatter import content_hash, split_frontmatter


class CoreMemoryIntegrityService:
    """Read-only drift detection for owner-approved core memories."""

    def __init__(self, layout):
        self.layout = layout

    def inspect(self, memory_id: str) -> dict[str, str]:
        path = self._find(memory_id)
        if path is None:
            return {
                "memory_id": memory_id,
                "state": "missing",
                "approved_hash": "",
                "current_hash": "",
                "last_approved_at": "",
                "relative_path": "",
            }
        raw = path.read_text(encoding="utf-8-sig")
        metadata, body = split_frontmatter(raw)
        approved = str(metadata.get("approved_hash") or "")
        current = content_hash(body)
        state = "healthy" if approved and current == approved else "external_modified"
        return {
            "memory_id": memory_id,
            "state": state,
            "approved_hash": approved,
            "current_hash": current,
            "last_approved_at": str(metadata.get("approved_at") or metadata.get("promoted_at") or ""),
            "relative_path": self.layout.relative(path).as_posix(),
        }

    def scan(self) -> list[dict[str, str]]:
        root = self.layout.root / "03-Knowledge" / "Core-Memory"
        results = []
        for path in root.rglob("*.md") if root.exists() else ():
            metadata, _ = split_frontmatter(path.read_text(encoding="utf-8-sig"))
            memory_id = str(metadata.get("id") or "")
            if memory_id:
                results.append(self.inspect(memory_id))
        return results

    def _find(self, memory_id: str) -> Path | None:
        root = self.layout.root / "03-Knowledge" / "Core-Memory"
        for path in root.rglob("*.md") if root.exists() else ():
            try:
                metadata, _ = split_frontmatter(path.read_text(encoding="utf-8-sig"))
            except OSError:
                continue
            if str(metadata.get("id") or "") == memory_id:
                return path
        return None
