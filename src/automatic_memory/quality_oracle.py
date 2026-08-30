"""Deterministic, offline evidence oracle for the frozen automatic-memory set.

The oracle is deliberately independent of retrieval policy.  It validates the
immutable identities and answer contract emitted by the existing Gateway and
the production MCP registration, then records a bounded diagnostic result.
There is no text-similarity or model judge in this path.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .evaluation import CorpusRecord, EvaluationQuestion, load_corpus, load_questions


MAX_CONTEXT_CHARS = 12_000
_RESULT_KEYS = frozenset({
    "identities", "citations", "answer_atoms", "used_chars", "query_mode",
    "as_of", "reason",
})
_BUCKET_ORDER = ("import", "retrieval", "provenance", "temporal", "mcp", "fallback", "context")
_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class FrozenFixtureError(ValueError):
    """Frozen corpus/question evidence is missing or contradictory."""


class ResultSchemaError(ValueError):
    """A Gateway/MCP observation does not have the closed oracle shape."""


class CheckpointMismatch(ValueError):
    """A checkpoint belongs to another run, fixture, or code commit."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise FrozenFixtureError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: Any, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise FrozenFixtureError(f"{field} must be a sequence")
    values = tuple(_text(item, f"{field}[]") for item in value)
    if not allow_empty and not values:
        raise FrozenFixtureError(f"{field} must not be empty")
    if len(values) != len(set(values)):
        raise FrozenFixtureError(f"{field} contains duplicates")
    return values


def _result_text(value: Any, field: str) -> str:
    try:
        return _text(value, field)
    except FrozenFixtureError as exc:
        raise ResultSchemaError(str(exc)) from exc


def _hashes_comparable(left: str, right: str) -> bool:
    """Only compare content hashes that use the same representation."""
    return bool(_SHA256_RE.fullmatch(left) and _SHA256_RE.fullmatch(right)) or (
        not _SHA256_RE.fullmatch(left) and not _SHA256_RE.fullmatch(right)
    )


