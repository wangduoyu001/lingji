"""Fail-closed, bounded enumeration for already-authorized source roots."""

from __future__ import annotations

import os
import re
from pathlib import Path
try:
    import pwd
except ImportError:  # pragma: no cover
    pwd = None  # type: ignore[assignment]

from src.obsidian.discovery import discover_memory_paths

from .models import SourceRecord

MAX_FILES = 10_000
MAX_DEPTH = 4
_SENSITIVE_NAMES = {".env", ".envrc", "credentials", "credential", "auth", "token", "cookie", "cookies", "private", "secret", "secrets", "keychain", "login", "logins"}
_SENSITIVE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
_EXTENSIONS = {
    "chatgpt_export": {".json", ".zip"}, "codex_transcript": {".jsonl"}, "codex": {".jsonl"}, "codex_history": {".jsonl"},
    "generic_ai_history": {".json", ".jsonl", ".md", ".markdown"}, "history_inbox": {".json", ".jsonl", ".md", ".markdown"},
    "codex_rollout": {".jsonl"},
}


def validate_codex_rollout_root(root: Path | str, effective_home: Path | str | None = None) -> Path:
    """Return a canonical Codex root only when it is one exact home root."""
    lexical = Path(os.path.abspath(str(Path(root).expanduser())))
    if any(parent.is_symlink() for parent in (lexical, *lexical.parents)):
        raise PermissionError("symbolic-link Codex root is not allowed")
    resolved = lexical.resolve(strict=False)
    if effective_home:
        home = Path(effective_home).expanduser().resolve(strict=False)
    elif os.environ.get("HOME"):
        home = Path(os.environ["HOME"]).expanduser().resolve(strict=False)
    elif pwd is not None:
        home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=False)
    else:
        home = Path.home().resolve(strict=False)
    expected = {home / ".codex" / "sessions", home / ".codex" / "archived_sessions"}
    if resolved not in expected:
        raise PermissionError("Codex rollout root must be one exact effective-home root")
    return resolved


def _reject_root(root: Path) -> Path:
    lexical = Path(os.path.abspath(str(root.expanduser())))
    resolved = lexical.resolve(strict=False)
    home = Path.home().resolve(strict=False)
    if resolved == Path(resolved.anchor) or resolved == home:
        raise PermissionError("unsafe filesystem root or whole home directory")
    if lexical.is_symlink() or resolved.is_symlink():
        raise PermissionError("symbolic-link source roots are not allowed")
    return resolved


def _sensitive(path: Path) -> bool:
    # Match tokens in the selected component, not operating-system ancestors
    # such as macOS's /private/var temporary tree. Separators are boundaries,
    # so safe names such as ``author.json`` are not overblocked while
    # ``AUTH-token.json`` and ``auth_token.json`` are rejected.
    name = path.name.casefold()
    if any(name.endswith(suffix) for suffix in _SENSITIVE_SUFFIXES):
        return True
    stem = name.rsplit(".", 1)[0] if "." in name else name
    tokens = {token for token in re.split(r"[^a-z0-9]+", stem) if token}
    return bool(tokens & _SENSITIVE_NAMES)


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root)
        return True
    except ValueError:
        return False


def enumerate_authorized_files(
    source: SourceRecord, *, effective_home: Path | str | None = None
) -> tuple[Path, ...]:
    if source.status != "authorized":
        return ()
    root = _reject_root(Path(source.root))
    if _sensitive(root):
        raise PermissionError("unsafe credential/auth/private database source root")
    if source.kind == "codex_rollout":
        # Only the two discovered Codex roots are admissible; an arbitrary
        # directory must never become a transcript import root.
        root = validate_codex_rollout_root(root, effective_home)
    if not root.is_dir() or source.kind == "claude_desktop":
        return ()
    if source.kind == "obsidian":
        decisions = discover_memory_paths(root)
        selected = [decision.path for decision in decisions if _within(root, decision.path) and not _sensitive(decision.path)]
        return tuple(sorted(selected, key=lambda item: item.relative_to(root).as_posix())[:MAX_FILES])
    extensions = _EXTENSIONS.get(source.kind)
    if not extensions:
        raise PermissionError(f"unsupported automatic-memory source kind: {source.kind}")
    files: list[Path] = []
    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        directories[:] = [name for name in directories if not _sensitive(current_path / name) and not (current_path / name).is_symlink() and depth < MAX_DEPTH]
        for name in names:
            candidate = current_path / name
            if candidate.is_symlink() or not candidate.is_file() or _sensitive(candidate):
                continue
            if source.kind == "codex_rollout" and not name.startswith("rollout-"):
                continue
            if candidate.suffix.casefold() in extensions:
                files.append(candidate)
                if len(files) > MAX_FILES:
                    raise PermissionError("authorized source contains too many files")
    return tuple(sorted(files, key=lambda item: item.relative_to(root).as_posix()))


__all__ = ["MAX_DEPTH", "MAX_FILES", "enumerate_authorized_files", "validate_codex_rollout_root"]
