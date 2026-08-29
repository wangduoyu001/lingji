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


def test_codex_rollout_authorized_enumeration_never_follows_escape(tmp_path: Path):
    root = tmp_path / "home" / ".codex" / "sessions"
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
