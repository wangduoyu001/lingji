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
)


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
    assert "retrieval" in failed.failure_buckets

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
    assert "provenance" in result.failure_buckets
    assert "temporal" in result.failure_buckets
    assert "context" in result.failure_buckets
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
