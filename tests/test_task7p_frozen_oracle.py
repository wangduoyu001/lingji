from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.automatic_memory.quality_oracle import (
    CheckpointMismatch,
    FrozenFixtureError,
    FrozenQuestionOracle,
    QuestionCheckpointStore,
    ResultSchemaError,
    load_frozen_fixtures,
    observation_from_context_pack,
)
from src.automatic_memory.quality_evidence import CanonicalFunctionalEvidence
from src.automatic_memory.scale_benchmark import readiness_from_envelope


FIXTURES = Path(__file__).parent / "evaluation" / "fixtures"
CORPUS = FIXTURES / "automatic_memory_corpus.jsonl"
QUESTIONS = FIXTURES / "automatic_memory_questions.jsonl"


def _identity(question, fixture):
    record = fixture.corpus_by_fact[question.expected_fact_ids[0]]
    return {
        "fact_id": record.fact_id,
        "source_id": record.source_id,
        "conversation_id": record.conversation_id,
        "message_id": record.message_id,
        "content_hash": record.content_hash,
        "citation_id": record.citation_id,
    }


def _pack(question, fixture, *, identity=None, mode=None, used_chars=120):
    identity = identity or _identity(question, fixture)
    return {
        "identities": [identity],
        "citations": [identity["citation_id"]],
        "answer_atoms": list(question.expected_answer_atoms),
        "used_chars": used_chars,
        "query_mode": mode or question.mode,
        "as_of": question.as_of,
        "reason": "selected",
    }


def test_fixture_audit_freezes_sequence_answers_identities_mcp_and_budget():
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)

    assert len(fixture.corpus) == 145
    assert len(fixture.questions) == 100
    assert fixture.corpus[0].sequence == 0
    question = fixture.questions[0]
    assert question.expected_answer_atoms
    assert question.expected_source_ids == ("source-preference-001",)
    assert question.expected_message_ids == ("message-preference-001",)
    assert question.disallowed_source_ids
    assert question.disallowed_message_ids
    assert question.mcp_expectation == "strict_parity"
    assert question.max_chars == 4000


def test_offline_oracle_requires_complete_ordered_identity_and_counts_forbidden():
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    question = fixture.questions[0]
    oracle = FrozenQuestionOracle(fixture)
    identity = _identity(question, fixture)

    passed = oracle.evaluate(question, gateway=_pack(question, fixture), mcp=_pack(question, fixture))
    assert passed.passed is True
    assert passed.gateway_message_ids == question.expected_message_ids
    assert passed.mcp_message_ids == question.expected_message_ids
    assert passed.failure_buckets == ()

    wrong_order = dict(identity, message_id="message-preference-002")
    failed = oracle.evaluate(
        question,
        gateway=_pack(question, fixture, identity=wrong_order),
        mcp=_pack(question, fixture, identity=wrong_order),
    )
    assert failed.passed is False
    assert failed.failure_buckets == ("provenance",)

    forbidden = fixture.corpus_by_fact[question.forbidden_fact_ids[0]]
    forbidden_identity = {
        "fact_id": forbidden.fact_id,
        "source_id": forbidden.source_id,
        "conversation_id": forbidden.conversation_id,
        "message_id": forbidden.message_id,
        "content_hash": forbidden.content_hash,
        "citation_id": forbidden.citation_id,
    }
    false_positive = oracle.evaluate(
        question,
        gateway=_pack(question, fixture, identity=forbidden_identity),
        mcp=_pack(question, fixture, identity=forbidden_identity),
    )
    assert false_positive.false_positive_count == 1
    assert "retrieval" in false_positive.failure_buckets


def test_oracle_checks_citations_temporal_mode_and_hard_context_cap():
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    question = fixture.questions[90]
    oracle = FrozenQuestionOracle(fixture)
    pack = _pack(question, fixture)
    pack["citations"] = []
    pack["query_mode"] = "current"
    pack["used_chars"] = 12001
    result = oracle.evaluate(question, gateway=pack, mcp=pack)
    assert result.passed is False
    assert result.failure_buckets == ("provenance",)
    assert {"gateway_citation_mismatch", "gateway_temporal_mismatch", "gateway_context_budget_exceeded"} <= set(result.failures)
    assert result.gateway_reason == "selected"


