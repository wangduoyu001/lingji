from pathlib import Path

import pytest

from src.automatic_memory.quality_evidence import ExpectedImportedRow, ImportedEvidenceAudit, ProtectedTreeSentinel


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
        def list_ingestion_messages(self, ingestion_batch_id, *, limit=200, offset=0):
            rows = [
                {"source_id": "s", "source_external_id": "source", "conversation_id": "c", "conversation_external_id": "conversation", "message_id": "p1", "message_external_id": "m1", "ingestion_batch_id": ingestion_batch_id, "ingestion_ordinal": 0, "role": "user", "sequence": 1, "occurred_at": "", "content_hash": "h1"},
                {"source_id": "s", "source_external_id": "source", "conversation_id": "c", "conversation_external_id": "conversation", "message_id": "p2", "message_external_id": "m1", "ingestion_batch_id": ingestion_batch_id, "ingestion_ordinal": 1, "role": "assistant", "sequence": 0, "occurred_at": "", "content_hash": "wrong"},
                {"source_id": "s", "source_external_id": "source", "conversation_id": "conversation-2", "conversation_external_id": "conversation-2", "message_id": "p3", "message_external_id": "extra", "ingestion_batch_id": ingestion_batch_id, "ingestion_ordinal": 2, "role": "user", "sequence": 2, "occurred_at": "", "content_hash": "hx"},
            ]
            return {"items": rows[offset:offset + limit], "pagination": {"total": len(rows), "offset": offset, "limit": limit, "has_more": False}}
    expected = (ExpectedImportedRow("source", "conversation", "m1", 0, 1, "user", "h1", ""),)
    audit = ImportedEvidenceAudit.from_read_model(ReadModel(), ingestion_batch_id="batch", expected_rows=expected)
    assert (audit.actual_rows, len(audit.extra_external_keys), audit.stable_duplicates.message_records, audit.role_matches, audit.content_hash_matches) == (3, 1, 1, 1, 1)
