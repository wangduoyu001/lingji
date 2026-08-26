from __future__ import annotations

from pathlib import Path

import pytest

from src.automatic_memory.quality_evidence import (
    ContentHashGroup,
    ExpectedImportedRow,
    ImportedEvidenceAudit,
    StableDuplicateSummary,
    build_expected_import_rows,
)
from src.extraction.models import (
    ExtractionBatch,
    StructuredConversation,
    StructuredMessage,
    StructuredSource,
)
from src.sources import ExternalMessageKey


class FakeReadModel:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, int, int]] = []

    def list_ingestion_messages(self, ingestion_batch_id: str, *, limit: int = 200, offset: int = 0):
        self.calls.append((ingestion_batch_id, limit, offset))
        selected = [row for row in self.rows if row["ingestion_batch_id"] == ingestion_batch_id]
        items = selected[offset : offset + limit]
        return {
            "items": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(selected),
                "has_more": offset + len(items) < len(selected),
            },
        }


def expected_rows() -> tuple[ExpectedImportedRow, ...]:
    return (
        ExpectedImportedRow("s-1", "c-1", "m-1", 0, 0, "user", "h-1", "2026-01-01T00:00:00Z"),
        ExpectedImportedRow("s-1", "c-1", "m-2", 1, 1, "assistant", "h-2", "2026-01-01T00:00:01Z"),
        ExpectedImportedRow("s-2", "c-2", "m-3", 2, 0, "user", "h-1", "2026-01-01T00:00:02Z"),
    )


def persisted_row(item: ExpectedImportedRow, *, source_id: str | None = None, conversation_id: str | None = None):
    return {
        "source_id": source_id or f"source-primary-{item.source_external_id}",
        "source_external_id": item.source_external_id,
        "conversation_id": conversation_id or f"conversation-primary-{item.conversation_external_id}",
        "conversation_external_id": item.conversation_external_id,
        "message_id": f"message-primary-{item.message_external_id}",
        "message_external_id": item.message_external_id,
        "ingestion_batch_id": "batch-a",
        "ingestion_ordinal": item.ingestion_ordinal,
        "sequence": item.sequence,
        "role": item.role,
        "occurred_at": item.occurred_at,
        "content_hash": item.content_hash,
    }


def rows_for_expected(rows: tuple[ExpectedImportedRow, ...] | None = None) -> list[dict[str, object]]:
    return [persisted_row(item) for item in rows or expected_rows()]


def test_audit_is_batch_scoped_positional_and_read_only() -> None:
    rows = rows_for_expected()
    rows[0]["metadata"] = {"fixture_lifecycle": "active", "fixture_fact_id": "must-not-change"}
    rows.append({**rows[0], "ingestion_batch_id": "other-batch", "message_external_id": "leak"})
    before = [dict(row) for row in rows]
    read_model = FakeReadModel(rows)

    audit = ImportedEvidenceAudit.from_read_model(
        read_model,
        ingestion_batch_id="batch-a",
        expected_rows=expected_rows(),
    )

    assert audit.ready
    assert audit.expected_rows == audit.actual_rows == 3
    assert audit.stable_duplicates == StableDuplicateSummary(0, 0, 0, 0)
    assert read_model.calls == [("batch-a", 200, 0)]
    assert rows == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("role", "wrong-role"),
        ("sequence", 99),
        ("occurred_at", "wrong-time"),
        ("content_hash", "wrong-hash"),
        ("source_external_id", "wrong-source"),
        ("conversation_external_id", "wrong-conversation"),
        ("message_external_id", "wrong-message"),
    ],
)
def test_each_positional_field_mismatch_reduces_only_its_counter(field: str, value: object) -> None:
    rows = rows_for_expected()
    rows[0][field] = value
    audit = ImportedEvidenceAudit.from_read_model(
        FakeReadModel(rows), ingestion_batch_id="batch-a", expected_rows=expected_rows()
    )
    assert not audit.ready
    expected_count = {
        "message_external_id": "ordered_external_key_matches",
        "role": "role_matches",
        "sequence": "sequence_matches",
        "occurred_at": "timestamp_matches",
        "content_hash": "content_hash_matches",
        "source_external_id": "source_matches",
        "conversation_external_id": "conversation_matches",
    }
    assert audit.ordered_external_key_matches == (2 if field in {"message_external_id", "source_external_id", "conversation_external_id"} else 3)
    assert audit.role_matches == (2 if field == "role" else 3)
    assert audit.sequence_matches == (2 if field == "sequence" else 3)
    assert audit.timestamp_matches == (2 if field == "occurred_at" else 3)
    assert audit.content_hash_matches == (2 if field == "content_hash" else 3)
    assert audit.source_matches == (2 if field == "source_external_id" else 3)
    assert audit.conversation_matches == (2 if field == "conversation_external_id" else 3)
    assert getattr(audit, expected_count[field]) == 2 if field in expected_count else True


