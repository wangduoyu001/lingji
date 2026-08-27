from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path

import pytest

from src.auto_review import AutoMemoryPromotionService
from src.auto_review.models import PromotionEvidence, PromotionProjectionState, ReviewCandidate
from src.automatic_memory.quality_evidence import audit_promotion_persistence
from src.gateway import AIProfileRegistry, MemoryGateway
from src.indexer.index import PEMISIndex
from src.memory import VaultLayout
from src.obsidian.frontmatter import render_frontmatter
from src.retrieval.context_pack import ContextPackBuilder
from src.retrieval.hybrid import HybridRetriever, SearchFilters
from src.retrieval.memory_db import MemoryDatabase
from src.sources import SourceReadModel
from src.storage.state_db import StateDatabase


def _stores(tmp_path: Path) -> tuple[Path, StateDatabase, MemoryDatabase, SourceReadModel]:
    memory_path = tmp_path / "lingji_memory.db"
    state_path = tmp_path / "lingji_state.db"
    memory = MemoryDatabase(memory_path)
    return memory_path, StateDatabase(state_path), memory, SourceReadModel(memory)


def _messages(source: SourceReadModel, count: int = 2) -> list[dict[str, str]]:
    source_row = source.upsert_source({"source_type": "chat", "external_id": "chat-1"})
    conversation = source.upsert_conversation(
        {"source_id": source_row["source_id"], "external_id": "conv-1"}
    )
    return [
        source.upsert_message(
            {
                "source_id": source_row["source_id"],
                "conversation_id": conversation["conversation_id"],
                "external_id": f"msg-{index}",
                "role": "user",
                "sequence": index,
                "content": f"fact {index}",
            }
        )
        for index in range(1, count + 1)
    ]


