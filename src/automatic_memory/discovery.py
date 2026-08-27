"""Metadata-only discovery of possible automatic-memory source roots."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class DiscoveredSource:
    kind: str
    display_name: str
    candidate_root: str
    status: str
    capability: str
    reason: str | None = None


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


def discover_source_metadata(settings: object) -> tuple[DiscoveredSource, ...]:
    """Return source candidates using paths only; never opens candidate files."""
    env: Mapping[str, str] = getattr(settings, "environ", None) or os.environ
    values = (
        ("codex_transcript", "Codex transcript", ("codex_transcript_dir", "codex_transcript_root", "codex_history_dir")),
        ("chatgpt_export", "ChatGPT official export", ("chatgpt_export_dir", "chatgpt_download_dir")),
        ("generic_ai_history", "Generic AI History Inbox", ("generic_history_dir", "history_inbox_dir", "generic_inbox_dir")),
        ("obsidian", "Managed Obsidian memory", ("vault_path", "obsidian_vault_path", "vault_dir")),
    )
    result: list[DiscoveredSource] = []
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
        resolved = path.resolve(strict=False)
        status, reason = _metadata_status(resolved)
        result.append(DiscoveredSource(kind, display_name, str(resolved), status, "metadata_discovery", reason))
    claude_path = _candidate(getattr(settings, "claude_desktop_dir", None)) or _candidate(env.get("CLAUDE_DESKTOP_DIR"))
    result.append(DiscoveredSource(
        "claude_desktop", "Claude Desktop", str(claude_path.resolve(strict=False)) if claude_path else "",
        "unsupported" if bool(getattr(settings, "claude_owner_confirmed", False)) else "consent_required",
        "metadata_discovery", "Claude Desktop has no approved official export schema; opaque storage is not read",
    ))
    return tuple(result)


__all__ = ["DiscoveredSource", "discover_source_metadata"]
