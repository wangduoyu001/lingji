"""Fail-closed authorization boundary for automatic Obsidian memory.

The ordinary :class:`VaultLayout` index remains intentionally broad for
compatibility.  Automatic memory uses this module instead, so an old PEMIS
index can never silently promote an ordinary note.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .frontmatter import FrontmatterError, split_frontmatter

MEMORY_INBOX = "_LingJi/Memory Inbox"
MEMORY_LIBRARY = "_LingJi/Memory Library"
MEMORY_DIRECTORIES = (MEMORY_INBOX, MEMORY_LIBRARY)
FRONTMATTER_MAX_BYTES = 8192


@dataclass(frozen=True)
class ObsidianMemoryDecision:
    path: Path
    eligible: bool
    reason: str
    explicit_flag: bool = False

    @property
    def authorized(self) -> bool:
        return self.eligible

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "eligible": self.eligible,
            "reason": self.reason,
            "explicit_flag": self.explicit_flag,
        }


class ObsidianMemoryScope:
    """Classify a single path for the automatic-memory source.

    ``root`` is canonicalized once.  Every candidate is canonicalized before
    classification and symlinks are rejected even when they point back inside
    the Vault; this keeps the boundary deterministic across platforms.
    """

    def __init__(self, root: Path | str):
        self._root_lexical = Path(os.path.abspath(str(Path(root).expanduser())))
        self.root = self._root_lexical.resolve(strict=False)

    def decide(
        self,
        path: Path | str,
        frontmatter: Mapping[str, object] | None = None,
    ) -> ObsidianMemoryDecision:
        raw_candidate = Path(path).expanduser()
        if not raw_candidate.is_absolute():
            raw_candidate = self.root / raw_candidate

        # Check the lexical path before resolving it.  ``abspath`` normalizes
        # ``..`` without following symlinks; ``resolve`` would erase the link
        # and could turn an outside-vault link into an authorized target.
        lexical_candidate = Path(os.path.abspath(str(raw_candidate)))
        try:
            raw_relative = lexical_candidate.relative_to(self._root_lexical)
        except ValueError:
            return ObsidianMemoryDecision(lexical_candidate, False, "outside_vault")
        current_raw = self.root
        for part in raw_relative.parts:
            current_raw = current_raw / part
            try:
                if current_raw.is_symlink():
                    return ObsidianMemoryDecision(raw_candidate, False, "symlink")
            except OSError:
                return ObsidianMemoryDecision(raw_candidate, False, "invalid_path")

        candidate = raw_candidate.resolve(strict=False)

        try:
            relative = candidate.relative_to(self.root)
        except ValueError:
            return ObsidianMemoryDecision(candidate, False, "outside_vault")

        # lstat every existing component.  ``resolve`` alone loses whether the
        # input was a symlink, and following a symlink is never an authorization
        # signal for automatic memory.
        current = self.root
        for part in relative.parts:
            current = current / part
            try:
                if current.is_symlink():
                    return ObsidianMemoryDecision(candidate, False, "symlink")
            except OSError:
                return ObsidianMemoryDecision(candidate, False, "invalid_path")

        if candidate.is_dir():
            return ObsidianMemoryDecision(candidate, False, "directory")
        if candidate.suffix.casefold() != ".md":
            return ObsidianMemoryDecision(candidate, False, "non_markdown")

        metadata: Mapping[str, object]
        if frontmatter is not None:
            metadata = frontmatter
        else:
            try:
                metadata = self._read_frontmatter(candidate)
            except Exception:
                return ObsidianMemoryDecision(candidate, False, "invalid_frontmatter")

        flag = metadata.get("lingji_memory") if isinstance(metadata, Mapping) else None
        if flag is False:
            return ObsidianMemoryDecision(candidate, False, "explicitly_disabled", True)
        if flag is not None and not isinstance(flag, bool):
            return ObsidianMemoryDecision(candidate, False, "invalid_frontmatter", True)
        if flag is True:
            return ObsidianMemoryDecision(candidate, True, "explicitly_enabled", True)

        try:
            relative_posix = relative.as_posix()
            dedicated = any(
                relative_posix == directory or relative_posix.startswith(directory + "/")
                for directory in MEMORY_DIRECTORIES
            )
        except (AttributeError, TypeError):
            dedicated = False
        if dedicated:
            return ObsidianMemoryDecision(candidate, True, "authorized", False)
        return ObsidianMemoryDecision(candidate, False, "excluded_ordinary", False)

    def classify(self, path: Path | str) -> ObsidianMemoryDecision:
        return self.decide(path)

    def iter_markdown(self) -> tuple[ObsidianMemoryDecision, ...]:
        """Enumerate only safe Markdown files below the Vault.

        ``rglob`` itself does not follow directory symlinks on supported
        Python versions, but each candidate still goes through ``decide`` for
        a second, fail-closed check.
        """

        if not self._root_lexical.is_dir():
            return ()
        decisions: list[ObsidianMemoryDecision] = []
        for path in sorted(
            path for path in self._root_lexical.rglob("*")
            if path.is_file() and path.suffix.casefold() == ".md" and not path.is_symlink()
        ):
            decision = self.decide(path)
            if decision.eligible:
                decisions.append(decision)
        return tuple(decisions)

    @staticmethod
    def _read_frontmatter(path: Path) -> Mapping[str, object]:
        with path.open("rb") as handle:
            prefix = handle.read(4)
            if prefix.startswith(b"\xef\xbb\xbf"):
                prefix += handle.read(4)
            if prefix not in {b"---\n", b"\xef\xbb\xbf---\n"}:
                return {}
            while len(prefix) < FRONTMATTER_MAX_BYTES:
                line = handle.readline(FRONTMATTER_MAX_BYTES - len(prefix))
                if not line:
                    break
                prefix += line
                if line.rstrip(b"\r\n") == b"---":
                    break
        text = prefix.decode("utf-8-sig")
        if not text.startswith("---\n"):
            return {}
        end = text.find("\n---", 4)
        if end == -1:
            raise FrontmatterError("Frontmatter exceeds bounded read or is missing its closing delimiter")
        metadata, _ = split_frontmatter(text[: end + 4])
        return metadata


__all__ = [
    "MEMORY_INBOX",
    "MEMORY_LIBRARY",
    "MEMORY_DIRECTORIES",
    "ObsidianMemoryDecision",
    "ObsidianMemoryScope",
]
