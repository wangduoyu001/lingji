"""Export inbox (LingJi-owned receiving folder) tests — plan Task 5."""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

try:
    from src.automatic_memory.export_inbox import (
        EXPORT_INBOX_KINDS,
        ensure_export_inbox,
        export_inbox_dir,
    )
except ModuleNotFoundError:
    EXPORT_INBOX_KINDS = None  # type: ignore[assignment]
    ensure_export_inbox = None  # type: ignore[assignment]
    export_inbox_dir = None  # type: ignore[assignment]

try:
    from src.control.api import create_control_app
    from src.control.service import LocalControlService
except ModuleNotFoundError:  # pragma: no cover
    create_control_app = None  # type: ignore[assignment]
    LocalControlService = None  # type: ignore[assignment]


def _settings(tmp_path: Path) -> SimpleNamespace:
    storage = tmp_path / "storage"
    storage.mkdir()
    return SimpleNamespace(storage_path=storage)


def test_inbox_kinds_cover_official_export_sources():
    assert EXPORT_INBOX_KINDS is not None, "export inbox production module is absent"
    assert "chatgpt_export" in EXPORT_INBOX_KINDS
    for kind, meta in EXPORT_INBOX_KINDS.items():
        assert meta["purpose"] and meta["next_step"]


def test_ensure_is_idempotent_and_lingji_owned(tmp_path: Path):
    assert ensure_export_inbox is not None, "export inbox production module is absent"
    settings = _settings(tmp_path)

    first = ensure_export_inbox(settings, "chatgpt_export")
    second = ensure_export_inbox(settings, "chatgpt_export")

    expected_root = settings.storage_path / "exports" / "chatgpt_export"
    assert first["exists"] is True
    assert Path(first["inbox_path"]) == expected_root
    assert Path(second["inbox_path"]) == expected_root
    assert export_inbox_dir(settings, "chatgpt_export") == expected_root
    # Per-kind isolation: another kind gets its own folder.
    if "generic_ai_history" in EXPORT_INBOX_KINDS:
        ensure_export_inbox(settings, "generic_ai_history")
        assert (settings.storage_path / "exports" / "generic_ai_history").is_dir()


def test_status_counts_files_and_keeps_paths_out_of_copy(tmp_path: Path):
    assert ensure_export_inbox is not None, "export inbox production module is absent"
    settings = _settings(tmp_path)
    inbox = Path(ensure_export_inbox(settings, "chatgpt_export")["inbox_path"])
    (inbox / "ChatGPT-export-2026-09-01.zip").write_bytes(b"zip")
    (inbox / "Conversations.part1.zip").write_bytes(b"zip")

    status = ensure_export_inbox(settings, "chatgpt_export")

    assert status["file_count"] == 2
    assert status["exists"] is True
    assert "接收" in status["purpose"]
    assert "ZIP" in status["next_step"]
    assert status["last_checked_at"]
    copy_text = status["purpose"] + status["next_step"]
    assert str(inbox) not in copy_text, "owner-facing copy must not embed the folder path"


def test_ensure_writes_only_inside_its_own_inbox(tmp_path: Path, monkeypatch):
    assert ensure_export_inbox is not None, "export inbox production module is absent"
    settings = _settings(tmp_path)
    inbox_root = settings.storage_path / "exports" / "chatgpt_export"

    def deny_everywhere(path, *args, **kwargs):
        raise AssertionError(f"inbox creation must not chmod/unlink/rename anything: {path}")

    monkeypatch.setattr(os, "chmod", deny_everywhere)
    monkeypatch.setattr(os, "chown", deny_everywhere)
    monkeypatch.setattr(os, "unlink", deny_everywhere)
    monkeypatch.setattr(os, "rename", deny_everywhere)
    monkeypatch.setattr(os, "replace", deny_everywhere)

    real_open = io.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
            resolved = Path(file).resolve(strict=False)
            if not str(resolved).startswith(str(inbox_root.resolve())):
                raise AssertionError(f"inbox creation wrote outside its own folder: {resolved}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(io, "open", guarded_open)

    status = ensure_export_inbox(settings, "chatgpt_export")
    assert status["exists"] is True
    # Re-running must stay idempotent without touching other trees.
    assert ensure_export_inbox(settings, "chatgpt_export")["file_count"] == 0


def test_unknown_kind_fails_closed(tmp_path: Path):
    assert ensure_export_inbox is not None, "export inbox production module is absent"
    settings = _settings(tmp_path)
    with pytest.raises(LookupError):
        ensure_export_inbox(settings, "unknown_source_kind")


def test_inbox_routes_are_authenticated_and_safe(tmp_path: Path):
    if create_control_app is None or LocalControlService is None:
        pytest.fail("control API production modules are absent")
    assert ensure_export_inbox is not None, "export inbox production module is absent"
    from src.storage import StateDatabase

    storage = tmp_path / "storage"
    storage.mkdir()
    settings = SimpleNamespace(storage_path=storage)
    control = LocalControlService.__new__(LocalControlService)
    control.state_db = StateDatabase(storage / "lingji_state.db")
    control.settings = settings
    app = create_control_app(settings, service=control, token="local-secret")
    headers = {"X-LingJi-Token": "local-secret"}

    with TestClient(app) as client:
        assert client.get("/api/automatic-memory/export-inbox").status_code == 401
        listing = client.get("/api/automatic-memory/export-inbox", headers=headers)
        assert listing.status_code == 200
        rows = listing.json()
        kinds = {row["kind"] for row in rows}
        assert "chatgpt_export" in kinds
        for row in rows:
            assert row["exists"] is True, "listing must auto-ensure LingJi-owned inboxes"
            assert isinstance(row["file_count"], int)

        ensured = client.post(
            "/api/automatic-memory/export-inbox/ensure",
            headers=headers,
            json={"kind": "chatgpt_export"},
        )
        assert ensured.status_code == 200
        assert ensured.json()["exists"] is True

        missing = client.post(
            "/api/automatic-memory/export-inbox/ensure",
            headers=headers,
            json={"kind": "unknown_source_kind"},
        )
        assert missing.status_code == 404
