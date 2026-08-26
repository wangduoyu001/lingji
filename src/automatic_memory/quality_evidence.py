"""Auditable evidence primitives for the automatic-memory quality gate."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SentinelEntry:
    path: str
    kind: str
    mode: int
    size: int
    sha256: str | None


@dataclass(frozen=True)
class SentinelChange:
    path: str
    before: SentinelEntry | None
    after: SentinelEntry | None


@dataclass(frozen=True)
class ProtectedTreeSentinel:
    entries: Mapping[str, SentinelEntry]

    @classmethod
    def capture(cls, roots: Sequence[Path]) -> "ProtectedTreeSentinel":
        entries: dict[str, SentinelEntry] = {}
        for configured in roots:
            root = Path(configured).expanduser().resolve(strict=False)
            if not root.exists():
                raise ValueError(f"missing protected root: {configured}")
            if Path(configured).expanduser().is_symlink():
                raise ValueError(f"symlink protected root: {configured}")
            for current, dirs, files in os.walk(root, followlinks=False):
                current_path = Path(current)
                for name in dirs + files:
                    path = current_path / name
                    if path.is_symlink():
                        raise ValueError(f"symlink escape in protected tree: {path}")
                    stat = path.stat()
                    rel = str(path.relative_to(root))
                    kind = "dir" if path.is_dir() else "file"
                    digest = None
                    if kind == "file":
                        h = hashlib.sha256()
                        with path.open("rb") as stream:
                            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                                h.update(chunk)
                        digest = h.hexdigest()
                    entries[f"{root}:{rel}"] = SentinelEntry(f"{root}:{rel}", kind, stat.st_mode, stat.st_size, digest)
        return cls(entries)

    def diff(self, after: "ProtectedTreeSentinel") -> tuple[SentinelChange, ...]:
        changes = []
        for key in sorted(set(self.entries) | set(after.entries)):
            before, current = self.entries.get(key), after.entries.get(key)
            if before != current:
                changes.append(SentinelChange(key, before, current))
        return tuple(changes)


@dataclass(frozen=True)
class ImportedEvidenceAudit:
    expected: int
    actual: int
    missing: int
    extra: int
    duplicate: int
    ordered_role_matches: int
    content_hash_matches: int
    sequence_matches: int = 0
    source_matches: int = 0
    conversation_matches: int = 0

    @classmethod
    def from_read_model(cls, read_model: Any, expected_records: Sequence[Any]) -> "ImportedEvidenceAudit":
        rows: list[Mapping[str, Any]] = []
        offset = 0
        while True:
            page = read_model.list_messages(owner=True, limit=200, offset=offset)
            rows.extend(page.get("items") or [])
            if not page.get("next_offset"):
                break
            offset = int(page["next_offset"])
        expected_ids = [str(getattr(r, "message_id")) for r in expected_records]
        actual_ids = [str(row.get("external_id") or row.get("message_id") or "") for row in rows]
        counts = {key: actual_ids.count(key) for key in set(actual_ids)}
        duplicate = sum(max(0, count - 1) for count in counts.values())
        expected_set = set(expected_ids)
        actual_set = set(actual_ids)
        by_id: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            by_id.setdefault(str(row.get("external_id") or row.get("message_id") or ""), row)
        role = sequence = content = source = conversation = 0
        for expected in expected_records:
            row = by_id.get(str(getattr(expected, "message_id")))
            if row is None:
                continue
            role += int(str(row.get("role") or "") == str(getattr(expected, "role", "")))
            sequence += int(str(row.get("sequence") or "") == str(getattr(expected, "sequence", row.get("sequence"))))
            content += int(str(row.get("content_hash") or "") == str(getattr(expected, "content_hash", "")))
            source += int(str(row.get("source_id") or "") == str(getattr(expected, "source_id", "")))
            conversation += int(str(row.get("conversation_id") or "") == str(getattr(expected, "conversation_id", "")))
        return cls(len(expected_records), len(rows), len(expected_set - actual_set), len(actual_set - expected_set), duplicate, role, content, sequence, source, conversation)
