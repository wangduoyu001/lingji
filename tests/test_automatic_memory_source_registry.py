from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sqlite3

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
    registry.pause_scan(scan.scan_id)
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


def test_symlink_component_is_rejected_before_source_registration(tmp_path: Path):
    """Catches path checks that only inspect the final root component."""
    real_root = tmp_path / "real-root"
    real_root.mkdir()
    linked_parent = tmp_path / "linked-parent"
    try:
        linked_parent.symlink_to(real_root, target_is_directory=True)
    except OSError as exc:
        pytest.fail(f"symlink fixture could not be created: {exc}")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    scope = AuthorizationScope(
        grant_id="grant-symlink",
        source_kinds=("codex_export",),
        roots=(str(linked_parent / "nested"),),
        granted_at=now,
        expires_at=None,
        owner_confirmed=True,
    )
    with pytest.raises(PermissionError):
        SourceRegistry(StateDatabase(tmp_path / "state.db")).register(
            scope, "codex_export", str(linked_parent / "nested")
        )


def test_expired_persisted_grant_is_visible_and_blocks_scan_lifecycle(tmp_path: Path):
    """Catches authorization expiry being checked only during initial register."""
    root = tmp_path / "root"
    root.mkdir()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    database_path = tmp_path / "state.db"
    registry = SourceRegistry(StateDatabase(database_path))
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-expiring",
            source_kinds=("chatgpt_export",),
            roots=(str(root),),
            granted_at=now,
            expires_at=now + timedelta(days=1),
            owner_confirmed=True,
        ),
        "chatgpt_export",
        str(root),
    )
    scan = registry.start_scan(source.source_id)
    registry.pause_scan(scan.scan_id)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE automatic_memory_grants SET expires_at = ? WHERE grant_id = ?",
            ((now - timedelta(minutes=1)).isoformat(), "grant-expiring"),
        )

    assert registry.list_sources()[0].status == "expired"
    with pytest.raises(PermissionError):
        registry.start_scan(source.source_id)
    with pytest.raises(PermissionError):
        registry.pause_scan(scan.scan_id)
    with pytest.raises(PermissionError):
        registry.retry_scan(scan.scan_id)


def test_revoke_cancels_running_and_paused_scans_and_blocks_retry(tmp_path: Path):
    """Catches revocation leaving resumable scans active in the same database."""
    root_running = tmp_path / "running"
    root_paused = tmp_path / "paused"
    root_running.mkdir()
    root_paused.mkdir()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    registry = SourceRegistry(StateDatabase(tmp_path / "state.db"))

    def authorize(grant_id: str, root: Path):
        return registry.register(
            AuthorizationScope(
                grant_id=grant_id,
                source_kinds=("chatgpt_export",),
                roots=(str(root),),
                granted_at=now,
                expires_at=None,
                owner_confirmed=True,
            ),
            "chatgpt_export",
            str(root),
        )

    running_source = authorize("grant-running", root_running)
    running_scan = registry.start_scan(running_source.source_id)
    assert registry.revoke(running_source.source_id).status == "revoked"
    assert registry.get_scan(running_scan.scan_id).status == "cancelled"
    with pytest.raises(PermissionError):
        registry.retry_scan(running_scan.scan_id)

    paused_source = authorize("grant-paused", root_paused)
    paused_scan = registry.start_scan(paused_source.source_id)
    registry.pause_scan(paused_scan.scan_id)
    registry.revoke(paused_source.source_id)
    assert registry.get_scan(paused_scan.scan_id).status == "cancelled"
    with pytest.raises(PermissionError):
        registry.retry_scan(paused_scan.scan_id)


def test_register_is_atomic_idempotent_and_rejects_persisted_scope_conflict(tmp_path: Path):
    """Catches multi-transaction register races and grant-id scope widening."""
    root = tmp_path / "root"
    root.mkdir()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    database_path = tmp_path / "state.db"
    scope = AuthorizationScope(
        grant_id="grant-concurrent",
        source_kinds=("chatgpt_export",),
        roots=(str(root),),
        granted_at=now,
        expires_at=now + timedelta(days=1),
        owner_confirmed=True,
    )
    state_db = StateDatabase(database_path)

    def register_once(_index: int):
        return SourceRegistry(state_db).register(
            scope, "chatgpt_export", str(root)
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(register_once, range(16)))
    assert len({item.source_id for item in results}) == 1

    conflicting_scope = AuthorizationScope(
        grant_id="grant-concurrent",
        source_kinds=("chatgpt_export",),
        roots=(str(root),),
        granted_at=now,
        expires_at=now + timedelta(days=2),
        owner_confirmed=True,
    )
    with pytest.raises(PermissionError):
        SourceRegistry(StateDatabase(database_path)).register(
            conflicting_scope, "chatgpt_export", str(root)
        )


def test_start_scan_is_idempotent_and_failed_scan_requires_retry(tmp_path: Path):
    """Catches duplicate active scans and a fresh scan bypassing failed recovery."""
    root = tmp_path / "root"
    root.mkdir()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    database_path = tmp_path / "state.db"
    registry = SourceRegistry(StateDatabase(database_path))
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-scan-idempotent",
            source_kinds=("chatgpt_export",),
            roots=(str(root),),
            granted_at=now,
            expires_at=None,
            owner_confirmed=True,
        ),
        "chatgpt_export",
        str(root),
    )
    first = registry.start_scan(source.source_id)
    assert registry.start_scan(source.source_id).scan_id == first.scan_id
    registry.pause_scan(first.scan_id)
    assert registry.start_scan(source.source_id).scan_id == first.scan_id
    registry.update_scan(first.scan_id, status="failed", last_error="retryable")
    with pytest.raises(ValueError):
        registry.start_scan(source.source_id)
    retried = registry.retry_scan(first.scan_id)
    assert retried.scan_id == first.scan_id
    assert retried.status == "running"


def test_concurrent_start_scan_creates_one_active_scan(tmp_path: Path):
    """Catches check-then-insert races that create multiple active scans."""
    root = tmp_path / "root"
    root.mkdir()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    database_path = tmp_path / "state.db"
    state_db = StateDatabase(database_path)
    setup = SourceRegistry(state_db)
    source = setup.register(
        AuthorizationScope(
            grant_id="grant-scan-concurrent",
            source_kinds=("chatgpt_export",),
            roots=(str(root),),
            granted_at=now,
            expires_at=None,
            owner_confirmed=True,
        ),
        "chatgpt_export",
        str(root),
    )

    def start_once(_index: int):
        return SourceRegistry(state_db).start_scan(source.source_id)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(start_once, range(16)))
    assert len({item.scan_id for item in results}) == 1
    with sqlite3.connect(database_path) as connection:
        active_count = connection.execute(
            """
            SELECT COUNT(*) FROM automatic_memory_scans
            WHERE source_id = ? AND status IN ('running', 'paused')
            """,
            (source.source_id,),
        ).fetchone()[0]
    assert active_count == 1