def test_swapped_persisted_order_is_not_sorted_away() -> None:
    rows = rows_for_expected()
    rows[0], rows[1] = rows[1], rows[0]
    audit = ImportedEvidenceAudit.from_read_model(
        FakeReadModel(rows), ingestion_batch_id="batch-a", expected_rows=expected_rows()
    )
    assert not audit.ready
    assert audit.ordered_external_key_matches == 1
    assert audit.role_matches == 1
    assert audit.sequence_matches == 1


def test_missing_extra_and_duplicate_composite_keys_are_deterministic() -> None:
    rows = rows_for_expected()
    rows.pop(1)
    rows.append({**rows[0], "ingestion_ordinal": 1})
    rows.append({**rows[0], "ingestion_ordinal": 2, "message_external_id": "extra"})
    audit = ImportedEvidenceAudit.from_read_model(
        FakeReadModel(rows), ingestion_batch_id="batch-a", expected_rows=expected_rows()
    )
    assert not audit.ready
    assert audit.missing_external_keys == (expected_rows()[1].stable_external_key,)
    assert audit.extra_external_keys == (ExternalMessageKey("s-1", "c-1", "extra"),)
    assert audit.stable_duplicates.message_records == 1


def test_duplicate_scopes_use_primary_ids_and_composite_external_keys() -> None:
    expected = expected_rows()
    rows = rows_for_expected()
    # A repeated message external ID under another source/conversation is not a duplicate.
    rows[2]["message_external_id"] = "m-1"
    rows[2]["source_external_id"] = "s-2"
    rows[2]["conversation_external_id"] = "c-2"
    rows[2]["source_id"] = "source-primary-s-2"
    rows[2]["conversation_id"] = "conversation-primary-c-2"
    audit = ImportedEvidenceAudit.from_read_model(
        FakeReadModel(rows), ingestion_batch_id="batch-a", expected_rows=expected
    )
    assert audit.stable_duplicates.message_records == 0

    rows = rows_for_expected()
    rows[1]["source_id"] = "source-primary-s-1-alt"
    rows[1]["conversation_id"] = "conversation-primary-c-1-alt"
    audit = ImportedEvidenceAudit.from_read_model(
        FakeReadModel(rows), ingestion_batch_id="batch-a", expected_rows=expected
    )
    assert audit.stable_duplicates.source_records == 1
    assert audit.stable_duplicates.conversation_records == 1
    assert audit.stable_duplicates.message_records == 0


def test_repeated_messages_in_one_source_and_conversation_are_not_scope_duplicates() -> None:
    rows = rows_for_expected()
    rows[1]["source_id"] = rows[0]["source_id"]
    rows[1]["conversation_id"] = rows[0]["conversation_id"]
    audit = ImportedEvidenceAudit.from_read_model(
        FakeReadModel(rows), ingestion_batch_id="batch-a", expected_rows=expected_rows()
    )
    assert audit.stable_duplicates.source_records == 0
    assert audit.stable_duplicates.conversation_records == 0


def test_equal_content_is_one_deterministic_intentional_group_not_duplicate() -> None:
    rows = rows_for_expected()
    rows.reverse()
    audit = ImportedEvidenceAudit.from_read_model(
        FakeReadModel(rows), ingestion_batch_id="batch-a", expected_rows=expected_rows()
    )
    assert audit.stable_duplicates.total == 0
    assert audit.intentional_content_hash_groups == (
        ContentHashGroup(
            "h-1",
            (
                ExternalMessageKey("s-1", "c-1", "m-1"),
                ExternalMessageKey("s-2", "c-2", "m-3"),
            ),
        ),
    )


