"""Task 4R1 round-5 final-breaker RED contracts.

These tests are intentionally authored against the round-5 base before the
repair.  They exercise the real selector/audit/promotion/runner boundaries;
the report records the exact RED command and assertions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.auto_review.models import ReviewCandidate
from src.auto_review.promotion import AutoMemoryPromotionService, PromotionStatus
from src.automatic_memory import quality_gate
from src.automatic_memory.quality_evidence import ExpectedImportedRow, ImportedEvidenceAudit
from src.retrieval.memory_db import MemoryDatabase
from src.sources.read_model import SourceReadModel
from src.storage.state_db import StateDatabase


CORPUS = Path(__file__).parent / "fixtures" / "automatic_memory_corpus.jsonl"
QUESTIONS = Path(__file__).parent / "fixtures" / "automatic_memory_questions.jsonl"


def _candidate(memory_id: str, *, confidence: float = 0.99, source_refs: tuple[str, ...] = ("message-ext",)) -> ReviewCandidate:
    title = f"Remember {memory_id}"
    content = f"Owner evidence for {memory_id}."
    structured = {"memory_id": memory_id}
    content_hash = hashlib.sha256(
        json.dumps(
            {"title": title, "content": content, "structured": structured},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return ReviewCandidate(
        memory_id=memory_id,
        title=title,
        content=content,
        memory_type="preference",
        content_hash=content_hash,
        source_refs=source_refs,
        confidence=confidence,
        authority="direct_user",
        source_kind="user_chat",
        extractor_version=f"round5-{memory_id}",
        structured_content=structured,
    )


def _source_harness(tmp_path: Path):
    memory = MemoryDatabase(tmp_path / "memory.db")
    read_model = SourceReadModel(memory)
    source_id = read_model.stable_id("source", "source")
    conversation_id = read_model.stable_id("conversation", source_id, "conversation")
    read_model.upsert_bundle(
        {
            "source": {
                "source_id": source_id,
                "source_type": "generic",
                "display_name": "S",
                "external_id": "source-ext",
            },
            "conversations": [
                {
                    "conversation_id": conversation_id,
                    "external_id": "conversation-ext",
                    "title": "C",
                    "messages": [
                        {"external_id": "message-ext", "role": "user", "sequence": 0, "content": "owner evidence"},
                    ],
                }
            ],
        }
    )
    return memory, read_model


def test_gateway_boundary_is_expectation_blind_empty_is_a_miss_and_invalid_identity_fails_closed(tmp_path: Path, monkeypatch):
    persisted = [
        {"external_id": "m1", "message_id": "primary-1", "content_hash": "h1"},
        {"external_id": "m2", "message_id": "primary-2", "content_hash": "h2"},
    ]
    identity = quality_gate.build_prequery_identity_map(
        persisted,
        {"m1": ("fact-a", "cite-a"), "m2": ("fact-b", "cite-b")},
    )
    gateway_rows = [
        {"message_id": "m1", "content_hash": "h1"},
        {"message_id": "m2", "content_hash": "h2"},
    ]
    expected = quality_gate.select_gateway_evidence(gateway_rows, identity)
    mutated_question = {"expected_fact_ids": ["forged"], "forbidden_fact_ids": ["fact-a"]}
    assert quality_gate.select_gateway_evidence(gateway_rows, identity) == expected
    mutated_question["expected_fact_ids"] = ["fact-b"]
    assert quality_gate.select_gateway_evidence(gateway_rows, identity) == expected
    assert quality_gate.select_gateway_evidence([gateway_rows[1]], identity) == (("fact-b", "cite-b"),)
    assert quality_gate.select_gateway_evidence([], identity) == ()
    with pytest.raises(ValueError, match="identity"):
        quality_gate.select_gateway_evidence([{"message_id": "m1"}], identity)
    with pytest.raises(ValueError, match="duplicate"):
        quality_gate.select_gateway_evidence([gateway_rows[0], gateway_rows[0]], identity)

    # With a valid identity map removed and 100 successful empty Gateway
    # responses, readiness still means the selector ran for every response.
    monkeypatch.setattr(quality_gate, "_all_messages", lambda _read_model: [])
    monkeypatch.setattr(
        quality_gate.MemoryGateway,
        "build_context_pack",
        lambda *args, **kwargs: {"sections": [], "markdown": ""},
    )
    output = tmp_path / "empty-gateway.json"
    quality_gate.run_quality_gate(CORPUS, QUESTIONS, output_path=output)
    envelope = json.loads(output.read_text(encoding="utf-8"))
    assert envelope["quality_evidence_readiness"]["gateway_selection"] is True


def test_import_audit_requires_persisted_order_and_all_row_invariants():
    expected = (
        ExpectedImportedRow("source", "conversation", "m1", 0, "user", "h1", "2026-01-01T00:00:00+00:00"),
        ExpectedImportedRow("source", "conversation", "m2", 1, "assistant", "h2", "2026-01-01T00:00:01+00:00"),
    )

    class ReadModel:
        def list_messages(self, **_kwargs):
            # Persisted order is deliberately swapped; sorting by source,
            # conversation and sequence must not hide the defect.
            return {
                "items": [
                    {
                        "external_id": "m2",
                        "role": "user",
                        "sequence": 9,
                        "content_hash": "h3",
                        "source_external_id": "wrong-source",
                        "conversation_external_id": "wrong-conversation",
                    },
                    {
                        "external_id": "m1",
                        "role": "assistant",
                        "sequence": 8,
                        "content_hash": "h3",
                        "source_external_id": "wrong-source",
                        "conversation_external_id": "wrong-conversation",
                    },
                ],
                "next_offset": None,
            }

    audit = ImportedEvidenceAudit.from_read_model(ReadModel(), expected)
    assert audit.actual == audit.expected == 2
    assert audit.missing == audit.extra == 0
    assert audit.duplicate_content_hashes == 1
    assert audit.ordered_external_id_matches == 0
    assert audit.sequence_matches == 0
    assert audit.role_matches == 0
    assert audit.content_hash_matches == 0
    assert audit.source_matches == 0
    assert audit.conversation_matches == 0


def test_runner_keeps_sentinel_unavailable_nullable_and_does_not_report_zero(tmp_path: Path, monkeypatch):
    def unavailable(_roots):
        raise ValueError("missing protected root: vault")

    monkeypatch.setattr(quality_gate.ProtectedTreeSentinel, "capture", unavailable)
    output = tmp_path / "sentinel-unavailable.json"
    quality_gate.run_quality_gate(CORPUS, QUESTIONS, output_path=output)
    envelope = json.loads(output.read_text(encoding="utf-8"))
    assert envelope["production_pollution"] is None
    assert envelope["protected_tree_capture_error"] == "missing protected root: vault"
    assert envelope["quality_evidence_readiness"]["import_audit"] is False


def test_promotion_attaches_current_evidence_only_after_projection_and_resets_non_active_results(tmp_path: Path):
    memory, read_model = _source_harness(tmp_path)
    service = AutoMemoryPromotionService(
        state_db=StateDatabase(tmp_path / "state.db"),
        memory_db=memory,
        evidence_store=read_model,
    )
    active = service.evaluate(_candidate("active"))
    assert active["status"] == PromotionStatus.ACTIVE.value
    assert active["promotion_evidence"]["candidate_id"] == "active"
    assert active["promotion_evidence"]["resulting_lifecycle"] == PromotionStatus.ACTIVE.value

    pending = service.evaluate(_candidate("pending", confidence=0.80))
    assert pending["status"] == PromotionStatus.PENDING_OWNER_REVIEW.value
    assert "promotion_evidence" not in pending

    rejected = service.reject(
        "pending",
        expected_content_hash=pending["content_hash"],
        owner_confirmed=True,
        reason="round-5 test",
    )
    assert rejected["status"] == PromotionStatus.REJECTED.value
    assert "promotion_evidence" not in rejected

    service.projection_writer = lambda **_kwargs: (_ for _ in ()).throw(OSError("projection unavailable"))
    error = service.evaluate(_candidate("error"))
    assert error["status"] == PromotionStatus.ERROR.value
    assert error.get("promotion_evidence", {}).get("candidate_id") == "error"


def test_runner_quarantines_unmeasured_4r2_fields_and_keeps_status_not_evaluated(tmp_path: Path):
    output = tmp_path / "readiness.json"
    quality_gate.run_quality_gate(CORPUS, QUESTIONS, output_path=output)
    envelope = json.loads(output.read_text(encoding="utf-8"))
    assert envelope["functional_status"] == "NOT_EVALUATED"
    assert envelope["phase_status"] == "NOT_EVALUATED"
    assert envelope["mcp_parity"]["status"] == "NOT_MEASURED"
    assert envelope["semantic_degradation"]["status"] == "NOT_MEASURED"
    assert envelope["corruption_isolation"]["status"] == "NOT_MEASURED"
    assert envelope["context_baseline"]["status"] == "NOT_MEASURED"
    assert envelope["quality_evidence_readiness"]["mcp_parity"] is False
    assert envelope["quality_evidence_readiness"]["degradation"] is False
    assert envelope["quality_evidence_readiness"]["context_baseline"] is False


def test_round5_review_record_has_no_pending_commit_placeholders():
    report = Path(__file__).parents[2] / ".superpowers" / "sdd" / "2026-08-26-phase1-automatic-memory-followup" / "task-4-report.md"
    text = report.read_text(encoding="utf-8")
    assert "TDD_ORDER_NOT_MET" in text
    assert "round-5" in text.lower()
    assert "Production pollution `null`" in text
    assert "待提交" not in text
    assert "follows below" not in text
    assert "this round commit follows below" not in text
