from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal, Mapping

from src.sources import ResolvedMessageRef


class PromotionProjectionState(str, Enum):
    PREPARING = "preparing"
    VISIBLE_ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    REPAIR_REQUIRED = "repair_required"


@dataclass(frozen=True)
class ProvenanceRef:
    kind: Literal["message", "event", "source", "conversation", "evidence"]
    value: str
    content_hash: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"message", "event", "source", "conversation", "evidence"}:
            raise ValueError("unsupported provenance kind")
        if not str(self.value).strip():
            raise ValueError("provenance value is required")
        if self.content_hash is not None and not str(self.content_hash).strip():
            raise ValueError("provenance content_hash must not be empty")

    def to_dict(self) -> dict[str, str | None]:
        return {"kind": self.kind, "value": self.value, "content_hash": self.content_hash}


@dataclass(frozen=True)
class ResolvedProvenance:
    linkable_messages: tuple[ResolvedMessageRef, ...]
    context_only_refs: tuple[ProvenanceRef, ...]


@dataclass(frozen=True)
class BatchLinkResult:
    created_messages: tuple[ResolvedMessageRef, ...]
    reused_messages: tuple[ResolvedMessageRef, ...]


@dataclass(frozen=True)
class ProjectionWriteResult:
    memory_id: str
    decision_id: str
    created: bool
    state: PromotionProjectionState


@dataclass(frozen=True)
class PromotionEvidence:
    candidate_id: str
    decision_id: str
    memory_id: str
    state: PromotionProjectionState
    resolved_messages: tuple[ResolvedMessageRef, ...] = ()
    context_only_refs: tuple[ProvenanceRef, ...] = ()
    projection_created: bool = False
    created_links: tuple[ResolvedMessageRef, ...] = ()
    reused_links: tuple[ResolvedMessageRef, ...] = ()
    removed_links: tuple[ResolvedMessageRef, ...] = ()
    rollback_verified: bool = False
    error_codes: tuple[str, ...] = ()
    terminal_event_id: str | None = None


@dataclass(frozen=True)
class PromotionPersistenceAudit:
    expected_memory_ids: tuple[str, ...]
    persisted_memory_ids: tuple[str, ...]
    missing_memory_ids: tuple[str, ...]
    extra_memory_ids: tuple[str, ...]
    duplicate_memory_records: int

    @property
    def ready(self) -> bool:
        return bool(self.expected_memory_ids) and len(self.expected_memory_ids) == len(set(self.expected_memory_ids)) and not self.missing_memory_ids and not self.extra_memory_ids and self.duplicate_memory_records == 0


class AutoReviewMode(str, Enum):
    OFF = "OFF"
    SHADOW = "SHADOW"
    ACTIVE = "ACTIVE"


