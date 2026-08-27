from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


class SourceAuthorityResolver:
    """Query-time guard for automatic structured evidence.

    StateDatabase is the only authority.  MemoryDatabase status is a derived
    projection and therefore cannot make an automatic evidence result current.
    The resolver performs one StateDB read for all source IDs in a result set.
    """

    def __init__(self, state_db: Any | None):
        self.state_db = state_db

    @staticmethod
    def _automatic_source_id(item: Mapping[str, Any]) -> str:
        relationships = item.get("relationships") or {}
        if not isinstance(relationships, Mapping):
            return ""
        return str(relationships.get("automatic_memory_source_id") or "").strip()

    def _decisions(self, source_ids: set[str]) -> tuple[dict[str, bool], str, str]:
        if not source_ids:
            return {}, "available", "none"
        if self.state_db is None:
            return {source_id: False for source_id in source_ids}, "unavailable", "source_authority_unavailable"
        try:
            now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
            rows = self.state_db.list_automatic_memory_sources(now=now)
            authorized = {
                str(row.get("source_id") or "")
                for row in rows
                if str(row.get("status") or "").strip().lower() == "authorized"
            }
        except Exception:
            return {source_id: False for source_id in source_ids}, "unavailable", "source_authority_unavailable"
        decisions = {source_id: source_id in authorized for source_id in source_ids}
        if all(decisions.values()):
            return decisions, "available", "none"
        return decisions, "denied", "source_authority_denied"

    def filter_current(self, items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
        source_ids = {
            source_id
            for item in items
            if str(item.get("memory_type") or "") == "structured_evidence"
            for source_id in (self._automatic_source_id(item),)
            if source_id
        }
        decisions, status, reason = self._decisions(source_ids)
        if not source_ids:
            return items, {"source_authority": "available", "reason_code": "none"}
        filtered = [
            item
            for item in items
            if not (
                str(item.get("memory_type") or "") == "structured_evidence"
                and self._automatic_source_id(item)
                and not decisions.get(self._automatic_source_id(item), False)
            )
        ]
        return filtered, {"source_authority": status, "reason_code": reason}

    def authorize_source_ids(self, source_ids: set[str]) -> tuple[dict[str, bool], dict[str, str]]:
        decisions, status, reason = self._decisions({str(value).strip() for value in source_ids if str(value).strip()})
        return decisions, {"source_authority": status, "reason_code": reason}

    def allows_current(self, item: Mapping[str, Any]) -> tuple[bool, dict[str, str]]:
        if str(item.get("memory_type") or "") != "structured_evidence":
            return True, {"source_authority": "available", "reason_code": "none"}
        source_id = self._automatic_source_id(item)
        if not source_id:
            return True, {"source_authority": "available", "reason_code": "none"}
        decisions, status, reason = self._decisions({source_id})
        return decisions.get(source_id, False), {"source_authority": status, "reason_code": reason}
