"""Synthetic local AI app manifest discovery tests (Task 4 of the owner intake plan)."""

from __future__ import annotations

import io
import os
import plistlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

try:
    from src.automatic_memory.app_manifest import (
        APP_CATALOG,
        discover_app_manifest,
    )
except ModuleNotFoundError:
    APP_CATALOG = None  # type: ignore[assignment]
    discover_app_manifest = None  # type: ignore[assignment]

try:
    from src.control.api import create_control_app
    from src.control.service import LocalControlService
except ModuleNotFoundError:  # pragma: no cover
    create_control_app = None  # type: ignore[assignment]
    LocalControlService = None  # type: ignore[assignment]

CAPABILITY_KEYS = {
    "auto_discovery",
    "requires_authorization",
    "official_export_inbox",
    "session_read",
    "message_body_view",
    "model_process_status",
}


def _make_app(root: Path, name: str, bundle_id: str, version: str) -> Path:
    bundle = root / name
    contents = bundle / "Contents"
    contents.mkdir(parents=True)
    payload = {
        "CFBundleIdentifier": bundle_id,
        "CFBundleShortVersionString": version,
        "CFBundleName": name.removesuffix(".app"),
    }
    (contents / "Info.plist").write_bytes(plistlib.dumps(payload))
    return bundle


