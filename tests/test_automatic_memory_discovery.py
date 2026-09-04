from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.automatic_memory.models import SourceRecord
try:
    from src.automatic_memory.discovery import discover_source_metadata
    from src.automatic_memory.path_policy import enumerate_authorized_files
except ModuleNotFoundError:
    discover_source_metadata = None  # type: ignore[assignment]
    enumerate_authorized_files = None  # type: ignore[assignment]


def test_discovery_reports_metadata_without_reading_chat_body(tmp_path: Path, monkeypatch):
    assert discover_source_metadata is not None, "Task 3 discovery module is absent"
    assert enumerate_authorized_files is not None, "Task 3 path policy module is absent"
    codex_root = tmp_path / "codex"
    codex_root.mkdir()
    transcript = codex_root / "session.jsonl"
    transcript.write_text("body must not be read", encoding="utf-8")
    original = Path.read_text

    def fail_body_read(self, *args, **kwargs):
        if self == transcript:
            raise AssertionError("discovery read chat body before authorization")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_body_read)
    settings = SimpleNamespace(
        codex_transcript_dir=codex_root,
        chatgpt_export_dir=tmp_path / "missing-chatgpt",
        generic_history_dir=tmp_path / "history",
        vault_path=tmp_path / "vault",
    )

    discovered = discover_source_metadata(settings)

    codex = next(item for item in discovered if item.kind == "codex_transcript")
    assert codex.status == "available"
    assert codex.capability == "metadata_discovery"
    assert codex.candidate_root == str(codex_root.resolve())


@pytest.mark.parametrize("bad_name", [".env", "credentials.json", "auth-token.json", "cookies.sqlite", "private.db"])
def test_path_policy_excludes_sensitive_files_and_symlink_escape(tmp_path: Path, bad_name: str):
    assert enumerate_authorized_files is not None, "Task 3 path policy module is absent"
    root = tmp_path / "authorized"
    root.mkdir()
    (root / bad_name).write_text("secret", encoding="utf-8")
    safe = root / "session.jsonl"
    safe.write_text("safe", encoding="utf-8")
    outside = tmp_path / "outside.jsonl"
    outside.write_text("outside", encoding="utf-8")
    link = root / "linked.jsonl"
    try:
        link.symlink_to(outside)
    except OSError:
        link = None

    source = SourceRecord("source-1", "codex_transcript", str(root), "authorized", "metadata_discovery", "v1")
    files = enumerate_authorized_files(source)

    assert files == (safe,)


@pytest.mark.parametrize("root", [Path("/"), Path.home()])
def test_path_policy_rejects_filesystem_root_and_whole_home(root: Path):
    assert enumerate_authorized_files is not None, "Task 3 path policy module is absent"
    source = SourceRecord("source-1", "generic_ai_history", str(root), "authorized", "metadata_discovery", "v1")
    with pytest.raises(PermissionError, match="root|home|unsafe"):
        enumerate_authorized_files(source)


def test_obsidian_policy_reads_only_managed_paths(tmp_path: Path):
    assert enumerate_authorized_files is not None, "Task 3 path policy module is absent"
    vault = tmp_path / "vault"
    managed = vault / "_LingJi" / "Memory Inbox" / "managed.md"
    ordinary = vault / "03-Knowledge" / "ordinary.md"
    managed.parent.mkdir(parents=True)
    ordinary.parent.mkdir(parents=True)
    managed.write_text("# Managed", encoding="utf-8")
    ordinary.write_text("# Ordinary", encoding="utf-8")
    source = SourceRecord("source-1", "obsidian", str(vault), "authorized", "metadata_discovery", "v1")

    files = enumerate_authorized_files(source)

    assert files == (managed,)


@pytest.mark.parametrize(
    "bad_name",
    [".env", ".env.production", ".env.local", "config.json", "config-export.jsonl", "auth.json", "Cookie Store.jsonl", "secrets.md", "Login Data.json"],
)
def test_path_policy_rejects_env_config_and_credential_file_variants(tmp_path: Path, bad_name: str):
    """`.env.production`/`config.json` must fail closed like credentials do."""
    assert enumerate_authorized_files is not None, "Task 3 path policy module is absent"
    root = tmp_path / "generic"
    root.mkdir()
    (root / bad_name).write_text("sensitive", encoding="utf-8")
    safe_author = root / "author.json"
    safe_author.write_text("{}", encoding="utf-8")
    safe_session = root / "session-notes.md"
    safe_session.write_text("ordinary chat content", encoding="utf-8")

    source = SourceRecord("source-1", "generic_ai_history", str(root), "authorized", "metadata_discovery", "v1")
    files = enumerate_authorized_files(source)

    assert files == (safe_author, safe_session)


def test_path_policy_prunes_sensitive_named_directories(tmp_path: Path):
    assert enumerate_authorized_files is not None, "Task 3 path policy module is absent"
    root = tmp_path / "generic"
    for directory in ("config", ".env.d", "server.key", "certs.pem", "history.db-wal"):
        (root / directory).mkdir(parents=True)
        (root / directory / "notes.json").write_text("{}", encoding="utf-8")
    safe = root / "session.jsonl"
    safe.write_text("safe", encoding="utf-8")

    source = SourceRecord("source-1", "generic_ai_history", str(root), "authorized", "metadata_discovery", "v1")
    files = enumerate_authorized_files(source)

    assert files == (safe,)


@pytest.mark.parametrize("root_name", ["server.key", "certs.pem", "history.db-wal", "history.db-shm", ".env.production", "keys.d"])
def test_path_policy_rejects_sensitive_named_roots(tmp_path: Path, root_name: str):
    assert enumerate_authorized_files is not None, "Task 3 path policy module is absent"
    root = tmp_path / "sources" / root_name
    root.mkdir(parents=True)

    source = SourceRecord("source-1", "generic_ai_history", str(root), "authorized", "metadata_discovery", "v1")
    with pytest.raises(PermissionError):
        enumerate_authorized_files(source)


