"""Auditable evidence primitives for the automatic-memory quality gate."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ExpectedImportedRow:
    source_external_id: str
    conversation_external_id: str
    message_external_id: str
    sequence: int
    role: str
    content_hash: str
    occurred_at: str


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
            configured_path = Path(configured).expanduser()
            root = configured_path.resolve(strict=False)
            try:
                if not root.exists():
                    raise ValueError(f"missing protected root: {configured}")
                if configured_path.is_symlink():
                    raise ValueError(f"symlink protected root: {configured}")
            except ValueError:
                raise
            except OSError as exc:
                raise ValueError(f"unreadable protected root: {configured}") from exc

            def onerror(exc: OSError) -> None:
                raise ValueError(f"unreadable protected tree: {exc}") from exc

            try:
                for current, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
                    current_path = Path(current)
                    for name in dirs + files:
                        path = current_path / name
                        try:
                            if path.is_symlink():
                                raise ValueError(f"symlink escape in protected tree: {path}")
                            stat = path.stat()
                        except ValueError:
                            raise
                        except OSError as exc:
                            raise ValueError(f"unreadable protected tree entry: {path}") from exc
                        rel = str(path.relative_to(root))
                        kind = "dir" if path.is_dir() else "file"
                        digest = None
                        if kind == "file":
                            h = hashlib.sha256()
                            try:
                                with path.open("rb") as stream:
                                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                                        h.update(chunk)
                            except OSError as exc:
                                raise ValueError(f"unreadable protected tree entry: {path}") from exc
                            digest = h.hexdigest()
                        key = f"{root}:{rel}"
                        entries[key] = SentinelEntry(key, kind, stat.st_mode, stat.st_size, digest)
            except ValueError:
                raise
            except OSError as exc:
                raise ValueError(f"unreadable protected tree: {root}") from exc
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
    ordered_external_id_matches: int = 0

    @property
    def role_matches(self) -> int:
        return self.ordered_role_matches

    @property
    def ordered_message_id_matches(self) -> int:
        return self.ordered_external_id_matches

    @property
    def ordered_external_message_id_matches(self) -> int:
        return self.ordered_external_id_matches

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
        def expected_id(item: Any) -> str:
            return str(getattr(item, "message_external_id", getattr(item, "message_id", "")))

        expected_ids = [expected_id(r) for r in expected_records]
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
            row = by_id.get(expected_id(expected))
            if row is None:
                continue
            role += int(str(row.get("role") or "") == str(getattr(expected, "role", "")))
            sequence += int(str(row.get("sequence") if row.get("sequence") is not None else "") == str(getattr(expected, "sequence", "")))
            content += int(str(row.get("content_hash") or "") == str(getattr(expected, "content_hash", "")))
            source += int(str(row.get("source_external_id") or row.get("source_id") or "") == str(getattr(expected, "source_external_id", getattr(expected, "source_id", ""))))
            conversation += int(str(row.get("conversation_external_id") or row.get("conversation_id") or "") == str(getattr(expected, "conversation_external_id", getattr(expected, "conversation_id", ""))))
        actual_order = [
            str(row.get("external_id") or row.get("message_id") or "")
            for row in sorted(rows, key=lambda row: (
                str(row.get("source_external_id") or row.get("source_id") or ""),
                str(row.get("conversation_external_id") or row.get("conversation_id") or ""),
                int(row.get("sequence") or 0), str(row.get("message_id") or ""),
            ))
        ]
        expected_order = [
            expected_id(item)
            for item in sorted(expected_records, key=lambda item: (
                str(getattr(item, "source_external_id", getattr(item, "source_id", ""))),
                str(getattr(item, "conversation_external_id", getattr(item, "conversation_id", ""))),
                int(getattr(item, "sequence", 0)),
            ))
        ]
        ordered_external = len(expected_order) if actual_order == expected_order else 0
        return cls(len(expected_records), len(rows), len(expected_set - actual_set), len(actual_set - expected_set), duplicate, role, content, sequence, source, conversation, ordered_external)


@dataclass(frozen=True)
class QualityEvidenceReadiness:
    import_audit: bool
    promotion_provenance: bool
    gateway_selection: bool
    mcp_parity: bool
    degradation: bool
    context_baseline: bool
    scale: bool

    @property
    def functional_fields_ready(self) -> bool:
        return all((self.import_audit, self.promotion_provenance, self.gateway_selection,
                    self.mcp_parity, self.degradation, self.context_baseline))

    @property
    def functional_status(self) -> str:
        return "PASS" if self.functional_fields_ready else "NOT_EVALUATED"

    @property
    def should_run_acceptance_gate(self) -> bool:
        return self.functional_fields_ready