@pytest.fixture()
def synthetic_applications(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Synthetic /Applications + home with extension dirs; no real machine data."""
    applications = tmp_path / "Applications"
    _make_app(applications, "ChatGPT.app", "com.openai.chat", "1.2025.12")
    _make_app(applications, "Claude.app", "com.anthropic.claudefordesktop", "3.1.0")
    _make_app(applications, "Cursor.app", "com.todesktop.230313mzl4w4u92", "2026.01")
    _make_app(applications, "Windsurf.app", "com.codeium.windsurf", "1.9")
    _make_app(applications, "Ollama.app", "com.ollama.ollama", "0.6.0")
    _make_app(applications, "LM Studio.app", "com.lmstudio.blah", "0.3.9")
    _make_app(applications, "Visual Studio Code.app", "com.microsoft.VSCode", "1.99.0")
    _make_app(applications, "Firefox.app", "org.mozilla.firefox", "130.0")
    home = tmp_path / "home"
    for directory, names in (
        (".vscode/extensions", ["saoudrizwan.claude-dev-3.2.1", "rooveterinaryinc.roo-cline-2.4.0", "continue.continue-0.9.27", "ms-python.python-2026.1.0"]),
        (".cursor/extensions", ["anysphere.php-hover-1.0.0"]),
        (".windsurf/extensions", []),
    ):
        (home / directory).mkdir(parents=True)
        for name in names:
            (home / directory / name).mkdir()
            (home / directory / name / "package.json").write_text("{}", encoding="utf-8")
    return applications, home, tmp_path


def _settings(applications: Path, home: Path, tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        app_manifest_app_roots=(applications,),
        app_manifest_extension_base=home,
        app_manifest_process_provider=lambda: [("ChatGPT", 421), ("ollama", 512), ("Safari", 99)],
        environ={"HOME": str(home)},
        storage_path=tmp_path / "storage",
    )


def test_catalog_covers_owner_required_categories():
    assert APP_CATALOG is not None, "app manifest production module is absent"
    required = {
        "chatgpt_official", "codex_rollout", "claude_desktop", "cursor", "windsurf",
        "opencode", "zcode", "vscode", "cline", "roo_code", "continue", "ollama", "lm_studio",
    }
    assert required <= set(APP_CATALOG)
    for kind, entry in APP_CATALOG.items():
        assert set(entry.capabilities) == CAPABILITY_KEYS, kind
        if kind not in {"chatgpt_official", "codex_rollout", "zcode"}:
            assert entry.capabilities["session_read"] is False, kind


def test_manifest_discovers_whitelisted_apps_and_processes(synthetic_applications):
    assert discover_app_manifest is not None, "app manifest production module is absent"
    applications, home, tmp_path = synthetic_applications
    rows = discover_app_manifest(_settings(applications, home, tmp_path))

    by_kind = {row["kind"]: row for row in rows}
    for kind in ("chatgpt_official", "claude_desktop", "cursor", "windsurf", "ollama", "lm_studio", "vscode"):
        assert kind in by_kind, f"{kind} must be discovered"
    assert "firefox" not in APP_CATALOG
    assert all(row["kind"] in APP_CATALOG for row in rows)

    chatgpt = by_kind["chatgpt_official"]
    assert chatgpt["running"] is True
    assert chatgpt["bundle_id"] == "com.openai.chat"
    assert chatgpt["version"] == "1.2025.12"
    assert chatgpt["capabilities"]["official_export_inbox"] is True
    assert chatgpt["supported"] is True

    ollama = by_kind["ollama"]
    assert ollama["running"] is True
    assert ollama["capabilities"]["model_process_status"] is True

    cursor = by_kind["cursor"]
    assert cursor["running"] is None or cursor["running"] is False
    assert cursor["supported"] is False
    assert cursor["capabilities"]["session_read"] is False
    assert "暂不支持自动读取" in cursor["detail"]

    claude = by_kind["claude_desktop"]
    assert claude["capabilities"]["session_read"] is False
    assert claude["supported"] is False

    for row in rows:
        serialized = str(row)
        assert "/private/var" not in serialized
        if not row["supported"]:
            assert "com.todesktop" not in serialized, "unsupported rows must not expose raw bundle ids"


def test_manifest_detects_vscode_agent_extensions_without_reading_files(synthetic_applications):
    assert discover_app_manifest is not None, "app manifest production module is absent"
    applications, home, tmp_path = synthetic_applications
    rows = discover_app_manifest(_settings(applications, home, tmp_path))
    by_kind = {row["kind"]: row for row in rows}

    for kind in ("cline", "roo_code", "continue"):
        assert kind in by_kind, f"{kind} extension must be detected"
        assert by_kind[kind]["supported"] is False
        assert by_kind[kind]["capabilities"]["session_read"] is False

    serialized_manifest = repr(rows)
    assert "ms-python" not in serialized_manifest, "non-agent extensions must stay out of the manifest"


def test_manifest_ignores_symlinks_and_is_bounded(tmp_path: Path):
    assert discover_app_manifest is not None, "app manifest production module is absent"
    applications = tmp_path / "Applications"
    applications.mkdir()
    outside = tmp_path / "outside"
    _make_app(outside, "Ollama.app", "com.ollama.ollama", "0.6.0")
    try:
        (applications / "Ollama.app").symlink_to(outside / "Ollama.app")
    except OSError:
        pytest.skip("symlink creation unavailable")
    for index in range(700):
        (applications / f"Filler-{index}.app").mkdir()

    settings = SimpleNamespace(
        app_manifest_app_roots=(applications,),
        app_manifest_extension_base=tmp_path / "home",
        app_manifest_process_provider=lambda: [],
        environ={"HOME": str(tmp_path / "home")},
        storage_path=tmp_path / "storage",
    )
    rows = discover_app_manifest(settings)
    assert all(row["kind"] != "ollama" for row in rows), "symlinked app bundles must be ignored"


def test_manifest_has_no_source_side_effects(synthetic_applications, monkeypatch):
    assert discover_app_manifest is not None, "app manifest production module is absent"
    applications, home, tmp_path = synthetic_applications

    real_open = io.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"manifest discovery must not write: {file}")
        return real_open(file, mode, *args, **kwargs)

    def deny(*args, **kwargs):
        raise AssertionError("manifest discovery must not mutate the filesystem or spawn processes")

    import subprocess as subprocess_module

    monkeypatch.setattr(io, "open", guarded_open)
    monkeypatch.setattr(os, "chmod", deny)
    monkeypatch.setattr(os, "chown", deny)
    monkeypatch.setattr(os, "unlink", deny)
    monkeypatch.setattr(os, "rename", deny)
    monkeypatch.setattr(os, "replace", deny)
    monkeypatch.setattr(os, "remove", deny)
    monkeypatch.setattr(os, "system", deny)
    monkeypatch.setattr(subprocess_module, "Popen", deny)
    monkeypatch.setattr(subprocess_module, "run", deny)

    rows = discover_app_manifest(_settings(applications, home, tmp_path))
    assert rows


def test_apps_route_is_authenticated_and_projects_safe_rows(synthetic_applications):
    if create_control_app is None or LocalControlService is None:
        pytest.fail("control API production modules are absent")
    assert discover_app_manifest is not None, "app manifest production module is absent"
    applications, home, tmp_path = synthetic_applications
    storage = tmp_path / "storage"
    storage.mkdir()
    settings = SimpleNamespace(storage_path=storage)
    control = LocalControlService.__new__(LocalControlService)
    from src.storage import StateDatabase as _StateDatabase

    control.state_db = _StateDatabase(storage / "lingji_state.db")
    app_settings = _settings(applications, home, tmp_path)
    app_settings.storage_path = storage
    control.settings = app_settings
    app = create_control_app(settings, service=control, token="local-secret")

    with TestClient(app) as client:
        denied = client.get("/api/automatic-memory/apps")
        assert denied.status_code == 401
        response = client.get("/api/automatic-memory/apps", headers={"X-LingJi-Token": "local-secret"})
        assert response.status_code == 200
        rows = response.json()
        by_kind = {row["kind"]: row for row in rows}
        assert "chatgpt_official" in by_kind and "cursor" in by_kind
        for row in rows:
            assert set(row["capabilities"]) == CAPABILITY_KEYS
            assert isinstance(row["display_name"], str) and row["display_name"]
            assert "pid" not in row, "app rows must not leak process ids"
        cursor_text = repr(by_kind["cursor"])
        assert str(applications) not in cursor_text, "app rows must not expose absolute install roots"
        assert "com.todesktop" not in cursor_text, "raw bundle ids stay out of unsupported app rows"


def test_running_processes_are_whitelisted_and_bounded(synthetic_applications):
    from src.automatic_memory.app_manifest import discover_running_processes

    applications, home, tmp_path = synthetic_applications
    settings = _settings(applications, home, tmp_path)
    settings.app_manifest_process_provider = lambda: [
        ("ChatGPT", 421), ("ChatGPT Helper (Renderer)", 422), ("ollama", 512),
        ("Safari", 99), ("bash", 101), ("Cursor Helper", 700),
    ] + [(f"noise-{i}", 1000 + i) for i in range(2500)]

    rows = discover_running_processes(settings)

    by_name = {row["display_name"]: row for row in rows}
    assert by_name["ChatGPT"]["pid"] == 421
    assert by_name["Ollama"]["pid"] == 512
    assert by_name["Cursor"]["pid"] == 700
    assert len(rows) <= 1000, "process rows must be bounded"
    assert all(set(row) >= {"kind", "display_name", "pid", "state", "updated_at"} for row in rows)
    assert all(row["state"] == "running" for row in rows)
    assert all("Safari" not in row["display_name"] and "bash" not in row["display_name"] for row in rows)
    serialized = repr(rows)
    assert "/Applications" not in serialized and str(home) not in serialized
    assert "noisy" not in serialized and "noise-" not in serialized


def test_processes_route_is_authenticated(synthetic_applications):
    if create_control_app is None or LocalControlService is None:
        pytest.fail("control API production modules are absent")
    from src.storage import StateDatabase

    applications, home, tmp_path = synthetic_applications
    storage = tmp_path / "storage"
    storage.mkdir()
    settings = SimpleNamespace(storage_path=storage)
    control = LocalControlService.__new__(LocalControlService)
    control.state_db = StateDatabase(storage / "lingji_state.db")
    control.settings = _settings(applications, home, tmp_path)
    control.settings.storage_path = storage
    app = create_control_app(settings, service=control, token="local-secret")
    headers = {"X-LingJi-Token": "local-secret"}

    with TestClient(app) as client:
        assert client.get("/api/automatic-memory/processes").status_code == 401
        response = client.get("/api/automatic-memory/processes", headers=headers)
        assert response.status_code == 200
        rows = response.json()
        assert rows and all(row["state"] == "running" for row in rows)
