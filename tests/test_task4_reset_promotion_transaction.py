from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.auto_review.models import ProvenanceRef, ReviewCandidate
from src.retrieval.memory_db import MemoryDatabase
from src.sources import SourceReadModel
from src.storage.state_db import StateDatabase


def _stores(tmp_path: Path) -> tuple[StateDatabase, MemoryDatabase, SourceReadModel]:
    memory = MemoryDatabase(tmp_path / "lingji_memory.db")
    return (
        StateDatabase(tmp_path / "lingji_state.db"),
        memory,
        SourceReadModel(memory),
    )


def _message(source: SourceReadModel, content: str = "fact") -> dict:
    source_row = source.upsert_source({"source_type": "chat", "external_id": "chat-1"})
    conversation = source.upsert_conversation(
        {"source_id": source_row["source_id"], "external_id": "conv-1"}
    )
    return source.upsert_message(
        {
            "source_id": source_row["source_id"],
            "conversation_id": conversation["conversation_id"],
            "external_id": "msg-1",
            "role": "user",
            "sequence": 1,
            "content": content,
        }
    )


def test_legacy_derived_writer_cannot_publish_active_projection(tmp_path: Path) -> None:
    _, memory, _ = _stores(tmp_path)

    with pytest.raises((RuntimeError, ValueError, NotImplementedError)):
        memory.upsert_derived_projection(
            memory_id="memory-1",
            title="A fact",
            content="fact",
            content_hash="hash",
            evidence_refs=[],
            confidence=0.99,
            authority="direct_user",
            source_kind="chat",
            policy_version="memory-promotion-1",
            decision_id="decision-1",
            candidate_metadata={},
        )


def test_batch_link_returns_created_and_preserves_atomic_contract(tmp_path: Path) -> None:
    _, memory, source = _stores(tmp_path)
    first = _message(source)
    assert first["message_id"]
    memory.prepare_derived_projection(
        memory_id="memory-1", title="A fact", content="fact", content_hash="hash",
        evidence_refs=(), confidence=0.99, authority="direct_user", source_kind="chat",
        policy_version="memory-promotion-1", decision_id="decision-1", candidate_metadata={}
    )

    result = source.link_message_memory_batch(
        [first],
        "memory-1",
        decision_id="decision-1",
    )

    assert result.created_messages[0].message_id == first["message_id"]
    assert source.memory_links("memory-1")[0]["relation_type"] == "derived_from"


def test_mapping_provenance_is_retained_as_typed_data() -> None:
    candidate = ReviewCandidate.from_mapping(
        {
            "memory_id": "memory-1",
            "title": "A fact",
            "content": "fact",
            "source_refs": [{"kind": "message", "value": "msg-1", "content_hash": "abc"}],
        }
    )
    assert isinstance(candidate.source_refs[0], ProvenanceRef)
    assert candidate.source_refs[0].to_dict() == {"kind": "message", "value": "msg-1", "content_hash": "abc"}
    assert json.dumps({"refs": [item.to_dict() for item in candidate.source_refs]}, sort_keys=True, separators=(",", ":")) == (
        '{"refs":[{"content_hash":"abc","kind":"message","value":"msg-1"}]}'
    )


def test_state_promotion_event_is_stable_and_conflicts_fail_closed(tmp_path: Path) -> None:
    state = StateDatabase(tmp_path / "state.db")
    first = state.record_promotion_event_once("decision-1", "memory_promotion_preparing", "memory-1", {"b": 2, "a": 1})
    second = state.record_promotion_event_once("decision-1", "memory_promotion_preparing", "memory-1", {"a": 1, "b": 2})
    assert first == second
    assert state.get_event(first)["stable_event_id"] == first
    with pytest.raises(ValueError, match="conflict"):
        state.record_promotion_event_once("decision-1", "memory_promotion_preparing", "memory-1", {"a": 9})
