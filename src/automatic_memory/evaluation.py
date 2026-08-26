"""Frozen, deterministic quality contracts for the automatic-memory phase.

This module deliberately knows nothing about retrieval, promotion, storage, or
models.  It validates hand-authored evidence and compares that evidence with
the literal expectations in the golden questions.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence


QuestionCategory = Literal[
    "stable_preference",
    "current_project_decision",
    "superseded_decision",
    "cross_session",
    "authority_conflict",
    "protected_candidate",
    "scope_negative",
    "temporal_explanation",
    "context_dedup",
]
QuestionMode = Literal["current", "as_of", "history", "why"]
CorpusRole = Literal["user", "assistant", "system", "tool"]
Lifecycle = Literal["active", "superseded", "invalidated", "archived"]

CATEGORY_COUNTS: dict[QuestionCategory, int] = {
    "stable_preference": 20,
    "current_project_decision": 20,
    "superseded_decision": 15,
    "cross_session": 10,
    "authority_conflict": 10,
    "protected_candidate": 10,
    "scope_negative": 5,
    "temporal_explanation": 5,
    "context_dedup": 5,
}

_CORPUS_KEYS = frozenset(
    {
        "fact_id",
        "source_id",
        "conversation_id",
        "message_id",
        "role",
        "content",
        "occurred_at",
        "lifecycle",
        "authority",
        "project_id",
        "privacy",
        "agent_scope",
        "citation_id",
        "memory_kind",
        "risk",
    }
)
_QUESTION_KEYS = frozenset(
    {
        "question_id",
        "category",
        "query",
        "mode",
        "expected_fact_ids",
        "forbidden_fact_ids",
        "expected_citation_ids",
        "requires_owner_review",
    }
)
_SECRET_OR_PATH = re.compile(
    r"(?:-----BEGIN|\bBearer\s+|\b(?:api[_-]?key|secret|password|token)\s*[:=]|"
    r"\bsk-[A-Za-z0-9_-]{10,}|\bAKIA[0-9A-Z]{12,}|"
    r"(?:[A-Za-z]:\\|/(?:Users|home|private|var|tmp)/))",
    re.IGNORECASE,
)


class EvaluationInputError(ValueError):
    """Raised when fixture or run evidence is malformed or incomplete."""


@dataclass(frozen=True)
class CorpusRecord:
    fact_id: str
    source_id: str
    conversation_id: str
    message_id: str
    role: CorpusRole
    content: str
    occurred_at: str
    lifecycle: Lifecycle
    authority: str
    project_id: str
    privacy: str
    agent_scope: tuple[str, ...]
    citation_id: str
    memory_kind: str
    risk: str


@dataclass(frozen=True)
class EvaluationQuestion:
    question_id: str
    category: QuestionCategory
    query: str
    mode: QuestionMode
    expected_fact_ids: tuple[str, ...]
    forbidden_fact_ids: tuple[str, ...]
    expected_citation_ids: tuple[str, ...]
    requires_owner_review: bool


@dataclass(frozen=True)
class QuestionResult:
    question_id: str
    recalled_fact_ids: tuple[str, ...]
    citation_ids: tuple[str, ...]
    expected_fact_count: int
    recalled_expected_count: int
    expected_citation_count: int
    correct_citation_count: int
    context_chars: int
    passed: bool
    failures: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationReport:
    answered_questions: int
    imported_messages: int
    expected_messages: int
    ordered_role_matches: int
    expected_ordered_roles: int
    valid_fact_hits: int
    valid_fact_total: int
    citation_hits: int
    citation_total: int
    automatic_activation_correct: int
    automatic_activation_total: int
    valid_fact_recall: float
    citation_accuracy: float
    automatic_activation_accuracy: float
    protected_false_promotions: int
    stale_current_leaks: int
    duplicate_records: int
    context_reduction: float
    mcp_successes: int
    mcp_attempts: int
    mcp_success_rate: float
    production_pollution: int
    owner_review_success: float | None
    reboot_recovery: float | None
    blocked_reasons: tuple[str, ...]


def _read_jsonl(source: str | Path | Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(source, (str, Path)):
        try:
            lines = Path(source).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise EvaluationInputError(f"cannot read fixture: {source}") from exc
        values: list[dict[str, Any]] = []
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                raise EvaluationInputError(f"blank JSONL line at {line_number}")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvaluationInputError(f"invalid JSONL at line {line_number}") from exc
            if not isinstance(value, dict):
                raise EvaluationInputError(f"JSONL line {line_number} is not an object")
            values.append(value)
        return values
    return [dict(value) for value in source]


def _scan_for_sensitive_text(value: Any, *, location: str) -> None:
    if isinstance(value, str):
        if _SECRET_OR_PATH.search(value):
            raise EvaluationInputError(f"secret-like or path-like content at {location}")
    elif isinstance(value, Mapping):
        for key, child in value.items():
            _scan_for_sensitive_text(child, location=f"{location}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _scan_for_sensitive_text(child, location=f"{location}[{index}]")


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationInputError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: Any, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise EvaluationInputError(f"{field} must be a non-empty JSON array")
    result = tuple(_required_string(item, f"{field}[]") for item in value)
    if len(set(result)) != len(result):
        raise EvaluationInputError(f"duplicate values in {field}")
    return result


def _validate_keys(value: Mapping[str, Any], expected: frozenset[str], kind: str) -> None:
    missing = expected - value.keys()
    extra = value.keys() - expected
    if missing or extra:
        raise EvaluationInputError(f"{kind} keys mismatch; missing={sorted(missing)}, extra={sorted(extra)}")


def _parse_corpus(value: Mapping[str, Any], index: int) -> CorpusRecord:
    _validate_keys(value, _CORPUS_KEYS, "corpus")
    _scan_for_sensitive_text(value, location=f"corpus[{index}]")
    role = value["role"]
    lifecycle = value["lifecycle"]
    if role not in {"user", "assistant", "system", "tool"}:
        raise EvaluationInputError(f"invalid corpus role at {index}")
    if lifecycle not in {"active", "superseded", "invalidated", "archived"}:
        raise EvaluationInputError(f"invalid corpus lifecycle at {index}")
    return CorpusRecord(
        fact_id=_required_string(value["fact_id"], "fact_id"),
        source_id=_required_string(value["source_id"], "source_id"),
        conversation_id=_required_string(value["conversation_id"], "conversation_id"),
        message_id=_required_string(value["message_id"], "message_id"),
        role=role,
        content=_required_string(value["content"], "content"),
        occurred_at=_required_string(value["occurred_at"], "occurred_at"),
        lifecycle=lifecycle,
        authority=_required_string(value["authority"], "authority"),
        project_id=_required_string(value["project_id"], "project_id"),
        privacy=_required_string(value["privacy"], "privacy"),
        agent_scope=_string_tuple(value["agent_scope"], "agent_scope", allow_empty=False),
        citation_id=_required_string(value["citation_id"], "citation_id"),
        memory_kind=_required_string(value["memory_kind"], "memory_kind"),
        risk=_required_string(value["risk"], "risk"),
    )


def load_corpus(source: str | Path | Sequence[Mapping[str, Any]]) -> tuple[CorpusRecord, ...]:
    records = tuple(_parse_corpus(value, index) for index, value in enumerate(_read_jsonl(source)))
    if len({record.fact_id for record in records}) != len(records):
        raise EvaluationInputError("duplicate corpus fact_id")
    if len({record.message_id for record in records}) != len(records):
        raise EvaluationInputError("duplicate corpus message_id")
    if len({record.citation_id for record in records}) != len(records):
        raise EvaluationInputError("duplicate corpus citation_id")
    return records


def _parse_question(value: Mapping[str, Any], index: int) -> EvaluationQuestion:
    _validate_keys(value, _QUESTION_KEYS, "question")
    _scan_for_sensitive_text(value, location=f"question[{index}]")
    category = value["category"]
    mode = value["mode"]
    if category not in CATEGORY_COUNTS:
        raise EvaluationInputError(f"invalid question category at {index}")
    if mode not in {"current", "as_of", "history", "why"}:
        raise EvaluationInputError(f"invalid question mode at {index}")
    if not isinstance(value["requires_owner_review"], bool):
        raise EvaluationInputError(f"requires_owner_review must be boolean at {index}")
    expected = _string_tuple(value["expected_fact_ids"], "expected_fact_ids", allow_empty=False)
    forbidden = _string_tuple(value["forbidden_fact_ids"], "forbidden_fact_ids", allow_empty=False)
    if set(expected) & set(forbidden):
        raise EvaluationInputError(f"expected and forbidden IDs overlap at {index}")
    return EvaluationQuestion(
        question_id=_required_string(value["question_id"], "question_id"),
        category=category,
        query=_required_string(value["query"], "query"),
        mode=mode,
        expected_fact_ids=expected,
        forbidden_fact_ids=forbidden,
        expected_citation_ids=_string_tuple(value["expected_citation_ids"], "expected_citation_ids", allow_empty=False),
        requires_owner_review=value["requires_owner_review"],
    )


def load_questions(
    source: str | Path | Sequence[Mapping[str, Any]],
    *,
    corpus: Sequence[CorpusRecord] | None = None,
) -> tuple[EvaluationQuestion, ...]:
    questions = tuple(_parse_question(value, index) for index, value in enumerate(_read_jsonl(source)))
    if len({question.question_id for question in questions}) != len(questions):
        raise EvaluationInputError("duplicate question_id")
    if corpus is not None:
        fact_ids = {record.fact_id for record in corpus}
        citation_ids = {record.citation_id for record in corpus}
        for question in questions:
            if not set(question.expected_fact_ids) <= fact_ids:
                raise EvaluationInputError(f"missing expected evidence for {question.question_id}")
            if not set(question.forbidden_fact_ids) <= fact_ids:
                raise EvaluationInputError(f"missing forbidden evidence for {question.question_id}")
            if not set(question.expected_citation_ids) <= citation_ids:
                raise EvaluationInputError(f"missing citation evidence for {question.question_id}")
    return questions


def score_question(
    question: EvaluationQuestion,
    *,
    recalled_fact_ids: Sequence[str],
    citation_ids: Sequence[str],
    context_chars: int,
) -> QuestionResult:
    recalled = tuple(recalled_fact_ids)
    citations = tuple(citation_ids)
    if len(set(recalled)) != len(recalled) or len(set(citations)) != len(citations):
        raise EvaluationInputError(f"duplicate evidence in {question.question_id}")
    if not isinstance(context_chars, int) or isinstance(context_chars, bool) or context_chars < 0:
        raise EvaluationInputError(f"invalid context length in {question.question_id}")
    expected = set(question.expected_fact_ids)
    expected_citations = set(question.expected_citation_ids)
    recalled_expected = len(expected & set(recalled))
    correct_citations = len(expected_citations & set(citations))
    failures: list[str] = []
    if set(recalled) & set(question.forbidden_fact_ids):
        failures.append("forbidden_fact_recalled")
    if recalled_expected != len(expected):
        failures.append("expected_fact_missing")
    if correct_citations != len(expected_citations):
        failures.append("citation_missing_or_incorrect")
    return QuestionResult(
        question_id=question.question_id,
        recalled_fact_ids=recalled,
        citation_ids=citations,
        expected_fact_count=len(expected),
        recalled_expected_count=recalled_expected,
        expected_citation_count=len(expected_citations),
        correct_citation_count=correct_citations,
        context_chars=context_chars,
        passed=not failures,
        failures=tuple(failures),
    )


def _nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EvaluationInputError(f"{field} must be a non-negative integer")
    return value


def _finite_number(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise EvaluationInputError(f"{field} must be finite")
    return float(value)


def evaluate_run(
    questions: Sequence[EvaluationQuestion],
    results: Sequence[QuestionResult],
    *,
    imported_messages: int,
    expected_messages: int,
    ordered_role_matches: int,
    expected_ordered_roles: int,
    automatic_activation_correct: int,
    automatic_activation_total: int,
    protected_false_promotions: int = 0,
    stale_current_leaks: int = 0,
    duplicate_records: int = 0,
    context_reduction: float,
    mcp_successes: int,
    mcp_attempts: int,
    production_pollution: int = 0,
    owner_review_success: float | None = None,
    reboot_recovery: float | None = None,
    blocked_reasons: Sequence[str] = (),
) -> EvaluationReport:
    if len(questions) != 100:
        raise EvaluationInputError("evaluation run must contain exactly 100 questions")
    question_ids = [question.question_id for question in questions]
    result_ids = [result.question_id for result in results]
    if len(set(question_ids)) != 100 or len(results) != 100 or len(set(result_ids)) != 100:
        raise EvaluationInputError("evaluation run has duplicate or incomplete question IDs")
    if set(question_ids) != set(result_ids):
        raise EvaluationInputError("evaluation results do not match the 100 questions")
    question_by_id = {question.question_id: question for question in questions}
    for result in results:
        question = question_by_id[result.question_id]
        _scan_for_sensitive_text(result.recalled_fact_ids, location=f"result[{result.question_id}].facts")
        _scan_for_sensitive_text(result.citation_ids, location=f"result[{result.question_id}].citations")
        expected_result = score_question(
            question,
            recalled_fact_ids=result.recalled_fact_ids,
            citation_ids=result.citation_ids,
            context_chars=result.context_chars,
        )
        if result != expected_result:
            raise EvaluationInputError(f"result evidence is inconsistent for {result.question_id}")
    for name, value in (
        ("imported_messages", imported_messages),
        ("expected_messages", expected_messages),
        ("ordered_role_matches", ordered_role_matches),
        ("expected_ordered_roles", expected_ordered_roles),
        ("automatic_activation_correct", automatic_activation_correct),
        ("automatic_activation_total", automatic_activation_total),
        ("protected_false_promotions", protected_false_promotions),
        ("stale_current_leaks", stale_current_leaks),
        ("duplicate_records", duplicate_records),
        ("mcp_successes", mcp_successes),
        ("mcp_attempts", mcp_attempts),
        ("production_pollution", production_pollution),
    ):
        _nonnegative_int(value, name)
    if owner_review_success is not None:
        _finite_number(owner_review_success, "owner_review_success")
    if reboot_recovery is not None:
        _finite_number(reboot_recovery, "reboot_recovery")
    reduction = _finite_number(context_reduction, "context_reduction")
    by_id = {result.question_id: result for result in results}
    ordered_results = [by_id[question.question_id] for question in questions]
    valid_hits = sum(result.recalled_expected_count for result in ordered_results)
    valid_total = sum(result.expected_fact_count for result in ordered_results)
    citation_hits = sum(result.correct_citation_count for result in ordered_results)
    citation_total = sum(result.expected_citation_count for result in ordered_results)
    valid_recall = 100.0 * valid_hits / valid_total if valid_total else math.nan
    citation_accuracy = 100.0 * citation_hits / citation_total if citation_total else math.nan
    activation_accuracy = (
        100.0 * automatic_activation_correct / automatic_activation_total
        if automatic_activation_total
        else math.nan
    )
    mcp_rate = 100.0 * mcp_successes / mcp_attempts if mcp_attempts else math.nan
    return EvaluationReport(
        answered_questions=100,
        imported_messages=imported_messages,
        expected_messages=expected_messages,
        ordered_role_matches=ordered_role_matches,
        expected_ordered_roles=expected_ordered_roles,
        valid_fact_hits=valid_hits,
        valid_fact_total=valid_total,
        citation_hits=citation_hits,
        citation_total=citation_total,
        automatic_activation_correct=automatic_activation_correct,
        automatic_activation_total=automatic_activation_total,
        valid_fact_recall=valid_recall,
        citation_accuracy=citation_accuracy,
        automatic_activation_accuracy=activation_accuracy,
        protected_false_promotions=protected_false_promotions,
        stale_current_leaks=stale_current_leaks,
        duplicate_records=duplicate_records,
        context_reduction=reduction,
        mcp_successes=mcp_successes,
        mcp_attempts=mcp_attempts,
        mcp_success_rate=mcp_rate,
        production_pollution=production_pollution,
        owner_review_success=owner_review_success,
        reboot_recovery=reboot_recovery,
        blocked_reasons=tuple(_required_string(reason, "blocked_reason") for reason in blocked_reasons),
    )


def _ratio_matches(numerator: int, denominator: int, reported: float) -> bool:
    return denominator > 0 and math.isfinite(reported) and math.isclose(
        reported, 100.0 * numerator / denominator, rel_tol=1e-9, abs_tol=1e-9
    )


class AutomaticMemoryAcceptanceGate:
    """Deterministic PASS/FAIL/BLOCKED ordering for a measured report."""

    @staticmethod
    def evaluate(report: EvaluationReport) -> Literal["PASS", "FAIL", "BLOCKED"]:
        numeric_fields = (
            "valid_fact_recall",
            "citation_accuracy",
            "automatic_activation_accuracy",
            "context_reduction",
            "mcp_success_rate",
        )
        if any(
            not isinstance(getattr(report, field), (int, float))
            or isinstance(getattr(report, field), bool)
            or not math.isfinite(float(getattr(report, field)))
            for field in numeric_fields
        ):
            return "FAIL"
        measured_failure = (
            report.answered_questions != 100
            or report.expected_messages <= 0
            or report.imported_messages != report.expected_messages
            or report.expected_ordered_roles <= 0
            or report.ordered_role_matches != report.expected_ordered_roles
            or report.valid_fact_total <= 0
            or report.valid_fact_hits < 0
            or report.valid_fact_hits > report.valid_fact_total
            or report.citation_total <= 0
            or report.citation_hits < 0
            or report.citation_hits > report.citation_total
            or report.automatic_activation_total <= 0
            or report.automatic_activation_correct < 0
            or report.automatic_activation_correct > report.automatic_activation_total
            or report.mcp_attempts <= 0
            or report.mcp_successes < 0
            or report.mcp_successes > report.mcp_attempts
            or not _ratio_matches(report.valid_fact_hits, report.valid_fact_total, report.valid_fact_recall)
            or not _ratio_matches(report.citation_hits, report.citation_total, report.citation_accuracy)
            or not _ratio_matches(
                report.automatic_activation_correct,
                report.automatic_activation_total,
                report.automatic_activation_accuracy,
            )
            or not _ratio_matches(report.mcp_successes, report.mcp_attempts, report.mcp_success_rate)
            or report.valid_fact_recall < 90.0
            or report.citation_accuracy < 95.0
            or report.automatic_activation_accuracy < 95.0
            or report.mcp_success_rate < 95.0
            or report.context_reduction < 90.0
            or report.protected_false_promotions != 0
            or report.stale_current_leaks != 0
            or report.duplicate_records != 0
            or report.production_pollution != 0
            or (report.owner_review_success is not None and report.owner_review_success != 100.0)
            or (report.reboot_recovery is not None and report.reboot_recovery != 100.0)
        )
        if measured_failure:
            return "FAIL"
        if report.owner_review_success is None or report.reboot_recovery is None or report.blocked_reasons:
            return "BLOCKED"
        return "PASS"


AcceptanceGate = AutomaticMemoryAcceptanceGate
