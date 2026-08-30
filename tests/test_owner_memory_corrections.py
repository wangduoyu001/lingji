from pathlib import Path

import pytest

from src.obsidian.frontmatter import content_hash, render_frontmatter, split_frontmatter
from src.project_memory.review_service import MemoryReviewError, MemoryReviewService


class Layout:
    def __init__(self, root: Path):
        self.root = root

    def relative(self, path):
        return Path(path).resolve().relative_to(self.root.resolve())

    @staticmethod
    def sanitize_filename(value):
        return str(value).replace("/", "-")


class Lifecycle:
    def __init__(self, root: Path):
        self.layout = Layout(root)
        self.state_db = None

    def promote_candidate(self, source, owner_confirmed, **_):
        target = self.layout.root / "03-Knowledge/Core-Memory/General/core.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        metadata, body = split_frontmatter(Path(source).read_text(encoding="utf-8"))
        metadata.update({"memory_tier": "core", "status": "active", "review_status": "approved"})
        target.write_text(render_frontmatter(metadata, body), encoding="utf-8")
        Path(source).unlink()
        return {"id": metadata["id"], "relative_path": self.layout.relative(target).as_posix(), "status": "active"}

    def propose_memory(self, agent_id, title, content, metadata=None):
        path = self.layout.root / "01-Inbox/AI-Memory/corrections/new.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        values = {"id": "corrected-1", "title": title, "memory_tier": "candidate", "review_status": "needs_review", "status": "needs_review", **(metadata or {})}
        path.write_text(render_frontmatter(values, f"## 候选记忆\n\n{content}\n\n## 主人审核\n"), encoding="utf-8")
        return {"id": values["id"], "relative_path": self.layout.relative(path).as_posix(), "status": "needs_review"}

    def reject_candidate(self, source, owner_confirmed, reason=""):
        metadata, body = split_frontmatter(Path(source).read_text(encoding="utf-8"))
        metadata.update({"status": "rejected", "review_status": "rejected", "rejection_reason": reason})
        target = self.layout.root / "09-Archive" / Path(source).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_frontmatter(metadata, body), encoding="utf-8")
        Path(source).unlink()
        return {"id": metadata["id"], "relative_path": self.layout.relative(target).as_posix(), "status": "rejected"}

    def supersede_memory(self, memory_path, superseded_by, owner_confirmed, reason=""):
        path = self.layout.root / self.layout.relative(memory_path)
        metadata, body = split_frontmatter(path.read_text(encoding="utf-8"))
        metadata.update({"status": "superseded", "valid_to": "2026-08-29T00:00:00+00:00", "superseded_by": superseded_by, "supersede_reason": reason})
        path.write_text(render_frontmatter(metadata, body), encoding="utf-8")
        return {"id": metadata["id"], "status": "superseded", "superseded_by": superseded_by}


def write_candidate(root: Path) -> Path:
    path = root / "01-Inbox/AI-Memory/codex/c.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_frontmatter(
            {"id": "candidate-1", "title": "原始主题", "memory_tier": "candidate", "review_status": "needs_review", "status": "needs_review"},
            "## 候选记忆\n\n原始内容\n\n## 主人审核\n",
        ),
        encoding="utf-8",
    )
    return path


def write_core(root: Path) -> Path:
    path = root / "03-Knowledge/Core-Memory/General/current.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_frontmatter(
            {"id": "core-1", "title": "当前主题", "memory_tier": "core", "status": "active", "review_status": "approved"},
            "## 核心记忆\n\n当前内容\n",
        ),
        encoding="utf-8",
    )
    return path


def test_owner_correction_creates_new_version_and_supersedes_old(tmp_path):
    old = write_core(tmp_path)
    service = MemoryReviewService(Lifecycle(tmp_path))

    result = service.correct_core_memory("core-1", content="修正后的内容", expected_content_hash=content_hash(old.read_text(encoding="utf-8")), owner_confirmed=True, reason="主人修正")

    assert result["status"] == "active"
    assert result["superseded_id"] == "core-1"
    assert result["id"] != "core-1"
    old_meta, _ = split_frontmatter(old.read_text(encoding="utf-8"))
    assert old_meta["status"] == "superseded"
    assert old_meta["superseded_by"] == result["id"]
    assert "修正后的内容" in (tmp_path / result["relative_path"]).read_text(encoding="utf-8")


