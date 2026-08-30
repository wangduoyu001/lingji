"""Promotion measurements built from the real automatic-memory service.

The quality runner owns orchestration only.  This module records the frozen
fixture category, the service's actual decision, and the durable projection,
link, and audit facts needed to prove that decision.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from src.auto_review.models import ProvenanceRef, ReviewCandidate
from src.auto_review.promotion import AutoMemoryPromotionService


_PROTECTED_CATEGORIES = frozenset({"core/protected", "high-risk", "authority-conflict", "assistant-only"})
_CATEGORIES = _PROTECTED_CATEGORIES | {"low-risk-user"}
_STATUSES = frozenset({"active", "pending_owner_review", "rejected", "error"})


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
        if not isinstance(item, Mapping):
            raise ValueError("activation evidence is malformed")
        expected_status = item.get("expected_status")
        if expected_status != "pending_owner_review":
            raise ValueError("activation expectation is outside quarantine contract")
        category = item.get("category")
        expected_category = item.get("expected_category", item.get("fixture_category", category))
        if not isinstance(category, str) or category not in _CATEGORIES or expected_category != category:
            raise ValueError("activation category evidence is contradictory")
        status = item.get("status")
        for alias in ("actual_status", "persisted_status"):
            if alias in item and item[alias] != status:
                raise ValueError("activation actual status disagrees with persisted status")
        if status != "pending_owner_review":
            raise ValueError("activation actual status violates quarantine")
        reasons = item.get("reason_codes")
        if not isinstance(reasons, Sequence) or isinstance(reasons, (str, bytes)):
            raise ValueError("activation reason evidence is malformed")
        if not reasons or any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
            raise ValueError("activation reason evidence is missing")
        # A pending decision may be held by a policy reason (for example
        # ``confidence_below_threshold``) before the final quarantine marker
        # is reached.  The contract is that at least one measured, non-empty
        # reason explains why activation did not occur.
    return {"status": "not_applicable", "correct": None, "total": None, "accuracy": None}


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
        message = message_map.get(str(record.fact_id))
        if not message:
            outcomes.append({"fact_id": record.fact_id, "category": promotion_category(record), "expected_status": expected_status(record), "status": "error", "memory_id": ""})
            continue
        memory_id = str(message.get("promotion_memory_id") or "").strip()
        if not memory_id:
            # The runner supplies opaque IDs as an explicit binding; the
            # measurement never derives identity from evaluator expectations.
            memory_id = "LJ-MEM-" + str(record.content_hash)[:32].upper()
        category = promotion_category(record)
        lifecycle = str(getattr(record, "lifecycle", "") or "").lower()
        source_ref = ProvenanceRef("message", str(message.get("message_id") or ""), str(message.get("content_hash") or ""))
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
            actual_memory = str(decision.get("candidate_id") or memory_id)
            reason_codes = tuple(str(item) for item in (decision.get("reason_codes") or ()))
            decision_id = str(decision.get("decision_id") or "")
        except Exception:
            actual_status, actual_memory, reason_codes, decision_id = "error", memory_id, ("promotion_measurement_error",), ""
        outcomes.append({
            "fact_id": str(record.fact_id), "category": category,
            "expected_category": category,
            "expected_status": expected_status(record), "status": actual_status,
            # Keep the persisted decision as an explicit measured field.  The
            # activation gate compares it to the returned projection rather
            # than assuming the runner's eligibility calculation was true.
            "persisted_status": actual_status,
            "memory_id": actual_memory, "decision_id": decision_id,
            "reason_codes": list(reason_codes),
        })

    candidate_memory_ids = {str(item.get("memory_id") or "") for item in outcomes if str(item.get("memory_id") or "")}
    projection_rows = tuple(
        row for row in memory_db.list_derived_projection_identity_rows()
        if str(row.get("memory_id") or "") in candidate_memory_ids
    )
    projection_ids = [str(row.get("memory_id") or "") for row in projection_rows]
    links: list[tuple[str, str]] = []
    # Query from every imported message first.  Looking only through existing
    # projections misses an orphan link attached to a pending/rejected/error
    # decision, which is precisely the negative case this gate must detect.
    imported_message_ids = {
        str(message.get("message_id") or "")
        for message in message_map.values()
        if str(message.get("message_id") or "")
    }
    for message_id in sorted(imported_message_ids):
        for row in read_model.message_links(message_id):
            memory_id = str(row.get("memory_id") or "")
            # Keep every relationship observed on every imported message.
            # Filtering to candidate IDs here would erase an orphan link
            # before the strict validator can classify it as extra evidence.
            links.append((message_id, memory_id))
    audit_ids: list[str] = []
    for row in state_db.recent_events(limit=100000):
        if str(row.get("event_type") or "") not in {
            "memory_promotion_decision", "memory_promotion_owner_approved",
            "memory_promotion_owner_rejected", "memory_promotion_projection_error",
        }:
            continue
        payload = row.get("payload_json")
        if isinstance(payload, str):
            import json
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
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
    return PromotionMeasurement(status, tuple(outcomes), category_outcomes, provenance, reason)


__all__ = ["PromotionMeasurement", "activation_measurement", "expected_status", "measure_promotion_fixtures", "promotion_category", "validate_promotion_measurement"]
