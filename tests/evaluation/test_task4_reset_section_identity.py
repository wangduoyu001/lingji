from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType

import pytest

from src.automatic_memory.evaluation import CorpusRecord
from src.automatic_memory.evidence_identity import (
    EvidenceIdentityError,
    MessageIdentity,
    build_identity_registry,
    select_context_evidence,
)
from src.sources.read_model import SourceReadModel


def _record(*, fact_id: str = "fact-1", message_id: str = "msg-1", citation_id: str = "cite-1") -> CorpusRecord:
    text = "真实消息正文"
    return CorpusRecord(
        fact_id=fact_id,
        topic_key="topic",
        source_id="source-1",
        conversation_id="conversation-1",
        message_id=message_id,
        role="user",
        content=text,
        content_hash=SourceReadModel.content_hash(text),
        occurred_at="2026-08-27T00:00:00Z",
        lifecycle="active",
        supersedes_fact_id=None,
        authority="owner-confirmed",
        project_id="project-1",
        privacy="synthetic",
        agent_scope=("agent-1",),
        citation_id=citation_id,
        memory_kind="fact",
        risk="low",
    )


def _registry(*, record: CorpusRecord | None = None):
    record = record or _record()
    persisted = [{
        "source_id": "source-1",
        "conversation_id": "conversation-1",
        "message_id": record.message_id,
        "content_hash": record.content_hash,
    }]
    return build_identity_registry(
        corpus=(record,),
        persisted_messages=persisted,
        promotion_bindings={"memory-1": record.fact_id},
        message_links=[{"message_id": record.message_id, "memory_id": "memory-1"}],
    )


def _memory(kind: str = "retrieved_memory", memory_id: str = "memory-1") -> dict:
    return {"kind": kind, "memory_id": memory_id, "text": "事实正文", "citation": {"memory_id": memory_id}}


def _raw(*, memory_id: str = "memory-1", text: str = "真实消息正文", **overrides) -> dict:
    values = {
        "kind": "raw_message_evidence",
        "memory_id": memory_id,
        "source_id": "source-1",
        "conversation_id": "conversation-1",
        "message_id": "msg-1",
        "content_hash": SourceReadModel.content_hash(text),
        "text": text,
    }
    values.update(overrides)
    values["citation"] = {
        "memory_id": values.get("memory_id"),
        "source_id": values.get("source_id"),
        "conversation_id": values.get("conversation_id"),
        "message_id": values.get("message_id"),
        "content_hash": values.get("content_hash"),
    }
    return values


def test_all_memory_sections_validate_without_message_ids():
    registry = _registry()
    for kind in ("core_memory", "retrieved_memory", "project_authority_memory"):
        selected = select_context_evidence({"sections": [_memory(kind)]}, registry)
        assert selected.fact_ids == ("fact-1",)
        assert selected.citation_ids == ()


@pytest.mark.parametrize("field", ["memory_id", "source_id", "conversation_id", "message_id", "content_hash"])
def test_raw_identity_requires_full_matching_fields(field: str):
    values = _raw()
    values[field] = "" if field != "content_hash" else "wrong-hash"
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [values]}, _registry())


def test_raw_identity_requires_complete_production_citation():
    registry = _registry()
    without_citation = _raw()
    without_citation.pop("citation")
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [without_citation]}, registry)
    for field in ("memory_id", "source_id", "conversation_id", "message_id", "content_hash"):
        values = _raw()
        values["citation"].pop(field)
        with pytest.raises(EvidenceIdentityError):
            select_context_evidence({"sections": [values]}, registry)


@pytest.mark.parametrize("field", ["memory_id", "source_id", "conversation_id", "message_id", "content_hash"])
def test_raw_citation_must_match_top_level(field: str):
    values = _raw()
    values["citation"][field] = "wrong" if field != "content_hash" else "0" * 64
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [values]}, _registry())


def test_memory_and_linked_raw_evidence_share_fact_and_enrich_citation():
    selected = select_context_evidence({"sections": [_memory(), _raw()]}, _registry())
    assert selected.fact_ids == ("fact-1",)
    assert selected.citation_ids == ("cite-1",)
    assert len(selected.stable_identities) == 2


