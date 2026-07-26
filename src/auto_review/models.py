from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


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
    source_refs: tuple[str, ...] = ()
    content_hash: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReviewCandidate":
        def values(name: str, fallback: str = "") -> tuple[str, ...]:
            raw = value.get(name)
            if raw in (None, ""):
                raw = value.get(fallback) if fallback else None
            if raw in (None, ""):
                return ()
            if isinstance(raw, (list, tuple, set)):
                return tuple(str(item) for item in raw if str(item).strip())
            return (str(raw),)

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
