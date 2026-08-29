from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.gateway.owner_memory_cards import OwnerMemoryCardProjector


class FixtureDatabase:
    def __init__(self):
        self.documents = [
            {
                "memory_id": "mem-active",
                "relative_path": "03-Knowledge/topic.md",
                "title": "Release plan",
                "memory_type": "knowledge",
                "memory_tier": "derived",
                "status": "active",
                "review_status": "approved",
                "privacy": "private",
                "confidence": "0.96",
                "valid_from": "2026-01-01T00:00:00Z",
                "valid_to": None,
                "superseded_by": None,
                "content_hash": "hash-active",
                "relationships": {
                    "evidence_refs": [{"kind": "message", "value": "msg-1", "content_hash": "hash-msg-1"}],
                    "authority": "user_explicit",
                    "topic_key": "release-plan",
                },
            },
            {
                "memory_id": "mem-candidate",
                "relative_path": "__derived__/automatic-memory/mem-candidate.md",
                "title": "Candidate preference",
                "memory_type": "knowledge",
                "memory_tier": "derived",
                "status": "needs_review",
                "review_status": "pending_owner_review",
                "privacy": "private",
                "confidence": "0.61",
                "valid_from": None,
                "valid_to": None,
                "superseded_by": None,
                "content_hash": "hash-candidate",
                "relationships": {
                    "evidence_refs": [{"kind": "message", "value": "msg-2", "content_hash": "hash-msg-2"}],
                    "authority": "old_chat_inference",
                },
            },
            {
                "memory_id": "mem-old",
                "relative_path": "03-Knowledge/old.md",
                "title": "Old plan",
                "memory_type": "knowledge",
                "memory_tier": "core",
                "status": "superseded",
                "review_status": "approved",
                "privacy": "private",
                "confidence": "0.99",
                "valid_from": "2025-01-01T00:00:00Z",
                "valid_to": "2026-02-01T00:00:00Z",
                "superseded_by": "mem-active",
                "content_hash": "hash-old",
                "relationships": {
                    "evidence_refs": [{"kind": "message", "value": "msg-3", "content_hash": "hash-msg-3"}],
                    "supersession_reason": "owner changed plan",
                },
            },
        ]

    def list_documents(self, *, include_chunks=False):
        return [
            {**item, "chunks": [{"chunk_id": f"chunk-{item['memory_id']}", "text": "full body"}]}
            if include_chunks
            else dict(item)
            for item in self.documents
        ]

    def fetch_memory(self, memory_id, include_chunks=True):
        for item in self.documents:
            if item["memory_id"] == memory_id:
                result = dict(item)
                if include_chunks:
                    result["chunks"] = [{"chunk_id": f"chunk-{memory_id}", "text": "full body"}]
                return result
        return None


class FixtureSources:
    def owner_viewer(self):
        return SimpleNamespace(owner=True, agent_id="lingji-local", allowed_privacy=("private",))

    def list_conversations(self, **kwargs):
        return {
            "items": [
                {
                    "conversation_id": "conv-unpromoted",
                    "source_id": "src-codex",
                    "title": "A conversation without permanent memory",
                    "message_count": 2,
                    "started_at": "2026-03-01T10:00:00Z",
                    "ended_at": "2026-03-01T10:02:00Z",
                    "privacy": "private",
                }
            ],
            "pagination": {"total": 1},
        }

    def list_messages(self, **kwargs):
        conversation_id = kwargs.get("conversation_id")
        if conversation_id == "conv-unpromoted":
            return {
                "items": [
                    {"message_id": "raw-1", "conversation_id": conversation_id, "source_id": "src-codex", "role": "user", "occurred_at": "2026-03-01T10:00:00Z", "content_hash": "raw-hash-1"},
                    {"message_id": "raw-2", "conversation_id": conversation_id, "source_id": "src-codex", "role": "assistant", "occurred_at": "2026-03-01T10:02:00Z", "content_hash": "raw-hash-2"},
                ],
                "pagination": {"total": 2},
            }
        return {"items": [], "pagination": {"total": 0}}

    def get_source(self, source_id):
        return {"item": {"source_id": source_id, "source_type": "codex_rollout", "display_name": "Codex 历史", "status": "active"}}

    def get_message(self, message_id, **kwargs):
        return {"item": {"message_id": message_id, "role": "assistant", "occurred_at": "2026-03-01T10:00:00Z", "content": "Evidence line", "content_hash": f"hash-{message_id}"}}

    def memory_sources(self, memory_id, **kwargs):
        refs = {"mem-active": ["msg-1"], "mem-candidate": ["msg-2"], "mem-old": ["msg-3"]}
        return {"links": [{"message_id": value, "content_preview": "bounded evidence preview"} for value in refs.get(memory_id, [])]}


