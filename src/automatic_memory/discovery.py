"""Metadata-only discovery of possible automatic-memory source roots."""

from __future__ import annotations

import os
import platform
import stat
try:
    import pwd
except ImportError:  # pragma: no cover - Windows compatibility
    pwd = None  # type: ignore[assignment]
from pathlib import Path
from typing import Any, Mapping

from .models import DiscoveredSource


def _candidate(value: Any) -> Path | None:
    text = str(value or "").strip()
    return Path(text).expanduser() if text else None


def _metadata_status(path: Path) -> tuple[str, str | None]:
    try:
        resolved = path.resolve(strict=False)
        if resolved.is_dir():
            return "available", None
        if resolved.exists():
            return "unsupported", "candidate root is not a directory"
        return "not_found", "candidate root does not exist"
    except OSError as exc:
        return "unavailable", f"candidate root metadata unavailable: {exc}"


_CODEX_MAX_FILES = 50_000
_CODEX_MAX_DIRECTORIES = 50_000
_CODEX_MAX_DEPTH = 5
_ROLLOUT_NAME = "rollout-"
_SENSITIVE_NAMES = frozenset({"auth", "config", "credentials", "cookie", "cookies", "token", "private", "secret", "secrets", "keychain", "login", "logins"})


def _sensitive_name(name: str) -> bool:
    stem = name.casefold().rsplit(".", 1)[0]
    tokens = {token for token in stem.replace("-", "_").split("_") if token}
    return bool(tokens & _SENSITIVE_NAMES)


def _effective_home(settings: object, env: Mapping[str, str]) -> Path:
    supplied = getattr(settings, "home_dir", None) or getattr(settings, "user_home", None)
    if supplied:
        return Path(str(supplied)).expanduser().resolve(strict=False)
    if env.get("HOME"):
        return Path(env["HOME"]).expanduser().resolve(strict=False)
    if pwd is not None:
        try:
            return Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=False)
        except (KeyError, OSError):
            pass
    return Path.home().resolve(strict=False)


def _darwin(settings: object) -> bool:
    value = getattr(settings, "platform_name", None) or getattr(settings, "platform_system", None) or getattr(settings, "platform", None)
    if value is None:
        value = platform.system()
    # Discovery is intentionally platform strict.  A caller must identify the
    # Darwin host explicitly; aliases are too easy to pass accidentally from a
    # user-provided setting and could enable local-path probing elsewhere.
    return str(value).strip().casefold() == "darwin"


def _rollout_inventory(root: Path) -> tuple[int | None, int | None, float | None, float | None, str | None]:
    """Inventory rollout files with stat only; never opens a file body."""
    lexical = Path(os.path.abspath(str(root)))
    if any(parent.is_symlink() for parent in (lexical, *lexical.parents)):
        return None, None, None, None, "codex_rollout"
    if root.is_symlink() or not root.is_dir():
        return None, None, None, None, "codex_rollout"
    count = 0
    bytes_total = 0
    earliest: float | None = None
    latest: float | None = None
    try:
        pending: list[tuple[Path, int]] = [(root, 0)]
        directories_seen = 0
        while pending:
            current_path, depth = pending.pop()
            if depth >= _CODEX_MAX_DEPTH:
                continue
            for entry in current_path.iterdir():
                if entry.is_symlink() or _sensitive_name(entry.name):
                    continue
                if entry.is_dir():
                    directories_seen += 1
                    if directories_seen > _CODEX_MAX_DIRECTORIES:
                        return None, None, None, None, "codex_rollout"
                    if depth < _CODEX_MAX_DEPTH:
                        pending.append((entry, depth + 1))
                    continue
                name = entry.name
                if not name.startswith(_ROLLOUT_NAME) or not name.casefold().endswith(".jsonl"):
                    continue
                info = entry.stat()
                if not stat.S_ISREG(info.st_mode):
                    continue
                count += 1
                if count > _CODEX_MAX_FILES:
                    return None, None, None, None, "codex_rollout"
                bytes_total += int(info.st_size)
                mtime = float(info.st_mtime)
                earliest = mtime if earliest is None else min(earliest, mtime)
                latest = mtime if latest is None else max(latest, mtime)
    except OSError:
        return None, None, None, None, "codex_rollout"
    return count, bytes_total, earliest, latest, "codex_rollout"


