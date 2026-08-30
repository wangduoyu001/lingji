"""Promotion measurements built from the real automatic-memory service.

The quality runner owns orchestration only.  This module records the frozen
fixture category, the service's actual decision, and the durable projection,
link, and audit facts needed to prove that decision.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from src.auto_review.models import ProvenanceRef, ReviewCandidate
from src.auto_review.promotion import AutoMemoryPromotionService


_PROTECTED_CATEGORIES = frozenset({"core/protected", "high-risk", "authority-conflict", "assistant-only"})
_CATEGORIES = _PROTECTED_CATEGORIES | {"low-risk-user"}
_STATUSES = frozenset({"active", "pending_owner_review", "rejected", "error"})
_ALLOWED_REASON_CODES = frozenset({
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
_STORAGE_REASON_CODES = frozenset({"promotion_payload_redacted"})


def promotion_category(record: Any) -> str:
    """Classify a frozen record from its explicit contract fields only."""
    memory_kind = str(getattr(record, "memory_kind", "") or "").strip().lower()
    risk = str(getattr(record, "risk", "") or "").strip().lower()
    privacy = str(getattr(record, "privacy", "") or "").strip().lower()
    authority = str(getattr(record, "authority", "") or "").strip().lower()
    if memory_kind in {"core", "core_memory", "protected_candidate"} or privacy in {"restricted", "sensitive", "secret"}:
        return "core/protected"
    if risk in {"high", "critical"}:
        return "high-risk"
    if memory_kind in {"authority_conflict", "conflict"}:
        return "authority-conflict"
    if authority in {"assistant", "assistant-suggestion", "assistant_inference", "assistant-inference", "ai_inference", "ai-inference"}:
        return "assistant-only"
    return "low-risk-user"


def expected_status(record: Any) -> str:
    """Return the current product contract while activation is quarantined."""
    return "pending_owner_review"


def activation_measurement(outcomes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Represent quarantined activation as unavailable after checking truth.

    The quality counter remains intentionally unavailable while quarantine is
    in force.  We still inspect every persisted outcome first, so a forged
    active/error status, category projection, or missing quarantine reason can
    never be hidden behind a convenient ``not_applicable`` result.
    """
    if not isinstance(outcomes, Sequence) or isinstance(outcomes, (str, bytes)) or not outcomes:
        raise ValueError("activation evidence is empty or malformed")
    for item in outcomes:
        _validate_activation_truth(item)
    return {"status": "not_applicable", "correct": None, "total": None, "accuracy": None}


def _reason_codes(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError(f"activation {label} evidence is missing")
    result: list[str] = []
    for reason in value:
        if not isinstance(reason, str) or not reason.strip() or reason != reason.strip() or reason not in _ALLOWED_REASON_CODES:
            raise ValueError(f"activation {label} evidence is malformed")
        result.append(reason)
    if len(result) != len(set(result)):
        raise ValueError(f"activation {label} evidence is duplicated")
    return tuple(result)


def _validate_activation_truth(item: Mapping[str, Any]) -> None:
    if not isinstance(item, Mapping):
        raise ValueError("activation evidence is malformed")
    fixture_category = item.get("fixture_category")
    expected_category = item.get("expected_category")
    category = item.get("category")
    if (
        fixture_category not in _CATEGORIES
        or expected_category != fixture_category
        or category != fixture_category
    ):
        raise ValueError("activation category evidence is contradictory")
    expected_status = item.get("expected_status")
    if expected_status != "pending_owner_review":
        raise ValueError("activation expectation is outside quarantine contract")
    service_status = item.get("service_status", item.get("status"))
    durable_status = item.get("durable_status", item.get("persisted_status"))
    if service_status != item.get("status") or durable_status != service_status:
        raise ValueError("activation actual status disagrees with durable status")
    if "actual_status" in item and item["actual_status"] != service_status:
        raise ValueError("activation actual status disagrees with service status")
    if "persisted_status" in item and item["persisted_status"] != durable_status:
        raise ValueError("activation persisted status disagrees with durable status")
    if service_status != "pending_owner_review":
        raise ValueError("activation actual status violates quarantine")
    service_category = item.get("service_category", category)
    durable_category = item.get("durable_category")
    if service_category != fixture_category or durable_category != fixture_category:
        raise ValueError("activation durable category disagrees with fixture")
    service_reasons = _reason_codes(item.get("service_reason_codes", item.get("reason_codes")), "service reason")
    durable_reasons = _reason_codes(item.get("durable_reason_codes"), "durable reason")
    reasons = _reason_codes(item.get("reason_codes"), "reason")
    if not set(durable_reasons) - set(service_reasons) <= _STORAGE_REASON_CODES or not set(service_reasons) <= set(durable_reasons) or reasons != service_reasons:
        raise ValueError("activation reason evidence disagrees with durable truth")


def _ids(values: Any, label: str) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"promotion_provenance {label} are malformed")
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"promotion_provenance {label} identity is empty or malformed")
        result.append(value)
    return result


