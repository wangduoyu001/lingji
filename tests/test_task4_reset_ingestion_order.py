from __future__ import annotations

import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from src.extraction.models import (
    ExtractionBatch,
    StructuredConversation,
    StructuredMessage,
    StructuredSource,
)
from src.extraction.structured_sink import StructuredReadModelSink
from src.retrieval import MemoryDatabase
from src.sources import (
    ExternalMessageKey,
    ResolvedMessageRef,
    SourceReadModel,
    SourceReadModelError,
)


def _bundle(source: str, conversation: str, messages: list[tuple[str, int, str]]) -> dict:
    return {
        "source": {
            "source_type": "test",
            "external_id": source,
            "display_name": source,
        },
        "conversations": [
            {
                "external_id": conversation,
                "title": conversation,
                "started_at": "2026-01-01T00:00:00+00:00",
                "messages": [
                    {
                        "external_id": external_id,
                        "role": "user",
                        "sequence": sequence,
                        "occurred_at": occurred_at,
                        "content": f"content-{external_id}",
                        "metadata": {"secret": "must-not-leak"},
                    }
                    for external_id, sequence, occurred_at in messages
                ],
            }
        ],
    }


def _structured_batch() -> ExtractionBatch:
    return ExtractionBatch(
        documents=(),
        structured_sources=(
            StructuredSource(
                source_type="test",
                external_id="source-a",
                display_name="A",
                conversations=(
                    StructuredConversation(
                        external_id="conversation-a",
                        title="A",
                        messages=(
                            StructuredMessage("a-1", "user", "a1", 0, occurred_at="2026-01-02T00:00:00Z"),
                            StructuredMessage("a-2", "assistant", "a2", 1, occurred_at="2026-01-01T00:00:00Z"),
                        ),
                    ),
                ),
            ),
            StructuredSource(
                source_type="test",
                external_id="source-b",
                display_name="B",
                conversations=(
                    StructuredConversation(
                        external_id="conversation-b",
                        title="B",
                        messages=(
                            StructuredMessage("b-1", "user", "b1", 0, occurred_at="2026-01-04T00:00:00Z"),
                            StructuredMessage("b-2", "assistant", "b2", 1, occurred_at="2026-01-03T00:00:00Z"),
                        ),
                    ),
                ),
            ),
        ),
    )


def test_typed_external_identities_are_exact_case_sensitive_and_immutable():
    key = ExternalMessageKey("Source", "Conversation", "Message")
    assert key == ExternalMessageKey("Source", "Conversation", "Message")
    assert key != ExternalMessageKey("source", "Conversation", "Message")
    ref = ResolvedMessageRef("internal", key, "hash")
    assert ref.external_key.source_external_id == "Source"
    with pytest.raises(FrozenInstanceError):
        key.source_external_id = "changed"


def test_fresh_schema_is_v2_and_has_nullable_ingestion_columns_and_index(tmp_path: Path):
    model = SourceReadModel(MemoryDatabase(tmp_path / "memory.db"))
    assert model.schema_version() == "2"
    with model.database._connection() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(message_records)")}
        indexes = {row["name"] for row in connection.execute("PRAGMA index_list(message_records)")}
    assert {"ingestion_batch_id", "ingestion_ordinal"}.issubset(columns)
    assert "idx_message_ingestion_order" in indexes


def test_v1_migrates_additively_without_backfilling_existing_rows(tmp_path: Path):
    path = tmp_path / "v1.db"
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE source_read_model_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO source_read_model_meta VALUES ('schema_version', '1');
        CREATE TABLE source_records (
            source_id TEXT PRIMARY KEY, source_type TEXT NOT NULL, display_name TEXT NOT NULL,
            external_id TEXT, raw_reference TEXT, vault_reference TEXT, privacy TEXT NOT NULL,
            projects_json TEXT NOT NULL, agent_scope_json TEXT NOT NULL, status TEXT NOT NULL,
            content_hash TEXT NOT NULL, created_at TEXT, updated_at TEXT, metadata_json TEXT NOT NULL
        );
        CREATE TABLE conversation_records (
            conversation_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, external_id TEXT,
            title TEXT NOT NULL, participants_json TEXT NOT NULL, started_at TEXT, ended_at TEXT,
            message_count INTEGER NOT NULL, privacy TEXT NOT NULL, projects_json TEXT NOT NULL,
            agent_scope_json TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT,
            updated_at TEXT, metadata_json TEXT NOT NULL
        );
        CREATE TABLE message_records (
            message_id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, source_id TEXT NOT NULL,
            external_id TEXT, role TEXT NOT NULL, author TEXT, occurred_at TEXT,
            sequence INTEGER NOT NULL, content TEXT NOT NULL, content_hash TEXT NOT NULL,
            raw_reference TEXT, privacy TEXT NOT NULL, projects_json TEXT NOT NULL,
            agent_scope_json TEXT NOT NULL, created_at TEXT, updated_at TEXT,
            metadata_json TEXT NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT INTO source_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("source-id", "test", "source", "source", None, None, "private", "[]", "[]", "active", "hash", "now", "now", "{}"),
    )
    connection.execute(
        "INSERT INTO conversation_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("conversation-id", "source-id", "conversation", "conversation", "[]", None, None, 1, "private", "[]", "[]", "hash", "now", "now", "{}"),
    )
    connection.execute(
        "INSERT INTO message_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("message-id", "conversation-id", "source-id", "message", "user", None, "2026-01-01T00:00:00Z", 0, "content", "hash", None, "private", "[]", "[]", "now", "now", "{}"),
    )
    connection.commit()
    connection.close()
    database = MemoryDatabase(path)
    migrated = SourceReadModel(database)
    assert migrated.schema_version() == "2"
    rows = migrated.list_messages()["items"]
    assert len(rows) == 1
    with database._connection() as connection:
        row = connection.execute(
            "SELECT ingestion_batch_id, ingestion_ordinal FROM message_records"
        ).fetchone()
    assert row["ingestion_batch_id"] is None
    assert row["ingestion_ordinal"] is None


