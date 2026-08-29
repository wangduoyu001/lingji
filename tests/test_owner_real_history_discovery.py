from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.automatic_memory.discovery import discover_source_metadata
from src.automatic_memory.models import SourceRecord
from src.automatic_memory.path_policy import enumerate_authorized_files


def _write(path: Path, content: str, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_darwin_discovers_both_codex_roots_using_metadata_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    current = home / ".codex" / "sessions"
    archived = home / ".codex" / "archived_sessions"
    _write(current / "2026/08/28/rollout-a.jsonl", '{"secret":"body"}', 100.0)
    _write(current / "2026/08/29/rollout-b.jsonl", "{}\n{}", 200.0)
    _write(archived / "rollout-c.jsonl", "archive", 300.0)
    _write(home / ".codex" / "auth.json", "token", 400.0)
    _write(home / ".codex" / "config.toml", "secret", 401.0)
    _write(home / ".codex" / "state.sqlite", "db", 402.0)
    outside = tmp_path / "outside.jsonl"
    _write(outside, "outside", 500.0)
    try:
        (current / "2026/08/29/rollout-escape.jsonl").symlink_to(outside)
    except OSError:
        pass

    settings = SimpleNamespace(home_dir=home, platform_name="darwin", environ={})
    discovered = discover_source_metadata(settings)

    candidates = [item for item in discovered if item.kind == "codex_rollout"]
    assert [item.candidate_root for item in candidates] == [str(current.resolve()), str(archived.resolve())]
    assert [item.file_count for item in candidates] == [2, 1]
    assert [item.byte_count for item in candidates] == [len('{"secret":"body"}') + len("{}\n{}"), len("archive")]
    assert candidates[0].earliest_mtime == 100.0
    assert candidates[0].latest_mtime == 200.0
    assert candidates[0].format == "codex_rollout"
    assert candidates[0].owner_action["kind"] == "authorize"
    assert all(item.kind != "claude_desktop" or item.candidate_root != str(home / ".codex") for item in discovered)


def test_codex_rollout_authorized_enumeration_never_follows_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "home" / ".codex" / "sessions"
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    _write(root / "2026/08/29/rollout-safe.jsonl", "safe", 1.0)
    outside = tmp_path / "outside.jsonl"
    _write(outside, "outside", 2.0)
    try:
        (root / "escape.jsonl").symlink_to(outside)
    except OSError:
        pass
    source = SourceRecord("s1", "codex_rollout", str(root), "authorized", "metadata_discovery", "v1")
    files = enumerate_authorized_files(source)
    assert files == (root / "2026/08/29/rollout-safe.jsonl",)


def test_discovery_rejects_codex_ancestor_symlink_and_keeps_missing_counts_unknown(tmp_path: Path):
    home = tmp_path / "home"
    outside = tmp_path / "outside"
    _write(outside / "rollout-leak.jsonl", "must not enumerate", 9.0)
    (home / ".codex").mkdir(parents=True)
    try:
        (home / ".codex" / "sessions").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    discovered = discover_source_metadata(SimpleNamespace(home_dir=home, platform_name="darwin", environ={}))
    current = next(item for item in discovered if item.kind == "codex_rollout" and item.candidate_root.endswith("/sessions"))
    assert current.status == "unavailable"
    assert current.file_count is None
    assert current.byte_count is None
    assert current.reason and "symbolic" in current.reason
    missing = next(item for item in discovered if item.kind == "codex_rollout" and item.candidate_root.endswith("/archived_sessions"))
    assert missing.file_count is None
    assert missing.byte_count is None


def test_discovery_uses_explicit_empty_environment_without_host_leak(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path / "host-home"))
    discovered = discover_source_metadata(SimpleNamespace(platform_name="darwin", environ={}))
    codex = [item for item in discovered if item.kind == "codex_rollout"]
    assert all(str(tmp_path / "host-home") not in item.candidate_root for item in codex)


def test_discovery_never_opens_rollout_bodies_and_obeys_depth_bound(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    root = home / ".codex" / "sessions"
    deep = root
    for index in range(6):
        deep /= f"nested-{index}"
    _write(deep / "rollout-too-deep.jsonl", "do not read", 3.0)
    original_open = Path.open

    def reject_rollout_open(path: Path, *args, **kwargs):
        if path.suffix.casefold() == ".jsonl":
            raise AssertionError("discovery opened a rollout body")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_rollout_open)
    discovered = discover_source_metadata(SimpleNamespace(home_dir=home, platform_name="darwin", environ={}))
    current = next(item for item in discovered if item.kind == "codex_rollout" and item.candidate_root.endswith("/sessions"))
    assert current.file_count == 0
    assert current.byte_count == 0
