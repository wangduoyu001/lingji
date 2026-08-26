"""One fail-closed temporal contract shared by lexical and semantic retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

AUTHORITY_ORDER = {
    "old_chat_inference": 10,
    "automatic_summary": 20,
    "verified_source": 30,
    "current_project_authority": 40,
    "user_explicit": 50,
}
EXCLUDED_CURRENT = {"superseded", "invalidated", "archived", "rejected"}
ALL_LIFECYCLE_STATUSES = (
    "active", "needs_review", "received", "superseded", "invalidated", "archived", "rejected"
)


def parse_instant(value: Any, *, default: datetime | None = None) -> datetime | None:
    if value in (None, ""):
        return default
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return default
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    try:
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


@dataclass(frozen=True)
class TemporalQuery:
    mode: str = "current"
    as_of: str | None = None
    instant: datetime | None = None
    valid: bool = True

    @classmethod
    def from_values(cls, mode: str = "current", as_of: Any = None) -> "TemporalQuery":
        selected = str(mode or "current").strip().lower()
        if selected not in {"current", "as_of", "history", "why"}:
            return cls(mode="current", as_of=None, instant=None, valid=False)
        if selected == "history":
            return cls(mode=selected, as_of=None, instant=None, valid=True)
        instant = parse_instant(as_of, default=datetime.now(timezone.utc))
        if instant is None:
            return cls(mode=selected, as_of=str(as_of), instant=None, valid=False)
        return cls(mode=selected, as_of=instant.isoformat().replace("+00:00", "Z"), instant=instant)

    def allows(self, record: dict[str, Any]) -> tuple[bool, str]:
        status = str(record.get("status") or "").strip().lower()
        if not status and self.mode != "history":
            return False, "missing_status"
        start = parse_instant(record.get("valid_from"))
        end = parse_instant(record.get("valid_to"))
        if record.get("valid_from") not in (None, "") and start is None:
            return False, "malformed_valid_from"
        if record.get("valid_to") not in (None, "") and end is None:
            return False, "malformed_valid_to"
        if self.mode == "history":
            return True, "history_requested"
        if not self.valid or self.instant is None:
            return False, "malformed_query_time"
        if status in EXCLUDED_CURRENT:
            if self.mode == "as_of" and status in {"superseded", "invalidated", "archived"}:
                pass
            else:
                return False, f"status_{status or 'missing'}"
        if start is not None and self.instant < start:
            return False, "not_yet_valid"
        if end is not None and self.instant >= end:
            return False, "expired"
        return True, "currently_valid" if self.mode in {"current", "why"} else "valid_at_requested_time"


def authority_value(value: Any) -> int:
    return AUTHORITY_ORDER.get(str(value or "").strip().lower(), 0)


def temporal_fields(record: dict[str, Any]) -> dict[str, Any]:
    relationships = record.get("relationships") or {}
    if not isinstance(relationships, dict):
        relationships = {}
    authority = record.get("authority") or relationships.get("authority") or ""
    sources = record.get("source_refs") or relationships.get("evidence_refs") or relationships.get("sources") or []
    if isinstance(sources, str):
        sources = [sources]
    return {
        "status": record.get("status"),
        "valid_from": record.get("valid_from"),
        "valid_to": record.get("valid_to"),
        "superseded_by": record.get("superseded_by") or relationships.get("superseded_by") or "",
        "reason": record.get("supersession_reason") or record.get("invalidating_reason") or relationships.get("supersession_reason") or relationships.get("invalidating_reason") or "",
        "authority": authority,
        "authority_rank": authority_value(authority),
        "source_refs": [str(item) for item in sources if str(item).strip()],
        "created_by": record.get("created_by") or relationships.get("created_by") or "",
        "confirmed_by": record.get("confirmed_by") or relationships.get("confirmed_by") or "",
        "policy_version": record.get("policy_version") or relationships.get("policy_version") or "",
        "extractor_version": record.get("extractor_version") or relationships.get("extractor_version") or "",
    }