@pytest.mark.parametrize("version", ["0", "3", "future"])
def test_unknown_schema_versions_fail_closed(tmp_path: Path, version: str):
    path = tmp_path / f"schema-{version}.db"
    database = MemoryDatabase(path)
    SourceReadModel(database)
    with database._connection() as connection:
        connection.execute("UPDATE source_read_model_meta SET value = ? WHERE key = 'schema_version'", (version,))
    with pytest.raises(SourceReadModelError):
        SourceReadModel(database)


def test_sink_assigns_one_global_adapter_order_and_replay_is_idempotent(tmp_path: Path):
    database = MemoryDatabase(tmp_path / "memory.db")
    model = SourceReadModel(database)
    sink = StructuredReadModelSink(model, storage_path=tmp_path / "storage", memory_database=database)
    batch = _structured_batch()
    first = sink.write_batch(
        batch,
        raw_snapshot=None,
        vault_results={},
        execution_id="exec-1",
        adapter_name="test",
        adapter_version="1",
        indexing_succeeded=False,
    )
    ids_before = [item["message_id"] for item in model.list_ingestion_messages("exec-1")["items"]]
    second = sink.write_batch(
        batch,
        raw_snapshot=None,
        vault_results={},
        execution_id="exec-1",
        adapter_name="test",
        adapter_version="1",
        indexing_succeeded=False,
    )
    items = model.list_ingestion_messages("exec-1")["items"]
    assert first["state"] == second["state"] == "written"
    assert [item["ingestion_ordinal"] for item in items] == [0, 1, 2, 3]
    assert [item["message_id"] for item in items] == ids_before
    assert model.stats()["messages"] == 4
    assert model.list_messages()["items"][0]["occurred_at"] == "2026-01-04T00:00:00Z"


def test_legacy_no_batch_upsert_preserves_ingestion_owner(tmp_path: Path):
    model = SourceReadModel(MemoryDatabase(tmp_path / "memory.db"))
    bundle = _bundle("source", "conversation", [("message", 0, "2026-01-01T00:00:00Z")])
    model.upsert_bundle(bundle, ingestion_batch_id="exec", ingestion_ordinal_start=7)
    model.upsert_bundle(bundle)
    assert model.list_ingestion_messages("exec")["items"][0]["ingestion_ordinal"] == 7


def test_later_execution_becomes_current_owner_without_duplicate_rows(tmp_path: Path):
    model = SourceReadModel(MemoryDatabase(tmp_path / "memory.db"))
    bundle = _bundle("source", "conversation", [("message", 0, "2026-01-01T00:00:00Z")])
    first = model.upsert_bundle(bundle, ingestion_batch_id="exec-1")
    second = model.upsert_bundle(bundle, ingestion_batch_id="exec-2")
    assert first["next_ingestion_ordinal"] == second["next_ingestion_ordinal"] == 1
    assert model.stats()["messages"] == 1
    assert model.list_ingestion_messages("exec-1")["items"] == []
    assert model.list_ingestion_messages("exec-2")["items"][0]["ingestion_ordinal"] == 0


def test_ingestion_items_have_exact_safe_shape_and_unknown_batch_paginates(tmp_path: Path):
    model = SourceReadModel(MemoryDatabase(tmp_path / "memory.db"))
    model.upsert_bundle(_bundle("source", "conversation", [("message", 0, "2026-01-01T00:00:00Z")]), ingestion_batch_id="exec")
    item = model.list_ingestion_messages("exec")["items"][0]
    assert set(item) == {
        "source_id", "source_external_id", "conversation_id", "conversation_external_id",
        "message_id", "message_external_id", "ingestion_batch_id", "ingestion_ordinal",
        "sequence", "role", "occurred_at", "content_hash",
    }
    assert "content" not in item
    assert "metadata" not in item
    assert "privacy" not in item
    empty = model.list_ingestion_messages("missing", limit=1, offset=2)
    assert empty == {"items": [], "pagination": {"limit": 1, "offset": 2, "total": 0, "has_more": False}}


@pytest.mark.parametrize(
    "mutator",
    [
        lambda connection, ids: connection.execute("UPDATE message_records SET ingestion_ordinal = NULL WHERE message_id = ?", (ids[0],)),
        lambda connection, ids: connection.execute("UPDATE message_records SET ingestion_ordinal = 0 WHERE ingestion_ordinal = 1"),
        lambda connection, ids: connection.execute("UPDATE message_records SET ingestion_ordinal = 3 WHERE ingestion_ordinal = 1"),
    ],
)
def test_ingestion_batch_is_fully_validated_before_pagination(tmp_path: Path, mutator):
    database = MemoryDatabase(tmp_path / "memory.db")
    model = SourceReadModel(database)
    model.upsert_bundle(
        _bundle("source", "conversation", [("first", 0, "2026-01-01T00:00:00Z"), ("second", 1, "2026-01-01T00:01:00Z")]),
        ingestion_batch_id="exec",
    )
    with database._connection() as connection:
        ids = [row["message_id"] for row in connection.execute("SELECT message_id FROM message_records ORDER BY message_id")]
        mutator(connection, ids)
    with pytest.raises(SourceReadModelError):
        model.list_ingestion_messages("exec", limit=1, offset=1)