def _question_contract_hash(question: "FrozenQuestion") -> str:
    """Hash the complete frozen question, including its expected truth."""
    encoded = json.dumps(asdict(question), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FrozenCorpusRecord:
    """Immutable fixture row including all import-order evidence."""

    fact_id: str
    topic_key: str
    source_id: str
    conversation_id: str
    message_id: str
    role: str
    content: str
    content_hash: str
    occurred_at: str
    lifecycle: str
    supersedes_fact_id: str | None
    authority: str
    project_id: str
    privacy: str
    agent_scope: tuple[str, ...]
    citation_id: str
    memory_kind: str
    risk: str
    sequence: int

    @classmethod
    def from_record(cls, record: CorpusRecord) -> "FrozenCorpusRecord":
        return cls(
            fact_id=record.fact_id, topic_key=record.topic_key,
            source_id=record.source_id, conversation_id=record.conversation_id,
            message_id=record.message_id, role=record.role, content=record.content,
            content_hash=record.content_hash, occurred_at=record.occurred_at,
            lifecycle=record.lifecycle, supersedes_fact_id=record.supersedes_fact_id,
            authority=record.authority, project_id=record.project_id,
            privacy=record.privacy, agent_scope=tuple(record.agent_scope),
            citation_id=record.citation_id, memory_kind=record.memory_kind,
            risk=record.risk, sequence=record.sequence,
        )


@dataclass(frozen=True)
class FrozenQuestion:
    question_id: str
    category: str
    query: str
    mode: str
    as_of: str | None
    expected_fact_ids: tuple[str, ...]
    forbidden_fact_ids: tuple[str, ...]
    expected_citation_ids: tuple[str, ...]
    requires_owner_review: bool
    expected_source_ids: tuple[str, ...]
    expected_message_ids: tuple[str, ...]
    disallowed_source_ids: tuple[str, ...]
    disallowed_message_ids: tuple[str, ...]
    expected_answer_atoms: tuple[str, ...]
    negative_expectation: bool
    mcp_expectation: str
    max_chars: int

    @classmethod
    def from_question(cls, question: EvaluationQuestion) -> "FrozenQuestion":
        return cls(
            question_id=question.question_id, category=question.category,
            query=question.query, mode=question.mode, as_of=question.as_of,
            expected_fact_ids=tuple(question.expected_fact_ids),
            forbidden_fact_ids=tuple(question.forbidden_fact_ids),
            expected_citation_ids=tuple(question.expected_citation_ids),
            requires_owner_review=question.requires_owner_review,
            expected_source_ids=tuple(question.expected_source_ids),
            expected_message_ids=tuple(question.expected_message_ids),
            disallowed_source_ids=tuple(question.disallowed_source_ids),
            disallowed_message_ids=tuple(question.disallowed_message_ids),
            expected_answer_atoms=tuple(question.expected_answer_atoms),
            negative_expectation=question.negative_expectation,
            mcp_expectation=question.mcp_expectation,
            max_chars=question.max_chars,
        )


@dataclass(frozen=True)
class FrozenFixtures:
    corpus: tuple[FrozenCorpusRecord, ...]
    questions: tuple[FrozenQuestion, ...]
    file_hashes: Mapping[str, str]

    @property
    def corpus_by_fact(self) -> Mapping[str, FrozenCorpusRecord]:
        return {item.fact_id: item for item in self.corpus}


@dataclass(frozen=True)
class EvidenceIdentity:
    fact_id: str
    source_id: str
    conversation_id: str
    message_id: str
    content_hash: str
    citation_id: str

    @classmethod
    def from_mapping(cls, value: Any) -> "EvidenceIdentity":
        if not isinstance(value, Mapping):
            raise ResultSchemaError("identity must be a mapping")
        required = {"fact_id", "source_id", "conversation_id", "message_id", "content_hash", "citation_id"}
        if set(value) != required:
            raise ResultSchemaError("identity fields are not closed")
        return cls(*(_result_text(value[field], f"identity.{field}") for field in (
            "fact_id", "source_id", "conversation_id", "message_id", "content_hash", "citation_id"
        )))

    def to_mapping(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class QuestionDiagnostic:
    schema_version: int
    question_id: str
    category: str
    mode: str
    as_of: str | None
    gateway_identities: tuple[EvidenceIdentity, ...]
    mcp_identities: tuple[EvidenceIdentity, ...]
    gateway_used_chars: int
    mcp_used_chars: int
    gateway_mode: str
    mcp_mode: str
    gateway_as_of: str | None
    mcp_as_of: str | None
    gateway_reason: str
    mcp_reason: str
    false_positive_count: int
    failure_buckets: tuple[str, ...]
    failures: tuple[str, ...]
    passed: bool

    @property
    def gateway_fact_ids(self) -> tuple[str, ...]:
        return tuple(item.fact_id for item in self.gateway_identities)

    @property
    def mcp_fact_ids(self) -> tuple[str, ...]:
        return tuple(item.fact_id for item in self.mcp_identities)

    @property
    def gateway_source_ids(self) -> tuple[str, ...]:
        return tuple(item.source_id for item in self.gateway_identities)

    @property
    def mcp_source_ids(self) -> tuple[str, ...]:
        return tuple(item.source_id for item in self.mcp_identities)

    @property
    def gateway_message_ids(self) -> tuple[str, ...]:
        return tuple(item.message_id for item in self.gateway_identities)

    @property
    def mcp_message_ids(self) -> tuple[str, ...]:
        return tuple(item.message_id for item in self.mcp_identities)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "question_id": self.question_id,
            "category": self.category,
            "mode": self.mode,
            "as_of": self.as_of,
            "gateway_identities": [item.to_mapping() for item in self.gateway_identities],
            "mcp_identities": [item.to_mapping() for item in self.mcp_identities],
            "gateway_used_chars": self.gateway_used_chars,
            "mcp_used_chars": self.mcp_used_chars,
            "gateway_mode": self.gateway_mode,
            "mcp_mode": self.mcp_mode,
            "gateway_as_of": self.gateway_as_of,
            "mcp_as_of": self.mcp_as_of,
            "gateway_reason": self.gateway_reason,
            "mcp_reason": self.mcp_reason,
            "false_positive_count": self.false_positive_count,
            "failure_buckets": list(self.failure_buckets),
            "failures": list(self.failures),
            "passed": self.passed,
        }

    @classmethod
    def from_mapping(cls, value: Any) -> "QuestionDiagnostic":
        if not isinstance(value, Mapping):
            raise ResultSchemaError("diagnostic must be a mapping")
        required = {
            "schema_version", "question_id", "category", "mode", "as_of",
            "gateway_identities", "mcp_identities", "gateway_used_chars", "mcp_used_chars",
            "gateway_mode", "mcp_mode", "gateway_as_of", "mcp_as_of", "gateway_reason",
            "mcp_reason", "false_positive_count", "failure_buckets", "failures", "passed",
        }
        if set(value) != required:
            raise ResultSchemaError("diagnostic fields are not closed")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise ResultSchemaError("unsupported diagnostic schema")
        identities = {}
        for field in ("gateway_identities", "mcp_identities"):
            raw = value[field]
            if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
                raise ResultSchemaError(f"{field} must be a sequence")
            identities[field] = tuple(EvidenceIdentity.from_mapping(item) for item in raw)
            if len(identities[field]) != len(set(identities[field])):
                raise ResultSchemaError(f"{field} contains duplicate identities")
        ints = ("gateway_used_chars", "mcp_used_chars", "false_positive_count")
        if any(type(value[field]) is not int or value[field] < 0 for field in ints):
            raise ResultSchemaError("diagnostic counters are invalid")
        for field in ("question_id", "category", "mode", "gateway_mode", "mcp_mode", "gateway_reason", "mcp_reason"):
            _text(value[field], field)
        for field in ("as_of", "gateway_as_of", "mcp_as_of"):
            if value[field] is not None:
                _result_text(value[field], field)
        for field in ("failure_buckets", "failures"):
            _string_tuple(value[field], field)
        if any(bucket not in _BUCKET_ORDER for bucket in value["failure_buckets"]):
            raise ResultSchemaError("unknown failure bucket")
        if len(value["failure_buckets"]) > 1:
            raise ResultSchemaError("diagnostic must contain one primary failure bucket")
        if value["passed"] and (value["failure_buckets"] or value["failures"]):
            raise ResultSchemaError("passed diagnostic has failure details")
        if not value["passed"] and (not value["failure_buckets"] or not value["failures"]):
            raise ResultSchemaError("failed diagnostic lacks primary/detail failure")
        if value["gateway_used_chars"] > MAX_CONTEXT_CHARS or value["mcp_used_chars"] > MAX_CONTEXT_CHARS:
            raise ResultSchemaError("diagnostic context exceeds hard cap")
        if type(value["passed"]) is not bool:
            raise ResultSchemaError("passed must be boolean")
        return cls(
            schema_version=1, question_id=value["question_id"], category=value["category"],
            mode=value["mode"], as_of=value["as_of"],
            gateway_identities=identities["gateway_identities"], mcp_identities=identities["mcp_identities"],
            gateway_used_chars=value["gateway_used_chars"], mcp_used_chars=value["mcp_used_chars"],
            gateway_mode=value["gateway_mode"], mcp_mode=value["mcp_mode"],
            gateway_as_of=value["gateway_as_of"], mcp_as_of=value["mcp_as_of"],
            gateway_reason=value["gateway_reason"], mcp_reason=value["mcp_reason"],
            false_positive_count=value["false_positive_count"],
            failure_buckets=tuple(value["failure_buckets"]), failures=tuple(value["failures"]),
            passed=value["passed"],
        )


@dataclass(frozen=True)
class OracleRun:
    results: tuple[QuestionDiagnostic, ...]
    grouped_metrics: Mapping[str, Mapping[str, int]]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "results": [item.to_mapping() for item in self.results],
            "grouped_metrics": {key: dict(value) for key, value in self.grouped_metrics.items()},
        }


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_frozen_fixtures(corpus_path: str | Path, questions_path: str | Path) -> FrozenFixtures:
    corpus_path, questions_path = Path(corpus_path), Path(questions_path)
    try:
        corpus = tuple(FrozenCorpusRecord.from_record(item) for item in load_corpus(corpus_path))
        questions = tuple(FrozenQuestion.from_question(item) for item in load_questions(questions_path, corpus=corpus))
    except (OSError, ValueError, TypeError) as exc:
        raise FrozenFixtureError(str(exc)) from exc
    by_fact = {item.fact_id: item for item in corpus}
    if len(corpus) != 145 or len(questions) != 100:
        raise FrozenFixtureError("frozen fixture cardinality mismatch")
    for item in corpus:
        if not isinstance(item.sequence, int) or item.sequence < 0:
            raise FrozenFixtureError(f"invalid sequence for {item.fact_id}")
    for question in questions:
        if type(question.max_chars) is not int or question.max_chars <= 0 or question.max_chars > MAX_CONTEXT_CHARS:
            raise FrozenFixtureError(f"invalid question budget: {question.question_id}")
        if not question.expected_source_ids and not question.negative_expectation:
            raise FrozenFixtureError(f"missing expected source evidence: {question.question_id}")
        if len(question.expected_fact_ids) != len(question.expected_source_ids) or len(question.expected_fact_ids) != len(question.expected_message_ids):
            raise FrozenFixtureError(f"expected identity cardinality mismatch: {question.question_id}")
        for fact_id, source_id, message_id in zip(question.expected_fact_ids, question.expected_source_ids, question.expected_message_ids):
            record = by_fact.get(fact_id)
            if record is None or record.source_id != source_id or record.message_id != message_id:
                raise FrozenFixtureError(f"expected identity mismatch: {question.question_id}")
        if len(question.forbidden_fact_ids) != len(question.disallowed_source_ids) or len(question.forbidden_fact_ids) != len(question.disallowed_message_ids):
            raise FrozenFixtureError(f"disallowed identity cardinality mismatch: {question.question_id}")
        for fact_id, source_id, message_id in zip(question.forbidden_fact_ids, question.disallowed_source_ids, question.disallowed_message_ids):
            record = by_fact.get(fact_id)
            if record is None or record.source_id != source_id or record.message_id != message_id:
                raise FrozenFixtureError(f"disallowed identity mismatch: {question.question_id}")
        if bool(question.negative_expectation) != (not bool(question.expected_fact_ids)):
            raise FrozenFixtureError(f"negative expectation mismatch: {question.question_id}")
        if len(question.expected_answer_atoms) != len(question.expected_fact_ids):
            raise FrozenFixtureError(f"answer atom cardinality mismatch: {question.question_id}")
    return FrozenFixtures(
        corpus=corpus, questions=questions,
        file_hashes={"corpus": _hash(corpus_path), "questions": _hash(questions_path)},
    )