def test_mcp_parity_failure_is_a_bucket_not_an_empty_success():
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    question = fixture.questions[0]
    oracle = FrozenQuestionOracle(fixture)
    gateway = _pack(question, fixture)
    mcp = dict(_pack(question, fixture), reason="mcp_parity:retrieval_empty")
    result = oracle.evaluate(question, gateway=gateway, mcp=mcp)
    assert result.passed is False
    assert result.failure_buckets == ("mcp",)
    assert result.failures == ("mcp_parity_retrieval_empty",)


def test_result_schema_rejects_missing_extra_and_unknown_fields():
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    question = fixture.questions[0]
    oracle = FrozenQuestionOracle(fixture)
    pack = _pack(question, fixture)
    pack.pop("reason")
    with pytest.raises(ResultSchemaError):
        oracle.evaluate(question, gateway=pack, mcp=_pack(question, fixture))
    extra = dict(_pack(question, fixture), unexpected="no")
    with pytest.raises(ResultSchemaError):
        oracle.evaluate(question, gateway=extra, mcp=_pack(question, fixture))

    malformed_as_of = _pack(question, fixture)
    malformed_as_of["as_of"] = 7
    with pytest.raises(ResultSchemaError):
        oracle.evaluate(question, gateway=malformed_as_of, mcp=_pack(question, fixture))


def test_checkpoint_writes_one_atomic_result_per_question_and_resumes(tmp_path: Path):
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    oracle = FrozenQuestionOracle(fixture)
    store = QuestionCheckpointStore(
        tmp_path / "checkpoints",
        fixture_hashes=fixture.file_hashes,
        run_id="oracle:test-run",
        code_commit="a" * 40,
    )
    calls: list[str] = []

    def invoke(question):
        calls.append(question.question_id)
        return _pack(question, fixture), _pack(question, fixture)

    first = oracle.run(fixture.questions[:2], invoke, checkpoint_store=store)
    assert len(first.results) == 2
    assert calls == ["question-001", "question-002"]
    assert sorted(path.name for path in (tmp_path / "checkpoints").glob("*.json")) == [
        "question-001.json",
        "question-002.json",
    ]
    second = oracle.run(fixture.questions[:2], invoke, checkpoint_store=store)
    assert len(second.results) == 2
    assert calls == ["question-001", "question-002"]


def test_checkpoint_rejects_stale_fixture_run_or_commit(tmp_path: Path):
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    oracle = FrozenQuestionOracle(fixture)
    store = QuestionCheckpointStore(
        tmp_path / "checkpoints",
        fixture_hashes=fixture.file_hashes,
        run_id="oracle:test-run",
        code_commit="a" * 40,
    )
    question = fixture.questions[0]
    result = oracle.evaluate(question, gateway=_pack(question, fixture), mcp=_pack(question, fixture))
    store.save(result)
    payload_path = tmp_path / "checkpoints" / "question-001.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["fixture_hashes"]["corpus"] = "0" * 64
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CheckpointMismatch):
        store.load(question.question_id)

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["fixture_hashes"] = dict(fixture.file_hashes)
    payload["result"]["question_id"] = "question-002"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CheckpointMismatch):
        store.load(question.question_id)


def test_frozen_fixture_hashes_are_stable_and_sensitive_to_metadata_change(tmp_path: Path):
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    assert fixture.file_hashes["corpus"] == hashlib.sha256(CORPUS.read_bytes()).hexdigest()
    assert fixture.file_hashes["questions"] == hashlib.sha256(QUESTIONS.read_bytes()).hexdigest()
    modified = tmp_path / "questions.jsonl"
    modified.write_bytes(QUESTIONS.read_bytes() + b"\n")
    with pytest.raises(FrozenFixtureError):
        load_frozen_fixtures(CORPUS, modified)


def _canonical_diagnostic(question_id="question-001", *, passed=True, buckets=(), failures=(), extra=False):
    result = {
        "schema_version": 1,
        "question_id": question_id,
        "category": "stable_preference",
        "mode": "current",
        "as_of": None,
        "gateway_identities": [],
        "mcp_identities": [],
        "gateway_used_chars": 0,
        "mcp_used_chars": 0,
        "gateway_mode": "current",
        "mcp_mode": "current",
        "gateway_as_of": None,
        "mcp_as_of": None,
        "gateway_reason": "selected",
        "mcp_reason": "selected",
        "false_positive_count": 0,
        "failure_buckets": list(buckets),
        "failures": list(failures),
        "passed": passed,
    }
    if extra:
        result["unexpected"] = True
    return result


