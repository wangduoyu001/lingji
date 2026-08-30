"""Auditable evidence primitives for the automatic-memory quality gate."""
from __future__ import annotations

import hashlib
import errno
import json
import math
import os
import re
import secrets
import stat as stat_module
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Literal
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.models import ExtractionBatch
from src.sources import ExternalMessageKey, SourceReadModel, SourceReadModelError
from src.auto_review.models import PromotionEvidence, PromotionPersistenceAudit, PromotionProjectionState
from .evaluation import EvaluationReport


_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_PROMOTION_TRUTH_FIELDS = frozenset({
    "memory_id", "decision_id", "fixture_category", "expected_category",
    "expected_status", "service_status", "service_category",
    "service_reason_codes", "durable_status", "durable_category",
    "durable_reason_codes",
})
_PROMOTION_STATUSES = frozenset({"active", "pending_owner_review", "rejected", "error"})
_PROMOTION_CATEGORIES = frozenset({
    "core/protected", "high-risk", "authority-conflict", "assistant-only", "low-risk-user",
})
_PROMOTION_REASON_CODES = frozenset({
    "schema_invalid", "confidence_below_threshold",
    "direct_user_or_authoritative_source_required", "evidence_required",
    "evidence_reference_unverifiable", "unresolved_conflict", "duplicate_ambiguity",
    "core_memory_requires_owner", "restricted_requires_owner",
    "automatic_activation_quarantined", "structured_message_provenance_required",
    "promotion_measurement_error", "promotion_persist_failed",
    "promotion_terminal_event_pending", "promotion_lease_conflict",
    "promotion_start_event_failed", "projection_persist_failed", "projection_recovered",
    "promotion_payload_redacted",
    "core_requires_owner", "identity_requires_owner", "credentials_requires_owner",
    "credential_requires_owner", "secret_requires_owner", "secrets_requires_owner",
    "permission_requires_owner", "permissions_requires_owner", "medical_requires_owner",
    "legal_requires_owner", "financial_requires_owner", "security_requires_owner",
    "destructive_requires_owner", "irreversible_requires_owner", "privacy_requires_owner",
})


_RUNNER_ALLOWED_FIELDS = frozenset({
    "schema_version", "run_id", "code_commit", "fixture_hashes",
    "import_audit", "promotion_outcomes", "promotion_category_outcomes",
    "promotion_provenance", "gateway_selection", "mcp_parity",
    "qdrant_degradation", "semantic_degradation", "corruption_isolation",
    "context_baseline", "production_pollution", "measured_quality",
    "quality_evidence_readiness", "functional_status", "phase_status",
    "evidence_details", "readiness", "import_counts", "role_order_counts",
    "acceptance_root", "protected_tree_changes", "protected_tree_capture_error",
    "acceptance_boundary", "cleanup_inventory", "blocked_physical_evidence",
    "evaluation_report", "windows_status", "blocked_reasons",
})


@dataclass(frozen=True)
class ExpectedImportedRow:
    source_external_id: str
    conversation_external_id: str
    message_external_id: str
    ingestion_ordinal: int
    sequence: int
    role: str
    content_hash: str
    occurred_at: str

    @property
    def stable_external_key(self) -> ExternalMessageKey:
        return ExternalMessageKey(
            self.source_external_id,
            self.conversation_external_id,
            self.message_external_id,
        )


@dataclass(frozen=True)
class ContentHashGroup:
    content_hash: str
    member_external_keys: tuple[ExternalMessageKey, ...]


@dataclass(frozen=True)
class StableDuplicateSummary:
    source_records: int
    conversation_records: int
    message_records: int
    memory_records: int

    @property
    def total(self) -> int:
        return self.source_records + self.conversation_records + self.message_records + self.memory_records


