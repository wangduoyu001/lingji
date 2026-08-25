from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.storage import StateDatabase

try:
    from src.automatic_memory.models import AuthorizationScope
    from src.automatic_memory.source_registry import SourceRegistry
except ModuleNotFoundError:  # RED until Task 1 production modules exist.
    AuthorizationScope = None  # type: ignore[assignment,misc]
    SourceRegistry = None  # type: ignore[assignment,misc]


def test_authorized_source_and_scan_state_survive_state_database_reopen(tmp_path: Path):
    """Catches registries that keep authorization or scan progress only in memory."""
    if SourceRegistry is None or AuthorizationScope is None:
        pytest.fail("automatic-memory source registry production modules are absent")

    root = tmp_path / "authorized-export"
    root.mkdir()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    scope = AuthorizationScope(
        grant_id="grant-cn-owner-1",
        source_kinds=("chatgpt_export",),
        roots=(str(root),),
        granted_at=now,
        expires_at=now + timedelta(days=30),
        owner_confirmed=True,
    )
    database_path = tmp_path / "lingji_state.db"

    registry = SourceRegistry(StateDatabase(database_path))
    source = registry.register(scope, "chatgpt_export", str(root))
    assert source.kind == "chatgpt_export"
    assert source.root == str(root)
    assert source.status == "authorized"
    assert source.capability == "metadata_discovery"
    assert source.policy_version

    scan = registry.start_scan(source.source_id)
    assert scan.status == "running"
    assert scan.cursor is None
    assert scan.progress == 0
    assert scan.total is None
    assert scan.last_error is None
    assert scan.recovery_token is None

    # Simulate the scanner persisting a checkpoint and a recoverable failure.
    registry.update_scan(
        scan.scan_id,
        cursor="export/page-2",
        progress=2,
        total=5,
        status="failed",
        last_error="source changed during snapshot",
        recovery_token="recover-scan-1",
    )
    reopened = SourceRegistry(StateDatabase(database_path))
    persisted_source = reopened.list_sources()[0]
    persisted_scan = reopened.get_scan(scan.scan_id)
    assert persisted_source.source_id == source.source_id
    assert persisted_scan.cursor == "export/page-2"
    assert persisted_scan.progress == 2
    assert persisted_scan.total == 5
    assert persisted_scan.last_error == "source changed during snapshot"
    assert persisted_scan.recovery_token == "recover-scan-1"

    paused = reopened.pause_scan(scan.scan_id)
    assert paused.status == "paused"
    assert paused.cursor == "export/page-2"
    assert paused.progress == 2
    retried = reopened.retry_scan(scan.scan_id)
    assert retried.status == "running"
    assert retried.cursor == "export/page-2"
    assert retried.progress == 2
    assert retried.last_error is None
    assert retried.recovery_token == "recover-scan-1"

    revoked = reopened.revoke(source.source_id)
    assert revoked.status == "revoked"
    assert reopened.list_sources()[0].status == "revoked"


def test_registration_rejects_unconfirmed_or_non_allowlisted_exact_root(tmp_path: Path):
    """Catches path-prefix authorization and owner-confirmation bypasses."""
    if SourceRegistry is None or AuthorizationScope is None:
        pytest.fail("automatic-memory source registry production modules are absent")

    allowed = tmp_path / "allowed"
    sibling = tmp_path / "allowed-sibling"
    child = allowed / "nested"
    allowed.mkdir()
    sibling.mkdir()
    child.mkdir()
    registry = SourceRegistry(StateDatabase(tmp_path / "state.db"))
    now = datetime.now(timezone.utc).replace(microsecond=0)

    unconfirmed = AuthorizationScope(
        grant_id="grant-unconfirmed",
        source_kinds=("codex_export",),
        roots=(str(allowed),),
        granted_at=now,
        expires_at=None,
        owner_confirmed=False,
    )
    with pytest.raises(PermissionError):
        registry.register(unconfirmed, "codex_export", str(allowed))

    confirmed = AuthorizationScope(
        grant_id="grant-confirmed",
        source_kinds=("codex_export",),
        roots=(str(allowed),),
        granted_at=now,
        expires_at=None,
        owner_confirmed=True,
    )
    with pytest.raises(PermissionError):
        registry.register(confirmed, "codex_export", str(sibling))
    with pytest.raises(PermissionError):
        registry.register(confirmed, "codex_export", str(child))
