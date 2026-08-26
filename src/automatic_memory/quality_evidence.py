"""Auditable evidence primitives for the automatic-memory quality gate."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.models import ExtractionBatch
from src.sources import ExternalMessageKey, SourceReadModel


@dataclass(frozen=True)
class ExpectedImportedRow:
    source_external_id: str
    conversation_external_id: str
    message_external_id: str
    ingestion_ordinal: int
    sequence: int
    role: str
    content_hash: str
    occurred_at: str

    @property
    def stable_external_key(self) -> ExternalMessageKey:
        return ExternalMessageKey(
            self.source_external_id,
            self.conversation_external_id,
            self.message_external_id,
        )


@dataclass(frozen=True)
class ContentHashGroup:
    content_hash: str
    member_external_keys: tuple[ExternalMessageKey, ...]


@dataclass(frozen=True)
class StableDuplicateSummary:
    source_records: int
    conversation_records: int
    message_records: int
    memory_records: int

    @property
    def total(self) -> int:
        return self.source_records + self.conversation_records + self.message_records + self.memory_records


def build_expected_import_rows(batch: ExtractionBatch) -> tuple[ExpectedImportedRow, ...]:
    """Flatten adapter output using the one global ingestion order contract."""
    rows: list[ExpectedImportedRow] = []
    ordinal = 0
    for source in batch.structured_sources:
        for conversation in source.conversations:
            for message in conversation.messages:
                rows.append(
                    ExpectedImportedRow(
                        source_external_id=source.external_id,
                        conversation_external_id=conversation.external_id,
                        message_external_id=message.external_id,
                        ingestion_ordinal=ordinal,
                        sequence=int(message.sequence),
                        role=message.role,
                        content_hash=SourceReadModel.content_hash(message.content),
                        occurred_at=message.occurred_at,
                    )
                )
                ordinal += 1
    return tuple(rows)


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
    expected_rows: int
    actual_rows: int
    missing_external_keys: tuple[ExternalMessageKey, ...]
    extra_external_keys: tuple[ExternalMessageKey, ...]
    stable_duplicates: StableDuplicateSummary
    ordered_external_key_matches: int
    role_matches: int
    sequence_matches: int
    timestamp_matches: int
    content_hash_matches: int
    source_matches: int
    conversation_matches: int
    intentional_content_hash_groups: tuple[ContentHashGroup, ...]

    @property
    def ready(self) -> bool:
        expected = self.expected_rows
        return bool(
            expected > 0
            and self.actual_rows == expected
            and not self.missing_external_keys
            and not self.extra_external_keys
            and self.stable_duplicates.total == 0
            and all(
                value == expected
                for value in (
                    self.ordered_external_key_matches,
                    self.role_matches,
                    self.sequence_matches,
                    self.timestamp_matches,
                    self.content_hash_matches,
                    self.source_matches,
                    self.conversation_matches,
                )
            )
        )

    @classmethod
    def from_read_model(
        cls,
        read_model: SourceReadModel,
        *,
        ingestion_batch_id: str,
        expected_rows: Sequence[ExpectedImportedRow],
    ) -> "ImportedEvidenceAudit":
        rows: list[Mapping[str, Any]] = []
        offset = 0
        while True:
            page = read_model.list_ingestion_messages(ingestion_batch_id, limit=200, offset=offset)
            rows.extend(page.get("items") or [])
            pagination = page.get("pagination") or {}
            if not pagination.get("has_more"):
                break
            offset += int(pagination.get("limit") or len(page.get("items") or []))

        expected_keys = [item.stable_external_key for item in expected_rows]
        actual_keys = [
            ExternalMessageKey(
                str(row.get("source_external_id") or ""),
                str(row.get("conversation_external_id") or ""),
                str(row.get("message_external_id") or ""),
            )
            for row in rows
        ]
        expected_set = set(expected_keys)
        actual_set = set(actual_keys)
        source_identity: dict[str, set[str]] = {}
        conversation_identity: dict[tuple[str, str], set[str]] = {}
        message_counts: dict[ExternalMessageKey, int] = {}
        for row, key in zip(rows, actual_keys):
            source_identity.setdefault(key.source_external_id, set()).add(str(row.get("source_id") or ""))
            conversation_identity.setdefault((key.source_external_id, key.conversation_external_id), set()).add(str(row.get("conversation_id") or ""))
            message_counts[key] = message_counts.get(key, 0) + 1
        duplicates = StableDuplicateSummary(
            source_records=sum(max(0, len(ids) - 1) for ids in source_identity.values()),
            conversation_records=sum(max(0, len(ids) - 1) for ids in conversation_identity.values()),
            message_records=sum(max(0, count - 1) for count in message_counts.values()),
            memory_records=0,
        )
        paired = zip(expected_rows, rows)
        role = sequence = timestamp = content = source = conversation = ordered_external = 0
        for expected, row in paired:
            actual_key = ExternalMessageKey(
                str(row.get("source_external_id") or ""),
                str(row.get("conversation_external_id") or ""),
                str(row.get("message_external_id") or ""),
            )
            ordered_external += int(actual_key == expected.stable_external_key)
            role += int(row.get("role") == expected.role)
            sequence += int(row.get("sequence") == expected.sequence)
            timestamp += int(row.get("occurred_at") == expected.occurred_at)
            content += int(row.get("content_hash") == expected.content_hash)
            source += int(actual_key.source_external_id == expected.source_external_id)
            conversation += int(actual_key.conversation_external_id == expected.conversation_external_id)
        grouped: dict[str, set[ExternalMessageKey]] = {}
        for item in expected_rows:
            grouped.setdefault(item.content_hash, set()).add(item.stable_external_key)
        intentional = tuple(
            ContentHashGroup(content_hash, tuple(sorted(keys, key=lambda key: (key.source_external_id, key.conversation_external_id, key.message_external_id))))
            for content_hash, keys in sorted(grouped.items(), key=lambda pair: pair[0])
            if len(keys) >= 2
        )
        return cls(
            expected_rows=len(expected_rows),
            actual_rows=len(rows),
            missing_external_keys=tuple(sorted(expected_set - actual_set, key=lambda key: (key.source_external_id, key.conversation_external_id, key.message_external_id))),
            extra_external_keys=tuple(sorted(actual_set - expected_set, key=lambda key: (key.source_external_id, key.conversation_external_id, key.message_external_id))),
            stable_duplicates=duplicates,
            ordered_external_key_matches=ordered_external,
            role_matches=role,
            sequence_matches=sequence,
            timestamp_matches=timestamp,
            content_hash_matches=content,
            source_matches=source,
            conversation_matches=conversation,
            intentional_content_hash_groups=intentional,
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
