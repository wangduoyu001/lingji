from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.automatic_memory.evaluation import load_corpus, load_questions
from src.automatic_memory.evidence_identity import build_identity_registry, select_context_evidence
from src.automatic_memory.quality_gate import (
    AutomaticMemoryFunctionalGate,
    CORPUS_SHA256,
    QUESTIONS_SHA256,
    run_quality_gate,
)


ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "evaluation" / "fixtures" / "automatic_memory_corpus.jsonl"
QUESTIONS = ROOT / "evaluation" / "fixtures" / "automatic_memory_questions.jsonl"


def test_frozen_inputs_and_selector_are_expectation_blind():
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(CORPUS) == CORPUS_SHA256
    assert digest(QUESTIONS) == QUESTIONS_SHA256
    record = load_corpus(CORPUS)[0]
    registry = build_identity_registry(
        corpus=(record,),
        persisted_messages=[{
            "source_id": record.source_id,
            "conversation_id": record.conversation_id,
            "message_id": record.message_id,
            "content_hash": record.content_hash,
        }],
        promotion_bindings={"memory-1": record.fact_id},
        message_links=[{"message_id": record.message_id, "memory_id": "memory-1"}],
    )
    pack = {"sections": [{"kind": "retrieved_memory", "memory_id": "memory-1", "text": record.content}]}
    expected = {"expected_fact_ids": [record.fact_id], "forbidden_fact_ids": [], "expected_citation_ids": [record.citation_id]}
    baseline = select_context_evidence(pack, registry)
    expected["expected_fact_ids"] = ["forged"]
    expected["forbidden_fact_ids"] = [record.fact_id]
    expected["expected_citation_ids"] = ["forged-citation"]
    assert select_context_evidence(pack, registry) == baseline
    actual = json.loads(json.dumps(pack))
    actual["sections"][0]["memory_id"] = "unknown"
    with pytest.raises(ValueError):
        select_context_evidence(actual, registry)


def test_real_quality_gate_reports_measured_result(tmp_path: Path):
    output = tmp_path / "quality.json"
    report = run_quality_gate(CORPUS, QUESTIONS, output_path=output)
    assert report.answered_questions == 100
    assert report.imported_messages == report.expected_messages == len(load_corpus(CORPUS))
    assert len(load_questions(QUESTIONS, corpus=load_corpus(CORPUS))) == 100
    assert report.mcp_attempts == 100
    # The default test environment has no configured Production Vault root;
    # unavailable sentinel evidence is explicitly nullable, never numeric 0.
    assert report.production_pollution is None
    envelope = json.loads(output.read_text(encoding="utf-8"))
    assert envelope["production_pollution"] is None
    assert AutomaticMemoryFunctionalGate.evaluate(report) in {"PASS", "FAIL"}
