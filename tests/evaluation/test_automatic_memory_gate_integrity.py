from pathlib import Path

import pytest

from src.automatic_memory.quality_evidence import ProtectedTreeSentinel
from src.automatic_memory.quality_evidence import ImportedEvidenceAudit


def test_protected_sentinel_detects_nested_mutation(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "nested").mkdir()
    (root / "nested" / "x.txt").write_text("before", encoding="utf-8")
    before = ProtectedTreeSentinel.capture((root,))
    (root / "nested" / "x.txt").write_text("after", encoding="utf-8")
    changes = before.diff(ProtectedTreeSentinel.capture((root,)))
    assert any(change.path.endswith("nested/x.txt") for change in changes)


def test_protected_sentinel_rejects_symlink_escape(tmp_path: Path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir(); outside.mkdir()
    (outside / "secret").write_text("x", encoding="utf-8")
    (root / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        ProtectedTreeSentinel.capture((root,))


def test_protected_sentinel_rejects_missing_root(tmp_path: Path):
    with pytest.raises(ValueError, match="missing"):
        ProtectedTreeSentinel.capture((tmp_path / "missing",))


def test_import_audit_counts_extra_duplicate_and_role_order_hash():
    class ReadModel:
        def list_messages(self, **kwargs):
            return {"items": [
                {"external_id": "m1", "role": "user", "sequence": 1, "content_hash": "h1", "source_id": "s", "conversation_id": "c"},
                {"external_id": "m1", "role": "assistant", "sequence": 0, "content_hash": "wrong", "source_id": "other", "conversation_id": "other"},
                {"external_id": "extra", "role": "user", "sequence": 2, "content_hash": "hx", "source_id": "s", "conversation_id": "c"}], "next_offset": None}
    class R:
        message_id = "m1"; role = "user"; content_hash = "h1"; source_id = "s"; conversation_id = "c"; occurred_at = ""
    audit = ImportedEvidenceAudit.from_read_model(ReadModel(), [R()])
    assert (audit.actual, audit.extra, audit.duplicate, audit.ordered_role_matches, audit.content_hash_matches) == (3, 1, 1, 1, 1)