def _candidate(memory_id: str = "memory-1") -> ReviewCandidate:
    content = "durable fact"
    content_hash = hashlib.sha256(
        json.dumps(
            {"title": content, "content": content, "structured": {}},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return ReviewCandidate(
        memory_id=memory_id,
        title=content,
        content=content,
        content_hash=content_hash,
        source_refs=("LJ-MSG-00000000000000000000000000000001",),
        confidence=0.99,
        authority="direct_user",
        source_kind="chat",
    )


def _saga(
    state: StateDatabase,
    memory: MemoryDatabase,
    source: SourceReadModel,
    messages: list[dict[str, str]],
    *,
    memory_id: str = "memory-1",
) -> tuple[AutoMemoryPromotionService, ReviewCandidate, str, tuple[object, ...]]:
    candidate = _candidate(memory_id)
    candidate = ReviewCandidate(
        **{
            **candidate.__dict__,
            "source_refs": tuple(item["message_id"] for item in messages),
        }
    )
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    selected = service._normalize(candidate)
    provenance = service._normalize_provenance(selected)
    decision_id = service._decision_id(selected, "active", service.policy_version)
    service._record_promotion_event("memory_promotion_preparing", selected, decision_id, provenance)
    memory.prepare_derived_projection(
        memory_id=memory_id,
        title=selected.title,
        content=selected.content,
        content_hash=selected.content_hash,
        evidence_refs=tuple(provenance.linkable_messages),
        confidence=selected.confidence,
        authority=selected.authority,
        source_kind=selected.source_kind,
        policy_version=service.policy_version,
        decision_id=decision_id,
        candidate_metadata=dict(selected.metadata),
    )
    return service, candidate, decision_id, provenance.linkable_messages


def _status(memory: MemoryDatabase, memory_id: str) -> str | None:
    row = memory.fetch_memory(memory_id, include_chunks=False)
    return str(row["status"]) if row else None


def _event_count(state: StateDatabase, event_type: str, decision_id: str) -> int:
    return sum(
        1
        for row in state.recent_events(100000)
        if row["event_type"] == event_type
        and json.loads(row["payload_json"]).get("decision_id") == decision_id
    )


def _terminal_count(state: StateDatabase, decision_id: str) -> int:
    return sum(
        _event_count(state, event_type, decision_id)
        for event_type in (
            "memory_projection_activated",
            "memory_projection_rolled_back",
            "memory_projection_repair_required",
        )
    )


def test_recovery_case_01_second_link_failure_rolls_back_the_batch(tmp_path: Path) -> None:
    memory_path, state, memory, source = _stores(tmp_path)
    messages = _messages(source, 2)
    service, _, decision_id, refs = _saga(state, memory, source, messages)
    with memory._connection() as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_second_promotion_link
            BEFORE INSERT ON message_memory_links
            WHEN NEW.memory_id = 'memory-1'
              AND (SELECT COUNT(*) FROM message_memory_links WHERE memory_id = NEW.memory_id) >= 1
            BEGIN SELECT RAISE(ABORT, 'second promotion link rejected'); END
            """
        )
    with pytest.raises(sqlite3.IntegrityError, match="second promotion link rejected"):
        source.link_message_memory_batch(refs, "memory-1", decision_id=decision_id)
    reopened_memory = MemoryDatabase(memory_path)
    reopened_source = SourceReadModel(reopened_memory)
    assert reopened_source.memory_links("memory-1") == []
    assert _status(reopened_memory, "memory-1") == "preparing"
    assert _event_count(state, "memory_projection_activated", decision_id) == 0


def test_recovery_case_02_activation_retry_reuses_committed_links_and_terminal(tmp_path: Path) -> None:
    memory_path, state, memory, source = _stores(tmp_path)
    messages = _messages(source, 2)
    _, _, decision_id, refs = _saga(state, memory, source, messages)
    linked = source.link_message_memory_batch(refs, "memory-1", decision_id=decision_id)
    assert len(linked.created_messages) == 2
    with memory._connection() as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_activation_once
            BEFORE UPDATE OF status ON memory_documents
            WHEN NEW.memory_id = 'memory-1' AND NEW.status = 'active'
            BEGIN SELECT RAISE(ABORT, 'activation unavailable'); END
            """
        )
    with pytest.raises(sqlite3.IntegrityError, match="activation unavailable"):
        memory.activate_derived_projection("memory-1", decision_id=decision_id, required_messages=refs)
    with memory._connection() as connection:
        connection.execute("DROP TRIGGER fail_activation_once")
    reopened_memory = MemoryDatabase(memory_path)
    reopened_source = SourceReadModel(reopened_memory)
    reopened_memory.activate_derived_projection(
        "memory-1", decision_id=decision_id, required_messages=refs
    )
    state.record_promotion_event_once(
        decision_id,
        "memory_projection_activated",
        "memory-1",
        {"decision_id": decision_id, "memory_id": "memory-1", "state": "active"},
    )
    state.record_promotion_event_once(
        decision_id,
        "memory_projection_activated",
        "memory-1",
        {"decision_id": decision_id, "memory_id": "memory-1", "state": "active"},
    )
    assert len(reopened_source.memory_links("memory-1")) == 2
    assert _status(reopened_memory, "memory-1") == "active"
    assert _terminal_count(state, decision_id) == 1


def test_recovery_case_03_two_sqlite_connections_race_activation(tmp_path: Path) -> None:
    memory_path, state, memory, source = _stores(tmp_path)
    messages = _messages(source, 1)
    _, _, decision_id, refs = _saga(state, memory, source, messages)
    source.link_message_memory_batch(refs, "memory-1", decision_id=decision_id)
    barrier = threading.Barrier(2)
    results: list[str] = []
    errors: list[BaseException] = []

    def activate_from_restarted_connection() -> None:
        try:
            reopened = MemoryDatabase(memory_path)
            barrier.wait(timeout=5)
            reopened.activate_derived_projection(
                "memory-1", decision_id=decision_id, required_messages=refs
            )
            StateDatabase(tmp_path / "lingji_state.db").record_promotion_event_once(
                decision_id,
                "memory_projection_activated",
                "memory-1",
                {"decision_id": decision_id, "memory_id": "memory-1", "state": "active"},
            )
            results.append("active")
        except BaseException as exc:  # pragma: no cover - diagnostic collection
            errors.append(exc)

    workers = [threading.Thread(target=activate_from_restarted_connection) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=10)
    assert not errors
    assert results == ["active", "active"]
    reopened_state = StateDatabase(tmp_path / "lingji_state.db")
    assert _status(MemoryDatabase(memory_path), "memory-1") == "active"
    assert _terminal_count(reopened_state, decision_id) == 1
    assert not any(
        _event_count(reopened_state, event_type, decision_id)
        for event_type in ("memory_projection_rolled_back", "memory_projection_repair_required")
    )


def test_recovery_case_04_restart_after_start_before_prepare_rolls_back(tmp_path: Path) -> None:
    memory_path, state, memory, source = _stores(tmp_path)
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    decision_id = "decision-start-only"
    state.record_promotion_event_once(
        decision_id,
        "memory_promotion_preparing",
        "memory-1",
        {
            "candidate_id": "memory-1",
            "decision_id": decision_id,
            "memory_id": "memory-1",
            "content_hash": "hash",
            "policy_version": service.policy_version,
            "state": "preparing",
            "messages": [],
        },
    )
    reopened = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "lingji_state.db"),
        memory_db=MemoryDatabase(memory_path),
        evidence_store=SourceReadModel(MemoryDatabase(memory_path)),
    )
    evidence = reopened.reconcile_incomplete_projections()
    assert evidence[0].state is PromotionProjectionState.ROLLED_BACK
    assert _terminal_count(reopened.state_db, decision_id) == 1
    assert _status(reopened.memory_db, "memory-1") is None


