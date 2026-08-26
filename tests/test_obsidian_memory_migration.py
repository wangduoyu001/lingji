import hashlib
from pathlib import Path

import pytest

from src.obsidian.frontmatter import render_frontmatter
from src.obsidian.memory_migration import ObsidianMemoryMigration
from src.retrieval.memory_db import MemoryDatabase
from src.retrieval.incremental_sync import IncrementalMemorySynchronizer
from src.indexer.index import PEMISIndex


def _note(root: Path, relative: str, memory_id: str, **metadata) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    values = {"id": memory_id, "memory_type": "knowledge", "status": "active"}
    values.update(metadata)
    path.write_text(render_frontmatter(values, f"# {memory_id}\n\n普通正文 {memory_id}"), encoding="utf-8")
    return path


def test_dry_run_manifest_and_apply_never_change_vault(tmp_path):
    vault = tmp_path / "vault"
    storage = tmp_path / "storage"
    ordinary = _note(vault, "03-Knowledge/old.md", "OLD")
    authorized = _note(vault, "_LingJi/Memory Library/new.md", "NEW", lingji_memory=True)
    before = {
        path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns, path.stat().st_mode)
        for path in (ordinary, authorized)
    }
    db = MemoryDatabase(storage / "lingji_memory.db")
    index = PEMISIndex(vault, storage)
    # Legacy index is intentionally broad; migration must remove only its ordinary derived row.
    IncrementalMemorySynchronizer(db).sync(index.rebuild_index()["entries"].values(), vault)
    service = ObsidianMemoryMigration(db, manifest_dir=tmp_path / "manifests")
    manifest = service.plan(vault)
    assert manifest.validate()
    assert any(entry.action == "remove-derived" for entry in manifest.entries)
    assert ordinary.exists() and authorized.exists()

    result = service.apply(manifest, owner_confirmed=True)
    assert result.state == "applied"
    assert db.fetch_by_path("03-Knowledge/old.md") is None
    assert db.fetch_by_path("_LingJi/Memory Library/new.md") is not None
    for path, snapshot in before.items():
        assert (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns, path.stat().st_mode) == snapshot


def test_migration_is_idempotent_and_rollback_restores_derived_rows(tmp_path):
    vault = tmp_path / "vault"
    storage = tmp_path / "storage"
    old = _note(vault, "03-Knowledge/old.md", "OLD")
    db = MemoryDatabase(storage / "lingji_memory.db")
    index = PEMISIndex(vault, storage)
    IncrementalMemorySynchronizer(db).sync(index.rebuild_index()["entries"].values(), vault)
    service = ObsidianMemoryMigration(db, manifest_dir=tmp_path / "manifests")
    manifest = service.plan(vault)
    first = service.apply(manifest, owner_confirmed=True)
    second = service.apply(manifest, owner_confirmed=True)
    assert second.state == "applied"
    assert first.removed_derived == second.removed_derived
    assert db.fetch_by_path("03-Knowledge/old.md") is None

    rolled = service.rollback(first)
    assert rolled.state == "rolled_back"
    assert db.fetch_by_path("03-Knowledge/old.md") is not None
    assert old.read_text(encoding="utf-8")


def test_owner_confirmed_core_is_retained_and_confirmation_is_required(tmp_path):
    vault = tmp_path / "vault"
    storage = tmp_path / "storage"
    core = _note(vault, "03-Knowledge/Core-Memory/identity.md", "CORE", memory_tier="core", owner_confirmed=True)
    db = MemoryDatabase(storage / "lingji_memory.db")
    index = PEMISIndex(vault, storage)
    IncrementalMemorySynchronizer(db).sync(index.rebuild_index()["entries"].values(), vault)
    service = ObsidianMemoryMigration(db)
    manifest = service.plan(vault)
    assert all(entry.action == "retain" for entry in manifest.entries)
    with pytest.raises(PermissionError):
        service.apply(manifest, owner_confirmed=False)
    assert db.fetch_by_path("03-Knowledge/Core-Memory/identity.md") is not None


def test_scoped_sync_and_migration_preserve_non_obsidian_projection(tmp_path):
    vault = tmp_path / "vault"
    storage = tmp_path / "storage"
    _note(vault, "03-Knowledge/old.md", "OLD")
    db = MemoryDatabase(storage / "lingji_memory.db")
    index = PEMISIndex(vault, storage)
    IncrementalMemorySynchronizer(db).sync(index.rebuild_index()["entries"].values(), vault)
    external = {
        "id": "CHAT-1",
        "relative_path": "source://chat/1",
        "title": "chat",
        "memory_type": "chat",
        "content_hash": "external",
    }
    external_path = tmp_path / "chat.md"
    external_path.write_text("# chat\n\nchat evidence", encoding="utf-8")
    db.upsert_from_entry(external, external_path)
    from src.obsidian.memory_scope import ObsidianMemoryScope
    IncrementalMemorySynchronizer(db).sync(
        index.rebuild_index()["entries"].values(), vault, memory_scope=ObsidianMemoryScope(vault)
    )
    assert db.fetch_by_path("source://chat/1") is not None
    service = ObsidianMemoryMigration(db)
    manifest = service.plan(vault)
    assert any(entry.path == "source://chat/1" and entry.action == "retain" for entry in manifest.entries)
    assert not any(entry.path == "03-Knowledge/old.md" and entry.action == "remove-derived" for entry in manifest.entries)


def test_manifest_checksum_and_raw_ownership_are_fail_closed(tmp_path):
    vault = tmp_path / "vault"
    raw = tmp_path / "raw"
    _note(vault, "03-Knowledge/old.md", "OLD")
    raw.mkdir()
    (raw / "chat.json").write_text("chat", encoding="utf-8")
    (raw / "obsidian.md").write_text("vault copy", encoding="utf-8")
    (raw / "obsidian.md.meta.json").write_text('{"source_type":"obsidian"}', encoding="utf-8")
    service = ObsidianMemoryMigration(raw_root=raw)
    manifest = service.plan(vault)
    assert any(entry.path == "raw:obsidian.md" for entry in manifest.entries)
    assert not any(entry.path == "raw:chat.json" for entry in manifest.entries)
    payload = manifest.to_dict()
    payload["vault_hash"] = "tampered"
    payload["manifest_hash"] = manifest.manifest_hash
    assert not type(manifest).from_dict(payload).validate()