class FixtureStatistics:
    def vector_status(self):
        return {"state": "degraded", "ready": False, "collection_exists": False, "vectors": None}

    def vector_coverage(self):
        return {"state": "unavailable", "expected": None, "indexed": None, "missing": None}


class FixturePromotionEvents:
    def recent_events(self, limit=100000):
        return [{
            "event_type": "memory_promotion_decision",
            "entity_id": "candidate-from-state",
            "payload_json": '{"candidate_id":"candidate-from-state","title":"Pending event","status":"pending_owner_review","source_refs":["missing"]}',
        }]


def test_projects_owner_cards_and_unpromoted_read_only_evidence_without_full_text():
    projector = OwnerMemoryCardProjector(FixtureDatabase(), FixtureSources(), FixtureStatistics())

    result = projector.list_cards(limit=50, offset=0)

    assert result["pagination"] == {"limit": 50, "offset": 0, "total": 4, "has_more": False}
    cards = {item["memory_id"]: item for item in result["items"]}
    assert cards["mem-active"]["topic"] == "Release plan"
    assert cards["mem-active"]["evidence_count"] == 1
    assert "evidence" not in cards["mem-active"]
    assert cards["mem-active"]["conclusion"] is None
    assert cards["mem-active"]["layers"]["permanent"]["state"] == "not_permanent"
    assert cards["mem-active"]["layers"]["vector"]["state"] == "unavailable"
    assert cards["mem-candidate"]["action"]["type"] == "confirm"
    assert cards["mem-old"]["freshness"]["state"] == "superseded"
    assert cards["mem-old"]["freshness"]["replacement_id"] == "mem-active"

    evidence = cards["conversation:conv-unpromoted"]
    assert evidence["kind"] == "conversation_evidence"
    assert evidence["permanent_memory"] == "尚未加入永久记忆"
    assert evidence["source"]["message_count"] == 2
    assert "full body" not in repr(evidence)
    detail = projector.get_card("mem-active", include_evidence=True)["item"]
    assert len(detail["evidence"]) <= 3


def test_unknowns_are_not_invented_for_missing_dates_conflict_and_provenance_mismatch():
    database = FixtureDatabase()
    database.documents[0]["valid_from"] = None
    database.documents[0]["relationships"]["authority_conflict"] = True
    database.documents[0]["relationships"]["evidence_refs"] = [{"kind": "message", "value": "missing", "content_hash": "bad"}]
    projector = OwnerMemoryCardProjector(database, FixtureSources(), FixtureStatistics())

    card = projector.get_card("mem-active")["item"]

    assert card["freshness"]["state"] == "unknown"
    assert card["trust"]["conflict"] == "conflict"
    assert card["trust"]["provenance"] == "mismatch"
    assert card["conclusion"] is None
    assert card["action"]["type"] == "review"


def test_pending_promotion_event_is_read_as_a_candidate_without_persisting_a_memory():
    projector = OwnerMemoryCardProjector(FixtureDatabase(), FixtureSources(), FixtureStatistics(), state_db=FixturePromotionEvents())

    card = projector.get_card("candidate-from-state")["item"]

    assert card["state"] == "needs_review"
    assert card["action"]["type"] == "confirm"
    assert card["layers"]["permanent"]["state"] == "pending_owner_review"


@pytest.mark.parametrize("limit", [0, 51])
def test_card_limit_is_bounded(limit):
    projector = OwnerMemoryCardProjector(FixtureDatabase(), FixtureSources(), FixtureStatistics())
    with pytest.raises(ValueError):
        projector.list_cards(limit=limit)
