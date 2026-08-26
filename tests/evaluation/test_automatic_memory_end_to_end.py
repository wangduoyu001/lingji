from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.automatic_memory.evaluation import load_corpus, load_questions
from src.automatic_memory.quality_gate import (
    AutomaticMemoryFunctionalGate,
    CORPUS_SHA256,
    QUESTIONS_SHA256,
    run_quality_gate,
    select_retrieval_evidence,
)


ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "evaluation" / "fixtures" / "automatic_memory_corpus.jsonl"
QUESTIONS = ROOT / "evaluation" / "fixtures" / "automatic_memory_questions.jsonl"


def test_frozen_inputs_and_selector_are_expectation_blind():
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(CORPUS) == CORPUS_SHA256
    assert digest(QUESTIONS) == QUESTIONS_SHA256
    records = [{"metadata": {"fixture_fact_id": "fact-a", "fixture_citation_id": "cite-a"}},
               {"metadata": {"fixture_fact_id": "fact-b", "fixture_citation_id": "cite-b"}}]
    assert select_retrieval_evidence(records) == (("fact-a", "cite-a"), ("fact-b", "cite-b"))
    mutated = json.loads(json.dumps(records))
    mutated[0]["expected_fact_ids"] = ["forged"]
    assert select_retrieval_evidence(mutated) == select_retrieval_evidence(records)


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
