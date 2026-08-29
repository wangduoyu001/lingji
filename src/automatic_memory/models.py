from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class DiscoveredSource:
    """Metadata-only source evidence shown before owner authorization."""

    kind: str
    display_name: str
    candidate_root: str
    status: str
    capability: str
    reason: str | None = None
    file_count: int | None = None
    byte_count: int | None = None
    earliest_mtime: float | None = None
    latest_mtime: float | None = None
    format: str | None = None
    owner_action: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class AuthorizationScope:
    grant_id: str
    source_kinds: tuple[str, ...]
    roots: tuple[str, ...]
    granted_at: datetime
    expires_at: datetime | None
    owner_confirmed: bool


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    kind: str
    root: str
    status: str
    capability: str
    policy_version: str


@dataclass(frozen=True)
class ScanRun:
    scan_id: str
    source_id: str
    status: str
    cursor: str | None
    progress: int
    total: int | None
    last_error: str | None
    recovery_token: str | None
    source_sentinel: str | None = None
    lease_id: str | None = None
    attempt: int = 0
    queued: int | None = None
    reused: int | None = None
    counts_present: tuple[str, ...] = ()
    updated_at: str | None = None
