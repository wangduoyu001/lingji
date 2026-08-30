from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.control.project_memory_api import register_project_memory_routes
from src.gateway.memory_inspector import MemoryInspectorFacade
from src.gateway.profiles import AIProfileRegistry
from src.memory import MemoryLifecycleService, VaultLayout
from src.obsidian.frontmatter import content_hash, render_frontmatter, split_frontmatter
from src.project_memory.review_service import MemoryReviewService
from src.retrieval import MemoryDatabase
from src.sources import SourceQueryService, SourceReadModel
from src.storage.state_db import StateDatabase


class _Context:
    def build(self, *args, **kwargs):
        return {"project_id": args[1]}


class _Stats:
    def vector_status(self):
        return {"state": "unavailable", "ready": False, "vectors": None}

    def vector_coverage(self):
        return {"state": "unavailable", "expected": None, "indexed": None, "missing": None}


def _stack(tmp_path: Path):
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
                    "title": "Round3 integration",
                    "messages": [
                        {
                            "external_id": "message-1",
                            "role": "user",
                            "sequence": 1,
                            "occurred_at": "2026-08-01T10:00:00Z",
                            "content": "retained raw evidence",
                        }
                    ],
                }
            ],
        }
    )
    source_service = SourceQueryService(
        read_model,
        workspace="acceptance",
        vault_path=vault,
        raw_path=raw,
        profiles=AIProfileRegistry(),
    )
    state_db = StateDatabase(tmp_path / "state.db")
    lifecycle = MemoryLifecycleService(VaultLayout(vault), state_db=state_db)

    def sync(path: Path):
        metadata, _body = split_frontmatter(path.read_text(encoding="utf-8-sig"))
        database.upsert_from_entry(
            {
                **metadata,
                "id": metadata["id"],
                "relative_path": path.relative_to(vault).as_posix(),
                "title": metadata.get("title", path.stem),
            },
            path,
        )

    review = MemoryReviewService(
        lifecycle,
        database=database,
        index_sync=sync,
        state_db=state_db,
        evidence_store=source_service.read_model,
    )
    app = FastAPI()
    register_project_memory_routes(
        app,
        _Context(),
        review,
        token_validator=lambda token: token == "secret",
    )
    return vault, database, read_model, source_service, state_db, lifecycle, review, TestClient(app)


def _candidate(lifecycle: MemoryLifecycleService, title: str, content: str):
    result = lifecycle.propose_memory("integration", title, content)
    path = Path(result["path"])
    return result, path, content_hash(path.read_text(encoding="utf-8-sig"))


def _core(vault: Path, database: MemoryDatabase, read_model: SourceReadModel, memory_id: str, body: str):
    message_id = read_model.list_messages()["items"][0]["message_id"]
    path = vault / "03-Knowledge" / "Core-Memory" / "General" / f"{memory_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_frontmatter(
            {
                "id": memory_id,
                "title": "Integration core",
                "memory_tier": "core",
                "status": "active",
                "review_status": "approved",
                "privacy": "private",
                "evidence_refs": [{"kind": "message", "value": message_id}],
            },
            body,
        ),
        encoding="utf-8",
    )
    database.upsert_from_entry(
        {
            "id": memory_id,
            "relative_path": path.relative_to(vault).as_posix(),
            "title": "Integration core",
            "memory_tier": "core",
            "status": "active",
            "review_status": "approved",
            "privacy": "private",
            "evidence_refs": [{"kind": "message", "value": message_id}],
        },
        path,
    )
    read_model.link_message_memory(message_id, memory_id)
    return path, message_id


def test_production_projector_facade_returns_owner_card_dto_from_real_read_models(tmp_path):
    vault, database, read_model, source_service, _state_db, _lifecycle, _review, _client = _stack(tmp_path)
    path, _message_id = _core(vault, database, read_model, "core-dto", "# DTO\n\ncanonical body")
    facade = MemoryInspectorFacade(database, source_service, _Stats(), workspace="acceptance")

    dto = facade.get_card("core-dto", include_evidence=True)["item"]

    assert dto["memory_id"] == "core-dto"
    assert dto["kind"] == "memory"
    assert dto["action"]["type"] == "correct"
    assert dto["evidence"][0]["preview"] == "retained raw evidence"
    assert path.exists()


