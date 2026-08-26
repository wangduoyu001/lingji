"""Round-4 takeover RED tests.

These tests intentionally describe the missing truthfulness/provenance
contracts at the f9bf190 baseline.  They are kept as the auditable RED
starting point for the repair.
"""
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.auto_review.models import ReviewCandidate
from src.auto_review.promotion import AutoMemoryPromotionService, PromotionStatus
from src.automatic_memory import quality_evidence, quality_gate
from src.automatic_memory.quality_evidence import ImportedEvidenceAudit, ProtectedTreeSentinel
from src.retrieval.memory_db import MemoryDatabase
from src.sources.read_model import SourceReadModel
from src.storage.state_db import StateDatabase


@dataclass(frozen=True)
class ExpectedImportedRow:
    source_external_id: str
    conversation_external_id: str
    message_external_id: str
    sequence: int
    role: str
    content_hash: str
    occurred_at: str


def test_import_audit_uses_adapter_projection_and_detects_every_mismatch():
    class ReadModel:
        def list_messages(self, **_kwargs):
            return {"items": [
                {"external_id": "src:conv:message:m1", "role": "assistant", "sequence": 9,
                 "content_hash": "wrong", "source_id": "src-db", "conversation_id": "conv-db"},
                {"external_id": "src:conv:message:m1", "role": "user", "sequence": 0,
                 "content_hash": "h1", "source_id": "src-db", "conversation_id": "conv-db"},
                {"external_id": "extra", "role": "user", "sequence": 2,
                 "content_hash": "hx", "source_id": "src-db", "conversation_id": "conv-db"},
            ], "next_offset": None}

    expected = [ExpectedImportedRow("src", "conv", "src:conv:message:m1", 0, "user", "h1", "2026-01-01T00:00:00+00:00")]
    audit = ImportedEvidenceAudit.from_read_model(ReadModel(), expected)
    assert audit.duplicate == 1
    assert audit.extra == 1
    assert audit.ordered_external_id_matches == 0
    assert audit.sequence_matches == 0
    assert audit.role_matches == 0
    assert audit.content_hash_matches == 0
    assert audit.source_matches == 0
    assert audit.conversation_matches == 0


def test_selector_uses_prequery_identity_map_not_fixture_metadata_or_question_sets():
    identity = quality_gate.build_prequery_identity_map(
        [
            {"external_id": "m1", "content_hash": "h1"},
            {"external_id": "m2", "content_hash": "h2"},
        ],
        {"m1": ("fact-a", "cite-a"), "m2": ("fact-b", "cite-b")},
    )
    selected = quality_gate.select_gateway_evidence(
        [{"message_id": "m1", "content_hash": "h1"}, {"message_id": "m2", "content_hash": "h2"}],
        identity,
    )
    assert selected == (("fact-a", "cite-a"), ("fact-b", "cite-b"))


def _source_model(tmp_path: Path):
    memory = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(memory)
    source = read_model.stable_id("source", "source")
    conversation = read_model.stable_id("conversation", source, "conversation")
    read_model.upsert_bundle({
        "source": {"source_id": source, "source_type": "generic", "display_name": "S", "external_id": "source-ext"},
        "conversations": [{"conversation_id": conversation, "external_id": "conversation-ext", "title": "C", "messages": [
            {"external_id": "message-ext", "role": "user", "sequence": 0, "content": "owner evidence"},
        ]}],
    })
    return memory, read_model, source, conversation


