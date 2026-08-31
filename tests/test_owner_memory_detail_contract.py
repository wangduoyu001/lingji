from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from src.control.api import create_control_app
from src.gateway.memory_inspector import MemoryInspectorFacade
from src.gateway.profiles import AIProfileRegistry
from src.retrieval import MemoryDatabase
from src.sources import SourceQueryService, SourceReadModel


class _Control:
    def __init__(self, inspector):
        self.memory_inspector = inspector


class _TracingReadModel(SourceReadModel):
    def __init__(self, database):
        self.message_reads: list[tuple[str, bool]] = []
        self.sql: list[str] = []
        super().__init__(database)

    @contextmanager
    def _connection(self):
        with super()._connection() as connection:
            connection.set_trace_callback(self.sql.append)
            yield connection

    def get_message(self, message_id: str, *, include_content: bool):
        self.message_reads.append((str(message_id), include_content))
        return super().get_message(message_id, include_content=include_content)


def _seeded_facade() -> tuple[
    MemoryInspectorFacade, tempfile.TemporaryDirectory[str], _TracingReadModel
]:
    temp_dir = tempfile.TemporaryDirectory()
    root = Path(temp_dir.name)
    database = MemoryDatabase(root / "lingji_memory.db")
    with database._connection() as connection:
        connection.execute(
            """
            INSERT INTO memory_documents(
                memory_id, relative_path, title, memory_type, privacy,
                project_json, agent_scope_json, content_hash, modified_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "memory-1",
                "03-Knowledge/memory-1.md",
                "Bounded memory",
                "knowledge",
                "private",
                "[]",
                "[]",
                "memory-hash",
                "2026-08-31T00:00:00Z",
                "2026-08-31T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO memory_chunks(
                chunk_id, memory_id, ordinal, heading, text, start_line,
                end_line, char_count, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "chunk-1",
                "memory-1",
                0,
                "Heading",
                "x" * 200,
                1,
                4,
                200,
                "chunk-hash",
            ),
        )

    read_model = _TracingReadModel(database)
    messages = [
        {
            "message_id": f"m-{index:02d}",
            "external_id": f"m-{index:02d}",
            "role": "user",
            "sequence": index,
            "occurred_at": timestamp,
            "content": (f"message {index} " + "body ") * 500,
            "raw_reference": str(root / "raw" / "export.json"),
            "memory_links": [{"memory_id": "memory-1"}],
        }
        for index, timestamp in enumerate(
            (
                "2026-08-30T12:00:00Z",
                "2026-08-30T08:00:00-04:00",
                "2026-08-30T14:00:00+02:00",
                "2026-08-30T12:00:00Z",
                "2026-08-30T12:00:00Z",
                "2026-08-30T12:00:00Z",
                "2026-08-30T12:00:00Z",
            ),
            start=1,
        )
    ]
    read_model.upsert_bundle(
        {
            "source": {
                "source_id": "source-visible",
                "source_type": "chatgpt",
                "external_id": "visible-export",
                "display_name": "Visible source",
                "privacy": "private",
            },
            "conversations": [
                {
                    "conversation_id": "conversation-visible",
                    "external_id": "visible-conversation",
                    "title": "Visible conversation",
                    "messages": messages,
                }
            ],
        }
    )
    for source_id, status, privacy, external_id in (
        ("source-restricted", "restricted", "private", "restricted-export"),
        ("source-revoked", "revoked", "private", "revoked-export"),
        ("source-expired", "expired", "private", "expired-export"),
    ):
        read_model.upsert_bundle(
            {
                "source": {
                    "source_id": source_id,
                    "source_type": "chatgpt",
                    "external_id": external_id,
                    "display_name": source_id,
                    "privacy": privacy,
                    "status": status,
                    "raw_reference": str(root / "raw" / f"{source_id}.json"),
                },
                "conversations": [
                    {
                        "conversation_id": f"conversation-{source_id}",
                        "external_id": f"conversation-{source_id}",
                        "title": source_id,
                        "messages": [
                            {
                                "message_id": source_id,
                                "external_id": source_id,
                                "role": "assistant",
                                "sequence": 1,
                                "content": f"{source_id} body",
                                "memory_links": [{"memory_id": "memory-1"}],
                            }
                        ],
                    }
                ],
            }
        )

    service = SourceQueryService(
        read_model,
        workspace="acceptance",
        vault_path=root / "vault",
        raw_path=root / "raw",
        profiles=AIProfileRegistry(),
    )
    read_model.message_reads.clear()
    read_model.sql.clear()
    return (
        MemoryInspectorFacade(database, service, _Statistics(), workspace="acceptance"),
        temp_dir,
        read_model,
    )


class _Statistics:
    def memory_status(self):
        return {"state": "healthy", "documents": 1, "chunks": 1}

    def vector_status(self):
        return {"state": "unavailable", "source": "unavailable"}


def test_evidence_page_has_bounded_stable_order_and_pagination():
    facade, temp_dir, _read_model = _seeded_facade()
    try:
        page = facade.list_memory_evidence("memory-1", limit=3, offset=0)
        assert [item["message_id"] for item in page["items"]] == [
            "m-01",
            "m-02",
            "m-03",
        ]
        assert page["pagination"] == {
            "limit": 3,
            "offset": 0,
            "total": 7,
            "has_more": True,
        }
        assert all(len(item["excerpt"]) <= 240 for item in page["items"])
        assert all(len(item["content"]) <= 4000 for item in page["items"])
        assert sum(len(item["content"]) for item in page["items"]) <= 24000
    finally:
        temp_dir.cleanup()


def test_evidence_page_includes_safe_per_row_source_and_conversation_labels():
    facade, temp_dir, read_model = _seeded_facade()
    try:
        with read_model._connection() as connection:
            connection.execute(
                "UPDATE conversation_records SET title = ? WHERE conversation_id = ?",
                ("Visible conversation", "conversation-visible"),
            )
        page = facade.list_memory_evidence("memory-1", limit=2, offset=0)
        assert page["items"][0]["source_label"] == "Visible source"
        assert page["items"][0]["source_type"] == "chatgpt"
        assert page["items"][0]["conversation_title"] == "Visible conversation"
        assert all("raw_reference" in item for item in page["items"])
        assert all("metadata" not in item and "path" not in item for item in page["items"])
    finally:
        temp_dir.cleanup()


def test_evidence_page_rechecks_authority_and_safe_references():
    facade, temp_dir, _read_model = _seeded_facade()
    try:
        page = facade.list_memory_evidence("memory-1", limit=50, offset=0)
        message_ids = {item["message_id"] for item in page["items"]}
        assert {"source-restricted", "source-revoked", "source-expired"}.isdisjoint(
            message_ids
        )
        assert all("/Users/" not in (item["raw_reference"] or "") for item in page["items"])
        assert all("cookie" not in item for item in page["items"])
        assert all("auth_metadata" not in item for item in page["items"])
    finally:
        temp_dir.cleanup()


def test_canonical_cursor_pages_split_long_chunks_without_loss_or_duplicates():
    facade, temp_dir, _read_model = _seeded_facade()
    expected = "A" * 250 + "B" * 30
    try:
        with facade.database._connection() as connection:
            connection.execute("DELETE FROM memory_chunks WHERE memory_id = ?", ("memory-1",))
            connection.executemany(
                """
                INSERT INTO memory_chunks(
                    chunk_id, memory_id, ordinal, heading, text, start_line,
                    end_line, char_count, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("long-1", "memory-1", 0, "Long", "A" * 250, 1, 20, 250, "hash-a"),
                    ("long-2", "memory-1", 1, "Next", "B" * 30, 21, 24, 30, "hash-b"),
                ],
            )
        cursor = None
        pages: list[dict] = []
        for _ in range(10):
            item = facade.get_memory(
                "memory-1", chunk_limit=2, max_chars=100, cursor=cursor
            )["item"]
            pages.append(item)
            assert sum(len(str(chunk.get("text") or "")) for chunk in item["chunks"]) <= 100
            next_cursor = item.get("next_cursor")
            if next_cursor is None:
                break
            assert next_cursor != cursor
            assert len(next_cursor) <= 200
            assert "/" not in next_cursor and "A" not in next_cursor and "B" not in next_cursor
            cursor = next_cursor
        assert pages[-1].get("next_cursor") is None
        assert "".join(
            str(chunk.get("text") or "") for page in pages for chunk in page["chunks"]
        ) == expected
    finally:
        temp_dir.cleanup()


