"""Typed, expectation-blind identity registry for ContextPack evidence."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal, Mapping, Sequence, Union

from src.sources.read_model import SourceReadModel


@dataclass(frozen=True)
class MessageIdentity:
    source_id: str
    conversation_id: str
    message_id: str
    content_hash: str
    memory_id: str


@dataclass(frozen=True)
class EvaluationIdentityRegistry:
    memory_to_fact: Mapping[str, str]
    message_to_fact_citation: Mapping[MessageIdentity, tuple[str, str]]


@dataclass(frozen=True)
class MemorySectionIdentity:
    kind: Literal["core_memory", "retrieved_memory", "project_authority_memory"]
    memory_id: str


@dataclass(frozen=True)
class RawMessageSectionIdentity:
    kind: Literal["raw_message_evidence"]
    source_id: str
    conversation_id: str
    message_id: str
    content_hash: str
    memory_id: str


SectionIdentity = Union[MemorySectionIdentity, RawMessageSectionIdentity]


@dataclass(frozen=True)
class SelectedEvidence:
    fact_ids: tuple[str, ...]
    citation_ids: tuple[str, ...]
    stable_identities: tuple[SectionIdentity, ...]


class EvidenceIdentityError(ValueError):
    """Raised when evidence identity is absent, unknown, duplicated or contradictory."""


_MEMORY_KINDS = frozenset(("core_memory", "retrieved_memory", "project_authority_memory"))
_RAW_KIND = "raw_message_evidence"
_KINDS = _MEMORY_KINDS | {_RAW_KIND}


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceIdentityError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise EvidenceIdentityError(f"{field} must not contain surrounding whitespace")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceIdentityError(f"{label} must be a mapping")
    return value


def _corpus_field(record: Any, field: str) -> str:
    return _string(getattr(record, field, None), f"corpus.{field}")


def _row_field(row: Mapping[str, Any], field: str) -> str:
    return _string(row.get(field), f"persisted_messages.{field}")


def _corpus_binding_key(record: Any) -> tuple[str, str, str]:
    return (_corpus_field(record, "source_id"), _corpus_field(record, "conversation_id"), _corpus_field(record, "message_id"))


def _row_keys(row: Mapping[str, Any]) -> tuple[tuple[str, str, str], ...]:
    """Return explicit composite keys; never infer an identity from a suffix."""
    keys: list[tuple[str, str, str]] = []
    def strict(fields: tuple[str, str, str], label: str) -> tuple[str, str, str] | None:
        values = tuple(row.get(field) for field in fields)
        if not any(value is not None for value in values):
            return None
        if not all(isinstance(value, str) and value and value == value.strip() for value in values):
            raise EvidenceIdentityError(f"{label} composite identity must contain three exact strings")
        return values  # type: ignore[return-value]

    for fields, label in (
        (("source_id", "conversation_id", "message_id"), "internal"),
        (("source_external_id", "conversation_external_id", "message_external_id"), "external"),
        (("corpus_source_id", "corpus_conversation_id", "corpus_message_id"), "corpus"),
    ):
        value = strict(fields, label)
        if value is not None:
            keys.append(value)
    return tuple(dict.fromkeys(keys))


def build_identity_registry(
    *,
    corpus: Sequence[Any],
    persisted_messages: Sequence[Mapping[str, Any]],
    promotion_bindings: Mapping[str, str],
    message_links: Sequence[Mapping[str, Any]],
) -> EvaluationIdentityRegistry:
    """Build an immutable map from real persisted identities to evaluation labels."""
    if isinstance(corpus, (str, bytes)) or not isinstance(corpus, Sequence):
        raise EvidenceIdentityError("corpus must be a sequence")
    if isinstance(persisted_messages, (str, bytes)) or not isinstance(persisted_messages, Sequence):
        raise EvidenceIdentityError("persisted_messages must be a sequence")
    if not isinstance(promotion_bindings, Mapping):
        raise EvidenceIdentityError("promotion_bindings must be a mapping")
    if isinstance(message_links, (str, bytes)) or not isinstance(message_links, Sequence):
        raise EvidenceIdentityError("message_links must be a sequence")

    corpus_by_key: dict[tuple[str, str, str], tuple[str, str]] = {}
    facts: set[str] = set()
    citations: set[str] = set()
    for record in corpus:
        fact_id = _corpus_field(record, "fact_id")
        citation_id = _corpus_field(record, "citation_id")
        if fact_id in facts or citation_id in citations:
            raise EvidenceIdentityError("duplicate corpus fact or citation identity")
        facts.add(fact_id)
        citations.add(citation_id)
        key = _corpus_binding_key(record)
        if key in corpus_by_key:
            raise EvidenceIdentityError("duplicate corpus composite identity")
        corpus_by_key[key] = (fact_id, citation_id)

    memory_to_fact: dict[str, str] = {}
    bound_facts: set[str] = set()
    for memory_id, fact_id in promotion_bindings.items():
        memory = _string(memory_id, "promotion memory_id")
        fact = _string(fact_id, "promotion fact_id")
        if fact not in facts:
            raise EvidenceIdentityError(f"unknown promotion fact: {fact}")
        if memory in memory_to_fact and memory_to_fact[memory] != fact:
            raise EvidenceIdentityError(f"conflicting promotion binding: {memory}")
        if memory in memory_to_fact or fact in bound_facts:
            raise EvidenceIdentityError("duplicate promotion binding")
        memory_to_fact[memory] = fact
        bound_facts.add(fact)

    rows_by_message: dict[str, Mapping[str, Any]] = {}
    rows_by_key: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for raw_row in persisted_messages:
        row = _mapping(raw_row, "persisted message")
        source_id = _row_field(row, "source_id")
        conversation_id = _row_field(row, "conversation_id")
        message_id = _row_field(row, "message_id")
        _row_field(row, "content_hash")
        if message_id in rows_by_message:
            raise EvidenceIdentityError(f"duplicate persisted message_id: {message_id}")
        rows_by_message[message_id] = row
        for key in _row_keys(row):
            if key in rows_by_key:
                raise EvidenceIdentityError("duplicate persisted composite identity")
            rows_by_key[key] = row

    result: dict[MessageIdentity, tuple[str, str]] = {}
    seen_links: set[tuple[str, str]] = set()
    for raw_link in message_links:
        link = _mapping(raw_link, "message link")
        message_id = _string(link.get("message_id"), "message link message_id")
        memory_id = _string(link.get("memory_id"), "message link memory_id")
        pair = (message_id, memory_id)
        if pair in seen_links:
            raise EvidenceIdentityError("duplicate message link")
        seen_links.add(pair)
        row = rows_by_message.get(message_id)
        if row is None:
            raise EvidenceIdentityError(f"unknown persisted message: {message_id}")
        fact_id = memory_to_fact.get(memory_id)
        if fact_id is None:
            raise EvidenceIdentityError(f"unknown linked memory: {memory_id}")
        matches = [corpus_by_key[key] for key in _row_keys(row) if key in corpus_by_key]
        if not matches:
            raise EvidenceIdentityError("unknown persisted composite corpus identity")
        if len(set(matches)) != 1:
            raise EvidenceIdentityError("persisted message composite identities contradict")
        corpus_fact, citation_id = matches[0]
        if corpus_fact != fact_id:
            raise EvidenceIdentityError("message and memory promotion facts contradict")
        identity = MessageIdentity(
            source_id=_row_field(row, "source_id"),
            conversation_id=_row_field(row, "conversation_id"),
            message_id=message_id,
            content_hash=_row_field(row, "content_hash"),
            memory_id=memory_id,
        )
        if identity in result and result[identity] != (fact_id, citation_id):
            raise EvidenceIdentityError("conflicting registry key")
        if identity in result:
            raise EvidenceIdentityError("duplicate registry key")
        result[identity] = (fact_id, citation_id)

    return EvaluationIdentityRegistry(
        memory_to_fact=MappingProxyType(dict(memory_to_fact)),
        message_to_fact_citation=MappingProxyType(dict(result)),
    )


def _citation_identity(section: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = section.get("citation")
    if raw is None:
        return {}
    return _mapping(raw, "section citation")


def select_context_evidence(
    pack: Mapping[str, Any],
    registry: EvaluationIdentityRegistry,
    *,
    limit: int = 2,
) -> SelectedEvidence:
    """Validate every ContextPack section, then select distinct facts in order."""
    if not isinstance(pack, Mapping) or isinstance(pack, (str, bytes)):
        raise EvidenceIdentityError("pack must be a mapping")
    sections = pack.get("sections")
    if isinstance(sections, (str, bytes)) or not isinstance(sections, Sequence):
        raise EvidenceIdentityError("pack sections must be a non-string sequence")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise EvidenceIdentityError("limit must be a non-negative integer")
    if not isinstance(registry, EvaluationIdentityRegistry):
        raise EvidenceIdentityError("registry has an invalid type")

    validated: list[tuple[SectionIdentity, str, str | None]] = []
    canonical_seen: set[SectionIdentity] = set()
    for raw_section in sections:
        section = _mapping(raw_section, "section")
        kind = _string(section.get("kind"), "section kind")
        if kind not in _KINDS:
            raise EvidenceIdentityError(f"unsupported section kind: {kind}")
        memory_id = _string(section.get("memory_id"), "section memory_id")
        fact_id = registry.memory_to_fact.get(memory_id)
        if fact_id is None:
            raise EvidenceIdentityError(f"unknown section memory identity: {memory_id}")
        citation = _citation_identity(section)
        citation_memory = citation.get("memory_id")
        if citation_memory is not None and _string(citation_memory, "citation memory_id") != memory_id:
            raise EvidenceIdentityError("citation memory identity contradicts section")

        if kind in _MEMORY_KINDS:
            identity: SectionIdentity = MemorySectionIdentity(kind=kind, memory_id=memory_id)  # type: ignore[arg-type]
            citation_id = None
        else:
            values = {field: _string(section.get(field), f"raw section {field}") for field in ("source_id", "conversation_id", "message_id", "content_hash")}
            text = section.get("text")
            if not isinstance(text, str) or not text:
                raise EvidenceIdentityError("raw section text must be non-empty")
            if SourceReadModel.content_hash(text) != values["content_hash"]:
                raise EvidenceIdentityError("raw section content hash mismatch")
            if not citation:
                raise EvidenceIdentityError("raw section citation is required")
            for field, value in (("memory_id", memory_id), *values.items()):
                if field not in citation:
                    raise EvidenceIdentityError(f"raw citation {field} is required")
                if _string(citation[field], f"citation {field}") != value:
                    raise EvidenceIdentityError(f"citation {field} contradicts raw section")
            identity = RawMessageSectionIdentity(kind=_RAW_KIND, memory_id=memory_id, **values)  # type: ignore[arg-type]
            lookup = MessageIdentity(**values, memory_id=memory_id)  # type: ignore[arg-type]
            bound = registry.message_to_fact_citation.get(lookup)
            if bound is None:
                raise EvidenceIdentityError("unknown raw message identity")
            if bound[0] != fact_id:
                raise EvidenceIdentityError("raw message and memory facts contradict")
            citation_id = bound[1]
        if identity in canonical_seen:
            raise EvidenceIdentityError("duplicate canonical section identity")
        canonical_seen.add(identity)
        validated.append((identity, fact_id, citation_id))

    facts: list[str] = []
    citations: list[str] = []
    stable: list[SectionIdentity] = []
    for identity, fact_id, citation_id in validated:
        if fact_id not in facts:
            if len(facts) >= limit:
                continue
            facts.append(fact_id)
            stable.append(identity)
        elif identity not in stable and citation_id is not None:
            stable.append(identity)
        if fact_id in facts and citation_id is not None and citation_id not in citations:
            citations.append(citation_id)
    return SelectedEvidence(tuple(facts), tuple(citations), tuple(stable))


__all__ = [
    "MessageIdentity", "EvaluationIdentityRegistry", "SelectedEvidence",
    "MemorySectionIdentity", "RawMessageSectionIdentity", "SectionIdentity",
    "EvidenceIdentityError", "build_identity_registry", "select_context_evidence",
]