def test_empty_audit_is_not_ready() -> None:
    audit = ImportedEvidenceAudit.from_read_model(
        FakeReadModel([]), ingestion_batch_id="batch-a", expected_rows=()
    )
    assert audit.expected_rows == audit.actual_rows == 0
    assert not audit.ready


def test_build_expected_import_rows_flattens_once_with_global_ordinals() -> None:
    batch = ExtractionBatch(
        documents=(),
        structured_sources=(
            StructuredSource(
                "history", "source-A", "A",
                (StructuredConversation(
                    "conversation-A", "A", (
                        StructuredMessage("m-A", "user", "same", 10, occurred_at="t-A"),
                        StructuredMessage("m-B", "assistant", "other", 11, occurred_at="t-B"),
                    ),
                ),),
            ),
            StructuredSource(
                "history", "source-B", "B",
                (StructuredConversation(
                    "conversation-B", "B", (
                        StructuredMessage("m-C", "user", "same", 0, occurred_at="t-C"),
                    ),
                ),),
            ),
        ),
    )
    rows = build_expected_import_rows(batch)
    assert [row.ingestion_ordinal for row in rows] == [0, 1, 2]
    assert rows[0].stable_external_key == ExternalMessageKey("source-A", "conversation-A", "m-A")
    assert rows[0].content_hash == rows[2].content_hash


def test_generic_history_frozen_corpus_has_145_rows_and_five_groups(tmp_path: Path) -> None:
    from src.automatic_memory.quality_gate import _build_pipeline, _history_fixture
    from src.automatic_memory.evaluation import load_corpus
    from src.extraction.adapters.generic_ai_history import GenericAIHistoryAdapter
    from src.extraction.models import ExtractionRequest
    from src.memory.vault_layout import VaultLayout
    from src.retrieval.memory_db import MemoryDatabase
    from src.sources import SourceReadModel
    from src.storage.state_db import StateDatabase

    corpus = load_corpus(Path(__file__).parent / "fixtures" / "automatic_memory_corpus.jsonl")
    fixture = tmp_path / "history.json"
    _history_fixture(corpus, fixture)
    batch = GenericAIHistoryAdapter().extract(ExtractionRequest("task2-expected", "generic_ai_history", input_path=fixture))
    expected = build_expected_import_rows(batch)
    memory_db = MemoryDatabase(tmp_path / "storage" / "index" / "memory.db")
    state_db = StateDatabase(tmp_path / "storage" / "state" / "state.db")
    read_model = SourceReadModel(memory_db)
    VaultLayout(tmp_path / "vault").ensure()
    pipeline = _build_pipeline(tmp_path, memory_db, read_model, state_db)
    pipeline.execute("generic_ai_history", input_path=fixture, adapter_name="generic_ai_history", execution_id="task2-frozen")
    audit = ImportedEvidenceAudit.from_read_model(
        read_model, ingestion_batch_id="task2-frozen", expected_rows=expected
    )
    assert (audit.expected_rows, audit.actual_rows) == (145, 145)
    assert {
        audit.ordered_external_key_matches,
        audit.role_matches,
        audit.sequence_matches,
        audit.timestamp_matches,
        audit.content_hash_matches,
        audit.source_matches,
        audit.conversation_matches,
    } == {145}
    assert audit.stable_duplicates.total == 0
    assert len(audit.intentional_content_hash_groups) == 5
    assert all(len(group.member_external_keys) == 2 for group in audit.intentional_content_hash_groups)
    by_message_id = {record.message_id: record for record in corpus}
    for group in audit.intentional_content_hash_groups:
        message_ids = [key.message_external_id.rsplit(":message:", 1)[-1] for key in group.member_external_keys]
        records = [by_message_id[message_id] for message_id in message_ids]
        assert len(set(group.member_external_keys)) == 2
        assert len({key.conversation_external_id for key in group.member_external_keys}) == 2
        assert len({key.message_external_id for key in group.member_external_keys}) == 2
        assert len({record.fact_id for record in records}) == 2
        assert len({record.citation_id for record in records}) == 2
    assert audit.ready