def test_recovery_case_05_restart_after_prepare_before_links_removes_projection(tmp_path: Path) -> None:
    memory_path, state, memory, source = _stores(tmp_path)
    messages = _messages(source, 1)
    _, _, decision_id, _ = _saga(state, memory, source, messages)
    reopened_memory = MemoryDatabase(memory_path)
    reopened_source = SourceReadModel(reopened_memory)
    reopened = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "lingji_state.db"),
        memory_db=reopened_memory,
        evidence_store=reopened_source,
    )
    evidence = reopened.reconcile_incomplete_projections()
    assert evidence[0].state is PromotionProjectionState.ROLLED_BACK
    assert _status(reopened_memory, "memory-1") is None
    assert reopened_source.memory_links("memory-1") == []
    assert _terminal_count(reopened.state_db, decision_id) == 1


def test_recovery_case_06_restart_after_link_commit_activates_after_verification(tmp_path: Path) -> None:
    memory_path, state, memory, source = _stores(tmp_path)
    messages = _messages(source, 1)
    _, _, decision_id, refs = _saga(state, memory, source, messages)
    source.link_message_memory_batch(refs, "memory-1", decision_id=decision_id)
    reopened_memory = MemoryDatabase(memory_path)
    reopened_source = SourceReadModel(reopened_memory)
    evidence = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "lingji_state.db"),
        memory_db=reopened_memory,
        evidence_store=reopened_source,
    ).reconcile_incomplete_projections()
    assert evidence[0].state is PromotionProjectionState.VISIBLE_ACTIVE
    assert _status(reopened_memory, "memory-1") == "active"
    assert len(reopened_source.memory_links("memory-1")) == 1
    assert _terminal_count(StateDatabase(tmp_path / "lingji_state.db"), decision_id) == 1


def test_recovery_case_07_restart_after_activation_repairs_missing_terminal(tmp_path: Path) -> None:
    memory_path, state, memory, source = _stores(tmp_path)
    messages = _messages(source, 1)
    _, _, decision_id, refs = _saga(state, memory, source, messages)
    source.link_message_memory_batch(refs, "memory-1", decision_id=decision_id)
    memory.activate_derived_projection("memory-1", decision_id=decision_id, required_messages=refs)
    reopened_memory = MemoryDatabase(memory_path)
    reopened_source = SourceReadModel(reopened_memory)
    evidence = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "lingji_state.db"),
        memory_db=reopened_memory,
        evidence_store=reopened_source,
    ).reconcile_incomplete_projections()
    assert evidence[0].state is PromotionProjectionState.VISIBLE_ACTIVE
    assert _event_count(StateDatabase(tmp_path / "lingji_state.db"), "memory_projection_activated", decision_id) == 1
    assert len(reopened_source.memory_links("memory-1")) == 1