def test_duplicate_canonical_identity_and_unknown_identity_fail_closed():
    registry = _registry()
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [_memory(), _memory()]}, registry)
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [_memory(memory_id="unknown")]}, registry)
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [_raw(), _raw()]}, registry)
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [_raw(message_id="unknown-message")]}, registry)


def test_raw_message_and_memory_fact_contradiction_fails_closed():
    record = _record()
    identity = MessageIdentity(
        source_id=record.source_id,
        conversation_id=record.conversation_id,
        message_id=record.message_id,
        content_hash=record.content_hash,
        memory_id="memory-2",
    )
    registry = type(_registry())(
        memory_to_fact=MappingProxyType({"memory-2": "fact-2"}),
        message_to_fact_citation=MappingProxyType({identity: ("fact-1", "cite-1")}),
    )
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [_raw(memory_id="memory-2")]}, registry)


def test_limit_counts_distinct_facts_and_validates_overflow_sections():
    second = replace(_record(fact_id="fact-2", message_id="msg-2", citation_id="cite-2"), source_id="source-2", conversation_id="conversation-2")
    persisted = [
        {"source_id": "source-1", "conversation_id": "conversation-1", "message_id": "msg-1", "content_hash": _record().content_hash},
        {"source_id": "source-2", "conversation_id": "conversation-2", "message_id": "msg-2", "content_hash": second.content_hash},
    ]
    registry = build_identity_registry(
        corpus=(_record(), second),
        persisted_messages=persisted,
        promotion_bindings={"memory-1": "fact-1", "memory-2": "fact-2"},
        message_links=[
            {"message_id": "msg-1", "memory_id": "memory-1"},
            {"message_id": "msg-2", "memory_id": "memory-2"},
        ],
    )
    assert select_context_evidence({"sections": [_memory(), _raw(), _memory(memory_id="memory-2")]}, registry, limit=1).fact_ids == ("fact-1",)
    assert select_context_evidence({"sections": [_memory(), _raw(), _memory(memory_id="memory-2")]}, registry, limit=1).citation_ids == ("cite-1",)
    assert select_context_evidence({"sections": [_memory(), _raw(), _memory(memory_id="memory-2")]}, registry, limit=0).fact_ids == ()
    assert select_context_evidence({"sections": [_memory(), _raw(), _memory(memory_id="memory-2")]}, registry, limit=2).fact_ids == ("fact-1", "fact-2")
    ordered = select_context_evidence({"sections": [_memory(memory_id="memory-2"), _memory()]}, registry, limit=2)
    assert ordered.fact_ids == ("fact-2", "fact-1")
    assert tuple(item.memory_id for item in ordered.stable_identities) == ("memory-2", "memory-1")
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [_memory(), {"kind": "not-supported"}]}, registry, limit=1)
    overflow_invalid = {"sections": [_memory(), _raw()]}
    overflow_invalid["sections"].append({"kind": "raw_message_evidence", "memory_id": "memory-2", "text": "bad"})
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence(overflow_invalid, registry, limit=1)


def test_malformed_pack_and_invalid_limit_fail_closed():
    registry = _registry()
    for pack in (None, {"sections": "bad"}, {"sections": ["bad"]}, {"sections": [{"kind": "bad"}]}):
        with pytest.raises(EvidenceIdentityError):
            select_context_evidence(pack, registry)  # type: ignore[arg-type]
    assert select_context_evidence({"sections": []}, registry).fact_ids == ()
    for limit in (-1, True, 1.0):
        with pytest.raises(EvidenceIdentityError):
            select_context_evidence({"sections": []}, registry, limit=limit)  # type: ignore[arg-type]


def test_registry_rejects_conflicting_bindings_and_freezes_maps():
    record = _record()
    with pytest.raises(EvidenceIdentityError):
        build_identity_registry(
            corpus=(record,),
            persisted_messages=[],
            promotion_bindings={"memory-1": "missing-fact"},
            message_links=[],
        )
    registry = _registry()
    with pytest.raises(TypeError):
        registry.memory_to_fact["later"] = "fact-1"  # type: ignore[index]