def _pack_observation(value: Any) -> dict[str, Any]:
    """Validate the small observation boundary used by the oracle.

    The quality runner adapts the production ContextPack into this shape.  The
    adapter is intentionally outside this function so no alternate retrieval
    path can be introduced here.
    """
    if not isinstance(value, Mapping) or set(value) != _RESULT_KEYS:
        raise ResultSchemaError("observation fields are not closed")
    if isinstance(value["identities"], (str, bytes)) or not isinstance(value["identities"], Sequence):
        raise ResultSchemaError("identities must be a sequence")
    identities = tuple(EvidenceIdentity.from_mapping(item) for item in value["identities"])
    if len(identities) != len(set(identities)):
        raise ResultSchemaError("duplicate identity")
    citations = _string_tuple(value["citations"], "citations")
    atoms = _string_tuple(value["answer_atoms"], "answer_atoms")
    used = value["used_chars"]
    if type(used) is not int or used < 0:
        raise ResultSchemaError("used_chars must be a non-negative integer")
    mode = _result_text(value["query_mode"], "query_mode")
    as_of = value["as_of"]
    if as_of is not None:
        _result_text(as_of, "as_of")
    reason = _result_text(value["reason"], "reason")
    return {
        "identities": identities, "citations": citations, "answer_atoms": atoms,
        "used_chars": used, "query_mode": mode, "as_of": as_of, "reason": reason,
    }