def test_canonical_cursor_rejects_unknown_values():
    facade, temp_dir, _read_model = _seeded_facade()
    try:
        with pytest.raises(ValueError, match="cursor"):
            facade.get_memory("memory-1", chunk_limit=2, max_chars=100, cursor="not-a-cursor")
    finally:
        temp_dir.cleanup()


class _Inspector:
    def __init__(self, facade):
        self.facade = facade

    def list_memory_evidence(self, memory_id, **kwargs):
        return self.facade.list_memory_evidence(memory_id, **kwargs)

    def get_memory(self, memory_id, **kwargs):
        return self.facade.get_memory(memory_id, **kwargs)


def test_evidence_route_is_authenticated_and_canonical_route_accepts_bounds():
    facade, temp_dir, _read_model = _seeded_facade()
    try:
        client_context = TestClient(
            create_control_app(
                object(), service=_Control(_Inspector(facade)), token="secret"
            )
        )
        with client_context as client:
            assert client.get("/api/memory/inspector/memories/memory-1/evidence").status_code == 401
            response = client.get(
                "/api/memory/inspector/memories/memory-1/evidence?limit=3&offset=0",
                headers={"X-LingJi-Token": "secret"},
            )
            assert response.status_code == 200
            missing = client.get(
                "/api/memory/inspector/memories/missing/evidence",
                headers={"X-LingJi-Token": "secret"},
            )
            assert missing.status_code == 404
            bounded = client.get(
                "/api/memory/inspector/memories/memory-1?chunk_limit=1&max_chars=80",
                headers={"X-LingJi-Token": "secret"},
            )
            assert bounded.status_code == 200
            item = bounded.json()["item"]
            assert {"memory_id", "chunks"}.issubset(item)
            assert "layers" not in item and "action" not in item
            assert item["chunks"][0]["truncated"] is True
            assert item["next_cursor"]
            bad_cursor = client.get(
                "/api/memory/inspector/memories/memory-1?chunk_limit=1&max_chars=80&cursor=bad",
                headers={"X-LingJi-Token": "secret"},
            )
            assert bad_cursor.status_code == 422
    finally:
        temp_dir.cleanup()