def validate_promotion_measurement(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate durable promotion evidence and return measured counters.

    This deliberately computes every duplicate/missing/extra count from the
    supplied rows.  A caller cannot claim a clean result by filling in a zero.
    """
    if not isinstance(payload, Mapping):
        raise ValueError("promotion_provenance payload is malformed")
    raw_outcomes = payload.get("outcomes")
    if not isinstance(raw_outcomes, Sequence) or isinstance(raw_outcomes, (str, bytes)):
        raise ValueError("promotion_provenance outcomes are malformed")
    outcomes = [dict(item) for item in raw_outcomes if isinstance(item, Mapping)]
    if len(outcomes) != len(raw_outcomes) or not outcomes:
        raise ValueError("promotion_provenance outcomes are malformed")
    outcome_ids = []
    seen_decisions: set[str] = set()
    for item in outcomes:
        memory_id = item.get("memory_id")
        if not isinstance(memory_id, str) or not memory_id.strip() or memory_id != memory_id.strip():
            raise ValueError("promotion_provenance outcome identity is empty or malformed")
        outcome_ids.append(memory_id)
        if "decision_id" in item:
            decision_id = item.get("decision_id")
            if not isinstance(decision_id, str) or not decision_id.strip() or decision_id != decision_id.strip():
                raise ValueError("promotion_provenance decision identity is empty or malformed")
            if decision_id in seen_decisions:
                raise ValueError("promotion_provenance duplicate decision identity")
            seen_decisions.add(decision_id)
    if len(outcome_ids) != len(set(outcome_ids)):
        raise ValueError("promotion_provenance duplicate outcomes")
    for item in outcomes:
        status = item.get("status")
        if status not in _STATUSES:
            raise ValueError("promotion_provenance unknown outcome status")
        category = item.get("category")
        if category not in _CATEGORIES:
            raise ValueError("promotion_provenance unknown outcome category")
        if "expected_category" in item and item["expected_category"] != category:
            raise ValueError("promotion_provenance contradictory category")
        if "fixture_category" in item and item["fixture_category"] != category:
            raise ValueError("promotion_provenance contradictory category")
        if "expected_status" in item and item["expected_status"] != "pending_owner_review":
            raise ValueError("promotion_provenance unexpected quarantine status")
        if category in _PROTECTED_CATEGORIES and status == "active":
            raise ValueError("promotion_provenance protected outcome active")

    projection_ids = _ids(payload.get("projection_ids", ()), "projection")
    audit_ids = _ids(payload.get("audit_ids", ()), "audit")
    links = payload.get("memory_link_keys", ())
    if not isinstance(links, Sequence) or isinstance(links, (str, bytes)):
        raise ValueError("promotion_provenance links are malformed")
    link_keys = []
    for link in links:
        if not isinstance(link, Sequence) or isinstance(link, (str, bytes)) or len(link) != 2:
            raise ValueError("promotion_provenance link identity is malformed")
        message_id, memory_id = link
        if any(not isinstance(value, str) or not value.strip() or value != value.strip() for value in (message_id, memory_id)):
            raise ValueError("promotion_provenance link identity is empty")
        link_keys.append((message_id, memory_id))

    duplicate_projection_records = len(projection_ids) - len(set(projection_ids))
    duplicate_audit_records = len(audit_ids) - len(set(audit_ids))
    duplicate_links = len(link_keys) - len(set(link_keys))
    projection_set, audit_set = set(projection_ids), set(audit_ids)
    outcome_set = set(outcome_ids)
    missing_projection = sorted({item["memory_id"] for item in outcomes if item["status"] == "active"} - projection_set)
    extra_projection = sorted(projection_set - {item["memory_id"] for item in outcomes if item["status"] == "active"})
    missing_audit = sorted(outcome_set - audit_set)
    extra_audit = sorted(audit_set - outcome_set)
    active_ids = {item["memory_id"] for item in outcomes if item["status"] == "active"}
    linked_memory_ids = {memory_id for _, memory_id in link_keys}
    if any(item["status"] != "active" and item["memory_id"] in projection_set for item in outcomes):
        raise ValueError("promotion_provenance non-active projection")
    if any(item["status"] != "active" and item["memory_id"] in linked_memory_ids for item in outcomes):
        raise ValueError("promotion_provenance non-active link")
    if missing_projection or extra_projection or missing_audit or extra_audit or duplicate_projection_records or duplicate_audit_records or duplicate_links:
        raise ValueError("promotion_provenance missing/extra/duplicate evidence")
    if active_ids != linked_memory_ids:
        raise ValueError("promotion_provenance active link mismatch")
    return {
        "status": "ready",
        "expected": len(outcomes),
        "actual": len(outcomes),
        "active": sum(item["status"] == "active" for item in outcomes),
        "pending": sum(item["status"] == "pending_owner_review" for item in outcomes),
        "rejected": sum(item["status"] == "rejected" for item in outcomes),
        "error": sum(item["status"] == "error" for item in outcomes),
        "links_expected": len(active_ids),
        "links_actual": len(link_keys),
        "missing_projection": len(missing_projection),
        "extra_projection": len(extra_projection),
        "missing_audit": len(missing_audit),
        "extra_audit": len(extra_audit),
        "duplicate_records": duplicate_projection_records,
        "duplicate_audits": duplicate_audit_records,
        "duplicate_links": duplicate_links,
    }


def _event_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("payload_json")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    value = row.get("payload")
    return dict(value) if isinstance(value, Mapping) else {}


def _persisted_category(payload: Mapping[str, Any]) -> str | None:
    explicit = payload.get("category")
    if isinstance(explicit, str) and explicit.strip():
        return explicit
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    memory_kind = str(payload.get("memory_type") or metadata.get("memory_type") or "").strip().lower()
    privacy = str(payload.get("privacy") or metadata.get("privacy") or "").strip().lower()
    authority = str(payload.get("authority") or metadata.get("authority") or "").strip().lower()
    risk_flags = payload.get("risk_flags") or metadata.get("risk_flags") or ()
    if isinstance(risk_flags, str):
        risk_flags = (risk_flags,)
    risk = str(next(iter(risk_flags), "") or "").strip().lower()
    if memory_kind in {"core", "core_memory", "protected_candidate"} or privacy in {"restricted", "sensitive", "secret"}:
        return "core/protected"
    if risk in {"high", "critical"}:
        return "high-risk"
    if memory_kind in {"authority_conflict", "conflict"}:
        return "authority-conflict"
    if authority in {"assistant", "assistant-suggestion", "assistant_inference", "assistant-inference", "ai_inference", "ai-inference", "assistant_suggestion"}:
        return "assistant-only"
    if memory_kind or privacy or authority:
        return "low-risk-user"
    return None


def _durable_promotion_truth(state_db: Any, *, memory_id: str, decision_id: str) -> dict[str, Any] | None:
    recent_events = getattr(state_db, "recent_events", None)
    if not callable(recent_events) or not memory_id or not decision_id:
        return None
    try:
        events = recent_events(limit=100000)
    except Exception:
        return None
    for row in events:
        if not isinstance(row, Mapping) or str(row.get("event_type") or "") not in {
            "memory_promotion_decision", "memory_promotion_owner_approved",
            "memory_promotion_owner_rejected",
        }:
            continue
        payload = _event_payload(row)
        if str(payload.get("decision_id") or "") != decision_id:
            continue
        candidate_id = str(payload.get("candidate_id") or payload.get("memory_id") or "")
        if candidate_id != memory_id:
            continue
        return {
            "decision_id": decision_id,
            "status": payload.get("status"),
            "category": _persisted_category(payload),
            "reason_codes": payload.get("reason_codes"),
        }
    return None


def _truth_projection(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "memory_id": item.get("memory_id"),
        "decision_id": item.get("decision_id"),
        "fixture_category": item.get("fixture_category"),
        "expected_category": item.get("expected_category"),
        "expected_status": item.get("expected_status"),
        "service_status": item.get("service_status"),
        "service_category": item.get("service_category"),
        "service_reason_codes": list(item.get("service_reason_codes") or ()),
        "durable_status": item.get("durable_status"),
        "durable_category": item.get("durable_category"),
        "durable_reason_codes": list(item.get("durable_reason_codes") or ()),
    }


def _validate_measured_truth(outcomes: Sequence[Mapping[str, Any]]) -> None:
    for item in outcomes:
        _validate_activation_truth(item)


@dataclass(frozen=True)
class PromotionMeasurement:
    status: str
    outcomes: tuple[dict[str, Any], ...]
    category_outcomes: Mapping[str, Mapping[str, int]]
    provenance: Mapping[str, Any]
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def measure_promotion_fixtures(
    corpus: Sequence[Any],
    message_map: Mapping[str, Mapping[str, Any]],
    memory_db: Any,
    read_model: Any,
    state_db: Any,
) -> PromotionMeasurement:
    """Run one actual service decision per frozen record and inspect storage."""
    service = AutoMemoryPromotionService(state_db=state_db, memory_db=memory_db, evidence_store=read_model)
    outcomes: list[dict[str, Any]] = []
    for record in corpus:
        category = promotion_category(record)
        message = message_map.get(str(record.fact_id))
        if not message:
            outcomes.append({
                "fact_id": record.fact_id, "fixture_category": category,
                "category": category, "expected_category": category,
                "expected_status": expected_status(record), "status": "error",
                "memory_id": "", "decision_id": "", "reason_codes": ["promotion_measurement_error"],
                "service_status": "error", "service_category": category,
                "service_reason_codes": ["promotion_measurement_error"],
                "durable_status": "error", "durable_category": category,
                "durable_reason_codes": ["promotion_measurement_error"],
            })
            continue
        configured_memory_id = message.get("promotion_memory_id")
        if not isinstance(configured_memory_id, str) or not configured_memory_id.strip() or configured_memory_id != configured_memory_id.strip():
            outcomes.append({
                "fact_id": str(record.fact_id), "fixture_category": category,
                "category": category, "expected_category": category,
                "expected_status": expected_status(record), "status": "error",
                "memory_id": "", "decision_id": "", "reason_codes": ["promotion_measurement_error"],
                "service_status": "error", "service_category": category,
                "service_reason_codes": ["promotion_measurement_error"],
                "durable_status": "error", "durable_category": category,
                "durable_reason_codes": ["promotion_measurement_error"],
            })
            continue
        memory_id = configured_memory_id
        lifecycle = str(getattr(record, "lifecycle", "") or "").lower()
        source_message_id = message.get("message_id")
        source_content_hash = message.get("content_hash")
        if (
            not isinstance(source_message_id, str) or not source_message_id.strip() or source_message_id != source_message_id.strip()
            or not isinstance(source_content_hash, str) or not source_content_hash.strip() or source_content_hash != source_content_hash.strip()
        ):
            outcomes.append({
                "fact_id": str(record.fact_id), "fixture_category": category,
                "category": category, "expected_category": category,
                "expected_status": expected_status(record), "status": "error",
                "memory_id": memory_id, "decision_id": "", "reason_codes": ["promotion_measurement_error"],
                "service_status": "error", "service_category": category,
                "service_reason_codes": ["promotion_measurement_error"],
                "durable_status": "error", "durable_category": category,
                "durable_reason_codes": ["promotion_measurement_error"],
            })
            continue
        source_ref = ProvenanceRef("message", source_message_id, source_content_hash)
        metadata = {
            "direct_user_evidence": str(record.authority).lower() == "owner-confirmed",
            "memory_type": record.memory_kind,
            "project_ids": [record.project_id],
            "privacy": record.privacy,
            "agent_scope": list(record.agent_scope),
            "valid_from": record.occurred_at,
            "modified_at": record.occurred_at,
            "has_conflict": category == "authority-conflict" or lifecycle in {"superseded", "invalidated"},
            "current_authoritative": lifecycle == "active",
        }
        flags = (str(record.risk).lower(),) if str(record.risk).lower() in {"high", "critical"} else ()
        candidate = ReviewCandidate(
            memory_id=memory_id, title=record.topic_key, content=record.content,
            memory_type=record.memory_kind, privacy=record.privacy,
            project_ids=(record.project_id,), source_refs=(source_ref,),
            confidence=0.99 if expected_status(record) == "active" else 0.80,
            authority="user_explicit" if str(record.authority).lower() == "owner-confirmed" else "assistant_suggestion",
            source_kind="current_project_document" if str(record.authority).lower() == "owner-confirmed" else "assistant_inference",
            extractor_version="automatic-memory-v1", metadata=metadata, risk_flags=flags,
        )
        try:
            decision = service.evaluate(candidate)
            actual_status = str(decision.get("status") or "error")
            actual_memory = decision.get("candidate_id")
            if not isinstance(actual_memory, str) or not actual_memory.strip() or actual_memory != actual_memory.strip():
                actual_memory = ""
            reason_codes = tuple(str(item) for item in (decision.get("reason_codes") or ()))
            decision_id = str(decision.get("decision_id") or "")
            service_category = decision.get("category") or category
        except Exception:
            actual_status, actual_memory, reason_codes, decision_id, service_category = "error", "", ("promotion_measurement_error",), "", category
        durable = _durable_promotion_truth(state_db, memory_id=actual_memory, decision_id=decision_id)
        durable_status = durable.get("status") if durable else None
        durable_category = durable.get("category") if durable else None
        durable_reasons = durable.get("reason_codes") if durable else None
        outcomes.append({
            "fact_id": str(record.fact_id), "fixture_category": category,
            "category": service_category, "expected_category": category,
            "expected_status": expected_status(record), "status": actual_status,
            "persisted_status": durable_status,
            "memory_id": actual_memory, "decision_id": decision_id,
            "reason_codes": list(reason_codes),
            "service_status": actual_status, "service_category": service_category,
            "service_reason_codes": list(reason_codes),
            "durable_status": durable_status, "durable_category": durable_category,
            "durable_reason_codes": list(durable_reasons) if isinstance(durable_reasons, Sequence) and not isinstance(durable_reasons, (str, bytes)) else durable_reasons,
        })

    projection_rows = tuple(memory_db.list_derived_projection_identity_rows())
    projection_ids = [row.get("memory_id") if isinstance(row, Mapping) else None for row in projection_rows]
    links: list[tuple[str, str]] = []
    # Query from every imported message first.  Looking only through existing
    # projections misses an orphan link attached to a pending/rejected/error
    # decision, which is precisely the negative case this gate must detect.
    imported_message_ids = [message.get("message_id") if isinstance(message, Mapping) else None for message in message_map.values()]
    for message_id in sorted(imported_message_ids, key=lambda value: (value is None, str(value))):
        for row in read_model.message_links(message_id):
            linked_message_id = row.get("message_id") if isinstance(row, Mapping) else None
            memory_id = row.get("memory_id") if isinstance(row, Mapping) else None
            # Keep every relationship observed on every imported message.
            # Filtering to candidate IDs here would erase an orphan link
            # before the strict validator can classify it as extra evidence.
            links.append((linked_message_id, memory_id))
    audit_ids: list[str] = []
    for row in state_db.recent_events(limit=100000):
        if str(row.get("event_type") or "") not in {
            "memory_promotion_decision", "memory_promotion_owner_approved",
            "memory_promotion_owner_rejected", "memory_promotion_projection_error",
        }:
            continue
        payload = _event_payload(row)
        if isinstance(payload, Mapping) and payload.get("candidate_id"):
            audit_ids.append(str(payload["candidate_id"]))
    category_outcomes: dict[str, dict[str, int]] = {}
    for item in outcomes:
        bucket = category_outcomes.setdefault(item["category"], {"expected": 0, "actual": 0, "active": 0, "pending": 0, "rejected": 0, "error": 0})
        bucket["expected"] += 1
        status_key = item["status"] if item["status"] in {"active", "pending_owner_review", "rejected", "error"} else "error"
        bucket["actual"] += 1
        bucket["pending" if status_key == "pending_owner_review" else status_key] += 1
    try:
        _validate_measured_truth(outcomes)
        provenance = validate_promotion_measurement({
            "outcomes": outcomes,
            "projection_ids": projection_ids,
            "audit_ids": audit_ids,
            "memory_link_keys": links,
        })
        status, reason = "ready", ""
    except ValueError as exc:
        provenance = {"status": "failed", "reason": str(exc)}
        status, reason = "failed", "PROMOTION_PROVENANCE_FAILED"
    provenance = dict(provenance)
    provenance["outcomes"] = [_truth_projection(item) for item in outcomes]
    return PromotionMeasurement(status, tuple(outcomes), category_outcomes, provenance, reason)


__all__ = ["PromotionMeasurement", "activation_measurement", "expected_status", "measure_promotion_fixtures", "promotion_category", "validate_promotion_measurement"]
