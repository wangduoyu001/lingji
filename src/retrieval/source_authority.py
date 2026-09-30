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

    @staticmethod
    def _owner_approved_core(item: Mapping[str, Any]) -> bool:
        """主人门槛批准的 Core 记忆不随来源撤销隐藏。

        晋升（含 2026-09-22 起的自动晋升门槛）是主人对这条知识本身的批准；
        撤销来源只收回"继续采集与推导"，不改写已批准的永久记忆
        （Core 批量删除/改写须主人明确批准）。其余带来源链的派生层
        （evidence、evolving、候选）一律跟随来源授权。
        """
        return (
            str(item.get("memory_tier") or "").strip().lower() == "core"
            and str(item.get("review_status") or "").strip().lower() == "approved"
        )

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
            if self._governed(item)
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
                self._governed(item)
                and self._automatic_source_id(item)
                and not decisions.get(self._automatic_source_id(item), False)
            )
        ]
        return filtered, {"source_authority": status, "reason_code": reason}

    def authorize_source_ids(self, source_ids: set[str]) -> tuple[dict[str, bool], dict[str, str]]:
        decisions, status, reason = self._decisions({str(value).strip() for value in source_ids if str(value).strip()})
        return decisions, {"source_authority": status, "reason_code": reason}

    def allows_current(self, item: Mapping[str, Any]) -> tuple[bool, dict[str, str]]:
        source_id = self._automatic_source_id(item)
        if not source_id or self._owner_approved_core(item):
            return True, {"source_authority": "available", "reason_code": "none"}
        decisions, status, reason = self._decisions({source_id})
        return decisions.get(source_id, False), {"source_authority": status, "reason_code": reason}

    @classmethod
    def _governed(cls, item: Mapping[str, Any]) -> bool:
        """携带自动来源链且未被主人批准为 Core 的条目才受来源授权管辖。"""
        return bool(cls._automatic_source_id(item)) and not cls._owner_approved_core(item)