def test_evidence_metadata_read_is_body_free_and_full_reads_are_page_bounded():
    facade, temp_dir, read_model = _seeded_facade()
    try:
        facade.list_memory_evidence("memory-1", limit=3, offset=0)
        assert sum(include_content for _message_id, include_content in read_model.message_reads) == 3
        assert sum(not include_content for _message_id, include_content in read_model.message_reads) == 10
        metadata_queries = [
            " ".join(query.lower().split())
            for query in read_model.sql
            if "from message_records where message_id" in " ".join(query.lower().split())
        ]
        assert metadata_queries
        assert any(
            "select *" not in query
            and "select content" not in query
            for query in metadata_queries
        )
    finally:
        temp_dir.cleanup()


def test_evidence_raw_reference_rejects_sensitive_json_and_absolute_values():
    facade, temp_dir, read_model = _seeded_facade()
    try:
        adversarial = {
            "m-01": '{"cookie":"SECRET"}',
            "m-02": "credential=SECRET",
            "m-03": "/Users/owner/private.json",
        }
        with read_model._connection() as connection:
            for message_id, raw_reference in adversarial.items():
                connection.execute(
                    "UPDATE message_records SET raw_reference = ? WHERE message_id = ?",
                    (raw_reference, message_id),
                )
        items = {
            item["message_id"]: item
            for item in facade.list_memory_evidence("memory-1", limit=50)["items"]
        }
        assert items["m-01"]["raw_reference"] == ""
        assert items["m-02"]["raw_reference"] == ""
        assert items["m-03"]["raw_reference"] == ""
        for message_id, raw_reference in {
            "m-04": "raw:C:/Users/owner/private.json",
            "m-05": r"vault:c:\Users\owner\private.json",
            "m-06": "raw://server/share/private.json",
            "m-07": r"vault:\\server\share\private.json",
            "m-01": "file:///C:/Users/owner/private.json",
            "m-02": "vault:file%3A%2F%2FC%3A%2FUsers%2Fowner%2Fprivate.json",
        }.items():
            with read_model._connection() as connection:
                connection.execute(
                    "UPDATE message_records SET raw_reference = ? WHERE message_id = ?",
                    (raw_reference, message_id),
                )
            path_items = {
                item["message_id"]: item
                for item in facade.list_memory_evidence("memory-1", limit=50)["items"]
            }
            assert path_items[message_id]["raw_reference"] == ""
        with read_model._connection() as connection:
            connection.execute(
                "UPDATE message_records SET raw_reference = ? WHERE message_id = ?",
                ("raw:relative/path.json", "m-01"),
            )
            connection.execute(
                "UPDATE message_records SET raw_reference = ? WHERE message_id = ?",
                ("vault:folder/note.md", "m-02"),
            )
        legal_items = {
            item["message_id"]: item
            for item in facade.list_memory_evidence("memory-1", limit=50)["items"]
        }
        assert legal_items["m-01"]["raw_reference"] == "raw:relative/path.json"
        assert legal_items["m-02"]["raw_reference"] == "vault:folder/note.md"
        serialized = str(items)
        assert "SECRET" not in serialized
        assert "/Users/owner" not in serialized
    finally:
        temp_dir.cleanup()