def test_canonical_published_artifact_contains_one_nested_diagnostic_stream(tmp_path: Path):
    from src.automatic_memory import quality_gate

    with quality_gate.temporary_acceptance_roots(base_directory=tmp_path) as roots:
        envelope = quality_gate.run_quality_gate(
            CORPUS, QUESTIONS, output_path=roots.output_root / "quality.json", acceptance_roots=roots
        )
        payload = json.loads((roots.output_root / "quality.json").read_text(encoding="utf-8"))
    assert "question_diagnostics" not in payload
    assert "grouped_question_metrics" not in payload
    details = payload["evidence_details"]
    diagnostics = details["diagnostic_evidence"]
    assert len(diagnostics["question_diagnostics"]) == 100
    assert len(diagnostics["grouped_metrics"]) == 9
    canonical = CanonicalFunctionalEvidence.from_runner_payload(payload)
    assert len(canonical.data["diagnostic_evidence"]["question_diagnostics"]) == 100
    assert envelope.evidence_details["diagnostic_evidence"] == canonical.to_mapping()["diagnostic_evidence"]


def test_canonical_diagnostic_stream_rejects_duplicate_unknown_and_contradictory_rows():
    canonical = CanonicalFunctionalEvidence.complete_for_test().to_mapping()
    canonical["diagnostic_evidence"] = {
        "schema_version": 1,
        "question_diagnostics": [_canonical_diagnostic(), _canonical_diagnostic()],
        "grouped_metrics": {"stable_preference": {"questions": 2, "passed": 2, "failed": 0}},
    }
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(canonical)


def test_published_canonical_artifact_loads_scale_readiness(tmp_path: Path):
    payload = CanonicalFunctionalEvidence.complete_for_test().to_mapping()
    payload["quality_evidence_readiness"]["production_sentinel"] = "not_measured"
    payload["evidence_details"] = json.loads(json.dumps(payload))
    path = tmp_path / "canonical.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    readiness = readiness_from_envelope(path)
    assert readiness.scale_ready is True

    canonical = CanonicalFunctionalEvidence.complete_for_test().to_mapping()
    canonical["diagnostic_evidence"] = {
        "schema_version": 1,
        "question_diagnostics": [_canonical_diagnostic(extra=True)],
        "grouped_metrics": {},
    }
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(canonical)

    canonical = CanonicalFunctionalEvidence.complete_for_test().to_mapping()
    canonical["diagnostic_evidence"] = {
        "schema_version": 1,
        "question_diagnostics": [_canonical_diagnostic(passed=True, buckets=("retrieval",), failures=("missing",))],
        "grouped_metrics": {"stable_preference": {"questions": 1, "passed": 1, "failed": 0}},
    }
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(canonical)

    canonical = CanonicalFunctionalEvidence.complete_for_test().to_mapping()
    unknown = _canonical_diagnostic(question_id="question-999")
    canonical["diagnostic_evidence"] = {
        "schema_version": 1, "question_diagnostics": [unknown], "grouped_metrics": {},
    }
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(canonical)


def test_observation_requires_runtime_section_provenance_and_does_not_backfill_fixture_identity():
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    question = fixture.questions[0]
    pack = {
        "sections": [{"kind": "retrieved_memory", "memory_id": "runtime-memory", "text": question.expected_answer_atoms[0]}],
        "used_chars": 20,
        "query_mode": question.mode,
        "as_of": question.as_of,
        "diagnostics": {"reason_code": "selected"},
    }
    observed = observation_from_context_pack(pack, fixture, question.expected_fact_ids, question.expected_citation_ids)
    oracle = FrozenQuestionOracle(fixture)
    diagnostic = oracle.evaluate(question, gateway=observed, mcp=observed)
    assert diagnostic.failure_buckets == ("provenance",)
    assert "gateway_provenance_missing" in diagnostic.failures