def test_production_routes_execute_candidate_actions_and_owner_gate(tmp_path):
    vault, _database, _read_model, _source_service, _state_db, lifecycle, _review, client = _stack(tmp_path)
    headers = {"X-LingJi-Token": "secret"}

    approved, approved_path, approved_hash = _candidate(lifecycle, "Approve", "approve body")
    response = client.post(
        f"/api/memory/review/candidates/{approved['id']}/approve",
        headers=headers,
        json={"owner_confirmed": True, "expected_content_hash": approved_hash},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert not approved_path.exists()

    edited, edited_path, edited_hash = _candidate(lifecycle, "Edit", "edit body")
    response = client.post(
        f"/api/memory/review/candidates/{edited['id']}/edit-approve",
        headers=headers,
        json={"owner_confirmed": True, "expected_content_hash": edited_hash, "content": "edited canonical body"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    edited_target = vault / response.json()["relative_path"]
    assert "edited canonical body" in edited_target.read_text(encoding="utf-8")
    assert not edited_path.exists()

    rejected, rejected_path, rejected_hash = _candidate(lifecycle, "Reject", "reject body")
    response = client.post(
        f"/api/memory/review/candidates/{rejected['id']}/reject",
        headers=headers,
        json={"owner_confirmed": True, "expected_content_hash": rejected_hash, "reason": "证据不足"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert not rejected_path.exists()

    gated, gated_path, gated_hash = _candidate(lifecycle, "Gate", "must remain")
    response = client.post(
        f"/api/memory/review/candidates/{gated['id']}/edit-approve",
        headers=headers,
        json={"owner_confirmed": False, "expected_content_hash": gated_hash, "content": "must not write"},
    )
    assert response.status_code == 422
    assert "must remain" in gated_path.read_text(encoding="utf-8")


def test_production_routes_close_correct_invalidate_archive_and_conflict_retention(tmp_path):
    vault, database, read_model, source_service, state_db, lifecycle, _review, client = _stack(tmp_path)
    headers = {"X-LingJi-Token": "secret"}
    old, _message_id = _core(vault, database, read_model, "core-correct", "# Old\n\nold canonical")
    old_hash = content_hash(old.read_text(encoding="utf-8"))

    assert client.post("/api/memory/core/core-correct/correct", json={"owner_confirmed": True, "expected_content_hash": old_hash, "content": "new canonical", "reason": "主人修正"}).status_code == 401
    conflict = client.post(
        "/api/memory/core/core-correct/correct",
        headers=headers,
        json={"owner_confirmed": True, "expected_content_hash": "stale", "content": "must not overwrite", "reason": "冲突"},
    )
    assert conflict.status_code == 409
    assert "old canonical" in old.read_text(encoding="utf-8")

    response = client.post(
        "/api/memory/core/core-correct/correct",
        headers=headers,
        json={"owner_confirmed": True, "expected_content_hash": old_hash, "content": "new canonical", "reason": "主人修正"},
    )
    assert response.status_code == 200
    replacement_id = response.json()["id"]
    replacement = database.fetch_memory(replacement_id, include_chunks=True)
    assert any("new canonical" in str(chunk.get("text")) for chunk in replacement["chunks"])
    assert read_model.memory_links(replacement_id)
    assert source_service.memory_evidence(replacement_id)["items"][0]["content"] == "retained raw evidence"
    old_metadata, _ = split_frontmatter(old.read_text(encoding="utf-8"))
    assert old_metadata["status"] == "superseded"
    assert old_metadata["superseded_by"] == replacement_id
    assert any(event["event_type"] == "memory_owner_corrected" for event in state_db.recent_events(limit=50))
    facade = MemoryInspectorFacade(database, source_service, _Stats(), workspace="acceptance")
    assert facade.get_card(replacement_id, include_evidence=True)["item"]["state"] == "active"
    superseded_card = facade.get_card("core-correct", include_evidence=True)["item"]
    assert superseded_card["state"] == "superseded"
    assert superseded_card["action"]["type"] == "review"

    invalidated, _ = _core(vault, database, read_model, "core-invalidated", "# Invalidate\n\nbody")
    invalidated_hash = content_hash(invalidated.read_text(encoding="utf-8"))
    response = client.post(
        "/api/memory/core/core-invalidated/invalidate",
        headers=headers,
        json={"owner_confirmed": True, "expected_content_hash": invalidated_hash, "reason": "已过时", "valid_to": "2026-08-30T00:00:00Z"},
    )
    assert response.status_code == 200
    assert response.json()["valid_to"] == "2026-08-30T00:00:00Z"
    invalidated_metadata, _ = split_frontmatter(invalidated.read_text(encoding="utf-8"))
    assert invalidated_metadata["valid_to"] == "2026-08-30T00:00:00Z"
    assert invalidated_metadata["invalidating_reason"] == "已过时"

    archived, _ = _core(vault, database, read_model, "core-archived", "# Archive\n\nbody")
    archived_hash = content_hash(archived.read_text(encoding="utf-8"))
    response = client.post(
        "/api/memory/core/core-archived/archive",
        headers=headers,
        json={"owner_confirmed": True, "expected_content_hash": archived_hash, "reason": "不再属于当前记忆"},
    )
    assert response.status_code == 200
    archived_metadata, _ = split_frontmatter(archived.read_text(encoding="utf-8"))
    assert archived_metadata["status"] == "archived"
    assert archived_metadata["archive_reason"] == "不再属于当前记忆"
