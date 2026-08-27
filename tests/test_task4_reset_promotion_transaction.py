from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.auto_review.models import ProvenanceRef, ReviewCandidate
from src.retrieval.memory_db import MemoryDatabase
from src.sources import ExternalMessageKey, ResolvedMessageRef, SourceReadModel
from src.storage.state_db import StateDatabase
from src.automatic_memory.quality_evidence import audit_promotion_persistence
from src.retrieval.temporal import TemporalQuery
from src.auto_review.models import PromotionEvidence, PromotionProjectionState
from src.auto_review.promotion import AutoMemoryPromotionService


def test_append_requires_safe_promotion_event_boundary() -> None:
    class AppendOnlyState:
        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        def append_event(self, *args: object) -> None:
            self.calls.append(args)

    state = AppendOnlyState()
    service = object.__new__(AutoMemoryPromotionService)
    service.state_db = state
    with pytest.raises(RuntimeError, match="safe promotion event recorder unavailable"):
        service._append("memory_candidate_recorded", "candidate-1", {"token": "sk-secret"})
    assert state.calls == []


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_ordinary_promotion_event_rejects_non_finite_nested_values(tmp_path: Path, bad: float) -> None:
    database_path = tmp_path / "state.db"
    state = StateDatabase(database_path)
    with pytest.raises(ValueError, match="non-finite promotion payload value"):
        state.append_promotion_event(
            "memory_candidate_recorded",
            "candidate-1",
            {
                "structured_content": {"confidence": bad},
                "promotion_evidence": {"score": bad},
            },
        )
    with __import__("sqlite3").connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM events WHERE entity_id = ?",
            ("candidate-1",),
        ).fetchone()[0]
    assert count == 0


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
    first = state.record_promotion_event_once("decision-1", "memory_promotion_preparing", "memory-1", {"decision_id": "decision-1", "memory_id": "memory-1", "state": "preparing"})
    second = state.record_promotion_event_once("decision-1", "memory_promotion_preparing", "memory-1", {"state": "preparing", "memory_id": "memory-1", "decision_id": "decision-1"})
    assert first == second
    assert state.get_event(first)["stable_event_id"] == first
    with pytest.raises(ValueError, match="conflict"):
        state.record_promotion_event_once("decision-1", "memory_promotion_preparing", "memory-1", {"decision_id": "decision-1", "memory_id": "memory-1", "state": "preparing", "error_codes": ["changed"]})


def test_terminal_exclusivity_is_keyed_by_decision_not_entity(tmp_path: Path) -> None:
    state = StateDatabase(tmp_path / "state.db")
    state.record_promotion_event_once("decision-1", "memory_projection_activated", "memory-1", {"decision_id": "decision-1", "state": "active"})
    with pytest.raises(ValueError, match="terminal"):
        state.record_promotion_event_once("decision-1", "memory_projection_rolled_back", "other-memory", {"decision_id": "decision-1", "state": "rolled_back"})


