from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.automatic_memory.evaluation import load_corpus, load_questions
from src.automatic_memory.evidence_identity import (
    EvidenceIdentityError,
    SelectedEvidence,
    build_identity_registry,
    select_context_evidence,
)
from src.automatic_memory.quality_gate import (
    AutomaticMemoryFunctionalGate,
    CORPUS_SHA256,
    QUESTIONS_SHA256,
    run_quality_gate,
)
import src.automatic_memory.quality_gate as quality_gate_module
from src.retrieval.memory_db import MemoryDatabase
from src.sources.read_model import SourceReadModel
from src.storage.state_db import StateDatabase


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

    questions = load_questions(QUESTIONS, corpus=load_corpus(CORPUS))
    for question in questions:
        object.__setattr__(question, "expected_fact_ids", ("forged",))
        object.__setattr__(question, "forbidden_fact_ids", (record.fact_id,))
        object.__setattr__(question, "expected_citation_ids", ("forged-citation",))
        assert select_context_evidence(pack, registry) == baseline


def test_real_quality_gate_reports_measured_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    output = tmp_path / "quality.json"
    selector_calls = 0
    original_selector = quality_gate_module.select_context_evidence

    def counted_selector(*args, **kwargs):
        nonlocal selector_calls
        selector_calls += 1
        return original_selector(*args, **kwargs)

    monkeypatch.setattr(quality_gate_module, "select_context_evidence", counted_selector)
    report = run_quality_gate(CORPUS, QUESTIONS, output_path=output)
    assert report.answered_questions == 100
    assert report.imported_messages == report.expected_messages == len(load_corpus(CORPUS))
    assert len(load_questions(QUESTIONS, corpus=load_corpus(CORPUS))) == 100
    assert report.mcp_attempts == 100
    assert selector_calls == 100
    # The default test environment has no configured Production Vault root;
    # unavailable sentinel evidence is explicitly nullable, never numeric 0.
    assert report.production_pollution is None
    envelope = json.loads(output.read_text(encoding="utf-8"))
    assert envelope["production_pollution"] is None
    assert envelope["mcp_parity"]["status"] == "NOT_MEASURED"
    serialized = output.read_text(encoding="utf-8")
    assert "fixture_fact_id" not in serialized
    assert "fixture_citation_id" not in serialized
    assert AutomaticMemoryFunctionalGate.evaluate(report) in {"PASS", "FAIL"}


@pytest.mark.parametrize(
    "selected",
    [
        SelectedEvidence(("UNKNOWN-FACT",), (), ()),
        SelectedEvidence(("fact-preference-001",), ("UNKNOWN-CITATION",), ()),
    ],
)
def test_quality_runner_rejects_unknown_selected_membership(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: SelectedEvidence):
    monkeypatch.setattr(quality_gate_module, "select_context_evidence", lambda *_args, **_kwargs: selected)
    with pytest.raises(EvidenceIdentityError):
        run_quality_gate(CORPUS, QUESTIONS, output_path=tmp_path / "unknown.json")
    assert not (tmp_path / "unknown.json").exists()


def test_real_import_promotion_storage_snapshot_has_no_evaluation_labels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    held_roots: list[Path] = []
    real_rmtree = quality_gate_module.shutil.rmtree

    def hold_quality_root(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.name.startswith("lingji-acceptance-quality-"):
            held_roots.append(candidate)
            return
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(quality_gate_module.shutil, "rmtree", hold_quality_root)
    try:
        run_quality_gate(CORPUS, QUESTIONS, output_path=tmp_path / "storage-snapshot.json")
        assert len(held_roots) == 1
        root = held_roots[0]
        read_model = SourceReadModel(root / "storage" / "index" / "lingji_memory.db")
        memory_db = MemoryDatabase(root / "storage" / "index" / "lingji_memory.db")
        messages = []
        offset = 0
        while True:
            page = read_model.list_messages(owner=True, limit=200, offset=offset)
            messages.extend(page["items"])
            if not page.get("next_offset"):
                break
            offset = int(page["next_offset"])
        documents = memory_db.list_documents(include_chunks=True)
        state_db = StateDatabase(root / "storage" / "state" / "lingji_state.db")
        corpus = load_corpus(CORPUS)
        labels = {item.fact_id for item in corpus} | {item.citation_id for item in corpus}
        for row in messages:
            metadata = row.get("metadata") or {}
            serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            assert not any(key.startswith("fixture_") for key in metadata)
            assert not labels.intersection(serialized.split('"'))
        for row in documents:
            relationships = row.get("relationships") or {}
            serialized = json.dumps(relationships, ensure_ascii=False, sort_keys=True)
            assert not any(key.startswith("fixture_") for key in relationships)
            assert not labels.intersection(serialized.split('"'))
        for event in state_db.recent_events(limit=100000):
            payload = json.loads(str(event.get("payload_json") or "{}"))
            metadata = payload.get("metadata") or {}
            serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            assert not any(key.startswith("fixture_") for key in metadata)
            assert not labels.intersection(serialized.split('"'))
    finally:
        for root in held_roots:
            real_rmtree(root, ignore_errors=True)
