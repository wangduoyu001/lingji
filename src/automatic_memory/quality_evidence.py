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
    duplicate_external_ids: int = 0
    duplicate_content_hashes: int = 0

    @property
    def role_matches(self) -> int:
        return self.ordered_role_matches

    @property
    def ordered_message_id_matches(self) -> int:
        return self.ordered_external_id_matches

    @property
    def ordered_external_message_id_matches(self) -> int:
        return self.ordered_external_id_matches

    @property
    def duplicate_hashes(self) -> int:
        return self.duplicate_content_hashes

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

        def actual_id(row: Mapping[str, Any]) -> str:
            # ``message_id`` is a generated database primary key and cannot
            # stand in for the adapter's external identity.
            return str(row.get("external_id") or "")

        def actual_source(row: Mapping[str, Any]) -> str:
            return str(row.get("source_external_id") or row.get("source_id") or "")

        def actual_conversation(row: Mapping[str, Any]) -> str:
            return str(row.get("conversation_external_id") or row.get("conversation_id") or "")

        expected_ids = [expected_id(r) for r in expected_records]
        actual_ids = [actual_id(row) for row in rows]
        actual_hashes = [str(row.get("content_hash") or "") for row in rows]
        id_counts = {key: actual_ids.count(key) for key in set(actual_ids) if key}
        hash_counts = {key: actual_hashes.count(key) for key in set(actual_hashes) if key}
        duplicate_external_ids = sum(max(0, count - 1) for count in id_counts.values())
        duplicate_content_hashes = sum(max(0, count - 1) for count in hash_counts.values())
        # Count each duplicate row once when both its external ID and hash are
        # duplicated, while retaining the two diagnostic counters separately.
        seen_ids: set[str] = set()
        seen_hashes: set[str] = set()
        duplicate_rows: set[int] = set()
        for index, (external_id, content_hash) in enumerate(zip(actual_ids, actual_hashes)):
            if external_id and external_id in seen_ids:
                duplicate_rows.add(index)
            if content_hash and content_hash in seen_hashes:
                duplicate_rows.add(index)
            if external_id:
                seen_ids.add(external_id)
            if content_hash:
                seen_hashes.add(content_hash)
        duplicate = len(duplicate_rows)
        expected_set = set(expected_ids)
        actual_set = set(actual_ids)
        by_id: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            key = actual_id(row)
            if key:
                by_id.setdefault(key, row)
        role = sequence = content = source = conversation = 0
        for expected in expected_records:
            row = by_id.get(expected_id(expected))
            if row is None:
                continue
            role += int(str(row.get("role") or "") == str(getattr(expected, "role", "")))
            sequence += int(str(row.get("sequence") if row.get("sequence") is not None else "") == str(getattr(expected, "sequence", "")))
            content += int(str(row.get("content_hash") or "") == str(getattr(expected, "content_hash", "")))
            source += int(actual_source(row) == str(getattr(expected, "source_external_id", getattr(expected, "source_id", ""))))
            conversation += int(actual_conversation(row) == str(getattr(expected, "conversation_external_id", getattr(expected, "conversation_id", ""))))
        # Preserve the order delivered by the read model.  Sorting actual rows
        # here would turn a persisted-order defect into a false pass.
        ordered_external = len(expected_ids) if actual_ids == expected_ids else 0
        return cls(
            expected=len(expected_records),
            actual=len(rows),
            missing=len(expected_set - actual_set),
            extra=len(actual_set - expected_set),
            duplicate=duplicate,
            ordered_role_matches=role,
            content_hash_matches=content,
            sequence_matches=sequence,
            source_matches=source,
            conversation_matches=conversation,
            ordered_external_id_matches=ordered_external,
            duplicate_external_ids=duplicate_external_ids,
            duplicate_content_hashes=duplicate_content_hashes,
        )


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