def test_unknown_memory_returns_not_found_but_existing_empty_evidence_is_valid():
    facade, temp_dir, read_model = _seeded_facade()
    try:
        with facade.database._connection() as connection:
            connection.execute(
                "INSERT INTO memory_documents(memory_id, relative_path, title, memory_type, privacy, project_json, agent_scope_json, content_hash, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("memory-empty", "03-Knowledge/empty.md", "Empty", "knowledge", "private", "[]", "[]", "empty-hash", "2026-08-31T00:00:00Z"),
            )
        empty = facade.list_memory_evidence("memory-empty")
        assert empty["items"] == []
        assert empty["pagination"]["total"] == 0
        try:
            facade.list_memory_evidence("missing")
        except LookupError:
            pass
        else:
            raise AssertionError("unknown memory must raise LookupError")
    finally:
        temp_dir.cleanup()


def test_evidence_without_content_keeps_metadata_and_does_not_read_page_bodies():
    facade, temp_dir, read_model = _seeded_facade()
    try:
        page = facade.list_memory_evidence("memory-1", limit=2, include_content=False)
        assert page["items"]
        assert all("content" not in item for item in page["items"])
        assert not any(include_content for _message_id, include_content in read_model.message_reads)
    finally:
        temp_dir.cleanup()


def test_evidence_invalid_timestamp_and_sequence_are_deterministic_and_last():
    facade, temp_dir, read_model = _seeded_facade()
    try:
        with read_model._connection() as connection:
            connection.execute(
                "UPDATE message_records SET occurred_at = ?, sequence = ? WHERE message_id = ?",
                ("not-a-time", 999, "m-01"),
            )
            connection.execute(
                "UPDATE message_records SET occurred_at = ?, sequence = ? WHERE message_id = ?",
                (None, 998, "m-02"),
            )
        ids = [item["message_id"] for item in facade.list_memory_evidence("memory-1", limit=50)["items"]]
        assert ids[-2:] == ["m-02", "m-01"]
    finally:
        temp_dir.cleanup()
