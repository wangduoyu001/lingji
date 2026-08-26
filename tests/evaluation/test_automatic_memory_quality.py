from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.automatic_memory.evaluation import (
    CATEGORY_COUNTS,
    EvaluationInputError,
    evaluate_run,
    load_corpus,
    load_questions,
    score_question,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixtures():
    corpus = load_corpus(FIXTURE_DIR / "automatic_memory_corpus.jsonl")
    questions = load_questions(
        FIXTURE_DIR / "automatic_memory_questions.jsonl", corpus=corpus
    )
    return corpus, questions


def _perfect_results(corpus, questions):
    by_fact = {record.fact_id: record for record in corpus}
    return [
        score_question(
            question,
            by_fact,
            question.expected_fact_ids,
            question.expected_citation_ids,
            context_chars=100,
        )
        for question in questions
    ]


def _run_kwargs() -> dict[str, object]:
    return {
        "imported_messages": 100,
        "expected_messages": 100,
        "ordered_role_matches": 100,
        "expected_ordered_roles": 100,
        "automatic_activation_correct": 100,
        "automatic_activation_total": 100,
        "protected_false_promotions": 0,
        "stale_current_leaks": 0,
        "duplicate_records": 0,
        "baseline_context_chars": 1000,
        "rendered_context_chars": 100,
        "mcp_successes": 100,
        "mcp_attempts": 100,
        "production_pollution": 0,
        "owner_review_success": 100,
        "reboot_recovery": 100,
    }


def test_golden_questions_are_exactly_100_and_semantically_distinct() -> None:
    corpus, questions = _fixtures()
    assert len(questions) == 100
    assert len(corpus) > 100
    assert len({question.question_id for question in questions}) == 100
    assert {
        category: sum(question.category == category for question in questions)
        for category in CATEGORY_COUNTS
    } == CATEGORY_COUNTS
    assert len({question.query for question in questions}) == 100
    assert all("Synthetic query" not in question.query for question in questions)
    assert all("Synthetic evaluation record" not in record.content for record in corpus)


def test_fixture_relationships_are_real_shapes_not_category_labels() -> None:
    corpus, questions = _fixtures()
    by_fact = {record.fact_id: record for record in corpus}

    superseded = [q for q in questions if q.category == "superseded_decision"]
    assert len(superseded) == 15
    for question in superseded:
        replacement = by_fact[question.expected_fact_ids[0]]
        old = by_fact[question.forbidden_fact_ids[0]]
        assert replacement.supersedes_fact_id == old.fact_id
        assert replacement.topic_key == old.topic_key
        assert old.lifecycle == "superseded"
        assert replacement.lifecycle == "active"

    temporal = [q for q in questions if q.category == "temporal_explanation"]
    assert {q.mode for q in temporal} == {"as_of", "history", "why"}
    assert all(q.as_of for q in temporal)
    assert all(
        by_fact[q.expected_fact_ids[0]].topic_key
        == by_fact[q.forbidden_fact_ids[0]].topic_key
        for q in temporal
    )

    conflicts = [q for q in questions if q.category == "authority_conflict"]
    assert len(conflicts) == 10
    assert all(
        by_fact[q.expected_fact_ids[0]].authority
        != by_fact[q.forbidden_fact_ids[0]].authority
        for q in conflicts
    )
    assert all(
        by_fact[q.expected_fact_ids[0]].risk == "medium"
        for q in conflicts
    )

    cross_session = [q for q in questions if q.category == "cross_session"]
    assert all(
        len({by_fact[fact_id].conversation_id for fact_id in q.expected_fact_ids}) >= 2
        for q in cross_session
    )

    scope_negative = [q for q in questions if q.category == "scope_negative"]
    assert all(not q.expected_fact_ids for q in scope_negative)
    assert {by_fact[q.forbidden_fact_ids[0]].project_id for q in scope_negative} >= {
        "project-private",
        "project-other",
    }
    assert {by_fact[q.forbidden_fact_ids[0]].privacy for q in scope_negative} >= {
        "restricted",
        "private",
    }
    assert len({by_fact[q.forbidden_fact_ids[0]].agent_scope[0] for q in scope_negative}) >= 2

    dedup = [q for q in questions if q.category == "context_dedup"]
    assert all(
        by_fact[q.expected_fact_ids[0]].content_hash
        == by_fact[q.forbidden_fact_ids[0]].content_hash
        for q in dedup
    )


def test_question_loader_requires_citations_to_belong_to_expected_facts() -> None:
    corpus = load_corpus(FIXTURE_DIR / "automatic_memory_corpus.jsonl")
    raw = [
        json.loads(line)
        for line in (FIXTURE_DIR / "automatic_memory_questions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    changed = copy.deepcopy(raw[0])
    changed["expected_citation_ids"] = ["citation-current-021"]
    with pytest.raises(EvaluationInputError, match="citation"):
        load_questions([changed], corpus=corpus)


def test_question_loader_rejects_duplicate_complete_questions() -> None:
    raw = [
        json.loads(line)
        for line in (FIXTURE_DIR / "automatic_memory_questions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    with pytest.raises(EvaluationInputError, match="duplicate question_id"):
        load_questions([copy.deepcopy(raw[0]), copy.deepcopy(raw[0])])


def test_score_question_rejects_unknown_duplicate_extra_forbidden_and_mismatched_evidence() -> None:
    corpus, questions = _fixtures()
    by_fact = {record.fact_id: record for record in corpus}
    question = next(q for q in questions if q.category == "stable_preference")
    expected_fact = question.expected_fact_ids[0]
    expected_citation = question.expected_citation_ids[0]

    with pytest.raises(EvaluationInputError, match="unknown fact"):
        score_question(question, by_fact, ("fact-does-not-exist",), (expected_citation,), context_chars=100)
    with pytest.raises(EvaluationInputError, match="duplicate fact"):
        score_question(question, by_fact, (expected_fact, expected_fact), (expected_citation,), context_chars=100)
    with pytest.raises(EvaluationInputError, match="extra fact"):
        score_question(question, by_fact, (expected_fact, "fact-current-022"), (expected_citation,), context_chars=100)
    with pytest.raises(EvaluationInputError, match="forbidden fact"):
        score_question(question, by_fact, (question.forbidden_fact_ids[0],), (expected_citation,), context_chars=100)
    with pytest.raises(EvaluationInputError, match="unknown citation"):
        score_question(question, by_fact, (expected_fact,), ("citation-nope",), context_chars=100)
    with pytest.raises(EvaluationInputError, match="duplicate citation"):
        score_question(question, by_fact, (expected_fact,), (expected_citation, expected_citation), context_chars=100)
    with pytest.raises(EvaluationInputError, match="extra citation"):
        score_question(question, by_fact, (expected_fact,), (expected_citation, "citation-current-021"), context_chars=100)
    with pytest.raises(EvaluationInputError):
        score_question(question, by_fact, (expected_fact,), ("citation-current-021",), context_chars=100)


def test_score_question_passing_result_contains_exact_hand_authored_sets() -> None:
    corpus, questions = _fixtures()
    by_fact = {record.fact_id: record for record in corpus}
    question = next(q for q in questions if q.category == "scope_negative")
    result = score_question(question, by_fact, (), (), context_chars=100)
    assert result.passed is True
    assert result.recalled_fact_ids == ()
    assert result.citation_ids == ()
    assert result.expected_fact_count == 0
    assert result.expected_citation_count == 0


def test_perfect_run_derives_context_reduction_from_raw_counts() -> None:
    corpus, questions = _fixtures()
    report = evaluate_run(questions, _perfect_results(corpus, questions), **_run_kwargs())
    assert report.baseline_context_chars == 1000
    assert report.rendered_context_chars == 100
    assert report.context_reduction == 90
    assert report.valid_fact_recall == 100
    assert report.citation_accuracy == 100
    assert report.mcp_success_rate == 100


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("baseline_context_chars", 0),
        ("rendered_context_chars", 1001),
        ("rendered_context_chars", -1),
        ("baseline_context_chars", 1000.0),
        ("rendered_context_chars", True),
    ],
)
def test_evaluate_run_rejects_forged_or_invalid_context_bounds(field: str, value: object) -> None:
    corpus, questions = _fixtures()
    kwargs = _run_kwargs()
    kwargs[field] = value
    with pytest.raises(EvaluationInputError):
        evaluate_run(questions, _perfect_results(corpus, questions), **kwargs)


def test_evaluate_run_rejects_incomplete_duplicate_or_inconsistent_results() -> None:
    corpus, questions = _fixtures()
    results = _perfect_results(corpus, questions)
    with pytest.raises(EvaluationInputError):
        evaluate_run(questions, results[:-1], **_run_kwargs())
    with pytest.raises(EvaluationInputError):
        evaluate_run(questions, [results[0]] * 100, **_run_kwargs())
    first = results[0]
    results[0] = replace(first, expected_fact_count=first.expected_fact_count + 1)
    with pytest.raises(EvaluationInputError):
        evaluate_run(questions, results, **_run_kwargs())


@pytest.mark.parametrize(
    "field,value",
    [
        ("imported_messages", True),
        ("expected_messages", 100.0),
        ("ordered_role_matches", -1),
        ("automatic_activation_correct", 101),
        ("mcp_successes", 101),
    ],
)
def test_evaluate_run_rejects_non_boolean_integer_or_illegal_raw_counters(field: str, value: object) -> None:
    corpus, questions = _fixtures()
    kwargs = _run_kwargs()
    kwargs[field] = value
    with pytest.raises(EvaluationInputError):
        evaluate_run(questions, _perfect_results(corpus, questions), **kwargs)


@pytest.mark.parametrize(
    "payload",
    [
        {"question_id": "question-001"},
        ["not", "a", "mapping"],
        "not-a-row",
    ],
)
def test_jsonl_loader_rejects_non_mapping_or_incomplete_rows(payload: object) -> None:
    with pytest.raises(EvaluationInputError):
        load_questions([payload])  # type: ignore[list-item]


def test_corpus_parser_rejects_duplicate_ids_and_nested_sensitive_values() -> None:
    record = {
        "fact_id": "fact-custom-001",
        "topic_key": "topic-custom-001",
        "source_id": "source-custom-001",
        "conversation_id": "conversation-custom-001",
        "message_id": "message-custom-001",
        "role": "user",
        "content": "A calm synthetic preference about paper notebooks.",
        "content_hash": "a" * 64,
        "occurred_at": "2026-01-01T00:00:00Z",
        "lifecycle": "active",
        "supersedes_fact_id": None,
        "authority": "owner",
        "project_id": "project-custom",
        "privacy": "synthetic",
        "agent_scope": ["agent-custom"],
        "citation_id": "citation-custom-001",
        "memory_kind": "stable_preference",
        "risk": "low",
    }
    with pytest.raises(EvaluationInputError):
        load_corpus([record, dict(record)])
    nested_secret = dict(record, content={"metadata": {"api_token": "redacted"}})
    with pytest.raises(EvaluationInputError):
        load_corpus([nested_secret])
    nested_path = dict(record, content={"metadata": {"backup": "\\\\server\\share\\vault"}})
    with pytest.raises(EvaluationInputError):
        load_corpus([nested_path])


@pytest.mark.parametrize(
    "value",
    [
        "/root/private/record.json",
        "/etc/lingji/settings",
        "/opt/local/archive",
        "/workspace/project/data",
        "C:\\Users\\owner\\notes.json",
        "\\\\server\\share\\notes.json",
        "-----BEGIN PRIVATE KEY-----",
        "Bearer redacted-value",
        "password=redacted",
        "token: redacted",
    ],
)
def test_corpus_parser_rejects_common_path_and_secret_shapes(value: str) -> None:
    record = {
        "fact_id": "fact-custom-002",
        "topic_key": "topic-custom-002",
        "source_id": "source-custom-002",
        "conversation_id": "conversation-custom-002",
        "message_id": "message-custom-002",
        "role": "user",
        "content": value,
        "content_hash": "b" * 64,
        "occurred_at": "2026-01-01T00:00:00Z",
        "lifecycle": "active",
        "supersedes_fact_id": None,
        "authority": "owner",
        "project_id": "project-custom",
        "privacy": "synthetic",
        "agent_scope": ["agent-custom"],
        "citation_id": "citation-custom-002",
        "memory_kind": "stable_preference",
        "risk": "low",
    }
    with pytest.raises(EvaluationInputError):
        load_corpus([record])