def test_registry_rejects_conflicting_composite_representations_and_links():
    first = _record()
    second = replace(_record(fact_id="fact-2", message_id="msg-2", citation_id="cite-2"), source_id="source-2", conversation_id="conversation-2")
    row = {
        "source_id": first.source_id,
        "conversation_id": first.conversation_id,
        "message_id": first.message_id,
        "source_external_id": second.source_id,
        "conversation_external_id": second.conversation_id,
        "message_external_id": second.message_id,
        "content_hash": first.content_hash,
    }
    with pytest.raises(EvidenceIdentityError):
        build_identity_registry(
            corpus=(first, second), persisted_messages=[row],
            promotion_bindings={"memory-1": "fact-1"},
            message_links=[{"message_id": first.message_id, "memory_id": "memory-1"}],
        )
    with pytest.raises(EvidenceIdentityError):
        build_identity_registry(
            corpus=(first,), persisted_messages=[{
                "source_id": first.source_id, "conversation_id": first.conversation_id,
                "message_id": first.message_id, "content_hash": first.content_hash,
            }], promotion_bindings={"memory-1": "fact-1"},
            message_links=[{"message_id": first.message_id, "memory_id": "memory-1"}, {"message_id": first.message_id, "memory_id": "memory-1"}],
        )


@pytest.mark.parametrize(
    "representation",
    [
        {"source_external_id": " source-1 ", "conversation_external_id": "conversation-1", "message_external_id": "msg-1"},
        {"source_external_id": "source-1", "conversation_external_id": "conversation-1"},
        {"source_external_id": "source-1", "conversation_external_id": 7, "message_external_id": "msg-1"},
        {"corpus_source_id": " source-1 ", "corpus_conversation_id": "conversation-1", "corpus_message_id": "msg-1"},
    ],
)
def test_every_populated_composite_representation_is_exact_and_complete(representation):
    record = _record()
    row = {
        "source_id": record.source_id,
        "conversation_id": record.conversation_id,
        "message_id": record.message_id,
        "content_hash": record.content_hash,
        **representation,
    }
    with pytest.raises(EvidenceIdentityError):
        build_identity_registry(
            corpus=(record,), persisted_messages=[row],
            promotion_bindings={"memory-1": record.fact_id},
            message_links=[{"message_id": record.message_id, "memory_id": "memory-1"}],
        )


def test_registry_accepts_more_than_200_persisted_rows_with_exact_binding():
    record = _record()
    persisted = [{"source_id": record.source_id, "conversation_id": record.conversation_id, "message_id": record.message_id, "content_hash": record.content_hash}]
    persisted.extend({"source_id": f"source-{i}", "conversation_id": f"conversation-{i}", "message_id": f"message-{i}", "content_hash": record.content_hash} for i in range(201))
    registry = build_identity_registry(
        corpus=(record,), persisted_messages=persisted,
        promotion_bindings={"memory-1": "fact-1"},
        message_links=[{"message_id": record.message_id, "memory_id": "memory-1"}],
    )
    assert registry.memory_to_fact["memory-1"] == "fact-1"


def test_registry_keeps_persisted_snapshot_free_of_fixture_labels():
    record = _record()
    row = {
        "source_id": record.source_id,
        "conversation_id": record.conversation_id,
        "message_id": record.message_id,
        "content_hash": record.content_hash,
    }
    before = dict(row)
    build_identity_registry(
        corpus=(record,), persisted_messages=[row],
        promotion_bindings={"memory-1": record.fact_id},
        message_links=[{"message_id": record.message_id, "memory_id": "memory-1"}],
    )
    assert row == before
    assert not any(str(key).startswith("fixture_") for key in row)


@pytest.mark.parametrize("field,value", [("kind", " retrieved_memory "), ("memory_id", " memory-1 ")])
def test_canonical_kind_and_identity_reject_surrounding_whitespace(field: str, value: str):
    section = _memory()
    section[field] = value
    with pytest.raises(EvidenceIdentityError):
        select_context_evidence({"sections": [section]}, _registry())
