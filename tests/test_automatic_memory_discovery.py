from __future__ import annotations

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


def test_claude_discovery_is_explicitly_unsupported(tmp_path: Path):
    assert discover_source_metadata is not None, "Task 3 discovery module is absent"
    settings = SimpleNamespace(claude_desktop_dir=tmp_path / "claude")
    discovered = discover_source_metadata(settings)
    claude = next(item for item in discovered if item.kind == "claude_desktop")
    assert claude.status in {"unsupported", "consent_required"}
    assert "official" in (claude.reason or "")
