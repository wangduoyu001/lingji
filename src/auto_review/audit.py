from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from .models import AutoReviewDecision


def build_shadow_audit_payload(
    decision: AutoReviewDecision,
    *,
    previous_hash: str = "",
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Create optional tamper-evident metadata over the existing audit event stream."""

    timestamp = evaluated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    decision_payload = decision.to_dict()
    material = {
        "previous_hash": str(previous_hash or ""),
        "evaluated_at": timestamp,
        "decision": decision_payload,
    }
    event_hash = hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        "evaluated_at": timestamp,
        "previous_hash": str(previous_hash or ""),
        "event_hash": event_hash,
        "decision": decision_payload,
        "mutation_performed": False,
    }


def verify_shadow_audit_payload(payload: Mapping[str, Any]) -> bool:
    decision = payload.get("decision")
    if not isinstance(decision, Mapping):
        return False
    material = {
        "previous_hash": str(payload.get("previous_hash") or ""),
        "evaluated_at": str(payload.get("evaluated_at") or ""),
        "decision": dict(decision),
    }
    expected = hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return bool(expected and expected == payload.get("event_hash"))