class AutoReviewAction(str, Enum):
    WOULD_AUTO_APPROVE = "would_auto_approve"
    WOULD_APPEND_EVIDENCE = "would_append_evidence"
    WOULD_AUTO_REJECT_NOISE = "would_auto_reject_noise"
    REQUIRES_OWNER_REVIEW = "requires_owner_review"
    BLOCKED = "blocked"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ReviewCandidate:
    memory_id: str
    title: str
    content: str
    memory_type: str = "knowledge"
    importance: str = "medium"
    privacy: str = "private"
    project_ids: tuple[str, ...] = ()
    proposed_by: str = ""
    source_refs: tuple[ProvenanceRef | str, ...] = ()
    content_hash: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    # Extraction provenance used by the automatic-promotion boundary.  These
    # fields are optional so the legacy OFF/SHADOW evaluator remains backward
    # compatible with existing candidate producers.
    confidence: float | None = None
    authority: str = ""
    source_kind: str = ""
    extractor_version: str = ""
    structured_content: Mapping[str, Any] = field(default_factory=dict)
    risk_flags: tuple[str, ...] = ()
    provenance_errors: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReviewCandidate":
        provenance_errors: list[str] = []

        def typed_ref(item: Mapping[str, Any]) -> ProvenanceRef | None:
            kind = item.get("kind")
            raw_value = item.get("value")
            content_hash = item.get("content_hash")
            if not isinstance(kind, str) or kind not in {"message", "event", "source", "conversation", "evidence"}:
                provenance_errors.append("provenance_typed_invalid")
                return None
            if not isinstance(raw_value, str) or not raw_value.strip():
                provenance_errors.append("provenance_typed_invalid")
                return None
            if content_hash is not None and (not isinstance(content_hash, str) or not content_hash.strip()):
                provenance_errors.append("provenance_typed_invalid")
                return None
            return ProvenanceRef(kind=kind, value=raw_value, content_hash=content_hash)

        def values(name: str, fallback: str = "") -> tuple[Any, ...]:
            raw = value.get(name)
            if raw in (None, ""):
                raw = value.get(fallback) if fallback else None
            if raw in (None, ""):
                return ()
            if isinstance(raw, (list, tuple, set)):
                selected = raw
            else:
                selected = (raw,)
            result: list[Any] = []
            for item in selected:
                if isinstance(item, ProvenanceRef):
                    result.append(item)
                elif isinstance(item, Mapping):
                    ref = typed_ref(item)
                    if ref is not None:
                        result.append(ref)
                elif str(item).strip():
                    result.append(str(item).strip())
            return tuple(result)

        raw_flags = value.get("risk_flags") or (value.get("metadata") or {}).get("risk_flags") or ()
        if isinstance(raw_flags, str):
            raw_flags = (raw_flags,)
        raw_confidence = value.get("confidence")
        # JSON numbers are the only accepted confidence representation.  In
        # particular, bools and numeric-looking strings fail closed instead of
        # being silently coerced into an activation score.
        confidence = (
            raw_confidence
            if isinstance(raw_confidence, (int, float)) and not isinstance(raw_confidence, bool)
            else None
        )
        structured = value.get("structured_content") or value.get("structured") or {}
        if not isinstance(structured, Mapping):
            structured = {}
        return cls(
            memory_id=str(value.get("memory_id") or value.get("id") or "").strip(),
            title=str(value.get("title") or "").strip(),
            content=str(value.get("content") or value.get("content_preview") or "").strip(),
            memory_type=str(value.get("memory_type") or "knowledge").strip().lower(),
            importance=str(value.get("importance") or "medium").strip().lower(),
            privacy=str(value.get("privacy") or "private").strip().lower(),
            project_ids=values("project_ids", "project"),
            proposed_by=str(value.get("proposed_by") or "").strip(),
            source_refs=values("source_refs", "sources"),
            content_hash=str(value.get("current_hash") or value.get("content_hash") or "").strip(),
            metadata=dict(value.get("metadata") or {}),
            confidence=confidence,
            authority=str(value.get("authority") or value.get("source_authority") or "").strip().lower(),
            source_kind=str(value.get("source_kind") or value.get("source_type") or "").strip().lower(),
            extractor_version=str(value.get("extractor_version") or "").strip(),
            structured_content=dict(structured),
            risk_flags=tuple(str(item).strip().lower() for item in raw_flags if str(item).strip()),
            provenance_errors=tuple(dict.fromkeys(provenance_errors)),
        )


@dataclass(frozen=True)
class ReviewContext:
    mode: AutoReviewMode = AutoReviewMode.SHADOW
    target_project_id: str | None = None
    duplicate_memory_id: str | None = None
    duplicate_same_project: bool = False
    duplicate_same_type: bool = False
    evidence_only_change: bool = False
    evidence_sufficient: bool = False
    has_conflict: bool = False
    owner_authored: bool = False
    development_report_status: str | None = None
    requested_operation: str = "review"
    permission_or_privacy_change: bool = False
    low_value_noise: bool = False
    external_risk_points: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuleFinding:
    code: str
    message: str
    risk_points: int
    hard_manual: bool = False
    blocked: bool = False
    reversible: bool = True
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class AutoReviewDecision:
    decision_id: str
    candidate_id: str
    mode: AutoReviewMode
    action: AutoReviewAction
    risk_level: RiskLevel
    risk_score: int
    reasons: tuple[RuleFinding, ...]
    target_memory_id: str | None = None
    reversible: bool = True
    mutation_performed: bool = False
    contract_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.mode.value
        payload["action"] = self.action.value
        payload["risk_level"] = self.risk_level.value
        payload["reasons"] = [asdict(item) for item in self.reasons]
        return payload