def discover_source_metadata(settings: object) -> tuple[DiscoveredSource, ...]:
    """Return source candidates using paths only; never opens candidate files."""
    supplied_env = getattr(settings, "environ", None)
    env: Mapping[str, str] = os.environ if supplied_env is None else supplied_env
    values = (
        ("codex_transcript", "Codex transcript", ("codex_transcript_dir", "codex_transcript_root", "codex_history_dir")),
        ("chatgpt_export", "ChatGPT official export", ("chatgpt_export_dir", "chatgpt_download_dir")),
        ("generic_ai_history", "Generic AI History Inbox", ("generic_history_dir", "history_inbox_dir", "generic_inbox_dir")),
        ("obsidian", "Managed Obsidian memory", ("vault_path", "obsidian_vault_path", "vault_dir")),
    )
    result: list[DiscoveredSource] = []
    if _darwin(settings):
        home = _effective_home(settings, env)
        for root in (home / ".codex" / "sessions", home / ".codex" / "archived_sessions"):
            lexical = Path(os.path.abspath(str(root)))
            if any(parent.is_symlink() for parent in (lexical, *lexical.parents)):
                result.append(DiscoveredSource(
                    "codex_rollout", "Codex聊天记录", str(lexical), "unavailable", "metadata_discovery",
                    "symbolic-link Codex root is not traversed", None, None, None, None, "codex_rollout",
                    {"kind": "authorize", "label": "允许接管 Codex", "source_kind": "codex_rollout"},
                ))
                continue
            resolved = root.resolve(strict=False)
            status, reason = _metadata_status(resolved)
            count, byte_count, earliest, latest, fmt = _rollout_inventory(lexical)
            result.append(DiscoveredSource(
                "codex_rollout", "Codex聊天记录", str(resolved), status, "metadata_discovery", reason,
                count, byte_count, earliest, latest, fmt,
                {"kind": "authorize", "label": "允许接管 Codex", "source_kind": "codex_rollout"},
            ))
    configured_kinds: set[str] = set()
    for kind, display_name, attributes in values:
        path = next((_candidate(getattr(settings, name, None)) for name in attributes if _candidate(getattr(settings, name, None))), None)
        if path is None:
            path = _candidate(env.get({
                "codex_transcript": "LINGJI_CODEX_TRANSCRIPT_DIR",
                "chatgpt_export": "LINGJI_CHATGPT_EXPORT_DIR",
                "generic_ai_history": "LINGJI_GENERIC_HISTORY_DIR",
                "obsidian": "OBSIDIAN_VAULT_PATH",
            }[kind]))
        if path is None:
            continue
        configured_kinds.add(kind)
        resolved = path.resolve(strict=False)
        status, reason = _metadata_status(resolved)
        action = None
        if kind == "chatgpt_export":
            action = {"kind": "select_official_export", "label": "选择官方导出目录", "source_kind": kind}
        result.append(DiscoveredSource(kind, display_name, str(resolved), status, "metadata_discovery", reason, format=kind, owner_action=action))
    if "chatgpt_export" not in configured_kinds:
        result.append(DiscoveredSource(
            "chatgpt_export", "ChatGPT official export", "", "consent_required", "metadata_discovery",
            "ChatGPT 旧记录仅支持主人选择的官方导出目录", format="chatgpt_export",
            owner_action={"kind": "select_official_export", "label": "选择官方导出目录", "source_kind": "chatgpt_export"},
        ))
    claude_path = _candidate(getattr(settings, "claude_desktop_dir", None)) or _candidate(env.get("CLAUDE_DESKTOP_DIR"))
    result.append(DiscoveredSource(
        "claude_desktop", "Claude Desktop", str(claude_path.resolve(strict=False)) if claude_path else "",
        "unsupported" if bool(getattr(settings, "claude_owner_confirmed", False)) else "consent_required",
        "metadata_discovery", "Claude Desktop has no approved official export schema; opaque storage is not read",
    ))
    return tuple(result)


__all__ = ["DiscoveredSource", "discover_source_metadata"]