def test_observation_maps_only_actual_runtime_identity_and_ignores_caller_citation_ids():
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    question = fixture.questions[0]
    record = fixture.corpus[0]
    runtime = {
        "source_id": "runtime-source-001",
        "conversation_id": "runtime-conversation-001",
        "message_id": "runtime-message-001",
        "content_hash": hashlib.sha256(record.content.encode("utf-8")).hexdigest(),
    }
    pack = {
        "sections": [{
            "kind": "raw_message_evidence",
            "memory_id": "runtime-memory",
            **runtime,
            "text": record.content,
            "citation": {
                "memory_id": "runtime-memory",
                **runtime,
            },
        }],
        "used_chars": len(record.content),
        "query_mode": question.mode,
        "as_of": question.as_of,
        "diagnostics": {"reason_code": "selected"},
    }
    observed = observation_from_context_pack(
        pack, fixture, ("caller-forged-fact",), ("caller-forged-citation",),
        runtime_bindings={
            (runtime["source_id"], runtime["conversation_id"], runtime["message_id"]): (
                record.fact_id, record.citation_id,
            )
        },
    )
    assert observed["identities"][0]["fact_id"] == record.fact_id
    assert observed["identities"][0]["source_id"] == runtime["source_id"]
    assert observed["citations"] == [record.citation_id]


def test_primary_bucket_is_mutually_exclusive_and_joint_false_positive_is_per_question():
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    question = fixture.questions[0]
    oracle = FrozenQuestionOracle(fixture)
    forbidden = fixture.corpus_by_fact[question.forbidden_fact_ids[0]]
    forbidden_identity = {
        "fact_id": forbidden.fact_id,
        "source_id": forbidden.source_id,
        "conversation_id": forbidden.conversation_id,
        "message_id": forbidden.message_id,
        "content_hash": forbidden.content_hash,
        "citation_id": forbidden.citation_id,
    }
    gateway = _pack(question, fixture)
    mcp = _pack(question, fixture, identity=forbidden_identity)
    result = oracle.evaluate(question, gateway=gateway, mcp=mcp)
    assert len(result.failure_buckets) == 1
    assert result.failure_buckets[0] == "retrieval"
    assert result.false_positive_count == 1


def test_checkpoint_revalidates_question_semantics_and_budget(tmp_path: Path):
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    store = QuestionCheckpointStore(
        tmp_path / "checkpoints", fixture_hashes=fixture.file_hashes,
        run_id="oracle:test-run", code_commit="a" * 40,
    )
    question = fixture.questions[0]
    oracle = FrozenQuestionOracle(fixture)
    result = oracle.evaluate(question, gateway=_pack(question, fixture), mcp=_pack(question, fixture))
    store.save(result)
    path = tmp_path / "checkpoints" / "question-001.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["result"]["gateway_used_chars"] = 12001
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CheckpointMismatch):
        store.load(question.question_id)

    result = oracle.evaluate(question, gateway=_pack(question, fixture), mcp=_pack(question, fixture))
    store.save(result, question=question)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["result"]["gateway_identities"][0]["source_id"] = "forged-runtime-source"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CheckpointMismatch):
        store.load(question.question_id, question=question)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["result"]["gateway_used_chars"] = 0
    payload["result"]["passed"] = True
    payload["result"]["failure_buckets"] = ["retrieval"]
    payload["result"]["failures"] = ["contradiction"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CheckpointMismatch):
        store.load(question.question_id)


def test_oracle_runner_loads_checkpoint_and_continues_after_question_exception(tmp_path: Path):
    fixture = load_frozen_fixtures(CORPUS, QUESTIONS)
    oracle = FrozenQuestionOracle(fixture)
    store = QuestionCheckpointStore(
        tmp_path / "checkpoints", fixture_hashes=fixture.file_hashes,
        run_id="oracle:test-run", code_commit="a" * 40,
    )
    calls = []

    def invoke(question):
        calls.append(question.question_id)
        if question.question_id == "question-002":
            raise RuntimeError("synthetic adapter failure")
        return _pack(question, fixture), _pack(question, fixture)

    first = oracle.run(fixture.questions[:3], invoke, checkpoint_store=store)
    assert len(first.results) == 3
    assert first.results[1].failure_buckets == ("fallback",)
    assert first.results[1].failures == ("gateway_exception", "mcp_exception")
    calls.clear()
    second = oracle.run(fixture.questions[:3], invoke, checkpoint_store=store)
    assert calls == []
    assert second.results == first.results
