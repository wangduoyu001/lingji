"""Frozen, deterministic quality contracts for automatic memory.

The evaluator consumes hand-authored evidence.  It does not call retrieval,
promotion, a model, or any production data source.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence as SequenceABC
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
        "fact_id", "topic_key", "source_id", "conversation_id", "message_id",
        "role", "content", "content_hash", "occurred_at", "lifecycle",
        "supersedes_fact_id", "authority", "project_id", "privacy",
        "agent_scope", "citation_id", "memory_kind", "risk",
    }
)
_QUESTION_KEYS = frozenset(
    {
        "question_id", "category", "query", "mode", "as_of",
        "expected_fact_ids", "forbidden_fact_ids", "expected_citation_ids",
        "requires_owner_review",
    }
)
_SECRET_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?key|authorization|bearer|password|passphrase|"
    r"private[_-]?key|secret|token|pem)",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"(?:-----BEGIN(?: [^-]+)? PRIVATE KEY-----|\bBearer\s+\S+|"
    r"\b(?:api[_-]?key|password|passphrase|secret|token)\s*[:=]\s*\S+|"
    r"\bsk-[A-Za-z0-9_-]{10,}|\bAKIA[0-9A-Z]{12,})",
    re.IGNORECASE,
)
_UNIX_ABSOLUTE = re.compile(r"(?:^|[\s\"'=:(])/(?:[A-Za-z0-9._-]+)(?:/|$)")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_ABSOLUTE = re.compile(r"^\\\\[^\\/]+[\\/][^\\/]+")
_WINDOWS_EMBEDDED = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
_UNC_EMBEDDED = re.compile(r"(?:^|[\s\"'=:(])\\\\[^\\/\s]+[\\/][^\\/\s]+")


class EvaluationInputError(ValueError):
    """Raised when fixture or measured evidence is malformed."""


@dataclass(frozen=True)
class CorpusRecord:
    fact_id: str
    topic_key: str
    source_id: str
    conversation_id: str
    message_id: str
    role: CorpusRole
    content: str
    content_hash: str
    occurred_at: str
    lifecycle: Lifecycle
    supersedes_fact_id: str | None
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
    as_of: str | None
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
    baseline_context_chars: int
    rendered_context_chars: int
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
            if not isinstance(value, Mapping):
                raise EvaluationInputError(f"JSONL line {line_number} is not an object")
            values.append(dict(value))
        return values
    values = []
    for index, value in enumerate(source):
        if not isinstance(value, Mapping):
            raise EvaluationInputError(f"row {index} is not an object")
        values.append(dict(value))
    return values


def _scan_sensitive(value: Any, *, location: str) -> None:
    if isinstance(value, str):
        if (
            _SECRET_VALUE.search(value)
            or _WINDOWS_ABSOLUTE.search(value)
            or _UNC_ABSOLUTE.search(value)
            or _WINDOWS_EMBEDDED.search(value)
            or _UNC_EMBEDDED.search(value)
        ):
            raise EvaluationInputError(f"secret-like or path-like content at {location}")
        if _UNIX_ABSOLUTE.search(value):
            raise EvaluationInputError(f"absolute path-like content at {location}")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise EvaluationInputError(f"non-string mapping key at {location}")
            if _SECRET_KEY.search(key):
                raise EvaluationInputError(f"secret-like key at {location}.{key}")
            _scan_sensitive(child, location=f"{location}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _scan_sensitive(child, location=f"{location}[{index}]")


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationInputError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: Any, field: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise EvaluationInputError(f"{field} must be a {'non-empty ' if not allow_empty else ''}JSON array")
    result = tuple(_required_string(item, f"{field}[]") for item in value)
    if len(set(result)) != len(result):
        raise EvaluationInputError(f"duplicate values in {field}")
    return result


def _validate_keys(value: Mapping[str, Any], expected: frozenset[str], kind: str) -> None:
    missing = expected - value.keys()
    extra = value.keys() - expected
    if missing or extra:
        raise EvaluationInputError(
            f"{kind} keys mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )


def _parse_corpus(value: Mapping[str, Any], index: int) -> CorpusRecord:
    _validate_keys(value, _CORPUS_KEYS, "corpus")
    _scan_sensitive(value, location=f"corpus[{index}]")
    role = value["role"]
    lifecycle = value["lifecycle"]
    if role not in {"user", "assistant", "system", "tool"}:
        raise EvaluationInputError(f"invalid corpus role at {index}")
    if lifecycle not in {"active", "superseded", "invalidated", "archived"}:
        raise EvaluationInputError(f"invalid corpus lifecycle at {index}")
    if value["supersedes_fact_id"] is not None and not isinstance(value["supersedes_fact_id"], str):
        raise EvaluationInputError(f"supersedes_fact_id must be string or null at {index}")
    return CorpusRecord(
        fact_id=_required_string(value["fact_id"], "fact_id"),
        topic_key=_required_string(value["topic_key"], "topic_key"),
        source_id=_required_string(value["source_id"], "source_id"),
        conversation_id=_required_string(value["conversation_id"], "conversation_id"),
        message_id=_required_string(value["message_id"], "message_id"),
        role=role,
        content=_required_string(value["content"], "content"),
        content_hash=_required_string(value["content_hash"], "content_hash"),
        occurred_at=_required_string(value["occurred_at"], "occurred_at"),
        lifecycle=lifecycle,
        supersedes_fact_id=value["supersedes_fact_id"],
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
    fact_ids = {record.fact_id for record in records}
    for record in records:
        if record.supersedes_fact_id is not None:
            if record.supersedes_fact_id not in fact_ids:
                raise EvaluationInputError(f"missing superseded fact for {record.fact_id}")
            if record.supersedes_fact_id == record.fact_id:
                raise EvaluationInputError(f"fact cannot supersede itself: {record.fact_id}")
    return records


def _parse_question(value: Mapping[str, Any], index: int) -> EvaluationQuestion:
    _validate_keys(value, _QUESTION_KEYS, "question")
    _scan_sensitive(value, location=f"question[{index}]")
    category = value["category"]
    mode = value["mode"]
    if category not in CATEGORY_COUNTS:
        raise EvaluationInputError(f"invalid question category at {index}")
    if mode not in {"current", "as_of", "history", "why"}:
        raise EvaluationInputError(f"invalid question mode at {index}")
    as_of = value["as_of"]
    if as_of is not None and (not isinstance(as_of, str) or not as_of.strip()):
        raise EvaluationInputError(f"as_of must be string or null at {index}")
    if mode != "current" and as_of is None:
        raise EvaluationInputError(f"non-current mode requires as_of at {index}")
    if not isinstance(value["requires_owner_review"], bool):
        raise EvaluationInputError(f"requires_owner_review must be boolean at {index}")
    expected = _string_tuple(value["expected_fact_ids"], "expected_fact_ids", allow_empty=True)
    forbidden = _string_tuple(value["forbidden_fact_ids"], "forbidden_fact_ids", allow_empty=False)
    citations = _string_tuple(value["expected_citation_ids"], "expected_citation_ids", allow_empty=True)
    if set(expected) & set(forbidden):
        raise EvaluationInputError(f"expected and forbidden IDs overlap at {index}")
    return EvaluationQuestion(
        question_id=_required_string(value["question_id"], "question_id"),
        category=category,
        query=_required_string(value["query"], "query"),
        mode=mode,
        as_of=as_of,
        expected_fact_ids=expected,
        forbidden_fact_ids=forbidden,
        expected_citation_ids=citations,
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
    if len(questions) == 100:
        actual_counts = {category: sum(q.category == category for q in questions) for category in CATEGORY_COUNTS}
        if actual_counts != CATEGORY_COUNTS:
            raise EvaluationInputError(f"question category counts mismatch: {actual_counts}")
    if corpus is None:
        return questions
    by_fact = {record.fact_id: record for record in corpus}
    by_citation = {record.citation_id: record for record in corpus}
    for question in questions:
        if not set(question.expected_fact_ids) <= by_fact.keys():
            raise EvaluationInputError(f"missing expected fact evidence for {question.question_id}")
        if not set(question.forbidden_fact_ids) <= by_fact.keys():
            raise EvaluationInputError(f"missing forbidden fact evidence for {question.question_id}")
        if not set(question.expected_citation_ids) <= by_citation.keys():
            raise EvaluationInputError(f"missing expected citation evidence for {question.question_id}")
        expected_facts = set(question.expected_fact_ids)
        for citation_id in question.expected_citation_ids:
            if by_citation[citation_id].fact_id not in expected_facts:
                raise EvaluationInputError(
                    f"citation {citation_id} does not belong to expected facts for {question.question_id}"
                )
    return questions


def _evidence_ids(value: Sequence[str], field: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, SequenceABC):
        raise EvaluationInputError(f"{field} must be a sequence of IDs")
    result = tuple(_required_string(item, f"{field}[]") for item in value)
    if len(set(result)) != len(result):
        label = "fact" if "fact" in field else "citation" if "citation" in field else field
        raise EvaluationInputError(f"duplicate {label}")
    return result


def score_question(
    question: EvaluationQuestion,
    corpus_by_fact: Mapping[str, CorpusRecord],
    recalled_fact_ids: Sequence[str],
    citation_ids: Sequence[str],
    *,
    context_chars: int,
) -> QuestionResult:
    if not isinstance(corpus_by_fact, Mapping):
        raise EvaluationInputError("corpus identity must be a mapping")
    if any(
        not isinstance(key, str)
        or not isinstance(value, CorpusRecord)
        or key != value.fact_id
        for key, value in corpus_by_fact.items()
    ):
        raise EvaluationInputError("corpus identity contains invalid record")
    by_fact = dict(corpus_by_fact)
    by_citation = {record.citation_id: record for record in by_fact.values()}
    recalled = _evidence_ids(recalled_fact_ids, "recalled_fact_ids")
    citations = _evidence_ids(citation_ids, "citation_ids")
    unknown_facts = set(recalled) - set(by_fact)
    if unknown_facts:
        raise EvaluationInputError(f"unknown fact evidence: {sorted(unknown_facts)}")
    forbidden = set(question.forbidden_fact_ids)
    if forbidden & set(recalled):
        raise EvaluationInputError(f"forbidden fact evidence: {sorted(forbidden & set(recalled))}")
    expected = set(question.expected_fact_ids)
    extras = set(recalled) - expected
    if extras:
        raise EvaluationInputError(f"extra fact evidence: {sorted(extras)}")
    unknown_citations = set(citations) - set(by_citation)
    if unknown_citations:
        raise EvaluationInputError(f"unknown citation evidence: {sorted(unknown_citations)}")
    expected_citations = set(question.expected_citation_ids)
    extra_citations = set(citations) - expected_citations
    if extra_citations:
        raise EvaluationInputError(f"extra citation evidence: {sorted(extra_citations)}")
    for citation_id in citations:
        if by_citation[citation_id].fact_id not in expected:
            raise EvaluationInputError(f"citation {citation_id} does not belong to expected facts")
    if not isinstance(context_chars, int) or isinstance(context_chars, bool) or context_chars < 0:
        raise EvaluationInputError("context_chars must be a non-negative integer")
    recalled_expected_count = len(set(recalled) & expected)
    correct_citation_count = len(set(citations) & expected_citations)
    failures: list[str] = []
    if recalled_expected_count != len(expected):
        failures.append("expected_fact_missing")
    if correct_citation_count != len(expected_citations):
        failures.append("citation_missing_or_incorrect")
    return QuestionResult(
        question_id=question.question_id,
        recalled_fact_ids=recalled,
        citation_ids=citations,
        expected_fact_count=len(expected),
        recalled_expected_count=recalled_expected_count,
        expected_citation_count=len(expected_citations),
        correct_citation_count=correct_citation_count,
        context_chars=context_chars,
        passed=not failures,
        failures=tuple(failures),
    )


def _raw_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EvaluationInputError(f"{field} must be a non-negative integer")
    return value


def _percentage(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvaluationInputError(f"{field} must be a strict numeric percentage")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 100:
        raise EvaluationInputError(f"{field} must be finite and between 0 and 100")
    return result


def _validate_pair(numerator: int, denominator: int, name: str) -> None:
    if denominator <= 0:
        raise EvaluationInputError(f"{name} denominator must be positive")
    if numerator > denominator:
        raise EvaluationInputError(f"{name} numerator exceeds denominator")


def _context_reduction(baseline: int, rendered: int) -> float:
    _raw_int(baseline, "baseline_context_chars")
    _raw_int(rendered, "rendered_context_chars")
    if baseline <= 0:
        raise EvaluationInputError("baseline_context_chars must be positive")
    if rendered > baseline:
        raise EvaluationInputError("rendered_context_chars exceeds baseline_context_chars")
    return (1 - rendered / baseline) * 100


def evaluate_run(
    corpus_by_fact: Mapping[str, CorpusRecord],
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
    baseline_context_chars: int,
    rendered_context_chars: int,
    mcp_successes: int,
    mcp_attempts: int,
    production_pollution: int = 0,
    owner_review_success: float | None = None,
    reboot_recovery: float | None = None,
    blocked_reasons: Sequence[str] = (),
) -> EvaluationReport:
    if len(questions) != 100 or len(results) != 100:
        raise EvaluationInputError("evaluation run must contain exactly 100 questions and results")
    if any(not isinstance(result, QuestionResult) for result in results):
        raise EvaluationInputError("evaluation result is not a QuestionResult")
    question_ids = [question.question_id for question in questions]
    result_ids = [result.question_id for result in results]
    if len(set(question_ids)) != 100 or len(set(result_ids)) != 100 or set(question_ids) != set(result_ids):
        raise EvaluationInputError("evaluation results have duplicate, missing, or unknown question IDs")
    by_question = {question.question_id: question for question in questions}
    ordered_results: list[QuestionResult] = []
    for result in results:
        if not isinstance(result, QuestionResult):
            raise EvaluationInputError("evaluation result is not a QuestionResult")
        question = by_question[result.question_id]
        recomputed = score_question(
            question,
            corpus_by_fact,
            result.recalled_fact_ids,
            result.citation_ids,
            context_chars=result.context_chars,
        )
        if result != recomputed:
            raise EvaluationInputError(f"result does not match recomputed evidence: {result.question_id}")
        ordered_results.append(result)
    counters = {
        "imported_messages": imported_messages,
        "expected_messages": expected_messages,
        "ordered_role_matches": ordered_role_matches,
        "expected_ordered_roles": expected_ordered_roles,
        "automatic_activation_correct": automatic_activation_correct,
        "automatic_activation_total": automatic_activation_total,
        "protected_false_promotions": protected_false_promotions,
        "stale_current_leaks": stale_current_leaks,
        "duplicate_records": duplicate_records,
        "mcp_successes": mcp_successes,
        "mcp_attempts": mcp_attempts,
        "production_pollution": production_pollution,
    }
    for name, value in counters.items():
        counters[name] = _raw_int(value, name)
    _validate_pair(imported_messages, expected_messages, "messages")
    _validate_pair(ordered_role_matches, expected_ordered_roles, "ordered roles")
    _validate_pair(automatic_activation_correct, automatic_activation_total, "automatic activation")
    _validate_pair(mcp_successes, mcp_attempts, "MCP")
    reduction = _context_reduction(baseline_context_chars, rendered_context_chars)
    if owner_review_success is not None:
        owner_review_success = _percentage(owner_review_success, "owner_review_success")
    if reboot_recovery is not None:
        reboot_recovery = _percentage(reboot_recovery, "reboot_recovery")
    valid_hits = sum(result.recalled_expected_count for result in ordered_results)
    valid_total = sum(result.expected_fact_count for result in ordered_results)
    citation_hits = sum(result.correct_citation_count for result in ordered_results)
    citation_total = sum(result.expected_citation_count for result in ordered_results)
    _validate_pair(valid_hits, valid_total, "valid facts")
    _validate_pair(citation_hits, citation_total, "citations")
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
        valid_fact_recall=100 * valid_hits / valid_total,
        citation_accuracy=100 * citation_hits / citation_total,
        automatic_activation_accuracy=100 * automatic_activation_correct / automatic_activation_total,
        protected_false_promotions=protected_false_promotions,
        stale_current_leaks=stale_current_leaks,
        duplicate_records=duplicate_records,
        baseline_context_chars=baseline_context_chars,
        rendered_context_chars=rendered_context_chars,
        context_reduction=reduction,
        mcp_successes=mcp_successes,
        mcp_attempts=mcp_attempts,
        mcp_success_rate=100 * mcp_successes / mcp_attempts,
        production_pollution=production_pollution,
        owner_review_success=owner_review_success,
        reboot_recovery=reboot_recovery,
        blocked_reasons=tuple(_required_string(reason, "blocked_reason") for reason in blocked_reasons),
    )


def _valid_report_counter(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _valid_report_percentage(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and 0 <= float(value) <= 100


def _ratio_matches(numerator: Any, denominator: Any, reported: Any) -> bool:
    return (
        _valid_report_counter(numerator)
        and _valid_report_counter(denominator)
        and denominator > 0
        and numerator <= denominator
        and _valid_report_percentage(reported)
        and math.isclose(float(reported), 100 * numerator / denominator, rel_tol=1e-9, abs_tol=1e-9)
    )


class AutomaticMemoryAcceptanceGate:
    """Deterministic PASS/FAIL/BLOCKED quality gate."""

    @staticmethod
    def evaluate(report: EvaluationReport) -> Literal["PASS", "FAIL", "BLOCKED"]:
        raw_fields = (
            "answered_questions", "imported_messages", "expected_messages",
            "ordered_role_matches", "expected_ordered_roles", "valid_fact_hits",
            "valid_fact_total", "citation_hits", "citation_total",
            "automatic_activation_correct", "automatic_activation_total",
            "protected_false_promotions", "stale_current_leaks", "duplicate_records",
            "baseline_context_chars", "rendered_context_chars", "mcp_successes",
            "mcp_attempts", "production_pollution",
        )
        if any(not _valid_report_counter(getattr(report, field, None)) for field in raw_fields):
            return "FAIL"
        percentage_fields = (
            "valid_fact_recall", "citation_accuracy", "automatic_activation_accuracy",
            "context_reduction", "mcp_success_rate",
        )
        if any(not _valid_report_percentage(getattr(report, field, None)) for field in percentage_fields):
            return "FAIL"
        if report.owner_review_success is not None and not _valid_report_percentage(report.owner_review_success):
            return "FAIL"
        if report.reboot_recovery is not None and not _valid_report_percentage(report.reboot_recovery):
            return "FAIL"
        measured_failure = (
            report.answered_questions != 100
            or report.expected_messages <= 0
            or report.imported_messages != report.expected_messages
            or report.expected_ordered_roles <= 0
            or report.ordered_role_matches != report.expected_ordered_roles
            or not _ratio_matches(report.valid_fact_hits, report.valid_fact_total, report.valid_fact_recall)
            or not _ratio_matches(report.citation_hits, report.citation_total, report.citation_accuracy)
            or not _ratio_matches(report.automatic_activation_correct, report.automatic_activation_total, report.automatic_activation_accuracy)
            or not _ratio_matches(report.mcp_successes, report.mcp_attempts, report.mcp_success_rate)
            or report.baseline_context_chars <= 0
            or report.rendered_context_chars > report.baseline_context_chars
            or not math.isclose(
                report.context_reduction,
                (1 - report.rendered_context_chars / report.baseline_context_chars) * 100,
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
            or report.valid_fact_recall < 90
            or report.citation_accuracy < 95
            or report.automatic_activation_accuracy < 95
            or report.mcp_success_rate < 95
            or report.context_reduction < 90
            or report.protected_false_promotions != 0
            or report.stale_current_leaks != 0
            or report.duplicate_records != 0
            or report.production_pollution != 0
            or (report.owner_review_success is not None and report.owner_review_success != 100)
            or (report.reboot_recovery is not None and report.reboot_recovery != 100)
        )
        if measured_failure:
            return "FAIL"
        if report.owner_review_success is None or report.reboot_recovery is None or report.blocked_reasons:
            return "BLOCKED"
        return "PASS"


AcceptanceGate = AutomaticMemoryAcceptanceGate
