from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from src.gateway.owner_memory_cards import OwnerMemoryCardProjector
from src.gateway.profiles import AIProfileRegistry
from src.obsidian.frontmatter import render_frontmatter
from src.memory import MemoryLifecycleService, VaultLayout
from src.obsidian.frontmatter import content_hash, split_frontmatter
from src.project_memory.review_service import MemoryReviewService
from src.retrieval import MemoryDatabase
from src.sources import SourceQueryService, SourceReadModel
from src.storage.state_db import StateDatabase


def _actual_projector(tmp_path: Path, *, canonical_projection: str | None = None, source_cls=SourceQueryService):
    vault = tmp_path / "vault"
    raw = tmp_path / "raw"
    vault.mkdir()
    raw.mkdir()
    database = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(database)
    read_model.upsert_bundle(
        {
            "source": {"source_type": "chatgpt", "external_id": "export", "display_name": "ChatGPT"},
            "conversations": [
                {
                    "external_id": "conversation",
                    "title": "Direct conversation",
                    "messages": [
                        {"external_id": "message-1", "role": "user", "sequence": 1, "occurred_at": "2026-08-01T10:00:00Z", "content": "first source body"},
                        {"external_id": "message-2", "role": "assistant", "sequence": 2, "occurred_at": "2026-08-01T10:01:00Z", "content": "second source body"},
                    ],
                }
            ],
        }
    )
    messages = read_model.list_messages()["items"]
    memory_id = "core-direct"
    memory_path = vault / "03-Knowledge" / "Core-Memory" / "direct.md"
    memory_path.parent.mkdir(parents=True)
    memory_path.write_text("# Direct\n\nCanonical body\n", encoding="utf-8")
    database.upsert_from_entry(
        {
            "id": memory_id,
            "relative_path": "03-Knowledge/Core-Memory/direct.md",
            "title": "Direct memory",
            "memory_type": "knowledge",
            "memory_tier": "core",
            "status": "active",
            "review_status": "approved",
            "privacy": "private",
            "confidence": "0.95",
            "valid_from": "2026-01-01T00:00:00Z",
            "evidence_refs": [
                {"kind": "message", "value": item["message_id"], "content_hash": item["content_hash"]}
                for item in messages
            ],
        },
        memory_path,
    )
    with database._connection() as connection:
        if canonical_projection is not None:
            connection.execute(
                "UPDATE memory_documents SET relationships_json=? WHERE memory_id=?",
                (json.dumps({"canonical_projection": canonical_projection}), memory_id),
            )
    source_service = source_cls(
        read_model,
        workspace="acceptance",
        vault_path=vault,
        raw_path=raw,
        profiles=AIProfileRegistry(),
    )
    return database, read_model, source_service, memory_id, messages


def test_direct_projector_summary_preserves_unknown_vector_and_permanent_as_null(tmp_path):
    database, _read_model, source_service, _memory_id, _messages = _actual_projector(
        tmp_path, canonical_projection="unknown"
    )
    summary = OwnerMemoryCardProjector(database, source_service, statistics=None).summary()

    assert summary["vectorized"] is None
    assert summary["permanent"] is None


def test_direct_projector_get_card_does_not_prefetch_any_message_body(tmp_path):
    class CountingSourceQueryService(SourceQueryService):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.detail_ids: list[str] = []

        def get_message(self, message_id, **kwargs):
            self.detail_ids.append(message_id)
            return super().get_message(message_id, **kwargs)

    database, _read_model, source_service, memory_id, _messages = _actual_projector(
        tmp_path, source_cls=CountingSourceQueryService
    )
    OwnerMemoryCardProjector(database, source_service, statistics=None).get_card(memory_id)

    assert source_service.detail_ids == []


def test_direct_projector_event_only_card_uses_id_free_fallback(tmp_path):
    database, _read_model, source_service, _memory_id, _messages = _actual_projector(tmp_path)
    with database._connection() as connection:
        connection.execute("DELETE FROM memory_documents")

    events = SimpleNamespace(
        recent_events=lambda **_kwargs: [
            {
                "event_type": "memory_promotion_decision",
                "entity_id": "candidate-internal-id",
                "payload": {"status": "pending_owner_review"},
            }
        ]
    )
    card = OwnerMemoryCardProjector(database, source_service, state_db=events).get_card("candidate-internal-id")["item"]

    assert card["topic"] == "一条待核对的记忆"
    assert "candidate-internal-id" not in card["topic"]


def test_direct_correction_keeps_raw_links_and_projects_replacement_card(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    raw = tmp_path / "raw"
    raw.mkdir()
    database = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(database)
    read_model.upsert_bundle(
        {
            "source": {"source_type": "chatgpt", "external_id": "export", "display_name": "ChatGPT"},
            "conversations": [{"external_id": "conversation", "title": "Retention", "messages": [{
                "external_id": "message", "role": "user", "sequence": 1,
                "occurred_at": "2026-08-01T10:00:00Z", "content": "raw retention body",
            }]}],
        }
    )
    old = vault / "03-Knowledge" / "Core-Memory" / "General" / "old.md"
    old.parent.mkdir(parents=True)
    old.write_text(
        render_frontmatter(
            {
                "id": "core-retain", "title": "Retention", "memory_tier": "core",
                "status": "active", "review_status": "approved", "privacy": "private",
                "evidence_refs": [{"message_id": read_model.list_messages()["items"][0]["message_id"], "content_hash": read_model.list_messages()["items"][0]["content_hash"]}],
            },
            "# Retention\n\nCanonical old\n",
        ),
        encoding="utf-8",
    )
    message_id = read_model.list_messages()["items"][0]["message_id"]
    database.upsert_from_entry(
        {"id": "core-retain", "relative_path": "03-Knowledge/Core-Memory/General/old.md", "title": "Retention", "memory_tier": "core", "status": "active", "review_status": "approved", "privacy": "private", "evidence_refs": [{"message_id": message_id}]},
        old,
    )
    read_model.link_message_memory(message_id, "core-retain")
    state_db = StateDatabase(tmp_path / "state.db")
    lifecycle = MemoryLifecycleService(VaultLayout(vault), state_db=state_db)

    def sync(path):
        metadata, _body = split_frontmatter(path.read_text(encoding="utf-8-sig"))
        database.upsert_from_entry(
            {**metadata, "id": metadata["id"], "relative_path": str(path.relative_to(vault).as_posix()), "title": metadata.get("title", path.stem)},
            path,
        )

    service = MemoryReviewService(lifecycle, index_sync=sync, evidence_store=read_model)
    result = service.correct_core_memory(
        "core-retain",
        content="Canonical replacement",
        expected_content_hash=content_hash(old.read_text(encoding="utf-8")),
        owner_confirmed=True,
        reason="主人修正",
    )

    links = read_model.memory_links(result["id"])
    assert old.exists()
    assert any(event["event_type"] == "memory_owner_corrected" for event in state_db.recent_events(limit=20))
    assert links and links[0]["message_id"] == read_model.list_messages()["items"][0]["message_id"]
    source_service = SourceQueryService(read_model, workspace="acceptance", vault_path=vault, raw_path=raw, profiles=AIProfileRegistry())
    assert source_service.memory_evidence(result["id"])["items"][0]["content"] == "raw retention body"
    projector = OwnerMemoryCardProjector(
        database,
        source_service,
        statistics=None,
    )
    replacement = projector.get_card(result["id"])["item"]
    assert replacement["state"] == "active"
    assert replacement["evidence"][0]["preview"] == "raw retention body"
