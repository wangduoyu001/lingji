from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