@dataclass(frozen=True)
class CanonicalFunctionalEvidence:
    """The one wire contract for Task 7 functional evidence.

    The runner and the scale admission code deliberately share this typed
    boundary.  A plain dictionary is accepted only at the boundary and is
    immediately validated into this immutable artifact; neither side is
    allowed to invent a second set of field names.
    """

    data: Mapping[str, Any]

    _REQUIRED = frozenset({
        "schema_version", "run_id", "code_commit", "fixture_hashes",
        "import_audit", "promotion_outcomes", "promotion_category_outcomes",
        "promotion_provenance", "gateway_selection", "mcp_parity",
        "qdrant_degradation", "corruption_isolation", "context_baseline",
        "production_pollution", "measured_quality", "quality_evidence_readiness",
        "functional_status", "phase_status",
    })
    _STATUSES = frozenset({"not_measured", "ready", "failed", "invalid"})
    _QUALITY_STATUSES = frozenset({"PASS", "FAIL", "NOT_EVALUATED"})

    def __post_init__(self) -> None:
        # ``frozen=True`` only protects the dataclass attribute.  Freeze the
        # nested evidence tree as well so a validated view cannot be changed
        # after it has crossed the runner/scale boundary.
        object.__setattr__(self, "data", _freeze_evidence(self.data))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CanonicalFunctionalEvidence":
        try:
            if not isinstance(value, Mapping) or set(value) != set(cls._REQUIRED):
                raise ValueError("BLOCKED_4R2_REQUIRED")
            data = {str(key): value[key] for key in cls._REQUIRED}
            if type(data["schema_version"]) is not int or data["schema_version"] != 1:
                raise ValueError("BLOCKED_4R2_REQUIRED")
            commit = data["code_commit"]
            if (not isinstance(commit, str) or len(commit) != 40
                    or not _HEX_RE.fullmatch(commit)):
                raise ValueError("BLOCKED_4R2_REQUIRED")
            if not isinstance(data["run_id"], str) or not data["run_id"]:
                raise ValueError("BLOCKED_4R2_REQUIRED")
            hashes = data["fixture_hashes"]
            if (not isinstance(hashes, Mapping) or set(hashes) != {"corpus", "questions"}
                    or any(not isinstance(item, str) or len(item) != 64 or not _HEX_RE.fullmatch(item) for item in hashes.values())):
                raise ValueError("BLOCKED_4R2_REQUIRED")
            expected_run_id = f"quality:{hashes['corpus'][:16]}:{hashes['questions'][:16]}:{commit[:16]}"
            if data["run_id"] != expected_run_id:
                raise ValueError("BLOCKED_4R2_REQUIRED")
            for name in (
                "import_audit", "promotion_outcomes", "promotion_category_outcomes",
                "promotion_provenance", "gateway_selection", "mcp_parity",
                "qdrant_degradation", "corruption_isolation", "context_baseline",
                "measured_quality", "quality_evidence_readiness",
            ):
                if not isinstance(data[name], Mapping):
                    raise ValueError("BLOCKED_4R2_REQUIRED")
            readiness = data["quality_evidence_readiness"]
            expected_readiness = set(QualityEvidenceReadiness._FUNCTIONAL_FIELDS + QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",))
            if set(readiness) != expected_readiness or any(item not in cls._STATUSES for item in readiness.values()):
                raise ValueError("BLOCKED_4R2_REQUIRED")
            if data["functional_status"] not in cls._QUALITY_STATUSES or data["phase_status"] not in {"PASS", "FAIL", "BLOCKED", "NOT_EVALUATED"}:
                raise ValueError("BLOCKED_4R2_REQUIRED")
            if data["production_pollution"] is not None and type(data["production_pollution"]) is not int:
                raise ValueError("BLOCKED_4R2_REQUIRED")
            _validate_canonical_details(data)
            _reject_nonfinite_or_bool_numbers(data)
            return cls(data)
        except (TypeError, ValueError, KeyError):
            raise ValueError("BLOCKED_4R2_REQUIRED")

    @classmethod
    def from_runner_payload(cls, payload: Mapping[str, Any]) -> "CanonicalFunctionalEvidence":
        """Normalize the runner's in-memory result into this one wire shape."""
        if not isinstance(payload, Mapping):
            raise ValueError("BLOCKED_4R2_REQUIRED")
        if set(payload) - _RUNNER_ALLOWED_FIELDS:
            raise ValueError("BLOCKED_4R2_REQUIRED")
        details = payload.get("evidence_details")
        if details is not None:
            if not isinstance(details, Mapping):
                raise ValueError("BLOCKED_4R2_REQUIRED")
            canonical_details = cls.from_mapping(details)
            canonical_payload = canonical_details.to_mapping()
            _compare_runner_projections(payload, canonical_payload)
            return canonical_details
        details = payload
        def pick(name: str, default: Any = None) -> Any:
            value = payload.get(name)
            return details.get(name, default) if value is None else value

        qdrant = pick("qdrant_degradation", pick("semantic_degradation", {}))
        qdrant = dict(qdrant) if isinstance(qdrant, Mapping) else {}
        if "lexical_ids" not in qdrant:
            qdrant["lexical_ids"] = None
        if "degraded_ids" not in qdrant:
            qdrant["degraded_ids"] = None
        diagnostics = qdrant.get("diagnostics")
        if isinstance(diagnostics, Mapping):
            qdrant.setdefault("semantic", diagnostics.get("semantic"))
            qdrant.setdefault("lexical", diagnostics.get("lexical"))
        qdrant.setdefault("semantic", None)
        qdrant.setdefault("lexical", None)
        promotion = pick("promotion_provenance", {})
        promotion = dict(promotion) if isinstance(promotion, Mapping) else {}
        # Older test-only envelopes used link-oriented names.  Normalize
        # them once at this boundary; the canonical wire contract has one
        # vocabulary thereafter.
        promotion.setdefault("missing_projection", promotion.get("missing_links", 0))
        promotion.setdefault("extra_projection", promotion.get("extra_links", 0))
        promotion.setdefault("missing_audit", 0)
        promotion.setdefault("extra_audit", 0)
        promotion.setdefault("duplicate_audits", 0)
        promotion.setdefault("duplicate_links", 0)
        promotion.setdefault("duplicate_records", 0)
        promotion.pop("missing_links", None)
        promotion.pop("extra_links", None)
        corruption = pick("corruption_isolation", {})
        corruption = dict(corruption) if isinstance(corruption, Mapping) else {}
        corruption.setdefault("terminal_tasks", corruption.get("attempted", 0))
        corruption.setdefault("bad_source_messages", 0)
        corruption.setdefault("bad_source_leaks", corruption.get("bad_leakage_count", 0))
        corruption.setdefault("queue_status_counts", {})
        gateway = pick("gateway_selection", {})
        gateway = dict(gateway) if isinstance(gateway, Mapping) else {}
        gateway.setdefault("status", "failed")
        gateway.setdefault("calls_completed", 0)
        gateway.setdefault("selector_calls", 0)
        gateway.setdefault("unknown", 0)
        gateway.setdefault("duplicates", 0)
        mcp = pick("mcp_parity", {})
        mcp = dict(mcp) if isinstance(mcp, Mapping) else {}
        mcp.setdefault("status", "failed")
        mcp.setdefault("attempts", 0)
        mcp.setdefault("successes", 0)
        mcp.setdefault("strict_rate", (100.0 * mcp["successes"] / mcp["attempts"] if mcp.get("attempts") else 0.0))
        context = pick("context_baseline", {})
        context = dict(context) if isinstance(context, Mapping) else {}
        context.setdefault("status", "not_measured")
        context.setdefault("baseline_chars", None)
        context.setdefault("rendered_chars", None)
        context.setdefault("reduction", None)
        readiness = pick("quality_evidence_readiness", pick("readiness", {}))
        readiness = dict(readiness) if isinstance(readiness, Mapping) else {}
        readiness_fields = QualityEvidenceReadiness._FUNCTIONAL_FIELDS + QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",)
        readiness = {field: readiness.get(field, "not_measured") for field in readiness_fields}
        for field in readiness_fields:
            readiness.setdefault(field, "not_measured")
            value = readiness[field]
            readiness[field] = str(value).removeprefix("EvidenceState.").lower()
        normalized = {
            "schema_version": 1,
            "run_id": payload.get("run_id") or "",
            "code_commit": payload.get("code_commit") or "",
            "fixture_hashes": payload.get("fixture_hashes") or {},
            "import_audit": pick("import_audit", {}),
            "promotion_outcomes": pick("promotion_outcomes", {}),
            "promotion_category_outcomes": pick("promotion_category_outcomes", {}),
            "promotion_provenance": promotion,
            "gateway_selection": gateway,
            "mcp_parity": mcp,
            "qdrant_degradation": qdrant,
            "corruption_isolation": corruption,
            "context_baseline": context,
            "production_pollution": payload.get("production_pollution"),
            "measured_quality": pick("measured_quality", {}),
            "quality_evidence_readiness": readiness,
            "functional_status": payload.get("functional_status", "NOT_EVALUATED"),
            "phase_status": payload.get("phase_status", "NOT_EVALUATED"),
        }
        return cls.from_mapping(normalized)

    def to_mapping(self) -> dict[str, Any]:
        return _json_safe_copy(self.data)

    @classmethod
    def complete_for_test(cls) -> "CanonicalFunctionalEvidence":
        commit = "a" * 40
        corpus = "bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94"
        questions = "338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612"
        ready = {field: "ready" for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS + QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",)}
        return cls.from_mapping({
            "schema_version": 1,
            "run_id": f"quality:{corpus[:16]}:{questions[:16]}:{commit[:16]}",
            "code_commit": commit, "fixture_hashes": {"corpus": corpus, "questions": questions},
            "import_audit": {"expected_rows": 2, "actual_rows": 2, "missing_external_keys": [], "extra_external_keys": [], "stable_duplicates": {"source_records": 0, "conversation_records": 0, "message_records": 0, "memory_records": 0}, "ordered_external_key_matches": 2, "role_matches": 2, "sequence_matches": 2, "timestamp_matches": 2, "content_hash_matches": 2, "source_matches": 2, "conversation_matches": 2, "intentional_content_hash_groups": []},
            "promotion_outcomes": {"active": 0, "pending_owner_review": 2, "rejected": 0, "error": 0}, "promotion_category_outcomes": {},
            "promotion_provenance": {"status": "ready", "expected": 2, "actual": 2, "active": 0, "pending": 2, "rejected": 0, "error": 0, "links_expected": 2, "links_actual": 2, "missing_projection": 0, "extra_projection": 0, "missing_audit": 0, "extra_audit": 0, "duplicate_records": 0, "duplicate_audits": 0, "duplicate_links": 0, "outcomes": [
                {"memory_id": "m1", "decision_id": "d1", "fixture_category": "low-risk-user", "expected_category": "low-risk-user", "expected_status": "pending_owner_review", "service_status": "pending_owner_review", "service_category": "low-risk-user", "service_reason_codes": ["automatic_activation_quarantined"], "durable_status": "pending_owner_review", "durable_category": "low-risk-user", "durable_reason_codes": ["automatic_activation_quarantined"]},
                {"memory_id": "m2", "decision_id": "d2", "fixture_category": "low-risk-user", "expected_category": "low-risk-user", "expected_status": "pending_owner_review", "service_status": "pending_owner_review", "service_category": "low-risk-user", "service_reason_codes": ["automatic_activation_quarantined"], "durable_status": "pending_owner_review", "durable_category": "low-risk-user", "durable_reason_codes": ["automatic_activation_quarantined"]},
            ]},
            "gateway_selection": {"status": "ready", "calls_completed": 100, "selector_calls": 100, "unknown": 0, "duplicates": 0},
            "mcp_parity": {"status": "ready", "attempts": 100, "successes": 100, "strict_rate": 100.0},
            "qdrant_degradation": {"status": "ready", "semantic": "degraded", "lexical": "available", "lexical_ids": ["m1"], "degraded_ids": ["m1"]},
            "corruption_isolation": {"status": "ready", "terminal_tasks": 2, "attempted": 2, "completed": 1, "failed": 1, "continued": 1, "retrievable": 1, "bad_source_messages": 0, "bad_source_leaks": 0, "queue_status_counts": {"completed": 1, "failed": 1}},
            "context_baseline": {"status": "ready", "baseline_chars": 1000, "rendered_chars": 50, "reduction": 95.0}, "production_pollution": None,
            "measured_quality": {"status": "PASS", "mcp_attempts": 100, "mcp_successes": 100, "baseline_context_chars": 1000, "rendered_context_chars": 50, "context_reduction": 95.0},
            "quality_evidence_readiness": ready, "functional_status": "PASS", "phase_status": "BLOCKED",
        })


def _json_safe_copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_copy(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe_copy(child) for child in value]
    return value


def _freeze_evidence(value: Any) -> Any:
    """Recursively freeze the canonical evidence object."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_evidence(child) for key, child in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_evidence(child) for child in value)
    if isinstance(value, set):
        return frozenset(_freeze_evidence(child) for child in value)
    return value


def _compare_runner_projections(payload: Mapping[str, Any], canonical: Mapping[str, Any]) -> None:
    """Reject every compatibility projection that disagrees with evidence_details."""
    for field in CanonicalFunctionalEvidence._REQUIRED:
        if field not in payload:
            continue
        value = payload[field]
        if field == "quality_evidence_readiness":
            value = _normalize_readiness_projection(value)
        elif field in {"qdrant_degradation"}:
            value = _normalize_qdrant_projection(value)
        if not _strict_equal(value, canonical[field]):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    if "semantic_degradation" in payload:
        # The old runner spelling is accepted only as an exact projection of
        # the canonical qdrant section.
        if not _strict_equal(_normalize_qdrant_projection(payload["semantic_degradation"]), canonical["qdrant_degradation"]):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    for name, expected in (
        ("readiness", canonical["quality_evidence_readiness"]),
    ):
        if name in payload and not _strict_equal(_normalize_readiness_projection(payload[name]), expected):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    for name, expected in (
        ("import_counts", {"expected_messages": canonical["import_audit"]["expected_rows"], "imported_messages": canonical["import_audit"]["actual_rows"]}),
        ("role_order_counts", {"expected": canonical["import_audit"]["expected_rows"], "matched": canonical["import_audit"]["ordered_external_key_matches"]}),
    ):
        if name in payload:
            value = payload[name]
            if not isinstance(value, Mapping) or not _strict_equal(value, expected):
                raise ValueError("BLOCKED_4R2_REQUIRED")


def _strict_equal(left: Any, right: Any) -> bool:
    """Compare compatibility projections without Python's bool/int coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        if set(left) != set(right):
            return False
        return all(_strict_equal(left[key], right[key]) for key in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right))
    return left == right


def _normalize_readiness_projection(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    normalized = {}
    for key, item in value.items():
        if isinstance(item, EvidenceState):
            normalized[str(key)] = item.value
        elif isinstance(item, str):
            normalized[str(key)] = item.removeprefix("EvidenceState.").lower()
        else:
            normalized[str(key)] = item
    return normalized


def _normalize_qdrant_projection(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    normalized = dict(value)
    normalized.setdefault("lexical_ids", None)
    normalized.setdefault("degraded_ids", None)
    diagnostics = normalized.get("diagnostics")
    if isinstance(diagnostics, Mapping):
        normalized.setdefault("semantic", diagnostics.get("semantic"))
        normalized.setdefault("lexical", diagnostics.get("lexical"))
    normalized.setdefault("semantic", None)
    normalized.setdefault("lexical", None)
    return normalized


def _reject_nonfinite_or_bool_numbers(value: Any) -> None:
    import math
    if isinstance(value, Mapping):
        for child in value.values():
            _reject_nonfinite_or_bool_numbers(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            _reject_nonfinite_or_bool_numbers(child)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("BLOCKED_4R2_REQUIRED")


def _validate_canonical_details(data: Mapping[str, Any]) -> None:
    exact_sections = {
        "import_audit": {"expected_rows", "actual_rows", "missing_external_keys", "extra_external_keys", "stable_duplicates", "ordered_external_key_matches", "role_matches", "sequence_matches", "timestamp_matches", "content_hash_matches", "source_matches", "conversation_matches", "intentional_content_hash_groups"},
        "promotion_outcomes": {"active", "pending_owner_review", "rejected", "error"},
        "promotion_provenance": {"status", "expected", "actual", "active", "pending", "rejected", "error", "links_expected", "links_actual", "missing_projection", "extra_projection", "missing_audit", "extra_audit", "duplicate_records", "duplicate_audits", "duplicate_links", "outcomes"},
        "gateway_selection": {"status", "calls_completed", "selector_calls", "empty_responses", "selected_evidence", "empty_response_is_retrieval_miss", "unknown", "duplicates"},
        "mcp_parity": {"status", "attempts", "successes", "strict_rate", "failures"},
        "qdrant_degradation": {"status", "semantic", "lexical", "lexical_ids", "degraded_ids", "lexical_results", "degraded_results", "diagnostics"},
        "corruption_isolation": {"status", "terminal_tasks", "attempted", "completed", "failed", "continued", "retrievable", "bad_source_messages", "bad_source_leaks", "queue_status_counts", "reasons", "target_source_ids", "target_scan_ids", "target_job_ids", "work_outcome_counts", "valid_retrieval_identities", "bad_leakage_count", "reason"},
        "context_baseline": {"status", "baseline_chars", "rendered_chars", "reduction"},
        "measured_quality": {"status", "answered_questions", "valid_fact_hits", "valid_fact_total", "citation_hits", "citation_total", "automatic_activation_correct", "automatic_activation_total", "automatic_activation_accuracy", "mcp_successes", "mcp_attempts", "baseline_context_chars", "rendered_context_chars", "context_reduction"},
    }
    for section, allowed in exact_sections.items():
        if set(data[section]) - allowed:
            raise ValueError("BLOCKED_4R2_REQUIRED")
    # Measured sections are recursively closed.  A permissive top-level check
    # is not enough: an attacker can otherwise hide a second counter or status
    # in stable-duplicate, diagnostics, queue, or identity records.
    _require_nested_keys(data["import_audit"]["stable_duplicates"], {
        "source_records", "conversation_records", "message_records", "memory_records"},
        required={"source_records", "conversation_records", "message_records", "memory_records"})
    for field in ("missing_external_keys", "extra_external_keys"):
        _require_identity_list(data["import_audit"][field])
    _require_nested_keys(
        data["qdrant_degradation"].get("diagnostics"),
        {"semantic", "lexical", "reason_code", "source_authority"},
        required=set(), optional_none=True,
    )
    for field in ("target_source_ids", "target_scan_ids", "target_job_ids"):
        if field in data["corruption_isolation"]:
            _require_string_list(data["corruption_isolation"][field])
    if "reasons" in data["corruption_isolation"]:
        _require_string_list(data["corruption_isolation"]["reasons"])
    if "valid_retrieval_identities" in data["corruption_isolation"]:
        identities = data["corruption_isolation"]["valid_retrieval_identities"]
        if not isinstance(identities, (list, tuple)):
            raise ValueError("BLOCKED_4R2_REQUIRED")
        for identity in identities:
            _require_string_list(identity)
    for field in ("missing_external_keys", "extra_external_keys"):
        if not isinstance(data["import_audit"][field], (list, tuple)):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    groups = data["import_audit"]["intentional_content_hash_groups"]
    if not isinstance(groups, (list, tuple)):
        raise ValueError("BLOCKED_4R2_REQUIRED")
    group_hashes: set[str] = set()
    for group in groups:
        _require_nested_keys(group, {"content_hash", "member_external_keys"}, required={"content_hash", "member_external_keys"})
        content_hash = group["content_hash"]
        if not isinstance(content_hash, str) or not content_hash.strip() or content_hash != content_hash.strip() or content_hash in group_hashes:
            raise ValueError("BLOCKED_4R2_REQUIRED")
        group_hashes.add(content_hash)
        _require_identity_list(group["member_external_keys"])
    truth = data["promotion_provenance"].get("outcomes")
    if not isinstance(truth, (list, tuple)) or not truth:
        raise ValueError("BLOCKED_4R2_REQUIRED")
    memory_ids: set[str] = set()
    decision_ids: set[str] = set()
    truth_statuses: dict[str, int] = {status: 0 for status in _PROMOTION_STATUSES}
    for item in truth:
        _require_nested_keys(item, set(_PROMOTION_TRUTH_FIELDS), required=set(_PROMOTION_TRUTH_FIELDS))
        for identity_field, seen in (("memory_id", memory_ids), ("decision_id", decision_ids)):
            value = item[identity_field]
            if not isinstance(value, str) or not value.strip() or value != value.strip() or value in seen:
                raise ValueError("BLOCKED_4R2_REQUIRED")
            seen.add(value)
        if any(item[field] != "pending_owner_review" for field in ("expected_status", "service_status", "durable_status")):
            raise ValueError("BLOCKED_4R2_REQUIRED")
        if any(item[field] not in _PROMOTION_CATEGORIES for field in ("fixture_category", "expected_category", "service_category", "durable_category")):
            raise ValueError("BLOCKED_4R2_REQUIRED")
        if not all(item[field] == item["fixture_category"] for field in ("expected_category", "service_category", "durable_category")):
            raise ValueError("BLOCKED_4R2_REQUIRED")
        for reason_field in ("service_reason_codes", "durable_reason_codes"):
            _require_string_list(item[reason_field])
            if not item[reason_field]:
                raise ValueError("BLOCKED_4R2_REQUIRED")
            if any(reason not in _PROMOTION_REASON_CODES for reason in item[reason_field]):
                raise ValueError("BLOCKED_4R2_REQUIRED")
            if len(item[reason_field]) != len(set(item[reason_field])):
                raise ValueError("BLOCKED_4R2_REQUIRED")
        service_reasons = set(item["service_reason_codes"])
        durable_reasons = set(item["durable_reason_codes"])
        if not durable_reasons - service_reasons <= {"promotion_payload_redacted"} or not service_reasons <= durable_reasons:
            raise ValueError("BLOCKED_4R2_REQUIRED")
        truth_statuses[item["service_status"]] += 1
    aggregate = data["promotion_outcomes"]
    expected_aggregate = {
        "active": truth_statuses["active"],
        "pending_owner_review": truth_statuses["pending_owner_review"],
        "rejected": truth_statuses["rejected"],
        "error": truth_statuses["error"],
    }
    if not _strict_equal(aggregate, expected_aggregate):
        raise ValueError("BLOCKED_4R2_REQUIRED")
    for category, bucket in data["promotion_category_outcomes"].items():
        if not isinstance(category, str) or category not in {"core/protected", "high-risk", "authority-conflict", "assistant-only", "low-risk-user"}:
            raise ValueError("BLOCKED_4R2_REQUIRED")
        _require_nested_keys(bucket, {"expected", "actual", "active", "pending", "rejected", "error"}, required={"expected", "actual", "active", "pending", "rejected", "error"})
    for field in ("lexical_ids", "degraded_ids"):
        _require_string_list(data["qdrant_degradation"][field], allow_none=True)
    if "failures" in data["mcp_parity"]:
        _require_string_list(data["mcp_parity"]["failures"])
    for field in ("queue_status_counts", "work_outcome_counts"):
        if field in data["corruption_isolation"]:
            _require_counter_mapping(data["corruption_isolation"][field])
    if set(data["promotion_outcomes"]) != {"active", "pending_owner_review", "rejected", "error"}:
        raise ValueError("BLOCKED_4R2_REQUIRED")
    for value in data["promotion_category_outcomes"].values():
        if not isinstance(value, Mapping) or set(value) - {"expected", "actual", "active", "pending", "rejected", "error"}:
            raise ValueError("BLOCKED_4R2_REQUIRED")
    for section, required in {
        "import_audit": {"expected_rows", "actual_rows"},
        "promotion_provenance": {"status", "expected", "actual", "active", "pending", "rejected", "error", "links_expected", "links_actual", "missing_projection", "extra_projection", "missing_audit", "extra_audit", "duplicate_records", "duplicate_audits", "duplicate_links", "outcomes"},
        "gateway_selection": {"status", "calls_completed", "selector_calls"},
        "mcp_parity": {"status", "attempts", "successes", "strict_rate"},
        "qdrant_degradation": {"status", "semantic", "lexical", "lexical_ids", "degraded_ids"},
        "corruption_isolation": {"status", "terminal_tasks", "attempted", "completed", "failed", "continued", "retrievable", "bad_source_messages", "bad_source_leaks", "queue_status_counts"},
        "context_baseline": {"status", "baseline_chars", "rendered_chars", "reduction"},
    }.items():
        section_value = data[section]
        if not required <= set(section_value):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    numeric_fields = {
        "import_audit": ("expected_rows", "actual_rows", "ordered_external_key_matches", "role_matches", "sequence_matches", "timestamp_matches", "content_hash_matches", "source_matches", "conversation_matches"),
        "promotion_provenance": ("expected", "actual", "active", "pending", "rejected", "error", "links_expected", "links_actual", "missing_projection", "extra_projection", "missing_audit", "extra_audit", "duplicate_records", "duplicate_audits", "duplicate_links"),
        "gateway_selection": ("calls_completed", "selector_calls", "empty_responses", "selected_evidence", "unknown", "duplicates"),
        "mcp_parity": ("attempts", "successes"),
        "qdrant_degradation": ("lexical_results", "degraded_results"),
        "corruption_isolation": ("terminal_tasks", "attempted", "completed", "failed", "continued", "retrievable", "bad_source_messages", "bad_source_leaks", "bad_leakage_count"),
    }
    for section, fields in numeric_fields.items():
        if any(field in data[section] and (type(data[section].get(field)) is not int or data[section][field] < 0) for field in fields):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    stable = data["import_audit"]["stable_duplicates"]
    if any(type(stable[field]) is not int or stable[field] < 0 for field in ("source_records", "conversation_records", "message_records", "memory_records")):
        raise ValueError("BLOCKED_4R2_REQUIRED")
    for value in data["promotion_outcomes"].values():
        if type(value) is not int or value < 0:
            raise ValueError("BLOCKED_4R2_REQUIRED")
    for category in data["promotion_category_outcomes"].values():
        if any(type(category.get(field)) is not int or category[field] < 0 for field in category):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    measured = data["measured_quality"]
    for field in ("answered_questions", "valid_fact_hits", "valid_fact_total", "citation_hits", "citation_total", "mcp_successes", "mcp_attempts"):
        if field in measured and (type(measured[field]) is not int or measured[field] < 0):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    for field in ("automatic_activation_correct", "automatic_activation_total"):
        if field in measured and measured[field] is not None and (type(measured[field]) is not int or measured[field] < 0):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    for field in ("baseline_context_chars", "rendered_context_chars"):
        if field in measured and measured[field] is not None and (type(measured[field]) is not int or measured[field] < 0):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    if "automatic_activation_accuracy" in measured and measured["automatic_activation_accuracy"] is not None:
        if type(measured["automatic_activation_accuracy"]) not in (int, float) or not math.isfinite(float(measured["automatic_activation_accuracy"])) or not 0 <= measured["automatic_activation_accuracy"] <= 100:
            raise ValueError("BLOCKED_4R2_REQUIRED")
    if "context_reduction" in measured and measured["context_reduction"] is not None:
        if type(measured["context_reduction"]) not in (int, float) or not math.isfinite(float(measured["context_reduction"])) or not 0 <= measured["context_reduction"] <= 100:
            raise ValueError("BLOCKED_4R2_REQUIRED")
    context = data["context_baseline"]
    readiness = data["quality_evidence_readiness"]
    for section in ("mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline", "promotion_provenance"):
        if str(data[section].get("status") or "").lower() != str(readiness.get({"mcp_parity": "mcp_parity", "qdrant_degradation": "qdrant_degradation", "corruption_isolation": "corruption_isolation", "context_baseline": "context_baseline", "promotion_provenance": "promotion_provenance"}[section]) or "").lower():
            raise ValueError("BLOCKED_4R2_REQUIRED")
    if data["functional_status"] == "PASS" and any(readiness[field] != "ready" for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS if field != "production_sentinel"):
        raise ValueError("BLOCKED_4R2_REQUIRED")
    if context["status"] == "not_measured":
        if any(context[field] is not None for field in ("baseline_chars", "rendered_chars", "reduction")):
            raise ValueError("BLOCKED_4R2_REQUIRED")
    else:
        if any(type(context[field]) is not int for field in ("baseline_chars", "rendered_chars")) or type(context["reduction"]) not in (int, float):
            raise ValueError("BLOCKED_4R2_REQUIRED")


def _require_nested_keys(value: Any, allowed: set[str], *, required: set[str], optional_none: bool = False) -> None:
    if value is None and optional_none:
        return
    if not isinstance(value, Mapping) or not required <= set(value) or set(value) - allowed:
        raise ValueError("BLOCKED_4R2_REQUIRED")


def _require_string_list(value: Any, *, allow_none: bool = False) -> None:
    if value is None and allow_none:
        return
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
        raise ValueError("BLOCKED_4R2_REQUIRED")


def _require_identity_list(value: Any) -> None:
    if not isinstance(value, (list, tuple)):
        raise ValueError("BLOCKED_4R2_REQUIRED")
    seen: set[tuple[str, str, str]] = set()
    for item in value:
        _require_nested_keys(item, {"source_external_id", "conversation_external_id", "message_external_id"}, required={"source_external_id", "conversation_external_id", "message_external_id"})
        if any(not isinstance(item[field], str) for field in ("source_external_id", "conversation_external_id", "message_external_id")):
            raise ValueError("BLOCKED_4R2_REQUIRED")
        identity = tuple(item[field] for field in ("source_external_id", "conversation_external_id", "message_external_id"))
        if any(not field.strip() or field != field.strip() for field in identity) or identity in seen:
            raise ValueError("BLOCKED_4R2_REQUIRED")
        seen.add(identity)


def _require_counter_mapping(value: Any) -> None:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) or type(item) is not int or item < 0 for key, item in value.items()):
        raise ValueError("BLOCKED_4R2_REQUIRED")


def audit_promotion_persistence(memory_db: Any, *, promotion_evidence: Sequence[PromotionEvidence]) -> PromotionPersistenceAudit:
    """Compare durable active derived rows with verified activation evidence."""
    active = [item.memory_id for item in promotion_evidence if item.state is PromotionProjectionState.VISIBLE_ACTIVE or str(item.state) == PromotionProjectionState.VISIBLE_ACTIVE.value]
    expected = tuple(sorted(active))
    if len(active) != len(set(active)):
        expected = tuple(sorted(active))
    rows = tuple(memory_db.list_derived_projection_identity_rows())
    persisted = tuple(sorted(str(row.get("memory_id") or "") for row in rows))
    distinct = set(persisted)
    return PromotionPersistenceAudit(
        expected_memory_ids=expected,
        persisted_memory_ids=persisted,
        missing_memory_ids=tuple(sorted(set(expected) - distinct)),
        extra_memory_ids=tuple(sorted(distinct - set(expected))),
        duplicate_memory_records=max(0, len(persisted) - len(distinct)),
    )


def count_memory_projection_duplicates(memory_db: Any) -> int:
    """Count duplicate active derived projections from the durable read model."""
    rows = tuple(memory_db.list_derived_projection_identity_rows())
    counts: dict[str, int] = {}
    for row in rows:
        memory_id = str(row.get("memory_id") or "")
        if memory_id:
            counts[memory_id] = counts.get(memory_id, 0) + 1
    return sum(max(0, count - 1) for count in counts.values())


def build_expected_import_rows(batch: ExtractionBatch) -> tuple[ExpectedImportedRow, ...]:
    """Flatten adapter output using the one global ingestion order contract."""
    rows: list[ExpectedImportedRow] = []
    ordinal = 0
    for source in batch.structured_sources:
        for conversation in source.conversations:
            for message in conversation.messages:
                rows.append(
                    ExpectedImportedRow(
                        source_external_id=source.external_id,
                        conversation_external_id=conversation.external_id,
                        message_external_id=message.external_id,
                        ingestion_ordinal=ordinal,
                        sequence=int(message.sequence),
                        role=message.role,
                        content_hash=SourceReadModel.content_hash(message.content),
                        occurred_at=message.occurred_at,
                    )
                )
                ordinal += 1
    return tuple(rows)


@dataclass(frozen=True)
class SentinelEntry:
    path: str
    kind: str
    mode: int
    size: int
    sha256: str | None


@dataclass(frozen=True)
class SentinelChange:
    path: str
    before: SentinelEntry | None
    after: SentinelEntry | None


class EvidenceState(str, Enum):
    NOT_MEASURED = "not_measured"
    INVALID = "invalid"
    FAILED = "failed"
    READY = "ready"


class ProtectedTreeSentinelError(ValueError):
    """Base class for stable, path-redacting protected-tree errors."""

    def __init__(self, code: str):
        self.code = code
        labels = {
            "ROOT_MISSING": "missing protected root",
            "ROOT_SYMLINK": "symlink protected root",
            "TREE_SYMLINK": "symlink in protected tree",
            "TREE_MISSING": "missing protected tree entry",
        }
        super().__init__(labels.get(code, code))


class ProtectedTreeUnavailableError(ProtectedTreeSentinelError):
    """The configured tree cannot be measured."""


class ProtectedTreeInvalidError(ProtectedTreeSentinelError):
    """A tree measurement was partial, raced, or internally inconsistent."""


@dataclass(frozen=True)
class ProtectedTreeSentinel:
    root_contract: tuple[str, ...]
    entries: Mapping[str, SentinelEntry]

    @classmethod
    def capture(cls, roots: Sequence[Path]) -> "ProtectedTreeSentinel":
        """Capture a finite descriptor-anchored snapshot.

        The snapshot point is the successful final no-follow root descriptor
        identity observation and its comparison with the initial observation.
        A mutation strictly after that observation belongs to a later capture;
        this operation performs no unbounded post-snapshot retries.
        """
        if not roots:
            raise ProtectedTreeUnavailableError("ROOTS_EMPTY")

        canonical: list[Path] = []
        admitted: dict[Path, os.stat_result] = {}
        for configured in roots:
            path = Path(configured).expanduser()
            if not path.is_absolute():
                path = Path(os.path.abspath(path))
            else:
                path = Path(os.path.normpath(str(path)))
            # Check every existing path component without following symlinks.
            current = Path(path.anchor)
            try:
                for component in path.parts[1:]:
                    current /= component
                    item = os.lstat(current)
                    if stat_module.S_ISLNK(item.st_mode):
                        raise ProtectedTreeUnavailableError("ROOT_SYMLINK")
            except ProtectedTreeSentinelError:
                raise
            except FileNotFoundError as exc:
                raise ProtectedTreeUnavailableError("ROOT_MISSING") from exc
            except OSError as exc:
                raise ProtectedTreeUnavailableError("ROOT_UNAVAILABLE") from exc
            resolved = Path(os.path.realpath(path))
            try:
                root_stat = os.lstat(path)
            except FileNotFoundError as exc:
                raise ProtectedTreeUnavailableError("ROOT_MISSING") from exc
            except OSError as exc:
                raise ProtectedTreeUnavailableError("ROOT_UNAVAILABLE") from exc
            if stat_module.S_ISLNK(root_stat.st_mode):
                raise ProtectedTreeUnavailableError("ROOT_SYMLINK")
            if not stat_module.S_ISDIR(root_stat.st_mode):
                raise ProtectedTreeUnavailableError("ROOT_NOT_DIRECTORY")
            canonical.append(resolved)
            admitted[resolved] = root_stat

        canonical_sorted = sorted(canonical, key=lambda p: str(p))
        if len(set(canonical_sorted)) != len(canonical_sorted):
            raise ProtectedTreeUnavailableError("ROOT_DUPLICATE")
        for index, root in enumerate(canonical_sorted):
            for other in canonical_sorted[index + 1:]:
                try:
                    other.relative_to(root)
                except ValueError:
                    continue
                raise ProtectedTreeUnavailableError("ROOT_OVERLAP")

        identifiers = tuple(sorted(_root_identifier(root) for root in canonical_sorted))
        entries: dict[str, SentinelEntry] = {}
        for root in canonical_sorted:
            root_id = _root_identifier(root)
            fd = _open_anchored_directory(root)
            try:
                try:
                    root_identity = os.fstat(fd)
                except Exception as exc:
                    raise ProtectedTreeInvalidError("ROOT_FSTAT_FAILED") from exc
                if not _metadata_matches(admitted[root], root_identity):
                    raise ProtectedTreeInvalidError("ROOT_RACE")
                _capture_directory_fd(fd, root_id, "", entries, is_root=True)
                try:
                    final_fd = _open_anchored_directory(root)
                    try:
                        try:
                            final_identity = os.fstat(final_fd)
                        except Exception as exc:
                            raise ProtectedTreeInvalidError("ROOT_FSTAT_FAILED") from exc
                    finally:
                        owned_final_fd = final_fd
                        final_fd = -1
                        try:
                            os.close(owned_final_fd)
                        except Exception as exc:
                            raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc
                except ProtectedTreeSentinelError as exc:
                    if isinstance(exc, ProtectedTreeInvalidError) and exc.code == "ROOT_FSTAT_FAILED":
                        raise
                    raise ProtectedTreeInvalidError("ROOT_RACE") from exc
                if not _metadata_matches(root_identity, final_identity, include_size=False):
                    raise ProtectedTreeInvalidError("ROOT_RACE")
            finally:
                owned_fd = fd
                fd = -1
                try:
                    os.close(owned_fd)
                except Exception as exc:
                    raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc
        return cls(identifiers, entries)

    def diff(self, after: "ProtectedTreeSentinel") -> tuple[SentinelChange, ...]:
        if not isinstance(after, ProtectedTreeSentinel) or self.root_contract != after.root_contract:
            raise ProtectedTreeInvalidError("ROOT_CONTRACT_MISMATCH")
        changes = []
        for key in sorted(set(self.entries) | set(after.entries)):
            before, current = self.entries.get(key), after.entries.get(key)
            if before != current:
                changes.append(SentinelChange(key, before, current))
        return tuple(changes)


def cleanup_inventory_before_delete(root: Path) -> dict[str, Any]:
    """Capture path-free machine counts before deleting an acceptance root."""
    root = Path(root)
    inventory = {
        "file_count": 0, "directory_count": 0, "symlink_count": 0,
        "other_count": 0, "bytes": 0, "root_exists": os.path.lexists(os.fspath(root)),
    }
    if not inventory["root_exists"]:
        return inventory
    try:
        for path in (root, *root.rglob("*")):
            try:
                item = os.lstat(path)
            except OSError:
                inventory["other_count"] += 1
                continue
            if stat_module.S_ISLNK(item.st_mode):
                inventory["symlink_count"] += 1
            elif stat_module.S_ISDIR(item.st_mode):
                if path != root:
                    inventory["directory_count"] += 1
            elif stat_module.S_ISREG(item.st_mode):
                inventory["file_count"] += 1
                inventory["bytes"] += int(item.st_size)
            else:
                inventory["other_count"] += 1
    except OSError:
        inventory["other_count"] += 1
    return inventory


def cleanup_inventory_after_delete(root: Path) -> dict[str, Any]:
    """Verify deletion and report only machine counts, never path names."""
    root = Path(root)
    exists = os.path.lexists(os.fspath(root))
    if not exists:
        return {"root_exists": False, "remaining_count": 0, "remaining_bytes": 0, "error": None}
    before = cleanup_inventory_before_delete(root)
    remaining = sum(int(before.get(key, 0)) for key in ("file_count", "directory_count", "symlink_count", "other_count"))
    return {"root_exists": True, "remaining_count": remaining, "remaining_bytes": int(before.get("bytes", 0)), "error": "TEMP_CLEANUP_INCOMPLETE"}


def _root_identifier(root: Path) -> str:
    return hashlib.sha256(str(root).encode("utf-8")).hexdigest()


def _metadata_matches(first: os.stat_result, second: os.stat_result, *, include_size: bool = True) -> bool:
    fields = ("st_dev", "st_ino", "st_mode")
    if include_size:
        fields += ("st_size",)
    return all(
        not hasattr(first, field) or getattr(first, field) == getattr(second, field)
        for field in fields + ("st_mtime_ns", "st_ctime_ns")
    )


def _safe_traversal_available() -> bool:
    return bool(
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "supports_dir_fd")
        and any(getattr(fn, "__name__", "") == "open" for fn in os.supports_dir_fd)
        and any(getattr(fn, "__name__", "") == "stat" for fn in os.supports_dir_fd)
    )


def _safe_publication_available() -> bool:
    return bool(
        _safe_traversal_available()
        and any(getattr(fn, "__name__", "") == "rename" for fn in os.supports_dir_fd)
        and any(getattr(fn, "__name__", "") == "unlink" for fn in os.supports_dir_fd)
    )


def _open_anchored_directory(path: Path) -> int:
    if not _safe_traversal_available():
        raise ProtectedTreeUnavailableError("SAFE_TRAVERSAL_UNAVAILABLE")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = -1
    try:
        fd = os.open(path.anchor, flags)
        for component in path.parts[1:]:
            child_fd = os.open(component, flags, dir_fd=fd)
            previous_fd = fd
            fd = -1
            try:
                os.close(previous_fd)
            except Exception as exc:
                owned_child_fd = child_fd
                child_fd = -1
                try:
                    os.close(owned_child_fd)
                except Exception:
                    pass
                raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc
            fd = child_fd
        return fd
    except ProtectedTreeSentinelError:
        owned_fd = fd
        fd = -1
        if owned_fd >= 0:
            try:
                os.close(owned_fd)
            except Exception:
                pass
        raise
    except OSError as exc:
        owned_fd = fd
        fd = -1
        if owned_fd >= 0:
            try:
                os.close(owned_fd)
            except Exception:
                pass
        raise ProtectedTreeUnavailableError("ROOT_OPEN_FAILED") from exc


def _hash_fd(fd: int) -> str:
    digest = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            return digest.hexdigest()
        digest.update(chunk)


def _capture_file_fd(
    parent_fd: int,
    name: str,
    key: str,
    before: os.stat_result,
    entries: dict[str, SentinelEntry],
) -> None:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    fd = -1
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
        opened = os.fstat(fd)
        if not stat_module.S_ISREG(opened.st_mode) or not _metadata_matches(before, opened):
            raise ProtectedTreeInvalidError("FILE_REPLACED")
        first_digest = _hash_fd(fd)
        first_after = os.fstat(fd)
        second_digest = _hash_fd(fd)
        second_after = os.fstat(fd)
        if first_digest != second_digest:
            raise ProtectedTreeInvalidError("FILE_CONTENT_RACE")
        for observed in (first_after, second_after):
            if not stat_module.S_ISREG(observed.st_mode) or not _metadata_matches(before, observed):
                raise ProtectedTreeInvalidError("FILE_RACE")
        entries[key] = SentinelEntry(key, "file", stat_module.S_IMODE(before.st_mode), before.st_size, first_digest)
    except ProtectedTreeSentinelError:
        raise
    except OSError as exc:
        raise ProtectedTreeUnavailableError("FILE_UNREADABLE") from exc
    finally:
        if fd >= 0:
            owned_fd = fd
            fd = -1
            try:
                os.close(owned_fd)
            except Exception as exc:
                raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc


def _capture_directory_fd(
    fd: int,
    root_id: str,
    relative: str,
    entries: dict[str, SentinelEntry],
    *,
    is_root: bool = False,
) -> None:
    try:
        before = os.fstat(fd)
    except OSError as exc:
        raise ProtectedTreeInvalidError("TREE_UNAVAILABLE") from exc
    if not stat_module.S_ISDIR(before.st_mode):
        raise ProtectedTreeInvalidError("ROOT_REPLACED" if is_root else "TREE_REPLACED")
    key = f"{root_id}:{relative}" if relative else f"{root_id}:"
    entries[key] = SentinelEntry(key, "dir", stat_module.S_IMODE(before.st_mode), before.st_size, None)
    try:
        with os.scandir(fd) as iterator:
            names = sorted((item.name for item in iterator))
    except OSError as exc:
        raise ProtectedTreeUnavailableError("TREE_UNREADABLE") from exc
    for name in names:
        try:
            child_stat = os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise ProtectedTreeInvalidError("TREE_TRAVERSAL_RACE") from exc
        except OSError as exc:
            raise ProtectedTreeUnavailableError("TREE_UNREADABLE") from exc
        child_relative = f"{relative}/{name}" if relative else name
        child_key = f"{root_id}:{child_relative}"
        if stat_module.S_ISDIR(child_stat.st_mode):
            child_fd = -1
            try:
                child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                opened_child = os.fstat(child_fd)
                if not stat_module.S_ISDIR(opened_child.st_mode) or not _metadata_matches(child_stat, opened_child):
                    raise ProtectedTreeInvalidError("TREE_TRAVERSAL_RACE")
                _capture_directory_fd(child_fd, root_id, child_relative, entries)
            except ProtectedTreeSentinelError:
                raise
            except OSError as exc:
                raise ProtectedTreeInvalidError("TREE_TRAVERSAL_RACE") from exc
            finally:
                if child_fd >= 0:
                    owned_child_fd = child_fd
                    child_fd = -1
                    try:
                        os.close(owned_child_fd)
                    except Exception as exc:
                        raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc
        elif stat_module.S_ISREG(child_stat.st_mode):
            _capture_file_fd(fd, name, child_key, child_stat, entries)
        elif stat_module.S_ISLNK(child_stat.st_mode):
            raise ProtectedTreeUnavailableError("TREE_SYMLINK")
        else:
            raise ProtectedTreeUnavailableError("SPECIAL_FILE")
    try:
        with os.scandir(fd) as iterator:
            after_names = sorted((item.name for item in iterator))
        final_directory = os.fstat(fd)
    except OSError as exc:
        raise ProtectedTreeInvalidError("ROOT_RACE" if is_root else "TREE_TRAVERSAL_RACE") from exc
    if names != after_names or (
        not stat_module.S_ISDIR(final_directory.st_mode)
        or stat_module.S_IMODE(final_directory.st_mode) != stat_module.S_IMODE(before.st_mode)
        or final_directory.st_ino != before.st_ino
        or final_directory.st_dev != before.st_dev
    ):
        raise ProtectedTreeInvalidError("ROOT_RACE" if is_root else "TREE_TRAVERSAL_RACE")


class QualityPublicationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def write_quality_json_atomic(
    output_path: Path,
    value: Mapping[str, Any],
    *,
    protected_roots: Sequence[Path],
) -> None:
    """Write deterministic JSON beneath an already-admitted real directory."""
    output = Path(output_path).expanduser()
    if not output.is_absolute():
        output = Path(os.path.abspath(output))
    parent = output.parent
    if not _safe_publication_available():
        raise QualityPublicationError("UNSAFE_PUBLICATION_PLATFORM")
    try:
        current = Path(parent.anchor)
        for component in Path(os.path.abspath(parent)).parts[1:]:
            current /= component
            item = os.lstat(current)
            if stat_module.S_ISLNK(item.st_mode):
                raise QualityPublicationError("PARENT_SYMLINK")
    except QualityPublicationError:
        raise
    except FileNotFoundError as exc:
        raise QualityPublicationError("PARENT_UNAVAILABLE") from exc
    except OSError as exc:
        raise QualityPublicationError("PARENT_UNAVAILABLE") from exc

    # Admission is checked lexically/canonically before opening the parent;
    # the descriptor below is the authority for all subsequent operations.
    candidate = Path(os.path.realpath(output))
    for configured in protected_roots:
        protected = Path(os.path.realpath(Path(configured).expanduser()))
        try:
            candidate.relative_to(protected)
        except ValueError:
            continue
        raise QualityPublicationError("PROTECTED_OUTPUT")
    try:
        payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except Exception as exc:
        raise QualityPublicationError("SERIALIZATION_FAILED") from exc

    temporary: Path | None = None
    fd = -1
    parent_fd = -1
    parent_identity: tuple[int, int] | None = None
    try:
        parent_fd = _open_publication_parent(parent)
        parent_stat = os.fstat(parent_fd)
        parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
        try:
            target = os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
            if stat_module.S_ISLNK(target.st_mode):
                raise QualityPublicationError("OUTPUT_SYMLINK")
        except FileNotFoundError:
            pass
        except QualityPublicationError:
            raise
        except OSError as exc:
            raise QualityPublicationError("OUTPUT_UNAVAILABLE") from exc
        for _ in range(32):
            candidate_name = f".{output.name}.{secrets.token_hex(12)}.tmp"
            try:
                fd = os.open(candidate_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
                temporary = Path(candidate_name)
                break
            except FileExistsError:
                continue
        if temporary is None:
            raise QualityPublicationError("TEMP_CREATE_FAILED")
        try:
            with os.fdopen(fd, "wb", closefd=True) as stream:
                fd = -1
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception as exc:
            raise QualityPublicationError("WRITE_FAILED") from exc
        try:
            os.replace(temporary.name, output.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            temporary = None
        except Exception as exc:
            raise QualityPublicationError("REPLACE_FAILED") from exc
        try:
            current_parent = os.stat(parent, follow_symlinks=False)
            if parent_identity != (current_parent.st_dev, current_parent.st_ino):
                raise QualityPublicationError("PARENT_RACE_AFTER_REPLACE")
        except QualityPublicationError:
            raise
        except OSError as exc:
            raise QualityPublicationError("PARENT_RACE_AFTER_REPLACE") from exc
        try:
            os.fsync(parent_fd)
        except Exception as exc:
            unsupported = isinstance(exc, OSError) and exc.errno in {errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}
            if not unsupported:
                raise QualityPublicationError("DIRECTORY_FSYNC_FAILED_AFTER_REPLACE") from exc
    except QualityPublicationError:
        raise
    except OSError as exc:
        raise QualityPublicationError("PUBLICATION_FAILED") from exc
    finally:
        cleanup_error: QualityPublicationError | None = None
        if fd >= 0:
            owned_fd = fd
            fd = -1
            try:
                os.close(owned_fd)
            except Exception:
                pass
        if temporary is not None:
            try:
                if parent_fd >= 0:
                    os.unlink(temporary.name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            except Exception as exc:
                cleanup_error = QualityPublicationError("TEMP_CLEANUP_FAILED")
        if parent_fd >= 0:
            owned_parent_fd = parent_fd
            parent_fd = -1
            try:
                os.close(owned_parent_fd)
            except Exception:
                if cleanup_error is None:
                    cleanup_error = QualityPublicationError("FD_CLOSE_FAILED")
        if cleanup_error is not None:
            raise cleanup_error


def _open_publication_parent(path: Path) -> int:
    if not _safe_publication_available():
        raise QualityPublicationError("UNSAFE_PUBLICATION_PLATFORM")
    absolute = Path(os.path.abspath(path))
    fd = -1
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(absolute.anchor, flags)
        for component in absolute.parts[1:]:
            child = os.open(component, flags, dir_fd=fd)
            previous_fd = fd
            fd = -1
            try:
                os.close(previous_fd)
            except Exception as exc:
                owned_child = child
                child = -1
                try:
                    os.close(owned_child)
                except Exception:
                    pass
                raise QualityPublicationError("FD_CLOSE_FAILED") from exc
            fd = child
        return fd
    except QualityPublicationError:
        owned_fd = fd
        fd = -1
        if owned_fd >= 0:
            try:
                os.close(owned_fd)
            except Exception:
                pass
        raise
    except OSError as exc:
        owned_fd = fd
        fd = -1
        if owned_fd >= 0:
            try:
                os.close(owned_fd)
            except Exception:
                pass
        raise QualityPublicationError("PARENT_UNAVAILABLE") from exc


def _read_ingestion_rows(read_model: SourceReadModel, ingestion_batch_id: str) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    offset = 0
    expected_total: int | None = None
    while True:
        page = read_model.list_ingestion_messages(ingestion_batch_id, limit=200, offset=offset)
        pagination = page.get("pagination")
        if not isinstance(pagination, Mapping):
            raise SourceReadModelError("ingestion audit pagination is missing")
        total = pagination.get("total")
        page_offset = pagination.get("offset")
        page_limit = pagination.get("limit")
        has_more = pagination.get("has_more")
        if (
            isinstance(total, bool)
            or not isinstance(total, int)
            or total < 0
            or isinstance(page_offset, bool)
            or not isinstance(page_offset, int)
            or page_offset != offset
            or isinstance(page_limit, bool)
            or not isinstance(page_limit, int)
            or page_limit != 200
            or not isinstance(has_more, bool)
        ):
            raise SourceReadModelError("malformed ingestion audit pagination")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise SourceReadModelError("ingestion audit pagination total drift")
        items = page.get("items")
        if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
            raise SourceReadModelError("malformed ingestion audit page items")
        if len(items) > page_limit or offset + len(items) > total:
            raise SourceReadModelError("ingestion audit pagination overrun")
        rows.extend(items)
        if has_more and not items:
            raise SourceReadModelError("ingestion audit pagination made no progress")
        if has_more and offset + len(items) >= total:
            raise SourceReadModelError("ingestion audit pagination has_more is inconsistent")
        if not has_more:
            if len(rows) != total:
                raise SourceReadModelError("ingestion audit pagination final count mismatch")
            return rows
        next_offset = offset + len(items)
        if next_offset <= offset:
            raise SourceReadModelError("ingestion audit pagination made no progress")
        offset = next_offset


@dataclass(frozen=True)
class ImportedEvidenceAudit:
    expected_rows: int
    actual_rows: int
    missing_external_keys: tuple[ExternalMessageKey, ...]
    extra_external_keys: tuple[ExternalMessageKey, ...]
    stable_duplicates: StableDuplicateSummary
    ordered_external_key_matches: int
    role_matches: int
    sequence_matches: int
    timestamp_matches: int
    content_hash_matches: int
    source_matches: int
    conversation_matches: int
    intentional_content_hash_groups: tuple[ContentHashGroup, ...]

    @property
    def ready(self) -> bool:
        expected = self.expected_rows
        return bool(
            expected > 0
            and self.actual_rows == expected
            and not self.missing_external_keys
            and not self.extra_external_keys
            and self.stable_duplicates.total == 0
            and all(
                value == expected
                for value in (
                    self.ordered_external_key_matches,
                    self.role_matches,
                    self.sequence_matches,
                    self.timestamp_matches,
                    self.content_hash_matches,
                    self.source_matches,
                    self.conversation_matches,
                )
            )
        )

    @classmethod
    def from_read_model(
        cls,
        read_model: SourceReadModel,
        *,
        ingestion_batch_id: str,
        expected_rows: Sequence[ExpectedImportedRow],
    ) -> "ImportedEvidenceAudit":
        rows = _read_ingestion_rows(read_model, ingestion_batch_id)

        expected_keys = [item.stable_external_key for item in expected_rows]
        actual_keys = [
            ExternalMessageKey(
                str(row.get("source_external_id") or ""),
                str(row.get("conversation_external_id") or ""),
                str(row.get("message_external_id") or ""),
            )
            for row in rows
        ]
        expected_set = set(expected_keys)
        actual_set = set(actual_keys)
        source_identity: dict[str, set[str]] = {}
        conversation_identity: dict[tuple[str, str], set[str]] = {}
        message_counts: dict[ExternalMessageKey, int] = {}
        for row, key in zip(rows, actual_keys):
            source_id = str(row.get("source_id") or "")
            conversation_id = str(row.get("conversation_id") or "")
            if source_id:
                source_identity.setdefault(key.source_external_id, set()).add(source_id)
            if conversation_id:
                conversation_identity.setdefault((key.source_external_id, key.conversation_external_id), set()).add(conversation_id)
            message_counts[key] = message_counts.get(key, 0) + 1
        duplicates = StableDuplicateSummary(
            source_records=sum(max(0, len(ids) - 1) for ids in source_identity.values()),
            conversation_records=sum(max(0, len(ids) - 1) for ids in conversation_identity.values()),
            message_records=sum(max(0, count - 1) for count in message_counts.values()),
            memory_records=0,
        )
        paired = zip(expected_rows, rows)
        role = sequence = timestamp = content = source = conversation = ordered_external = 0
        for expected, row in paired:
            actual_key = ExternalMessageKey(
                str(row.get("source_external_id") or ""),
                str(row.get("conversation_external_id") or ""),
                str(row.get("message_external_id") or ""),
            )
            source_id = str(row.get("source_id") or "")
            conversation_id = str(row.get("conversation_id") or "")
            message_id = str(row.get("message_id") or "")
            internal_ids_valid = bool(source_id and conversation_id and message_id)
            ordered_external += int(internal_ids_valid and actual_key == expected.stable_external_key)
            role += int(row.get("role") == expected.role)
            sequence += int(row.get("sequence") == expected.sequence)
            timestamp += int(row.get("occurred_at") == expected.occurred_at)
            content += int(row.get("content_hash") == expected.content_hash)
            source += int(bool(source_id) and actual_key.source_external_id == expected.source_external_id)
            conversation += int(bool(conversation_id) and actual_key.conversation_external_id == expected.conversation_external_id)
        grouped: dict[str, set[ExternalMessageKey]] = {}
        for item in expected_rows:
            grouped.setdefault(item.content_hash, set()).add(item.stable_external_key)
        intentional = tuple(
            ContentHashGroup(content_hash, tuple(sorted(keys, key=lambda key: (key.source_external_id, key.conversation_external_id, key.message_external_id))))
            for content_hash, keys in sorted(grouped.items(), key=lambda pair: pair[0])
            if len(keys) >= 2
        )
        return cls(
            expected_rows=len(expected_rows),
            actual_rows=len(rows),
            missing_external_keys=tuple(sorted(expected_set - actual_set, key=lambda key: (key.source_external_id, key.conversation_external_id, key.message_external_id))),
            extra_external_keys=tuple(sorted(actual_set - expected_set, key=lambda key: (key.source_external_id, key.conversation_external_id, key.message_external_id))),
            stable_duplicates=duplicates,
            ordered_external_key_matches=ordered_external,
            role_matches=role,
            sequence_matches=sequence,
            timestamp_matches=timestamp,
            content_hash_matches=content,
            source_matches=source,
            conversation_matches=conversation,
            intentional_content_hash_groups=intentional,
        )


@dataclass(frozen=True)
class QualityEvidenceReadiness:
    import_audit: EvidenceState
    promotion_provenance: EvidenceState
    gateway_selection: EvidenceState
    production_sentinel: EvidenceState
    mcp_parity: EvidenceState
    qdrant_degradation: EvidenceState
    corruption_isolation: EvidenceState
    context_baseline: EvidenceState
    scale: EvidenceState
    owner_review: EvidenceState
    reboot_recovery: EvidenceState
    mac_release: EvidenceState
    windows_release: EvidenceState

    _FUNCTIONAL_FIELDS = (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
    )
    _MAC_FIELDS = ("scale", "owner_review", "reboot_recovery", "mac_release")

    @property
    def functional_measured(self) -> bool:
        return all(self._state(field) in (EvidenceState.READY, EvidenceState.FAILED) for field in self._FUNCTIONAL_FIELDS)

    @property
    def functional_ready(self) -> bool:
        return all(self._state(field) is EvidenceState.READY for field in self._FUNCTIONAL_FIELDS)

    @property
    def scale_ready(self) -> bool:
        """Measured functional quality required before the isolated scale run.

        Production/Vault sentinels are deliberately outside the Acceptance
        scale fixture.  They remain nullable and gate the later full phase,
        rather than making the Task7 scale admission circular.
        """
        return all(
            self._state(field) is EvidenceState.READY
            for field in self._FUNCTIONAL_FIELDS
            if field != "production_sentinel"
        )

    @property
    def mac_release_ready(self) -> bool:
        return self.functional_ready and all(self._state(field) is EvidenceState.READY for field in self._MAC_FIELDS)

    @property
    def windows_release_ready(self) -> bool:
        return self.mac_release_ready and self._state("windows_release") is EvidenceState.READY

    # Compatibility names are intentionally derived only; the runner still
    # has its historical return contract until Task 6 migrates it.
    @property
    def functional_fields_ready(self) -> bool:
        return self.functional_ready

    @property
    def functional_status(self) -> str:
        return "PASS" if self.functional_ready else "NOT_EVALUATED"

    @property
    def should_run_acceptance_gate(self) -> bool:
        return self.functional_measured

    def _state(self, field: str) -> EvidenceState | Any:
        return getattr(self, field)


@dataclass(frozen=True)
class QualityRunEnvelope:
    readiness: QualityEvidenceReadiness
    production_pollution: int | None
    evaluation_report: EvaluationReport | None
    functional_status: Literal["NOT_EVALUATED", "PASS", "FAIL"]
    phase_status: Literal["NOT_EVALUATED", "PASS", "FAIL", "BLOCKED"]
    windows_status: Literal["NOT_EVALUATED", "PASS", "FAIL", "BLOCKED"]
    blocked_reasons: tuple[str, ...]
    # This inventory is deliberately machine-only: it reports cleanup state
    # without embedding paths, exception text, fixture content or tokens.
    cleanup_inventory: Mapping[str, Any] = field(default_factory=dict)
    # Measured, path-free functional details retained for the quality report.
    evidence_details: Mapping[str, Any] = field(default_factory=dict)
    run_id: str | None = None
    fixture_hashes: Mapping[str, str] = field(default_factory=dict)
    quality_evidence_readiness: Mapping[str, Any] = field(default_factory=dict)
    code_commit: str | None = None
    # Task 3's immutable per-question diagnostics are an additional evidence
    # projection; canonical Task 2 aggregate fields remain authoritative.
    question_diagnostics: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    grouped_question_metrics: Mapping[str, Mapping[str, int]] = field(default_factory=dict)


def _reason_codes(values: Sequence[str]) -> tuple[str, ...]:
    allowed = {
        "WINDOWS_AFTER_MAC", "INVALID_EVIDENCE", "PRODUCTION_SENTINEL_MISMATCH",
        "PRODUCTION_SENTINEL_NOT_MEASURED",
        "MALFORMED_EVALUATION_REPORT", "GATE_EXCEPTION", "MALFORMED_GATE_RESULT",
        "CONTRADICTORY_FUNCTIONAL_EVIDENCE", "CONTRADICTORY_GATE_RESULT",
        "TEMP_CLEANUP_FAILED", "TEMP_CLEANUP_INCOMPLETE",
        "RUNNER_FAILED",
        "OWNER_REVIEW_NOT_RUN_IN_AUTOMATED_GATE", "REBOOT_RECOVERY_NOT_RUN_IN_AUTOMATED_GATE",
        "MAC_M5_P95_RESERVED_FOR_TASK_6", "MAC_IDLE_CPU_RESERVED_FOR_TASK_6",
    }
    for field in QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",):
        for state in EvidenceState:
            allowed.add(f"{field.upper()}_{state.value.upper()}")
    for stage in (
        "ADMISSION", "ROOT", "SENTINEL", "FIXTURE", "IMPORT", "GATEWAY",
        "PROMOTION", "AUDIT", "SCORING", "EVALUATOR", "PUBLICATION_PRE",
        "CLEANUP",
    ):
        allowed.add(f"RUNNER_{stage}_FAILED")
    result: list[str] = []
    try:
        iterator = iter(values)
        while True:
            try:
                value = next(iterator)
            except StopIteration:
                break
            except Exception:
                return ("UNTRUSTED_BLOCKED_REASON",)
            if type(value) is not str:
                code = "UNTRUSTED_BLOCKED_REASON"
            else:
                code = value.upper()
                if code not in allowed:
                    code = "UNTRUSTED_BLOCKED_REASON"
            if code not in result:
                result.append(code)
    except Exception:
        return ("UNTRUSTED_BLOCKED_REASON",)
    return tuple(result)


def _closed_envelope(readiness: QualityEvidenceReadiness, pollution: int | None, reasons: Sequence[str], *, measured_failure: bool = False) -> QualityRunEnvelope:
    if measured_failure:
        return QualityRunEnvelope(readiness, pollution, None, "FAIL", "FAIL", "BLOCKED", _reason_codes(reasons))
    return QualityRunEnvelope(readiness, pollution, None, "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED", _reason_codes(reasons))


def _safe_reason_values(values: Sequence[str]) -> tuple[Any, ...]:
    try:
        return tuple(values)
    except Exception:
        return ("UNTRUSTED_BLOCKED_REASON",)


def _valid_counter(value: Any) -> bool:
    return type(value) is int and value >= 0


def _valid_percentage(value: Any) -> bool:
    import math
    return (
        type(value) in (int, float)
        and math.isfinite(float(value)) and 0 <= float(value) <= 100
    )


def _valid_ratio(numerator: Any, denominator: Any, percentage: Any) -> bool:
    import math
    return (_valid_counter(numerator) and _valid_counter(denominator) and denominator > 0
            and numerator <= denominator and _valid_percentage(percentage)
            and math.isclose(float(percentage), 100 * numerator / denominator, rel_tol=1e-9, abs_tol=1e-9))


def _valid_evaluation_report(report: EvaluationReport, pollution: int) -> bool:
    if type(report) is not EvaluationReport:
        return False
    counters = (
        "answered_questions", "imported_messages", "expected_messages", "ordered_role_matches",
        "expected_ordered_roles", "valid_fact_hits", "valid_fact_total", "citation_hits", "citation_total",
        "automatic_activation_correct", "automatic_activation_total", "protected_false_promotions",
        "stale_current_leaks", "duplicate_records", "baseline_context_chars", "rendered_context_chars",
        "mcp_successes", "mcp_attempts", "production_pollution",
    )
    if any(not _valid_counter(getattr(report, field, None)) for field in counters):
        return False
    if report.production_pollution != pollution:
        return False
    if not all(_valid_ratio(*values) for values in (
        (report.valid_fact_hits, report.valid_fact_total, report.valid_fact_recall),
        (report.citation_hits, report.citation_total, report.citation_accuracy),
        (report.automatic_activation_correct, report.automatic_activation_total, report.automatic_activation_accuracy),
        (report.mcp_successes, report.mcp_attempts, report.mcp_success_rate),
    )):
        return False
    if not _valid_counter(report.baseline_context_chars) or report.baseline_context_chars <= 0:
        return False
    if report.rendered_context_chars > report.baseline_context_chars or not _valid_percentage(report.context_reduction):
        return False
    import math
    if not math.isclose(
        float(report.context_reduction),
        (1 - report.rendered_context_chars / report.baseline_context_chars) * 100,
        rel_tol=1e-9, abs_tol=1e-9,
    ):
        return False
    for field in ("owner_review_success", "reboot_recovery"):
        value = getattr(report, field)
        if value is not None and not _valid_percentage(value):
            return False
    if type(report.blocked_reasons) is not tuple or any(
        type(reason) is not str or not reason for reason in report.blocked_reasons
    ):
        return False
    return True


def finalize_quality_envelope(
    *,
    readiness: QualityEvidenceReadiness,
    production_pollution: int | None,
    evaluation_report: Any | None,
    acceptance_gate: Any,
    blocked_reasons: Sequence[str] = (),
    measured_failure: bool = False,
) -> QualityRunEnvelope:
    """Finalize immutable evidence around the unchanged frozen evaluator."""
    from dataclasses import replace
    fields = QualityEvidenceReadiness._FUNCTIONAL_FIELDS + QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",)
    if type(readiness) is not QualityEvidenceReadiness:
        return _closed_envelope(readiness, None, ("INVALID_EVIDENCE",))
    try:
        readiness_valid = all(type(getattr(readiness, field)) is EvidenceState for field in fields)
    except Exception:
        return _closed_envelope(readiness, None, ("INVALID_EVIDENCE",))
    if not readiness_valid:
        return _closed_envelope(readiness, None, ("INVALID_EVIDENCE",))
    sentinel = readiness.production_sentinel
    pollution_valid = (
        (sentinel is EvidenceState.READY and type(production_pollution) is int and production_pollution == 0)
        or (sentinel is EvidenceState.FAILED and type(production_pollution) is int and production_pollution > 0)
        or (sentinel in (EvidenceState.NOT_MEASURED, EvidenceState.INVALID) and production_pollution is None)
    )
    if not pollution_valid:
        return _closed_envelope(readiness, None, ("PRODUCTION_SENTINEL_MISMATCH",))
    if not readiness.functional_measured:
        if readiness.scale_ready and readiness.production_sentinel is EvidenceState.NOT_MEASURED and not measured_failure:
            return QualityRunEnvelope(
                readiness, production_pollution, None, "PASS", "BLOCKED", "BLOCKED",
                _reason_codes(tuple(blocked_reasons) + ("PRODUCTION_SENTINEL_NOT_MEASURED",)),
            )
        return _closed_envelope(readiness, production_pollution, blocked_reasons, measured_failure=measured_failure)
    if type(evaluation_report) is not EvaluationReport:
        return _closed_envelope(readiness, production_pollution, ("MALFORMED_EVALUATION_REPORT",))
    try:
        report_valid = _valid_evaluation_report(evaluation_report, production_pollution)
    except Exception:
        report_valid = False
    if not report_valid:
        return _closed_envelope(readiness, None, ("MALFORMED_EVALUATION_REPORT",))
    safe_reasons = _safe_reason_values(blocked_reasons)
    try:
        functional_report = replace(evaluation_report, owner_review_success=100.0, reboot_recovery=100.0, blocked_reasons=())
        functional_verdict = acceptance_gate.evaluate(functional_report)
    except Exception:
        if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
            return QualityRunEnvelope(
                readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED",
                _reason_codes(safe_reasons + ("GATE_EXCEPTION", "WINDOWS_AFTER_MAC")),
            )
        return _closed_envelope(readiness, production_pollution, ("GATE_EXCEPTION",))
    if type(functional_verdict) is not str or functional_verdict not in ("PASS", "FAIL"):
        if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
            return QualityRunEnvelope(
                readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED",
                _reason_codes(safe_reasons + ("MALFORMED_GATE_RESULT", "WINDOWS_AFTER_MAC")),
            )
        return _closed_envelope(readiness, production_pollution, ("MALFORMED_GATE_RESULT",))
    try:
        frozen_verdict = acceptance_gate.evaluate(evaluation_report)
    except Exception:
        if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
            return QualityRunEnvelope(
                readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED",
                _reason_codes(safe_reasons + ("GATE_EXCEPTION", "WINDOWS_AFTER_MAC")),
            )
        return _closed_envelope(readiness, production_pollution, ("GATE_EXCEPTION",))
    if type(frozen_verdict) is not str or frozen_verdict not in ("PASS", "FAIL", "BLOCKED"):
        if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
            return QualityRunEnvelope(
                readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED",
                _reason_codes(safe_reasons + ("MALFORMED_GATE_RESULT", "WINDOWS_AFTER_MAC")),
            )
        return _closed_envelope(readiness, production_pollution, ("MALFORMED_GATE_RESULT",))
    if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
        if functional_verdict == "PASS":
            # A measured failure is authoritative even if a downstream gate
            # incorrectly claims PASS.  Preserve the report for diagnosis and
            # never downgrade a real failure into an unavailable/blocked state.
            return QualityRunEnvelope(
                readiness,
                production_pollution,
                evaluation_report,
                "FAIL",
                "FAIL",
                "BLOCKED",
                _reason_codes(safe_reasons + ("CONTRADICTORY_FUNCTIONAL_EVIDENCE", "WINDOWS_AFTER_MAC")),
            )
    if functional_verdict == "FAIL":
        return QualityRunEnvelope(readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED", _reason_codes(safe_reasons + ("WINDOWS_AFTER_MAC",)))
    if any(getattr(readiness, field) in (EvidenceState.FAILED,) for field in QualityEvidenceReadiness._MAC_FIELDS):
        phase = "FAIL"
        reasons = safe_reasons
    elif not readiness.mac_release_ready:
        reasons_list = list(safe_reasons)
        for field in QualityEvidenceReadiness._MAC_FIELDS:
            state = getattr(readiness, field)
            if state is not EvidenceState.READY:
                reasons_list.append(f"{field}_{state.value}")
        phase = "BLOCKED"
        reasons = tuple(reasons_list)
    elif frozen_verdict == "PASS":
        phase = "PASS"
        reasons = safe_reasons
    elif frozen_verdict == "FAIL":
        phase = "FAIL"
        reasons = safe_reasons
    else:
        return _closed_envelope(readiness, production_pollution, ("CONTRADICTORY_GATE_RESULT",))
    if phase != "PASS":
        windows = "BLOCKED"
        reasons = tuple(reasons) + ("WINDOWS_AFTER_MAC",)
    elif readiness.windows_release is EvidenceState.READY:
        windows = "PASS"
    elif readiness.windows_release is EvidenceState.FAILED:
        windows = "FAIL"
    else:
        windows = "BLOCKED"
        reasons = tuple(reasons) + (f"windows_release_{readiness.windows_release.value}",)
    return QualityRunEnvelope(readiness, production_pollution, evaluation_report, "PASS", phase, windows, _reason_codes(reasons))