def observation_from_context_pack(
    pack: Mapping[str, Any],
    fixture: FrozenFixtures,
    fact_ids: Sequence[str],
    citation_ids: Sequence[str],
    *,
    reason_override: str | None = None,
    runtime_bindings: Mapping[tuple[str, str, str], tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Adapt a ContextPack using only identities present in its sections."""
    if not isinstance(pack, Mapping):
        raise ResultSchemaError("ContextPack must be a mapping")
    identities: list[dict[str, str]] = []
    sections = pack.get("sections")
    if isinstance(sections, (str, bytes)) or not isinstance(sections, Sequence):
        raise ResultSchemaError("ContextPack sections are malformed")
    # Caller selections are only a bounded filter. They are not provenance
    # and cannot supply a fact/citation identity when the runtime section does
    # not carry one.
    selected = {str(fact_id) for fact_id in fact_ids}
    fixture_bindings = {
        (record.source_id, record.conversation_id, record.message_id): (record.fact_id, record.citation_id)
        for record in fixture.corpus
    }
    bindings = runtime_bindings or fixture_bindings
    bound_facts = {binding[0] for binding in bindings.values()}
    selected_bound = selected & bound_facts
    require_provenance = bool(fact_ids)
    provenance_issue = False
    for section in sections:
        if not isinstance(section, Mapping):
            raise ResultSchemaError("ContextPack section is malformed")
        citation = section.get("citation") if isinstance(section.get("citation"), Mapping) else {}
        actual: dict[str, str] = {}
        for field in ("source_id", "conversation_id", "message_id", "content_hash"):
            values = []
            for source in (section, citation):
                candidate = source.get(field)
                if isinstance(candidate, str) and candidate.strip():
                    values.append(candidate.strip())
            if not values:
                provenance_issue = provenance_issue or require_provenance
                actual = {}
                break
            if len(set(values)) != 1:
                provenance_issue = True
                actual = {}
                break
            actual[field] = values[0]
        if not actual:
            continue
        binding = bindings.get((actual["source_id"], actual["conversation_id"], actual["message_id"]))
        if binding is None:
            provenance_issue = provenance_issue or require_provenance
            continue
        fact_id, citation_id = binding
        # Real runtime selections retain their selected subset. Unknown or
        # forged caller IDs do not erase actual runtime evidence.
        if selected_bound and fact_id not in selected_bound:
            continue
        identities.append({
            "fact_id": fact_id, "source_id": actual["source_id"],
            "conversation_id": actual["conversation_id"], "message_id": actual["message_id"],
            "content_hash": actual["content_hash"], "citation_id": citation_id,
        })
    answer_atoms = []
    for section in sections:
        text = section.get("text")
        if isinstance(text, str) and text.strip():
            answer_atoms.append(text.strip())
    used = pack.get("used_chars")
    if type(used) is not int:
        raise ResultSchemaError("ContextPack used_chars is not measured")
    return {
        "identities": identities,
        "citations": [identity["citation_id"] for identity in identities],
        "answer_atoms": answer_atoms,
        "used_chars": used,
        "query_mode": pack.get("query_mode", ""),
        "as_of": pack.get("as_of"),
        "reason": (
            f"{_text(reason_override, 'reason_override')}:provenance_missing"
            if reason_override is not None and provenance_issue
            else _text(reason_override, "reason_override")
            if reason_override is not None
            else "provenance:missing"
            if provenance_issue
            else str((pack.get("diagnostics") or {}).get("reason_code") or "selected")
        ),
    }


def _ordered_buckets(values: set[str]) -> tuple[str, ...]:
    return tuple(bucket for bucket in _BUCKET_ORDER if bucket in values)


def _primary_bucket(
    buckets: set[str], *, failures: Sequence[str], false_positive: bool,
) -> tuple[str, ...]:
    """Choose one counted bucket while retaining all reasons in ``failures``."""
    if false_positive and "retrieval" in buckets:
        return ("retrieval",)
    if any("provenance_missing" in failure for failure in failures) and "provenance" in buckets:
        return ("provenance",)
    return _ordered_buckets(buckets)[:1]


class FrozenQuestionOracle:
    """Score frozen questions from two already-executed production observations."""

    def __init__(
        self,
        fixture: FrozenFixtures,
        *,
        runtime_bindings: Mapping[tuple[str, str, str], tuple[str, str]] | None = None,
    ):
        self.fixture = fixture
        self._by_fact = fixture.corpus_by_fact
        self._runtime_bindings = dict(runtime_bindings or {})

    def _canonical_question(self, question: FrozenQuestion) -> FrozenQuestion:
        canonical = next((item for item in self.fixture.questions if item.question_id == question.question_id), None)
        if canonical is None:
            raise FrozenFixtureError(f"unknown question: {question.question_id}")
        if question != canonical:
            raise FrozenFixtureError(f"question truth mismatch: {question.question_id}")
        return canonical

    def evaluate(self, question: FrozenQuestion, *, gateway: Mapping[str, Any], mcp: Mapping[str, Any]) -> QuestionDiagnostic:
        question = self._canonical_question(question)
        gateway_value = _pack_observation(gateway)
        mcp_value = _pack_observation(mcp)
        buckets: set[str] = set()
        failures: list[str] = []

        def inspect(value: Mapping[str, Any], role: str) -> None:
            identities: tuple[EvidenceIdentity, ...] = value["identities"]
            facts = tuple(item.fact_id for item in identities)
            for identity in identities:
                expected = self._by_fact.get(identity.fact_id)
                if expected is None:
                    buckets.add("provenance"); failures.append(f"{role}_unknown_identity"); continue
                runtime_binding = self._runtime_bindings.get(
                    (identity.source_id, identity.conversation_id, identity.message_id)
                )
                if runtime_binding is None:
                    if (identity.source_id, identity.conversation_id, identity.message_id, identity.citation_id) != (
                        expected.source_id, expected.conversation_id, expected.message_id, expected.citation_id
                    ):
                        buckets.add("provenance"); failures.append(f"{role}_identity_mismatch")
                elif runtime_binding != (identity.fact_id, identity.citation_id):
                    buckets.add("provenance"); failures.append(f"{role}_runtime_identity_mismatch")
                if _hashes_comparable(identity.content_hash, expected.content_hash) and identity.content_hash != expected.content_hash:
                    buckets.add("provenance"); failures.append(f"{role}_content_hash_mismatch")
            if facts != question.expected_fact_ids:
                buckets.add("retrieval"); failures.append(f"{role}_identity_order_mismatch")
            forbidden = set(question.forbidden_fact_ids) | set(question.disallowed_source_ids) | set(question.disallowed_message_ids)
            false_positive = sum(1 for item in identities if item.fact_id in forbidden or item.source_id in forbidden or item.message_id in forbidden)
            if false_positive:
                failures.append(f"{role}_forbidden_evidence")
            if tuple(value["citations"]) != question.expected_citation_ids:
                buckets.add("provenance"); failures.append(f"{role}_citation_mismatch")
            if any(atom not in "\n".join(value["answer_atoms"]) for atom in question.expected_answer_atoms):
                buckets.add("retrieval"); failures.append(f"{role}_answer_atom_missing")
            if value["query_mode"] != question.mode or value["as_of"] != question.as_of:
                buckets.add("temporal"); failures.append(f"{role}_temporal_mismatch")
            if value["used_chars"] > MAX_CONTEXT_CHARS or value["used_chars"] > question.max_chars:
                buckets.add("context"); failures.append(f"{role}_context_budget_exceeded")
            if value["reason"].startswith(("exception:", "fallback:", "error:")):
                buckets.add("fallback"); failures.append(f"{role}_fallback")
            if value["reason"].startswith("provenance:") or ":provenance_missing" in value["reason"]:
                buckets.add("provenance"); failures.append(f"{role}_provenance_missing")
            if role == "mcp" and value["reason"].startswith("mcp_parity:"):
                buckets.add("mcp")
                failures.append(f"mcp_parity_{value['reason'].split(':', 1)[1]}")

        inspect(gateway_value, "gateway")
        inspect(mcp_value, "mcp")
        forbidden_facts = set(question.forbidden_fact_ids)
        forbidden_sources = set(question.disallowed_source_ids)
        forbidden_messages = set(question.disallowed_message_ids)
        false_positive = int(any(
            identity.fact_id in forbidden_facts
            or identity.source_id in forbidden_sources
            or identity.message_id in forbidden_messages
            for stream in (gateway_value["identities"], mcp_value["identities"])
            for identity in stream
        ))
        if false_positive:
            buckets.add("retrieval")
        if question.mcp_expectation == "strict_parity":
            if (
                gateway_value["identities"] != mcp_value["identities"]
                or gateway_value["used_chars"] != mcp_value["used_chars"]
                or gateway_value["query_mode"] != mcp_value["query_mode"]
                or gateway_value["as_of"] != mcp_value["as_of"]
            ):
                buckets.add("mcp"); failures.append("mcp_parity_mismatch")
        if gateway_value["query_mode"] != question.mode or mcp_value["query_mode"] != question.mode:
            buckets.add("temporal")
        return QuestionDiagnostic(
            schema_version=1, question_id=question.question_id, category=question.category,
            mode=question.mode, as_of=question.as_of,
            gateway_identities=gateway_value["identities"], mcp_identities=mcp_value["identities"],
            gateway_used_chars=gateway_value["used_chars"], mcp_used_chars=mcp_value["used_chars"],
            gateway_mode=gateway_value["query_mode"], mcp_mode=mcp_value["query_mode"],
            gateway_as_of=gateway_value["as_of"], mcp_as_of=mcp_value["as_of"],
            gateway_reason=gateway_value["reason"], mcp_reason=mcp_value["reason"],
            false_positive_count=false_positive,
            failure_buckets=_primary_bucket(buckets, failures=failures, false_positive=bool(false_positive)),
            failures=tuple(dict.fromkeys(failures)), passed=not buckets and not failures,
        )

    def exception_diagnostic(self, question: FrozenQuestion, exc: BaseException) -> QuestionDiagnostic:
        """Persist a bounded, stable diagnostic for an invocation failure."""
        question = self._canonical_question(question)
        reason = f"exception:{type(exc).__name__}"
        return QuestionDiagnostic(
            schema_version=1, question_id=question.question_id, category=question.category,
            mode=question.mode, as_of=question.as_of,
            gateway_identities=(), mcp_identities=(), gateway_used_chars=0, mcp_used_chars=0,
            gateway_mode=question.mode, mcp_mode=question.mode,
            gateway_as_of=question.as_of, mcp_as_of=question.as_of,
            gateway_reason=reason, mcp_reason=reason, false_positive_count=0,
            failure_buckets=("fallback",),
            failures=("gateway_exception", "mcp_exception"), passed=False,
        )

    def run(
        self,
        questions: Sequence[FrozenQuestion],
        invoke: Callable[[FrozenQuestion], tuple[Mapping[str, Any], Mapping[str, Any]]],
        *,
        checkpoint_store: "QuestionCheckpointStore | None" = None,
    ) -> OracleRun:
        if len({item.question_id for item in questions}) != len(tuple(questions)):
            raise FrozenFixtureError("duplicate question in run")
        results: list[QuestionDiagnostic] = []
        for question in questions:
            diagnostic = (
                checkpoint_store.load(question.question_id, question=question)
                if checkpoint_store else None
            )
            if diagnostic is None:
                try:
                    pair = invoke(question)
                    if not isinstance(pair, Sequence) or len(pair) != 2:
                        raise ResultSchemaError("invocation must return gateway and MCP observations")
                    diagnostic = self.evaluate(question, gateway=pair[0], mcp=pair[1])
                except Exception as exc:
                    diagnostic = self.exception_diagnostic(question, exc)
                if checkpoint_store:
                    checkpoint_store.save(diagnostic, question=question)
            results.append(diagnostic)
        grouped: dict[str, dict[str, int]] = {}
        for item in results:
            group = grouped.setdefault(item.category, {"questions": 0, "passed": 0, "failed": 0})
            group["questions"] += 1
            group["passed"] += int(item.passed)
            group["failed"] += int(not item.passed)
            for bucket in item.failure_buckets:
                group[bucket] = group.get(bucket, 0) + 1
        return OracleRun(tuple(results), grouped)


class QuestionCheckpointStore:
    """One atomic, identity-bound JSON result file per completed question."""

    def __init__(
        self,
        root: str | Path,
        *,
        fixture_hashes: Mapping[str, str],
        run_id: str,
        code_commit: str,
        questions: Sequence[FrozenQuestion] | Mapping[str, FrozenQuestion] | None = None,
    ):
        if set(fixture_hashes) != {"corpus", "questions"} or any(not isinstance(v, str) or len(v) != 64 for v in fixture_hashes.values()):
            raise CheckpointMismatch("invalid fixture identity")
        if not isinstance(run_id, str) or not run_id or not isinstance(code_commit, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", code_commit):
            raise CheckpointMismatch("invalid checkpoint identity")
        self.root = Path(root)
        self.fixture_hashes = dict(fixture_hashes)
        self.run_id = run_id
        self.code_commit = code_commit
        if isinstance(questions, Mapping):
            question_map = dict(questions)
        else:
            question_items = tuple(questions or ())
            question_map = {item.question_id: item for item in question_items}
            if len(question_map) != len(question_items):
                raise CheckpointMismatch("duplicate question identity")
        if any(not isinstance(item, FrozenQuestion) for item in question_map.values()):
            raise CheckpointMismatch("duplicate question identity")
        if any(key != item.question_id for key, item in question_map.items()):
            raise CheckpointMismatch("question map identity mismatch")
        self.questions = question_map

    def _path(self, question_id: str) -> Path:
        _text(question_id, "question_id")
        if not _ID_RE.fullmatch(question_id):
            raise CheckpointMismatch("unsafe question identity")
        return self.root / f"{question_id}.json"

    def _validate_question_result(self, question: FrozenQuestion, result: QuestionDiagnostic) -> None:
        if question.question_id != result.question_id:
            raise CheckpointMismatch("checkpoint question identity mismatch")
        if type(question.max_chars) is not int or question.max_chars <= 0 or question.max_chars > MAX_CONTEXT_CHARS:
            raise CheckpointMismatch("question budget exceeds hard cap")
        if result.gateway_used_chars > question.max_chars or result.mcp_used_chars > question.max_chars:
            raise CheckpointMismatch("checkpoint question budget exceeded")
        if (result.category, result.mode, result.as_of) != (question.category, question.mode, question.as_of):
            raise CheckpointMismatch("checkpoint question semantics mismatch")
        if result.gateway_mode != question.mode or result.mcp_mode != question.mode:
            raise CheckpointMismatch("checkpoint mode mismatch")
        if result.gateway_as_of != question.as_of or result.mcp_as_of != question.as_of:
            raise CheckpointMismatch("checkpoint as_of mismatch")
        if result.passed:
            expected_facts = question.expected_fact_ids
            expected_sources = question.expected_source_ids
            expected_messages = question.expected_message_ids
            expected_citations = question.expected_citation_ids
            for identities in (result.gateway_identities, result.mcp_identities):
                if tuple(item.fact_id for item in identities) != expected_facts:
                    raise CheckpointMismatch("passed checkpoint fact identity mismatch")
                if tuple(item.source_id for item in identities) != expected_sources:
                    raise CheckpointMismatch("passed checkpoint source identity mismatch")
                if tuple(item.message_id for item in identities) != expected_messages:
                    raise CheckpointMismatch("passed checkpoint message identity mismatch")
                if tuple(item.citation_id for item in identities) != expected_citations:
                    raise CheckpointMismatch("passed checkpoint citation identity mismatch")
    def save(self, result: QuestionDiagnostic, *, question: FrozenQuestion | None = None) -> None:
        if not isinstance(result, QuestionDiagnostic):
            raise ResultSchemaError("checkpoint requires QuestionDiagnostic")
        question = question or self.questions.get(result.question_id)
        if question is not None:
            self._validate_question_result(question, result)
        path = self._path(result.question_id)
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1, "run_id": self.run_id,
            "code_commit": self.code_commit, "fixture_hashes": self.fixture_hashes,
            "question_id": result.question_id,
            "question_contract_hash": _question_contract_hash(question) if question is not None else None,
            "result": result.to_mapping(),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fd, temporary = tempfile.mkstemp(prefix=f".{result.question_id}.", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)

    def load(self, question_id: str, *, question: FrozenQuestion | None = None) -> QuestionDiagnostic | None:
        path = self._path(question_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            required = {"schema_version", "run_id", "code_commit", "fixture_hashes", "question_id", "question_contract_hash", "result"}
            if not isinstance(payload, Mapping) or set(payload) != required:
                raise CheckpointMismatch("checkpoint fields are not closed")
            if payload["schema_version"] != 1 or payload["run_id"] != self.run_id or payload["code_commit"] != self.code_commit or payload["fixture_hashes"] != self.fixture_hashes or payload["question_id"] != question_id:
                raise CheckpointMismatch("checkpoint identity mismatch")
            result = QuestionDiagnostic.from_mapping(payload["result"])
            if result.question_id != question_id:
                raise CheckpointMismatch("checkpoint result identity mismatch")
            question = question or self.questions.get(question_id)
            contract_hash = payload["question_contract_hash"]
            if question is not None:
                self._validate_question_result(question, result)
                if contract_hash != _question_contract_hash(question):
                    raise CheckpointMismatch("checkpoint question truth mismatch")
            elif contract_hash is not None:
                if not isinstance(contract_hash, str) or not _SHA256_RE.fullmatch(contract_hash):
                    raise CheckpointMismatch("checkpoint question contract malformed")
            return result
        except CheckpointMismatch:
            raise
        except Exception as exc:
            raise CheckpointMismatch("checkpoint is malformed") from exc


__all__ = [
    "MAX_CONTEXT_CHARS", "FrozenFixtureError", "ResultSchemaError", "CheckpointMismatch",
    "FrozenCorpusRecord", "FrozenQuestion", "FrozenFixtures", "EvidenceIdentity",
    "QuestionDiagnostic", "OracleRun", "QuestionCheckpointStore", "FrozenQuestionOracle",
    "load_frozen_fixtures", "observation_from_context_pack",
]