def test_rollout_inventory_prunes_env_variant_directories(tmp_path: Path):
    """Discovery counting must not descend into credential-shaped folders."""
    assert discover_source_metadata is not None, "Task 3 discovery module is absent"
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions"
    sessions.mkdir(parents=True)
    good = sessions / "rollout-2026-01-01T00-00-00.jsonl"
    good.write_text("{}", encoding="utf-8")
    (sessions / ".env.d").mkdir()
    hidden = sessions / ".env.d" / "rollout-2026-01-02T00-00-00.jsonl"
    hidden.write_text("{}", encoding="utf-8")

    settings = SimpleNamespace(platform_name="darwin", home_dir=home, environ={"HOME": str(home)})
    discovered = discover_source_metadata(settings)

    codex = next(item for item in discovered if item.kind == "codex_rollout" and item.candidate_root == str(sessions.resolve()))
    assert codex.file_count == 1
    assert codex.byte_count == good.stat().st_size


def test_discovery_enumeration_and_snapshot_have_no_source_side_effects(tmp_path: Path, monkeypatch):
    """Spies prove read-only behavior: no process/network/write under source root."""
    assert discover_source_metadata is not None and enumerate_authorized_files is not None
    from src.automatic_memory.snapshot import ConsistentSnapshot
    from src.automatic_memory.source_registry import SourceRegistry
    from src.automatic_memory.models import AuthorizationScope
    from src.storage import StateDatabase

    root = tmp_path / "generic"
    root.mkdir()
    safe = root / "session-notes.md"
    safe.write_text("ordinary chat content", encoding="utf-8")
    source_tree_before = sorted((str(p.relative_to(root)), p.stat().st_mtime_ns, p.stat().st_size, p.stat().st_mode) for p in root.rglob("*"))

    def deny_source_path_write(target):
        try:
            resolved = Path(target).resolve(strict=False)
        except TypeError:
            return
        if str(resolved).startswith(str(root.resolve())):
            raise AssertionError(f"source tree was touched: {resolved}")

    real_open = open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            deny_source_path_write(file)
        return real_open(file, mode, *args, **kwargs)

    import io
    import os as os_module
    import socket as socket_module
    import subprocess as subprocess_module

    def deny(*_args, **_kwargs):
        raise AssertionError("discovery/enumeration/snapshot must not start processes or touch the network")

    monkeypatch.setattr(subprocess_module, "Popen", deny)
    monkeypatch.setattr(subprocess_module, "run", deny)
    monkeypatch.setattr(subprocess_module, "call", deny)
    monkeypatch.setattr(os_module, "system", deny)
    monkeypatch.setattr(os_module, "kill", deny)
    monkeypatch.setattr(socket_module.socket, "connect", deny)
    monkeypatch.setattr(socket_module, "create_connection", deny)
    monkeypatch.setattr(os_module, "chmod", deny)
    monkeypatch.setattr(os_module, "chown", deny)
    monkeypatch.setattr(io, "open", guarded_open)

    real_chmod = os_module.chmod
    real_rename = os_module.rename
    real_replace = os_module.replace
    real_unlink = os_module.unlink

    def guarded_chmod(path, *args, **kwargs):
        deny_source_path_write(path)
        return real_chmod(path, *args, **kwargs)

    def guarded_rename(src, *args, **kwargs):
        deny_source_path_write(src)
        return real_rename(src, *args, **kwargs)

    def guarded_replace(src, *args, **kwargs):
        deny_source_path_write(src)
        return real_replace(src, *args, **kwargs)

    def guarded_unlink(path, *args, **kwargs):
        deny_source_path_write(path)
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os_module, "chmod", guarded_chmod)
    monkeypatch.setattr(os_module, "rename", guarded_rename)
    monkeypatch.setattr(os_module, "replace", guarded_replace)
    monkeypatch.setattr(os_module, "unlink", guarded_unlink)

    settings = SimpleNamespace(
        platform_name="darwin",
        home_dir=tmp_path / "home",
        environ={"HOME": str(tmp_path / "home")},
        generic_history_dir=root,
        claude_owner_confirmed=False,
    )
    discovered = discover_source_metadata(settings)
    generic = next(item for item in discovered if item.kind == "generic_ai_history")

    state = StateDatabase(tmp_path / "lingji_state.db")
    registry = SourceRegistry(state)
    registered = registry.register(
        AuthorizationScope(
            grant_id="grant-spy",
            source_kinds=("generic_ai_history",),
            roots=(str(root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_ai_history",
        str(root),
    )
    files = enumerate_authorized_files(registered)
    assert files == (safe,)

    snapshot = ConsistentSnapshot(registry, tmp_path / "storage" / "raw")
    result = snapshot.capture(registered.source_id, safe)
    assert result.stable is True

    source_tree_after = sorted((str(p.relative_to(root)), p.stat().st_mtime_ns, p.stat().st_size, p.stat().st_mode) for p in root.rglob("*"))
    assert source_tree_after == source_tree_before, "source tree must be byte-identical after read-only intake"
    assert discover_source_metadata is not None, "Task 3 discovery module is absent"
    settings = SimpleNamespace(claude_desktop_dir=tmp_path / "claude")
    discovered = discover_source_metadata(settings)
    claude = next(item for item in discovered if item.kind == "claude_desktop")
    assert claude.status in {"unsupported", "consent_required"}
    assert "official" in (claude.reason or "")
