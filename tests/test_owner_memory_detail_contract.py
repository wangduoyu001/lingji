from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from src.control.api import create_control_app
from src.gateway.memory_inspector import MemoryInspectorFacade
from src.gateway.profiles import AIProfileRegistry
from src.retrieval import MemoryDatabase
from src.sources import SourceQueryService, SourceReadModel


class _Control:
    def __init__(self, inspector):
        self.memory_inspector = inspector


def _seeded_facade() -> tuple[MemoryInspectorFacade, tempfile.TemporaryDirectory[str]]:
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

    read_model = SourceReadModel(database)
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
    return (
        MemoryInspectorFacade(database, service, _Statistics(), workspace="acceptance"),
        temp_dir,
    )


class _Statistics:
    def memory_status(self):
        return {"state": "healthy", "documents": 1, "chunks": 1}

    def vector_status(self):
        return {"state": "unavailable", "source": "unavailable"}


def test_evidence_page_has_bounded_stable_order_and_pagination():
    facade, temp_dir = _seeded_facade()
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


def test_evidence_page_rechecks_authority_and_safe_references():
    facade, temp_dir = _seeded_facade()
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


class _Inspector:
    def __init__(self, facade):
        self.facade = facade

    def list_memory_evidence(self, memory_id, **kwargs):
        return self.facade.list_memory_evidence(memory_id, **kwargs)

    def get_memory(self, memory_id, **kwargs):
        return self.facade.get_memory(memory_id, **kwargs)


def test_evidence_route_is_authenticated_and_canonical_route_accepts_bounds():
    facade, temp_dir = _seeded_facade()
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
            bounded = client.get(
                "/api/memory/inspector/memories/memory-1?chunk_limit=1&max_chars=80",
                headers={"X-LingJi-Token": "secret"},
            )
            assert bounded.status_code == 200
            item = bounded.json()["item"]
            assert {"memory_id", "chunks"}.issubset(item)
            assert "layers" not in item and "action" not in item
            assert item["chunks"][0]["truncated"] is True
    finally:
        temp_dir.cleanup()