def test_active_reconcile_with_missing_message_link_requires_repair(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    from src.auto_review import AutoMemoryPromotionService, ReviewCandidate
    content = "fact"
    content_hash = __import__("hashlib").sha256(json.dumps({"title": content, "content": content, "structured": {}}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    candidate = ReviewCandidate(memory_id="memory-1", title=content, content=content, content_hash=content_hash, source_refs=(message["message_id"],), confidence=0.9, authority="direct_user", source_kind="chat")
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    result = service.evaluate(candidate)
    decision_id = result["decision_id"]
    with memory._connection() as connection:
        connection.execute("DELETE FROM message_memory_links WHERE memory_id=?", ("memory-1",))
    with state._connection() as connection:
        connection.execute("DELETE FROM events WHERE stable_event_id=?", (f"promotion:{decision_id}:memory_projection_activated",))
    evidence = service.reconcile_incomplete_projections()
    assert evidence and evidence[0].state.value == "repair_required"


def test_active_reconcile_terminal_conflict_reports_unreconciled_blocker(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    from src.auto_review import AutoMemoryPromotionService, ReviewCandidate
    content_hash = __import__("hashlib").sha256(json.dumps({"title": "fact", "content": "fact", "structured": {}}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", content_hash=content_hash, source_refs=(message["message_id"],), confidence=0.9, authority="direct_user", source_kind="chat")
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    result = service.evaluate(candidate)
    decision_id = result["decision_id"]
    with memory._connection() as connection:
        connection.execute("DELETE FROM message_memory_links WHERE memory_id=?", ("memory-1",))
    evidence = service.reconcile_incomplete_projections()
    assert evidence and "reconcile_unreconciled" in evidence[0].error_codes
    assert memory.fetch_memory("memory-1", include_chunks=False)["status"] == "repair_required"


def test_owner_approval_uses_stable_preparing_and_terminal_events(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    from src.auto_review import AutoMemoryPromotionService, ReviewCandidate
    content = "fact"
    content_hash = __import__("hashlib").sha256(json.dumps({"title": content, "content": content, "structured": {}}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    candidate = ReviewCandidate(memory_id="memory-1", title=content, content=content, content_hash=content_hash, source_refs=(message["message_id"],), confidence=0.5, authority="direct_user", source_kind="chat")
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    pending = service.evaluate(candidate)
    approved = service.approve(pending["candidate_id"], expected_content_hash=pending["content_hash"], owner_confirmed=True)
    assert approved["status"] == "active"
    event_types = {row["event_type"] for row in state.recent_events(100)}
    assert "memory_promotion_preparing" in event_types
    assert "memory_projection_activated" in event_types
    assert any(row["stable_event_id"] and row["stable_event_id"].endswith(":memory_projection_activated") for row in state.recent_events(100))


def test_unresolved_legacy_reference_is_context_evidence_not_message(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    from src.auto_review import AutoMemoryPromotionService, ReviewCandidate
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", source_refs=("source-only",), confidence=0.9, authority="direct_user", source_kind="chat")
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    result = service.evaluate(candidate)
    assert result["status"] == "pending_owner_review"
    recorded = service.candidate("memory-1")
    assert recorded["source_refs"][0]["kind"] == "evidence"


def test_typed_unknown_message_reports_stable_provenance_error(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    from src.auto_review import AutoMemoryPromotionService, ProvenanceRef, ReviewCandidate
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", source_refs=(ProvenanceRef("message", "missing"),), confidence=0.9, authority="direct_user", source_kind="chat")
    result = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source).evaluate(candidate)
    assert "provenance_unknown_message" in result["reason_codes"]


def test_promotion_event_rejects_secrets_paths_and_fixture_labels(tmp_path: Path) -> None:
    state = StateDatabase(tmp_path / "state.db")
    with pytest.raises(ValueError):
        state.record_promotion_event_once("decision-1", "memory_promotion_preparing", "memory-1", {"token": "sk-secret", "path": "/Users/private/x", "fixture_label": "fixture-x"})


def test_verify_rejects_forged_external_message_identity(tmp_path: Path) -> None:
    _, memory, source = _stores(tmp_path)
    message = _message(source)
    memory.prepare_derived_projection(memory_id="memory-1", title="fact", content="fact", content_hash="hash", evidence_refs=(), confidence=0.9, authority="direct_user", source_kind="chat", policy_version="memory-promotion-1", decision_id="decision-1", candidate_metadata={})
    actual = source.resolve_exact_message_ref(message["message_id"])
    source.link_message_memory_batch((actual,), "memory-1", decision_id="decision-1")
    forged = ResolvedMessageRef(actual.message_id, ExternalMessageKey("forged", actual.external_key.conversation_external_id, actual.external_key.message_external_id), actual.content_hash)
    assert source.verify_message_memory_links((forged,), "memory-1") is False


def test_event_provenance_resolves_exact_message_and_hash(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    event_id = state.append_event("evidence_recorded", "message", message["message_id"], {
        "message_id": message["message_id"], "content_hash": message["content_hash"],
    })
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", source_refs=(ProvenanceRef("event", str(event_id)),), confidence=0.9, authority="direct_user", source_kind="chat")
    result = __import__("src.auto_review", fromlist=["AutoMemoryPromotionService"]).AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source).evaluate(candidate)
    assert result["status"] == "active"


def test_event_provenance_hash_mismatch_is_stable_error(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    event_id = state.append_event("evidence_recorded", "message", message["message_id"], {
        "message_id": message["message_id"], "content_hash": "wrong",
    })
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", source_refs=(ProvenanceRef("event", str(event_id)),), confidence=0.9, authority="direct_user", source_kind="chat")
    result = __import__("src.auto_review", fromlist=["AutoMemoryPromotionService"]).AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source).evaluate(candidate)
    assert result["status"] == "pending_owner_review"
    assert "provenance_event_invalid" in result["reason_codes"]


def test_promotion_lease_claim_expiry_renew_and_owner_release(tmp_path: Path) -> None:
    state = StateDatabase(tmp_path / "state.db")
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert state.claim_promotion_lease("d", "one", now=start, ttl_seconds=5)
    assert not state.claim_promotion_lease("d", "two", now=start + timedelta(seconds=1))
    assert state.renew_promotion_lease("d", "one", now=start + timedelta(seconds=1), ttl_seconds=5)
    assert not state.release_promotion_lease("d", "two")
    assert state.release_promotion_lease("d", "one")
    assert state.claim_promotion_lease("d", "two", now=start + timedelta(seconds=2), ttl_seconds=5)


def test_rollback_refuses_foreign_owned_link_and_preserves_projection(tmp_path: Path) -> None:
    _, memory, source = _stores(tmp_path)
    message = _message(source)
    memory.prepare_derived_projection(memory_id="memory-1", title="fact", content="fact", content_hash="hash", evidence_refs=(), confidence=0.9, authority="direct_user", source_kind="chat", policy_version="memory-promotion-1", decision_id="owner-a", candidate_metadata={})
    source.link_message_memory_batch((message,), "memory-1", decision_id="owner-b")
    assert memory.remove_preparing_projection("memory-1", decision_id="owner-a") is False
    assert memory.fetch_memory("memory-1", include_chunks=False) is not None


def test_activation_rejects_wrong_relation_and_extra_links(tmp_path: Path) -> None:
    _, memory, source = _stores(tmp_path)
    first = _message(source)
    second = source.upsert_message({"source_id": first["source_id"], "conversation_id": first["conversation_id"], "external_id": "msg-2", "role": "user", "sequence": 2, "content": "second"})
    memory.prepare_derived_projection(memory_id="memory-1", title="fact", content="fact", content_hash="hash", evidence_refs=(), confidence=0.9, authority="direct_user", source_kind="chat", policy_version="memory-promotion-1", decision_id="decision-1", candidate_metadata={})
    actual = source.resolve_exact_message_ref(first["message_id"])
    extra = source.resolve_exact_message_ref(second["message_id"])
    source.link_message_memory_batch((actual, extra), "memory-1", decision_id="decision-1")
    with pytest.raises(ValueError, match="provenance"):
        memory.activate_derived_projection("memory-1", decision_id="decision-1", required_messages=(actual,))


def test_same_file_preflight_rejects_split_memory_and_source_databases(tmp_path: Path) -> None:
    state = StateDatabase(tmp_path / "state.db")
    memory = MemoryDatabase(tmp_path / "memory.db")
    source = SourceReadModel(MemoryDatabase(tmp_path / "other.db"))
    message = _message(source)
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", source_refs=(message["message_id"],), confidence=0.9, authority="direct_user", source_kind="chat")
    from src.auto_review import AutoMemoryPromotionService
    result = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source).evaluate(candidate)
    assert result["status"] == "error"
    assert memory.fetch_memory("memory-1") is None


def test_active_current_search_excludes_preparing_but_history_can_inspect(tmp_path: Path) -> None:
    memory = MemoryDatabase(tmp_path / "memory.db")
    memory.prepare_derived_projection(memory_id="memory-1", title="fact", content="fact", content_hash="hash", evidence_refs=(), confidence=0.9, authority="direct_user", source_kind="chat", policy_version="memory-promotion-1", decision_id="decision-1", candidate_metadata={})
    assert memory.fetch_memory("memory-1", include_chunks=False)["status"] == "preparing"
    assert memory.search_fts("fact", mode="current") == []
    assert memory.search_fts("fact", mode="history")


def test_ambiguous_legacy_external_reference_is_not_promoted(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    first = _message(source)
    source_row = source.upsert_source({"source_type": "chat", "external_id": "chat-2"})
    conversation = source.upsert_conversation({"source_id": source_row["source_id"], "external_id": "conv-2"})
    source.upsert_message({"source_id": source_row["source_id"], "conversation_id": conversation["conversation_id"], "external_id": "msg-1", "role": "user", "sequence": 1, "content": "other"})
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", source_refs=("msg-1",), confidence=0.9, authority="direct_user", source_kind="chat")
    service = __import__("src.auto_review", fromlist=["AutoMemoryPromotionService"]).AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    result = service.evaluate(candidate)
    assert result["status"] == "pending_owner_review"
    assert service.candidate("memory-1")["source_refs"][0]["kind"] == "evidence"


@pytest.mark.parametrize("mode", ["current", "why", "as_of", "history"])
@pytest.mark.parametrize("status", ["preparing", "repair_required", "rolled_back"])
def test_temporal_modes_never_treat_in_progress_promotion_as_effective(mode: str, status: str) -> None:
    query = TemporalQuery.from_values(mode, "2026-01-01T00:00:00Z")
    allowed, _ = query.allows({"status": status})
    assert allowed is (mode == "history")


def test_audit_uses_raw_rows_and_reports_injected_duplicates(tmp_path: Path) -> None:
    class RawRows:
        def list_derived_projection_identity_rows(self):
            return ({"memory_id": "m1"}, {"memory_id": "m1"}, {"memory_id": "m2"})
    evidence = (PromotionEvidence("m1", "d1", "m1", PromotionProjectionState.VISIBLE_ACTIVE),)
    audit = audit_promotion_persistence(RawRows(), promotion_evidence=evidence)
    assert audit.duplicate_memory_records == 1
    assert audit.extra_memory_ids == ("m2",)
    assert not audit.ready


def test_start_event_failure_has_no_projection_or_links(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", source_refs=(message["message_id"],), confidence=0.9, authority="direct_user", source_kind="chat")
    def fail_start(*args, **kwargs):
        raise RuntimeError("start unavailable")
    monkeypatch.setattr(state, "record_promotion_event_once", fail_start)
    service = __import__("src.auto_review", fromlist=["AutoMemoryPromotionService"]).AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    result = service.evaluate(candidate)
    assert result["status"] == "error"
    assert memory.fetch_memory("memory-1") is None
    assert source.memory_links("memory-1") == []


@pytest.mark.parametrize("failure_stage", ["prepare", "link_commit", "activation_commit"])
def test_promotion_failure_stages_leave_truthful_terminal_and_no_active_projection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_stage: str) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", source_refs=(message["message_id"],), confidence=0.9, authority="direct_user", source_kind="chat")
    from src.auto_review import AutoMemoryPromotionService
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    if failure_stage == "prepare":
        monkeypatch.setattr(memory, "prepare_derived_projection", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("prepare unavailable")))
    elif failure_stage == "link_commit":
        monkeypatch.setattr(source, "link_message_memory_batch", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("link unavailable")))
    else:
        monkeypatch.setattr(memory, "activate_derived_projection", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("activate unavailable")))
    result = service.evaluate(candidate)
    assert result["status"] == "error"
    assert memory.fetch_memory("memory-1") is None
    assert source.memory_links("memory-1") == []
    terminals = [row for row in state.recent_events(100) if row["event_type"] in {"memory_projection_rolled_back", "memory_projection_repair_required"}]
    assert len(terminals) == 1


def test_crash_after_activation_before_terminal_reconciles_active_audit(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    candidate = ReviewCandidate(memory_id="memory-1", title="fact", content="fact", source_refs=(message["message_id"],), confidence=0.9, authority="direct_user", source_kind="chat")
    from src.auto_review import AutoMemoryPromotionService
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=source)
    selected = service._normalize(candidate)
    provenance = service._normalize_provenance(selected)
    decision_id = service._decision_id(selected, "active", service.policy_version)
    service._record_promotion_event("memory_promotion_preparing", selected, decision_id, provenance)
    service._write_projection(selected, decision_id)
    evidence = service.reconcile_incomplete_projections()
    assert evidence and evidence[0].state is PromotionProjectionState.VISIBLE_ACTIVE
    assert len([row for row in state.recent_events(100) if row["event_type"] == "memory_projection_activated"]) == 1


@pytest.mark.parametrize("payload", [
    {"messages": [{"message_id": "m", "metadata": {"arbitrary": True}}]},
    {"errors": ["Traceback: private failure"]},
    {"errors": ["/Users/private/fixture"]},
    {"errors": [float("nan")]},
])
def test_promotion_payload_scanner_rejects_nested_or_nonfinite_data(tmp_path: Path, payload: dict) -> None:
    state = StateDatabase(tmp_path / "state.db")
    with pytest.raises(ValueError):
        state.record_promotion_event_once("decision-1", "memory_promotion_preparing", "memory-1", payload)


def test_duplicate_canonical_message_refs_fail_closed_before_projection(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    candidate = ReviewCandidate(
        memory_id="memory-duplicate", title="fact", content="fact",
        source_refs=(message["message_id"], message["message_id"]),
        confidence=0.9, authority="direct_user", source_kind="chat",
    )
    result = __import__("src.auto_review", fromlist=["AutoMemoryPromotionService"]).AutoMemoryPromotionService(
        state_db=state, memory_db=memory, evidence_store=source
    ).evaluate(candidate)
    assert result["status"] == "pending_owner_review"
    assert "provenance_duplicate_message" in result["reason_codes"]
    assert memory.fetch_memory("memory-duplicate") is None


def test_malformed_canonical_message_payload_is_rejected(tmp_path: Path) -> None:
    state = StateDatabase(tmp_path / "state.db")
    with pytest.raises(ValueError, match="promotion_payload_schema_invalid"):
        state.record_promotion_event_once(
            "decision-1", "memory_promotion_preparing", "memory-1",
            {"decision_id": "decision-1", "memory_id": "memory-1", "state": "preparing",
             "messages": ["message-1"]},
        )


def test_malformed_typed_provenance_returns_owner_safe_result(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    result = __import__("src.auto_review", fromlist=["AutoMemoryPromotionService"]).AutoMemoryPromotionService(
        state_db=state, memory_db=memory, evidence_store=source
    ).evaluate({
        "memory_id": "memory-malformed", "title": "fact", "content": "fact",
        "source_refs": [{"kind": "message", "value": 42, "content_hash": []}],
        "confidence": 0.9, "authority": "direct_user", "source_kind": "chat",
    })
    assert result["status"] == "pending_owner_review"
    assert "provenance_typed_invalid" in result["reason_codes"]


def test_ordinary_promotion_audit_redacts_forbidden_metadata(tmp_path: Path) -> None:
    state, memory, source = _stores(tmp_path)
    message = _message(source)
    candidate = ReviewCandidate(
        memory_id="memory-safe-audit", title="fact", content="fact",
        source_refs=(message["message_id"],), confidence=0.5,
        authority="direct_user", source_kind="chat",
        metadata={"token": "sk-live-secret", "path": "/Users/private/fixture"},
    )
    service = __import__("src.auto_review", fromlist=["AutoMemoryPromotionService"]).AutoMemoryPromotionService(
        state_db=state, memory_db=memory, evidence_store=source
    )
    service.evaluate(candidate)
    payloads = [row["payload_json"] for row in state.recent_events(100)]
    assert all("sk-live-secret" not in payload and "/Users/private/fixture" not in payload for payload in payloads)


def test_direct_prepare_rejects_noncanonical_refs_and_secret_metadata(tmp_path: Path) -> None:
    _, memory, _ = _stores(tmp_path)
    with pytest.raises(ValueError, match="promotion_evidence_ref_invalid"):
        memory.prepare_derived_projection(
            memory_id="memory-1", title="fact", content="fact", content_hash="hash",
            evidence_refs=["message-1"], confidence=0.9, authority="direct_user",
            source_kind="chat", policy_version="memory-promotion-1", decision_id="decision-1",
            candidate_metadata={},
        )
    with pytest.raises(ValueError, match="promotion_metadata_forbidden"):
        memory.prepare_derived_projection(
            memory_id="memory-2", title="fact", content="fact", content_hash="hash",
            evidence_refs=(), confidence=0.9, authority="direct_user", source_kind="chat",
            policy_version="memory-promotion-1", decision_id="decision-2",
            candidate_metadata={"token": "sk-live-secret"},
        )


def test_verify_duplicate_expected_message_refs_fails_closed(tmp_path: Path) -> None:
    _, memory, source = _stores(tmp_path)
    message = _message(source)
    memory.prepare_derived_projection(
        memory_id="memory-1", title="fact", content="fact", content_hash="hash",
        evidence_refs=(), confidence=0.9, authority="direct_user", source_kind="chat",
        policy_version="memory-promotion-1", decision_id="decision-1", candidate_metadata={},
    )
    actual = source.resolve_exact_message_ref(message["message_id"])
    source.link_message_memory_batch((actual,), "memory-1", decision_id="decision-1")
    assert source.verify_message_memory_links((actual, actual), "memory-1", decision_id="decision-1") is False