def _candidate(refs):
    import hashlib, json
    title, content, structured = "Remember", "owner evidence", {"x": 1}
    digest = hashlib.sha256(json.dumps({"title": title, "content": content, "structured": structured}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return ReviewCandidate(memory_id="candidate", title=title, content=content, memory_type="preference",
                           content_hash=digest, source_refs=tuple(refs), confidence=.99, authority="direct_user",
                           source_kind="user_chat", extractor_version="r4", structured_content=structured)


def test_promotion_resolves_generic_refs_and_rejects_ambiguous_or_unresolved(tmp_path: Path):
    memory, read_model, source, conversation = _source_model(tmp_path)
    state = StateDatabase(tmp_path / "state.db")
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=read_model)
    active = service.evaluate(_candidate(("message-ext",)))
    assert active["status"] == PromotionStatus.ACTIVE.value
    assert read_model.memory_links(active["candidate_id"])
    unresolved = service.evaluate(_candidate(("missing-ref",)).__class__(**{**_candidate(("missing-ref",)).__dict__, "memory_id": "candidate-2"}))
    assert unresolved["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value


def test_promotion_fails_closed_for_ambiguous_conversation_ref(tmp_path: Path):
    memory = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(memory)
    source = read_model.stable_id("source", "s")
    conversation = read_model.stable_id("conversation", source, "c")
    read_model.upsert_bundle({
        "source": {"source_id": source, "source_type": "generic", "display_name": "S"},
        "conversations": [{"conversation_id": conversation, "external_id": "ambiguous-conversation", "title": "C", "messages": [
            {"external_id": "m1", "role": "user", "sequence": 0, "content": "one"},
            {"external_id": "m2", "role": "user", "sequence": 1, "content": "two"},
        ]}],
    })
    service = AutoMemoryPromotionService(state_db=StateDatabase(tmp_path / "state.db"), memory_db=memory, evidence_store=read_model)
    result = service.evaluate(_candidate(("ambiguous-conversation",)))
    assert result["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value


def test_promotion_compensates_all_links_when_a_later_link_fails(tmp_path: Path):
    class Evidence:
        def __init__(self): self.created = []
        def resolve_message_refs(self, refs): return ("msg-1", "msg-2")
        def link_message_memory(self, message_id, memory_id, **_kwargs):
            self.created.append(message_id)
            if message_id == "msg-2": raise OSError("link failed")
        def unlink_message_memory(self, message_id, memory_id): self.created.remove(message_id)
        def get_message(self, *_args, **_kwargs): return None
    memory = MemoryDatabase(tmp_path / "memory.db")
    state = StateDatabase(tmp_path / "state.db")
    evidence = Evidence()
    service = AutoMemoryPromotionService(state_db=state, memory_db=memory, evidence_store=evidence)
    result = service.evaluate(_candidate(("generic-ref-1", "generic-ref-2")))
    assert result["status"] == PromotionStatus.ERROR.value
    assert evidence.created == []
    assert memory.fetch_memory("candidate") is None


def test_sentinel_fails_closed_on_unreadable_descendant(tmp_path: Path, monkeypatch):
    root = tmp_path / "protected"; root.mkdir()
    (root / "data").write_text("x", encoding="utf-8")
    real_stat = Path.stat
    def broken_stat(self, *args, **kwargs):
        if self.name == "data": raise PermissionError("denied")
        return real_stat(self, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", broken_stat)
    with pytest.raises(ValueError, match="unreadable"):
        ProtectedTreeSentinel.capture((root,))


def test_readiness_isolation_does_not_publish_or_run_functional_gate():
    readiness = quality_evidence.QualityEvidenceReadiness(
        import_audit=True, promotion_provenance=True, gateway_selection=True,
        mcp_parity=False, degradation=False, context_baseline=False, scale=False,
    )
    assert readiness.functional_status == "NOT_EVALUATED"
    assert readiness.should_run_acceptance_gate is False
    assert not hasattr(readiness, "evaluate")


def test_invalid_gateway_evidence_fails_closed_instead_of_becoming_retrieval_miss():
    with pytest.raises(Exception):
        quality_gate.validate_selected_evidence(
            recalled=("forbidden", "forbidden"), citations=("unknown",),
            expected=("expected",), forbidden=("forbidden",), expected_citations=(),
        )


def test_runner_envelope_records_readiness_and_sentinel_failure(tmp_path: Path):
    root = Path(__file__).parent
    output = tmp_path / "quality.json"
    quality_gate.run_quality_gate(
        root / "fixtures" / "automatic_memory_corpus.jsonl",
        root / "fixtures" / "automatic_memory_questions.jsonl",
        output_path=output,
    )
    import json
    envelope = json.loads(output.read_text(encoding="utf-8"))
    assert envelope["quality_evidence_readiness"]["functional_status"] == "NOT_EVALUATED"
    assert "protected_tree_capture_error" in envelope
