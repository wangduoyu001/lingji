from pathlib import Path

import pytest

from src.obsidian.frontmatter import content_hash, render_frontmatter
from src.project_memory.review_service import MemoryReviewError, MemoryReviewService


class Layout:
    def __init__(self, root): self.root = root
    def relative(self, path): return Path(path).resolve().relative_to(self.root.resolve())


class Lifecycle:
    def __init__(self, root): self.layout = Layout(root); self.state_db = None; self.promoted = []
    def promote_candidate(self, source, owner_confirmed, **_):
        self.promoted.append(source)
        target = self.layout.root / "03-Knowledge/Core-Memory/General/core.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(Path(source).read_text(encoding="utf-8"), encoding="utf-8")
        Path(source).unlink()
        return {"id": "LJ-MEM-1", "relative_path": self.layout.relative(target).as_posix(), "status": "active", "memory_tier": "core", "pin_to_context": True}
    def reject_candidate(self, source, owner_confirmed, reason=""):
        return {"id": "LJ-MEM-1", "status": "rejected", "reason": reason}


def candidate(root):
    path = root / "01-Inbox/AI-Memory/codex/c.md"
    path.parent.mkdir(parents=True)
    path.write_text(render_frontmatter({"id": "LJ-MEM-1", "title": "T", "memory_tier": "candidate", "review_status": "needs_review", "status": "needs_review", "privacy": "private", "project": ["P"], "proposed_by": "codex"}, "## 候选记忆\n\nbody\n\n## 主人审核\n"), encoding="utf-8")
    return path


def test_approve_requires_hash_and_syncs(tmp_path):
    path = candidate(tmp_path); synced = []
    service = MemoryReviewService(Lifecycle(tmp_path), index_sync=synced.append)
    with pytest.raises(MemoryReviewError) as exc:
        service.approve("LJ-MEM-1", owner_confirmed=True, expected_content_hash="bad")
    assert exc.value.code == "MEMORY_REVIEW_CONFLICT"
    result = service.approve("LJ-MEM-1", owner_confirmed=True, expected_content_hash=content_hash(path.read_text(encoding="utf-8")))
    assert result["approved_hash"] and synced


def test_reject_requires_reason(tmp_path):
    path = candidate(tmp_path); service = MemoryReviewService(Lifecycle(tmp_path))
    with pytest.raises(ValueError):
        service.reject("LJ-MEM-1", owner_confirmed=True, expected_content_hash=content_hash(path.read_text()), reason="")
