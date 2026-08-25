from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.storage import StateDatabase

from .models import AuthorizationScope, ScanRun, SourceRecord


POLICY_VERSION = "automatic-memory-source-v1"
METADATA_DISCOVERY_CAPABILITY = "metadata_discovery"
_SCAN_STATUSES = {"running", "paused", "failed", "completed", "cancelled"}


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _canonical_root(root: str) -> str:
    if not isinstance(root, str) or not root.strip():
        raise ValueError("source root is required")
    candidate = Path(root).expanduser()
    absolute = Path(os.path.abspath(os.path.normpath(str(candidate))))
    current = absolute
    while current != current.parent:
        if current.is_symlink():
            raise PermissionError("symbolic-link source roots are not allowed")
        current = current.parent
    # Absolute/normpath canonicalization intentionally does not inspect or read
    # the directory; registration is metadata-only and exact-root based.
    return str(absolute)


class SourceRegistry:
    """Persistent authorization registry backed by the existing StateDatabase."""

    def __init__(self, state_db: StateDatabase):
        self.state_db = state_db

    def register(self, scope: AuthorizationScope, kind: str, root: str) -> SourceRecord:
        if not scope.owner_confirmed:
            raise PermissionError("owner confirmation is required")
        if not scope.grant_id.strip():
            raise ValueError("grant_id is required")
        if not kind or kind not in scope.source_kinds:
            raise PermissionError("source kind is not authorized")
        selected_root = _canonical_root(root)
        allowed_roots = {_canonical_root(value) for value in scope.roots}
        if selected_root not in allowed_roots:
            raise PermissionError("source root is not exactly authorized")
        now = datetime.now(timezone.utc)
        expires_at = (
            scope.expires_at
            if scope.expires_at is None or scope.expires_at.tzinfo is not None
            else scope.expires_at.replace(tzinfo=timezone.utc)
        )
        granted_at = (
            scope.granted_at
            if scope.granted_at.tzinfo is not None
            else scope.granted_at.replace(tzinfo=timezone.utc)
        )
        if expires_at is not None and expires_at <= now:
            raise PermissionError("authorization scope has expired")
        if granted_at > now:
            raise ValueError("authorization cannot be granted in the future")

        grant_values = {
            "grant_id": scope.grant_id,
            "source_kinds_json": json.dumps(
                sorted(set(scope.source_kinds)), ensure_ascii=False
            ),
            "roots_json": json.dumps(
                sorted(allowed_roots), ensure_ascii=False
            ),
            "granted_at": _iso(granted_at),
            "expires_at": _iso(expires_at) if expires_at else None,
            "owner_confirmed": scope.owner_confirmed,
            "created_at": _iso(now),
        }
        source_values = {
            "source_id": f"src-{uuid.uuid4().hex}",
            "grant_id": scope.grant_id,
            "kind": kind,
            "root": selected_root,
            "status": "authorized",
            "capability": METADATA_DISCOVERY_CAPABILITY,
            "policy_version": POLICY_VERSION,
            "created_at": _iso(now),
        }
        try:
            existing_source = self.state_db.register_automatic_memory_source_atomic(
                grant_values, source_values
            )
        except ValueError as exc:
            raise PermissionError(str(exc)) from exc
        if existing_source["status"] == "revoked":
            raise PermissionError("source authorization has been revoked")
        return self._source(existing_source)

    def revoke(self, source_id: str) -> SourceRecord:
        revoked_at = _iso(datetime.now(timezone.utc))
        try:
            source = self.state_db.revoke_automatic_memory_source_atomic(
                source_id,
                revoked_at=revoked_at,
                reason="source authorization revoked",
            )
        except KeyError as exc:
            raise LookupError(f"source not found: {source_id}") from exc
        return self._source(source)

    def list_sources(self) -> list[SourceRecord]:
        now = _iso(datetime.now(timezone.utc))
        return [
            self._source(row)
            for row in self.state_db.list_automatic_memory_sources(now=now)
        ]

    def start_scan(self, source_id: str) -> ScanRun:
        now = _iso(datetime.now(timezone.utc))
        try:
            row = self.state_db.start_automatic_memory_scan_atomic(
                source_id,
                {
                    "scan_id": f"scan-{uuid.uuid4().hex}",
                    "source_id": source_id,
                    "status": "running",
                    "cursor": None,
                    "progress": 0,
                    "total": None,
                    "last_error": None,
                    "recovery_token": None,
                    "updated_at": now,
                },
                now=now,
            )
        except KeyError as exc:
            raise LookupError(f"source not found: {source_id}") from exc
        return self._scan(row)

    def _require_active_source(self, source_id: str) -> dict[str, Any]:
        source = self.state_db.get_automatic_memory_source(
            source_id, now=_iso(datetime.now(timezone.utc))
        )
        if source is None:
            raise LookupError(f"source not found: {source_id}")
        if source["status"] == "expired":
            raise PermissionError("source authorization has expired")
        if source["status"] != "authorized":
            raise PermissionError("source is not authorized for scanning")
        return source

    def pause_scan(self, scan_id: str) -> ScanRun:
        scan = self._require_scan(scan_id)
        recovery_token = scan.recovery_token or f"resume-{secrets.token_urlsafe(18)}"
        try:
            row = self.state_db.pause_automatic_memory_scan_atomic(
                scan_id,
                recovery_token=recovery_token,
                now=_iso(datetime.now(timezone.utc)),
            )
        except KeyError as exc:
            raise LookupError(f"scan not found: {scan_id}") from exc
        return self._scan(row)

    def retry_scan(self, scan_id: str) -> ScanRun:
        try:
            row = self.state_db.retry_automatic_memory_scan_atomic(
                scan_id, now=_iso(datetime.now(timezone.utc))
            )
        except KeyError as exc:
            raise LookupError(f"scan not found: {scan_id}") from exc
        return self._scan(row)

    def get_scan(self, scan_id: str) -> ScanRun:
        row = self._require_scan_row(scan_id)
        self.state_db.get_automatic_memory_source(
            row["source_id"], now=_iso(datetime.now(timezone.utc))
        )
        return self._scan(row)

    def update_scan(
        self,
        scan_id: str,
        *,
        cursor: str | None = None,
        progress: int | None = None,
        total: int | None = None,
        status: str | None = None,
        last_error: str | None = None,
        recovery_token: str | None = None,
    ) -> ScanRun:
        """Persist scanner-owned progress/error data for later checkpoint work."""
        if status is not None and status not in _SCAN_STATUSES:
            raise ValueError(f"unsupported scan status: {status}")
        if progress is not None and progress < 0:
            raise ValueError("scan progress cannot be negative")
        values: dict[str, Any] = {"updated_at": _iso(datetime.now(timezone.utc))}
        for key, value in {
            "cursor": cursor,
            "progress": progress,
            "total": total,
            "status": status,
            "last_error": last_error,
            "recovery_token": recovery_token,
        }.items():
            if value is not None:
                values[key] = value
        return self._scan(self.state_db.update_automatic_memory_scan(scan_id, **values))

    def _require_scan_row(self, scan_id: str) -> dict[str, Any]:
        row = self.state_db.get_automatic_memory_scan(scan_id)
        if row is None:
            raise LookupError(f"scan not found: {scan_id}")
        return row

    def _require_scan(self, scan_id: str) -> ScanRun:
        return self._scan(self._require_scan_row(scan_id))

    @staticmethod
    def _source(row: dict[str, Any]) -> SourceRecord:
        return SourceRecord(
            source_id=row["source_id"],
            kind=row["kind"],
            root=row["root"],
            status=row["status"],
            capability=row["capability"],
            policy_version=row["policy_version"],
        )

    @staticmethod
    def _scan(row: dict[str, Any]) -> ScanRun:
        return ScanRun(
            scan_id=row["scan_id"],
            source_id=row["source_id"],
            status=row["status"],
            cursor=row["cursor"],
            progress=int(row["progress"]),
            total=int(row["total"]) if row["total"] is not None else None,
            last_error=row["last_error"],
            recovery_token=row["recovery_token"],
            source_sentinel=row.get("source_sentinel"),
            lease_id=row.get("lease_id"),
            attempt=int(row.get("attempt") or 0),
        )