def test_recovery_case_08_incomplete_extra_wrong_owner_links_stay_repair_required(tmp_path: Path) -> None:
    memory_path, state, memory, source = _stores(tmp_path)
    messages = _messages(source, 3)
    _, _, decision_id, refs = _saga(state, memory, source, messages)
    source.link_message_memory_batch((refs[0],), "memory-1", decision_id=decision_id)
    memory.activate_derived_projection("memory-1", decision_id=decision_id, required_messages=(refs[0],))
    source.link_message_memory_batch((refs[1],), "memory-1", decision_id="foreign-owner")
    with memory._connection() as connection:
        connection.execute(
            "INSERT INTO message_memory_links(message_id,memory_id,relation_type,confidence,created_at,created_by_decision_id) VALUES (?,?,?,?,?,NULL)",
            (refs[2].message_id, "memory-1", "derived_from", None, "2026-01-01T00:00:00"),
        )
    with state._connection() as connection:
        connection.execute(
            "DELETE FROM events WHERE stable_event_id=?",
            (f"promotion:{decision_id}:memory_projection_activated",),
        )
    restarted = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "lingji_state.db"),
        memory_db=MemoryDatabase(memory_path),
        evidence_store=SourceReadModel(MemoryDatabase(memory_path)),
    )
    first = restarted.reconcile_incomplete_projections()
    second = restarted.reconcile_incomplete_projections()
    assert first[0].state is PromotionProjectionState.REPAIR_REQUIRED
    assert second[0].state is PromotionProjectionState.REPAIR_REQUIRED
    assert _status(restarted.memory_db, "memory-1") == "repair_required"
    assert _event_count(restarted.state_db, "memory_projection_repair_required", decision_id) == 1
    assert _event_count(restarted.state_db, "memory_projection_activated", decision_id) == 0


def test_recovery_case_09_cleanup_cannot_delete_null_or_foreign_owned_links(tmp_path: Path) -> None:
    memory_path, state, memory, source = _stores(tmp_path)
    messages = _messages(source, 2)
    _, _, decision_id, refs = _saga(state, memory, source, messages)
    with memory._connection() as connection:
        for ref, owner in ((refs[0], None), (refs[1], "foreign-owner")):
            connection.execute(
                "INSERT INTO message_memory_links(message_id,memory_id,relation_type,confidence,created_at,created_by_decision_id) VALUES (?,?,?,?,?,?)",
                (ref.message_id, "memory-1", "derived_from", None, "2026-01-01T00:00:00", owner),
            )
    assert memory.remove_preparing_projection("memory-1", decision_id=decision_id) is False
    reopened_memory = MemoryDatabase(memory_path)
    reopened_source = SourceReadModel(reopened_memory)
    assert _status(reopened_memory, "memory-1") == "preparing"
    assert len(reopened_source.memory_links("memory-1")) == 2


def _write_note(root: Path, relative: str, values: dict[str, object], body: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_frontmatter(values, body), encoding="utf-8")


def _temporal_memory(tmp_path: Path) -> tuple[MemoryDatabase, Path]:
    vault = tmp_path / "vault"
    storage = tmp_path / "storage"
    VaultLayout(vault).ensure()
    _write_note(
        vault,
        "03-Knowledge/old.md",
        {
            "id": "old",
            "title": "architecture decision",
            "memory_type": "knowledge",
            "memory_tier": "archival",
            "status": "superseded",
            "privacy": "private",
            "project": ["LingJi"],
            "tags": ["decision"],
            "authority": "old_chat_inference",
            "valid_from": "2025-01-01T00:00:00Z",
            "valid_to": "2026-01-01T00:00:00Z",
            "superseded_by": "current",
        },
        "old architecture decision",
    )
    _write_note(
        vault,
        "03-Knowledge/current.md",
        {
            "id": "current",
            "title": "architecture decision",
            "memory_type": "knowledge",
            "memory_tier": "archival",
            "status": "active",
            "privacy": "private",
            "project": ["LingJi"],
            "tags": ["decision"],
            "authority": "user_explicit",
            "valid_from": "2026-01-01T00:00:00Z",
        },
        "current architecture decision",
    )
    database = MemoryDatabase(storage / "memory.db")
    index = PEMISIndex(vault, storage)
    index.build_index()
    database.rebuild_from_index(index.get_all(), vault)
    return database, vault