def test_owner_invalidation_requires_reason_and_preserves_file(tmp_path):
    current = write_core(tmp_path)
    service = MemoryReviewService(Lifecycle(tmp_path))
    expected = content_hash(current.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="reason"):
        service.invalidate_core_memory("core-1", expected_content_hash=expected, owner_confirmed=True, reason="")
    result = service.invalidate_core_memory("core-1", expected_content_hash=expected, owner_confirmed=True, reason="已不再适用")

    assert result["status"] == "invalidated"
    assert current.exists()
    metadata, _ = split_frontmatter(current.read_text(encoding="utf-8"))
    assert metadata["status"] == "invalidated"
    assert metadata["invalidating_reason"] == "已不再适用"


def test_owner_archive_requires_reason_and_returns_auditable_reason(tmp_path):
    current = write_core(tmp_path)
    service = MemoryReviewService(Lifecycle(tmp_path))
    expected = content_hash(current.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="reason"):
        service.archive_core_memory("core-1", expected_content_hash=expected, owner_confirmed=True, reason="")

    result = service.archive_core_memory("core-1", expected_content_hash=expected, owner_confirmed=True, reason="不再属于当前工作")
    assert result["status"] == "archived"
    metadata, _ = split_frontmatter(current.read_text(encoding="utf-8"))
    assert metadata["archive_reason"] == "不再属于当前工作"


def test_owner_correction_stale_hash_is_conflict_without_overwrite(tmp_path):
    current = write_core(tmp_path)
    service = MemoryReviewService(Lifecycle(tmp_path))

    with pytest.raises(MemoryReviewError) as exc:
        service.correct_core_memory("core-1", content="不能覆盖", expected_content_hash="stale", owner_confirmed=True, reason="修改")

    assert exc.value.code == "MEMORY_REVIEW_CONFLICT"
    assert "当前内容" in current.read_text(encoding="utf-8")


def test_candidate_confirm_edit_confirm_and_reject_keep_owner_gate(tmp_path):
    candidate = write_candidate(tmp_path)
    service = MemoryReviewService(Lifecycle(tmp_path))
    approved = service.approve("candidate-1", owner_confirmed=True, expected_content_hash=content_hash(candidate.read_text(encoding="utf-8")))
    assert approved["status"] == "active"

    candidate = write_candidate(tmp_path)
    edited = service.edit_and_approve("candidate-1", content="编辑后的内容", owner_confirmed=True, expected_content_hash=content_hash(candidate.read_text(encoding="utf-8")))
    assert edited["status"] == "active"

    candidate = write_candidate(tmp_path)
    rejected = service.reject("candidate-1", owner_confirmed=True, expected_content_hash=content_hash(candidate.read_text(encoding="utf-8")), reason="证据不足")
    assert rejected["status"] == "rejected"
    assert not candidate.exists()
    assert list((tmp_path / "09-Archive").rglob("*.md"))


def test_owner_correction_carries_provenance_relationships_and_validity(tmp_path):
    old = write_core(tmp_path)
    metadata, body = split_frontmatter(old.read_text(encoding="utf-8"))
    metadata.update({
        "source_refs": [{"message_id": "msg-1", "content_hash": "raw-1"}],
        "relationships": {"conversation_id": "conv-1", "evidence_refs": ["msg-1"]},
        "confidence": 0.94,
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_to": "2027-01-01T00:00:00Z",
    })
    old.write_text(render_frontmatter(metadata, body), encoding="utf-8")
    service = MemoryReviewService(Lifecycle(tmp_path))
    result = service.correct_core_memory("core-1", content="新内容", expected_content_hash=content_hash(old.read_text(encoding="utf-8")), owner_confirmed=True, reason="主人修正")
    new_meta, _ = split_frontmatter((tmp_path / result["relative_path"]).read_text(encoding="utf-8"))
    assert new_meta["source_refs"] == metadata["source_refs"]
    assert new_meta["relationships"] == metadata["relationships"]
    assert new_meta["confidence"] == metadata["confidence"]
    assert new_meta["valid_from"] == metadata["valid_from"]
    assert new_meta["valid_to"] == metadata["valid_to"]
