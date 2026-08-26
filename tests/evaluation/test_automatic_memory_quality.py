from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.automatic_memory.evaluation import (
    CATEGORY_COUNTS,
    EvaluationInputError,
    evaluate_run,
    load_corpus,
    load_questions,
    score_question,
    QuestionResult,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_golden_fixtures_have_exactly_100_questions_and_frozen_categories() -> None:
    corpus = load_corpus(FIXTURE_DIR / "automatic_memory_corpus.jsonl")
    questions = load_questions(
        FIXTURE_DIR / "automatic_memory_questions.jsonl", corpus=corpus
    )

    assert len(corpus) == 100
    assert len(questions) == 100
    assert len({record.fact_id for record in corpus}) == 100
    assert len({question.question_id for question in questions}) == 100
    assert {
        category: sum(question.category == category for question in questions)
        for category in CATEGORY_COUNTS
    } == CATEGORY_COUNTS


def test_golden_questions_use_literal_corpus_and_citation_ids() -> None:
    corpus = load_corpus(FIXTURE_DIR / "automatic_memory_corpus.jsonl")
    questions = load_questions(
        FIXTURE_DIR / "automatic_memory_questions.jsonl", corpus=corpus
    )
    fact_ids = {record.fact_id for record in corpus}
    citation_ids = {record.citation_id for record in corpus}

    for question in questions:
        assert set(question.expected_fact_ids) <= fact_ids
        assert set(question.forbidden_fact_ids) <= fact_ids
        assert set(question.expected_citation_ids) <= citation_ids


def test_perfect_run_reports_raw_numerators_and_denominators() -> None:
    corpus = load_corpus(FIXTURE_DIR / "automatic_memory_corpus.jsonl")
    questions = load_questions(
        FIXTURE_DIR / "automatic_memory_questions.jsonl", corpus=corpus
    )
    results = [
        score_question(
            question,
            recalled_fact_ids=question.expected_fact_ids,
            citation_ids=question.expected_citation_ids,
            context_chars=100,
        )
        for question in questions
    ]

    report = evaluate_run(
        questions,
        results,
        imported_messages=100,
        expected_messages=100,
        ordered_role_matches=100,
        expected_ordered_roles=100,
        automatic_activation_correct=95,
        automatic_activation_total=100,
        protected_false_promotions=0,
        stale_current_leaks=0,
        duplicate_records=0,
        context_reduction=95,
        mcp_successes=95,
        mcp_attempts=100,
        production_pollution=0,
        owner_review_success=100,
        reboot_recovery=100,
    )

    assert report.answered_questions == 100
    assert report.valid_fact_hits == 100
    assert report.valid_fact_total == 100
    assert report.citation_hits == 100
    assert report.citation_total == 100
    assert report.valid_fact_recall == 100
    assert report.citation_accuracy == 100
    assert report.mcp_success_rate == 95


@pytest.mark.parametrize(
    "payload",
    [
        {"question_id": "q-duplicate", "category": "stable_preference"},
        {"question_id": "q-missing", "category": "not-a-category"},
    ],
)
def test_fixture_parser_rejects_duplicate_or_malformed_questions(payload: dict[str, str]) -> None:
    with pytest.raises(EvaluationInputError):
        load_questions([payload, payload])


def test_evaluator_rejects_incomplete_or_duplicate_runs() -> None:
    corpus = load_corpus(FIXTURE_DIR / "automatic_memory_corpus.jsonl")
    questions = load_questions(
        FIXTURE_DIR / "automatic_memory_questions.jsonl", corpus=corpus
    )
    result = score_question(
        questions[0],
        recalled_fact_ids=questions[0].expected_fact_ids,
        citation_ids=questions[0].expected_citation_ids,
        context_chars=100,
    )

    with pytest.raises(EvaluationInputError):
        evaluate_run(questions, [result] * 100, imported_messages=100, expected_messages=100,
                     ordered_role_matches=100, expected_ordered_roles=100,
                     automatic_activation_correct=100, automatic_activation_total=100,
                     context_reduction=100, mcp_successes=100, mcp_attempts=100)


def test_evaluator_rejects_result_counts_that_do_not_match_literal_expectations() -> None:
    corpus = load_corpus(FIXTURE_DIR / "automatic_memory_corpus.jsonl")
    questions = load_questions(
        FIXTURE_DIR / "automatic_memory_questions.jsonl", corpus=corpus
    )
    results = [
        score_question(
            question,
            recalled_fact_ids=question.expected_fact_ids,
            citation_ids=question.expected_citation_ids,
            context_chars=100,
        )
        for question in questions
    ]
    first = results[0]
    results[0] = QuestionResult(
        question_id=first.question_id,
        recalled_fact_ids=first.recalled_fact_ids,
        citation_ids=first.citation_ids,
        expected_fact_count=0,
        recalled_expected_count=first.recalled_expected_count,
        expected_citation_count=first.expected_citation_count,
        correct_citation_count=first.correct_citation_count,
        context_chars=first.context_chars,
        passed=first.passed,
        failures=first.failures,
    )
    with pytest.raises(EvaluationInputError):
        evaluate_run(questions, results, imported_messages=100, expected_messages=100,
                     ordered_role_matches=100, expected_ordered_roles=100,
                     automatic_activation_correct=100, automatic_activation_total=100,
                     context_reduction=100, mcp_successes=100, mcp_attempts=100)


def test_fixture_files_contain_no_absolute_paths_or_secret_like_values() -> None:
    for fixture in FIXTURE_DIR.glob("*.jsonl"):
        text = fixture.read_text(encoding="utf-8")
        assert not any(marker in text for marker in ("/Users/", "/home/", "C:\\\\", "sk-"))
        for line in text.splitlines():
            json.loads(line)


def test_corpus_parser_rejects_duplicate_ids_and_sensitive_values() -> None:
    record = {
        "fact_id": "fact-1",
        "source_id": "source-1",
        "conversation_id": "conversation-1",
        "message_id": "message-1",
        "role": "user",
        "content": "Synthetic content",
        "occurred_at": "2026-01-01T00:00:00Z",
        "lifecycle": "active",
        "authority": "synthetic-owner",
        "project_id": "project-synthetic",
        "privacy": "synthetic",
        "agent_scope": ["agent-synthetic"],
        "citation_id": "citation-1",
        "memory_kind": "stable_preference",
        "risk": "low",
    }
    with pytest.raises(EvaluationInputError):
        load_corpus([record, dict(record)])
    secret = dict(record, content="api_key=do-not-accept")
    with pytest.raises(EvaluationInputError):
        load_corpus([secret])
    path_like = dict(record, content="C:\\\\private\\\\record.json")
    with pytest.raises(EvaluationInputError):
        load_corpus([path_like])