def test_recovery_case_10_authoritative_sqlite_excludes_stale_semantic_payload(tmp_path: Path) -> None:
    database, _ = _temporal_memory(tmp_path)
    stale_chunk = database.fetch_memory("old")["chunks"][0]["chunk_id"]

    class StaleSemanticPayload:
        def search(self, query: str, limit: int, filters: dict[str, object] | None = None) -> list[dict[str, object]]:
            return [{"chunk_id": stale_chunk, "memory_id": "old", "score": 1.0, "status": "active"}]

    retriever = HybridRetriever(database, semantic_provider=StaleSemanticPayload())
    current = retriever.search("architecture decision", filters=SearchFilters(mode="current"))
    why = retriever.search("architecture decision", filters=SearchFilters(mode="why"))
    assert {item["memory_id"] for item in current} == {"current"}
    assert {item["memory_id"] for item in why} == {"current"}
    excluded = why[0]["why"]["excluded_candidates"]
    old = next(item for item in excluded if item["memory_id"] == "old")
    assert old["reason"] == "status_superseded"
    assert old["reason"] == "status_superseded"


@pytest.mark.parametrize("mode", ["current", "why", "as_of", "history"])
def test_recovery_case_11_gateway_matches_raw_temporal_identities(tmp_path: Path, mode: str) -> None:
    database, _ = _temporal_memory(tmp_path)
    retriever = HybridRetriever(database)
    raw = retriever.search(
        "architecture decision",
        filters=SearchFilters(mode=mode, as_of="2025-06-01T00:00:00Z" if mode == "as_of" else None),
    )
    state_path = tmp_path / "state.db"
    gateway = MemoryGateway(
        database,
        retriever,
        ContextPackBuilder(database, retriever),
        object(),
        profiles=AIProfileRegistry(),
        state_db=StateDatabase(state_path),
    )
    through_gateway = gateway.search_memory(
        "chatgpt",
        "architecture decision",
        mode=mode,
        as_of="2025-06-01T00:00:00Z" if mode == "as_of" else None,
    )["results"]
    assert {item["memory_id"] for item in through_gateway} == {item["memory_id"] for item in raw}
    assert {item["memory_id"] for item in through_gateway} == ({"old"} if mode == "as_of" else ({"old", "current"} if mode == "history" else {"current"}))


def test_recovery_case_12_promotion_audit_reports_missing_extra_and_duplicates(tmp_path: Path) -> None:
    database, _ = _temporal_memory(tmp_path)
    evidence = (
        PromotionEvidence("m1", "d1", "m1", PromotionProjectionState.VISIBLE_ACTIVE),
        PromotionEvidence("m2", "d2", "m2", PromotionProjectionState.VISIBLE_ACTIVE),
    )

    class DurableRows:
        def list_derived_projection_identity_rows(self) -> tuple[dict[str, str], ...]:
            # Deliberately model rows exactly as a raw SQLite query would
            # return; duplicate IDs must not be hidden by a dict keyed on ID.
            return ({"memory_id": "m1"}, {"memory_id": "m1"}, {"memory_id": "extra"})

    audit = audit_promotion_persistence(DurableRows(), promotion_evidence=evidence)
    assert audit.expected_memory_ids == ("m1", "m2")
    assert audit.persisted_memory_ids == ("extra", "m1", "m1")
    assert audit.missing_memory_ids == ("m2",)
    assert audit.extra_memory_ids == ("extra",)
    assert audit.duplicate_memory_records == 1
    assert not audit.ready
    assert database.path.exists()
