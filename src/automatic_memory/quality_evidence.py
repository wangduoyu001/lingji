"""Auditable evidence primitives for the automatic-memory quality gate."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat as stat_module
from dataclasses import dataclass
from enum import Enum
from typing import Literal
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.models import ExtractionBatch
from src.sources import ExternalMessageKey, SourceReadModel, SourceReadModelError
from .evaluation import EvaluationReport


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


class EvidenceState(str, Enum):
    NOT_MEASURED = "not_measured"
    INVALID = "invalid"
    FAILED = "failed"
    READY = "ready"


class ProtectedTreeSentinelError(ValueError):
    """Base class for stable, path-redacting protected-tree errors."""

    def __init__(self, code: str):
        self.code = code
        labels = {
            "ROOT_MISSING": "missing protected root",
            "ROOT_SYMLINK": "symlink protected root",
            "TREE_SYMLINK": "symlink in protected tree",
            "TREE_MISSING": "missing protected tree entry",
        }
        super().__init__(labels.get(code, code))


class ProtectedTreeUnavailableError(ProtectedTreeSentinelError):
    """The configured tree cannot be measured."""


class ProtectedTreeInvalidError(ProtectedTreeSentinelError):
    """A tree measurement was partial, raced, or internally inconsistent."""


@dataclass(frozen=True)
class ProtectedTreeSentinel:
    root_contract: tuple[str, ...]
    entries: Mapping[str, SentinelEntry]

    @classmethod
    def capture(cls, roots: Sequence[Path]) -> "ProtectedTreeSentinel":
        if not roots:
            raise ProtectedTreeUnavailableError("ROOTS_EMPTY")

        canonical: list[Path] = []
        for configured in roots:
            path = Path(configured).expanduser()
            if not path.is_absolute():
                path = Path(os.path.abspath(path))
            else:
                path = Path(os.path.normpath(str(path)))
            # Check every existing path component without following symlinks.
            current = Path(path.anchor)
            try:
                for component in path.parts[1:]:
                    current /= component
                    item = os.lstat(current)
                    if stat_module.S_ISLNK(item.st_mode):
                        raise ProtectedTreeUnavailableError("ROOT_SYMLINK")
            except ProtectedTreeSentinelError:
                raise
            except FileNotFoundError as exc:
                raise ProtectedTreeUnavailableError("ROOT_MISSING") from exc
            except OSError as exc:
                raise ProtectedTreeUnavailableError("ROOT_UNAVAILABLE") from exc
            resolved = Path(os.path.realpath(path))
            try:
                root_stat = os.lstat(path)
            except FileNotFoundError as exc:
                raise ProtectedTreeUnavailableError("ROOT_MISSING") from exc
            except OSError as exc:
                raise ProtectedTreeUnavailableError("ROOT_UNAVAILABLE") from exc
            if stat_module.S_ISLNK(root_stat.st_mode):
                raise ProtectedTreeUnavailableError("ROOT_SYMLINK")
            if not stat_module.S_ISDIR(root_stat.st_mode):
                raise ProtectedTreeUnavailableError("ROOT_NOT_DIRECTORY")
            canonical.append(resolved)

        canonical_sorted = sorted(canonical, key=lambda p: str(p))
        if len(set(canonical_sorted)) != len(canonical_sorted):
            raise ProtectedTreeUnavailableError("ROOT_DUPLICATE")
        for index, root in enumerate(canonical_sorted):
            for other in canonical_sorted[index + 1:]:
                try:
                    other.relative_to(root)
                except ValueError:
                    continue
                raise ProtectedTreeUnavailableError("ROOT_OVERLAP")

        identifiers = tuple(sorted(_root_identifier(root) for root in canonical_sorted))
        entries: dict[str, SentinelEntry] = {}
        for root in canonical_sorted:
            root_id = _root_identifier(root)
            _capture_entry(root, root_id, "", entries, is_root=True)
        return cls(identifiers, entries)

    def diff(self, after: "ProtectedTreeSentinel") -> tuple[SentinelChange, ...]:
        if not isinstance(after, ProtectedTreeSentinel) or self.root_contract != after.root_contract:
            raise ProtectedTreeInvalidError("ROOT_CONTRACT_MISMATCH")
        changes = []
        for key in sorted(set(self.entries) | set(after.entries)):
            before, current = self.entries.get(key), after.entries.get(key)
            if before != current:
                changes.append(SentinelChange(key, before, current))
        return tuple(changes)


def _root_identifier(root: Path) -> str:
    return hashlib.sha256(str(root).encode("utf-8")).hexdigest()


def _capture_entry(
    path: Path,
    root_id: str,
    relative: str,
    entries: dict[str, SentinelEntry],
    *,
    is_root: bool = False,
) -> None:
    try:
        before = os.lstat(path)
    except FileNotFoundError as exc:
        raise ProtectedTreeUnavailableError("TREE_MISSING") from exc
    except OSError as exc:
        raise ProtectedTreeUnavailableError("TREE_UNAVAILABLE") from exc
    if stat_module.S_ISLNK(before.st_mode):
        raise ProtectedTreeUnavailableError("TREE_SYMLINK")
    if is_root and not stat_module.S_ISDIR(before.st_mode):
        raise ProtectedTreeInvalidError("ROOT_REPLACED")
    key = f"{root_id}:{relative}" if relative else f"{root_id}:"
    if stat_module.S_ISDIR(before.st_mode):
        entries[key] = SentinelEntry(key, "dir", stat_module.S_IMODE(before.st_mode), before.st_size, None)
        try:
            with os.scandir(path) as iterator:
                names = sorted((item.name for item in iterator))
        except OSError as exc:
            raise ProtectedTreeUnavailableError("TREE_UNREADABLE") from exc
        for name in names:
            child = path / name
            child_relative = f"{relative}/{name}" if relative else name
            try:
                _capture_entry(child, root_id, child_relative, entries)
            except ProtectedTreeUnavailableError as exc:
                if exc.code == "TREE_MISSING":
                    raise ProtectedTreeInvalidError("TREE_TRAVERSAL_RACE") from exc
                raise
        try:
            with os.scandir(path) as iterator:
                after_names = sorted((item.name for item in iterator))
        except OSError as exc:
            raise ProtectedTreeInvalidError("TREE_TRAVERSAL_RACE") from exc
        if names != after_names:
            raise ProtectedTreeInvalidError("TREE_TRAVERSAL_RACE")
        try:
            final_directory = os.lstat(path)
        except OSError as exc:
            raise ProtectedTreeInvalidError("ROOT_RACE" if is_root else "TREE_TRAVERSAL_RACE") from exc
        if (not stat_module.S_ISDIR(final_directory.st_mode)
                or stat_module.S_IMODE(final_directory.st_mode) != stat_module.S_IMODE(before.st_mode)
                or getattr(final_directory, "st_ino", None) != getattr(before, "st_ino", None)
                or getattr(final_directory, "st_dev", None) != getattr(before, "st_dev", None)):
            raise ProtectedTreeInvalidError("ROOT_RACE" if is_root else "TREE_TRAVERSAL_RACE")
    elif stat_module.S_ISREG(before.st_mode):
        digest = hashlib.sha256()
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(path, flags)
            try:
                opened = os.fstat(fd)
                if not stat_module.S_ISREG(opened.st_mode) or opened.st_size != before.st_size or stat_module.S_IMODE(opened.st_mode) != stat_module.S_IMODE(before.st_mode):
                    raise ProtectedTreeInvalidError("FILE_REPLACED")
                with os.fdopen(fd, "rb", closefd=True) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                    fd = -1
            finally:
                if fd >= 0:
                    os.close(fd)
            final = os.lstat(path)
        except ProtectedTreeSentinelError:
            raise
        except (OSError, ValueError) as exc:
            raise ProtectedTreeUnavailableError("FILE_UNREADABLE") from exc
        if (not stat_module.S_ISREG(final.st_mode) or final.st_size != before.st_size
                or stat_module.S_IMODE(final.st_mode) != stat_module.S_IMODE(before.st_mode)
                or getattr(final, "st_ino", None) != getattr(before, "st_ino", None)
                or getattr(final, "st_dev", None) != getattr(before, "st_dev", None)):
            raise ProtectedTreeInvalidError("FILE_RACE")
        entries[key] = SentinelEntry(key, "file", stat_module.S_IMODE(before.st_mode), before.st_size, digest.hexdigest())
    else:
        raise ProtectedTreeUnavailableError("SPECIAL_FILE")


class QualityPublicationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def write_quality_json_atomic(
    output_path: Path,
    value: Mapping[str, Any],
    *,
    protected_roots: Sequence[Path],
) -> None:
    """Write deterministic JSON beneath an already-admitted real directory."""
    output = Path(output_path).expanduser()
    if not output.is_absolute():
        output = Path(os.path.abspath(output))
    parent = output.parent
    try:
        parent_stat = os.lstat(parent)
    except OSError as exc:
        raise QualityPublicationError("PARENT_UNAVAILABLE") from exc
    if not stat_module.S_ISDIR(parent_stat.st_mode):
        raise QualityPublicationError("PARENT_NOT_DIRECTORY")
    try:
        current = Path(parent.anchor)
        for component in parent.parts[1:]:
            current /= component
            item = os.lstat(current)
            if stat_module.S_ISLNK(item.st_mode):
                raise QualityPublicationError("PARENT_SYMLINK")
        if output.exists() or output.is_symlink():
            item = os.lstat(output)
            if stat_module.S_ISLNK(item.st_mode):
                raise QualityPublicationError("OUTPUT_SYMLINK")
    except QualityPublicationError:
        raise
    except OSError as exc:
        raise QualityPublicationError("OUTPUT_UNAVAILABLE") from exc

    candidate = Path(os.path.realpath(output))
    for configured in protected_roots:
        protected = Path(os.path.realpath(Path(configured).expanduser()))
        try:
            candidate.relative_to(protected)
        except ValueError:
            continue
        raise QualityPublicationError("PROTECTED_OUTPUT")
    try:
        payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise QualityPublicationError("SERIALIZATION_FAILED") from exc

    temporary: Path | None = None
    fd = -1
    try:
        for _ in range(32):
            candidate_temp = parent / f".{output.name}.{secrets.token_hex(12)}.tmp"
            try:
                fd = os.open(candidate_temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                temporary = candidate_temp
                break
            except FileExistsError:
                continue
        if temporary is None:
            raise QualityPublicationError("TEMP_CREATE_FAILED")
        try:
            with os.fdopen(fd, "wb", closefd=True) as stream:
                fd = -1
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise QualityPublicationError("WRITE_FAILED") from exc
        try:
            os.replace(temporary, output)
            temporary = None
        except OSError as exc:
            raise QualityPublicationError("REPLACE_FAILED") from exc
        try:
            directory_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except (OSError, ValueError):
            # Directory fsync is unsupported on some platforms; replacement is
            # already atomic and durable at the file descriptor boundary.
            pass
    except QualityPublicationError:
        raise
    except OSError as exc:
        raise QualityPublicationError("PUBLICATION_FAILED") from exc
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise QualityPublicationError("TEMP_CLEANUP_FAILED") from exc


def _read_ingestion_rows(read_model: SourceReadModel, ingestion_batch_id: str) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    offset = 0
    expected_total: int | None = None
    while True:
        page = read_model.list_ingestion_messages(ingestion_batch_id, limit=200, offset=offset)
        pagination = page.get("pagination")
        if not isinstance(pagination, Mapping):
            raise SourceReadModelError("ingestion audit pagination is missing")
        total = pagination.get("total")
        page_offset = pagination.get("offset")
        page_limit = pagination.get("limit")
        has_more = pagination.get("has_more")
        if (
            isinstance(total, bool)
            or not isinstance(total, int)
            or total < 0
            or isinstance(page_offset, bool)
            or not isinstance(page_offset, int)
            or page_offset != offset
            or isinstance(page_limit, bool)
            or not isinstance(page_limit, int)
            or page_limit != 200
            or not isinstance(has_more, bool)
        ):
            raise SourceReadModelError("malformed ingestion audit pagination")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise SourceReadModelError("ingestion audit pagination total drift")
        items = page.get("items")
        if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
            raise SourceReadModelError("malformed ingestion audit page items")
        if len(items) > page_limit or offset + len(items) > total:
            raise SourceReadModelError("ingestion audit pagination overrun")
        rows.extend(items)
        if has_more and not items:
            raise SourceReadModelError("ingestion audit pagination made no progress")
        if has_more and offset + len(items) >= total:
            raise SourceReadModelError("ingestion audit pagination has_more is inconsistent")
        if not has_more:
            if len(rows) != total:
                raise SourceReadModelError("ingestion audit pagination final count mismatch")
            return rows
        next_offset = offset + len(items)
        if next_offset <= offset:
            raise SourceReadModelError("ingestion audit pagination made no progress")
        offset = next_offset


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
        rows = _read_ingestion_rows(read_model, ingestion_batch_id)

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
            source_id = str(row.get("source_id") or "")
            conversation_id = str(row.get("conversation_id") or "")
            if source_id:
                source_identity.setdefault(key.source_external_id, set()).add(source_id)
            if conversation_id:
                conversation_identity.setdefault((key.source_external_id, key.conversation_external_id), set()).add(conversation_id)
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
            source_id = str(row.get("source_id") or "")
            conversation_id = str(row.get("conversation_id") or "")
            message_id = str(row.get("message_id") or "")
            internal_ids_valid = bool(source_id and conversation_id and message_id)
            ordered_external += int(internal_ids_valid and actual_key == expected.stable_external_key)
            role += int(row.get("role") == expected.role)
            sequence += int(row.get("sequence") == expected.sequence)
            timestamp += int(row.get("occurred_at") == expected.occurred_at)
            content += int(row.get("content_hash") == expected.content_hash)
            source += int(bool(source_id) and actual_key.source_external_id == expected.source_external_id)
            conversation += int(bool(conversation_id) and actual_key.conversation_external_id == expected.conversation_external_id)
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
    import_audit: EvidenceState
    promotion_provenance: EvidenceState
    gateway_selection: EvidenceState
    production_sentinel: EvidenceState
    mcp_parity: EvidenceState
    qdrant_degradation: EvidenceState
    corruption_isolation: EvidenceState
    context_baseline: EvidenceState
    scale: EvidenceState
    owner_review: EvidenceState
    reboot_recovery: EvidenceState
    mac_release: EvidenceState
    windows_release: EvidenceState

    _FUNCTIONAL_FIELDS = (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
    )
    _MAC_FIELDS = ("scale", "owner_review", "reboot_recovery", "mac_release")

    @property
    def functional_measured(self) -> bool:
        return all(self._state(field) in (EvidenceState.READY, EvidenceState.FAILED) for field in self._FUNCTIONAL_FIELDS)

    @property
    def functional_ready(self) -> bool:
        return all(self._state(field) is EvidenceState.READY for field in self._FUNCTIONAL_FIELDS)

    @property
    def mac_release_ready(self) -> bool:
        return self.functional_ready and all(self._state(field) is EvidenceState.READY for field in self._MAC_FIELDS)

    @property
    def windows_release_ready(self) -> bool:
        return self.mac_release_ready and self._state("windows_release") is EvidenceState.READY

    # Compatibility names are intentionally derived only; the runner still
    # has its historical return contract until Task 6 migrates it.
    @property
    def functional_fields_ready(self) -> bool:
        return self.functional_ready

    @property
    def functional_status(self) -> str:
        return "PASS" if self.functional_ready else "NOT_EVALUATED"

    @property
    def should_run_acceptance_gate(self) -> bool:
        return self.functional_measured

    def _state(self, field: str) -> EvidenceState | Any:
        return getattr(self, field)


@dataclass(frozen=True)
class QualityRunEnvelope:
    readiness: QualityEvidenceReadiness
    production_pollution: int | None
    evaluation_report: EvaluationReport | None
    functional_status: Literal["NOT_EVALUATED", "PASS", "FAIL"]
    phase_status: Literal["NOT_EVALUATED", "PASS", "FAIL", "BLOCKED"]
    windows_status: Literal["NOT_EVALUATED", "PASS", "FAIL", "BLOCKED"]
    blocked_reasons: tuple[str, ...]


def _reason_codes(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        text = str(value)
        code = "".join(char if char.isalnum() else "_" for char in text.upper()).strip("_")
        if code and code not in result:
            result.append(code)
    return tuple(result)


def _closed_envelope(readiness: QualityEvidenceReadiness, pollution: int | None, reasons: Sequence[str]) -> QualityRunEnvelope:
    return QualityRunEnvelope(readiness, pollution, None, "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED", _reason_codes(reasons))


def finalize_quality_envelope(
    *,
    readiness: QualityEvidenceReadiness,
    production_pollution: int | None,
    evaluation_report: Any | None,
    acceptance_gate: Any,
    blocked_reasons: Sequence[str] = (),
) -> QualityRunEnvelope:
    """Finalize immutable evidence around the unchanged frozen evaluator."""
    from dataclasses import replace
    fields = QualityEvidenceReadiness._FUNCTIONAL_FIELDS + QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",)
    if not isinstance(readiness, QualityEvidenceReadiness) or any(type(getattr(readiness, field, None)) is not EvidenceState for field in fields):
        return _closed_envelope(readiness, None, ("INVALID_EVIDENCE",))
    sentinel = readiness.production_sentinel
    pollution_valid = (
        (sentinel is EvidenceState.READY and type(production_pollution) is int and production_pollution == 0)
        or (sentinel is EvidenceState.FAILED and type(production_pollution) is int and production_pollution > 0)
        or (sentinel in (EvidenceState.NOT_MEASURED, EvidenceState.INVALID) and production_pollution is None)
    )
    if not pollution_valid:
        return _closed_envelope(readiness, None, ("PRODUCTION_SENTINEL_MISMATCH",))
    if not readiness.functional_measured:
        return _closed_envelope(readiness, production_pollution, blocked_reasons)
    if not isinstance(evaluation_report, EvaluationReport):
        return _closed_envelope(readiness, production_pollution, ("MALFORMED_EVALUATION_REPORT",))
    if type(getattr(evaluation_report, "production_pollution", None)) is not int or evaluation_report.production_pollution != production_pollution:
        return _closed_envelope(readiness, None, ("MALFORMED_EVALUATION_REPORT",))
    try:
        functional_report = replace(evaluation_report, owner_review_success=100.0, reboot_recovery=100.0, blocked_reasons=())
        functional_verdict = acceptance_gate.evaluate(functional_report)
        frozen_verdict = acceptance_gate.evaluate(evaluation_report)
    except Exception:
        return _closed_envelope(readiness, production_pollution, ("GATE_EXCEPTION",))
    if functional_verdict not in ("PASS", "FAIL") or frozen_verdict not in ("PASS", "FAIL", "BLOCKED"):
        return _closed_envelope(readiness, production_pollution, ("MALFORMED_GATE_RESULT",))
    if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
        if functional_verdict == "PASS":
            return _closed_envelope(readiness, production_pollution, ("CONTRADICTORY_FUNCTIONAL_EVIDENCE",))
    if functional_verdict == "FAIL":
        return QualityRunEnvelope(readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED", _reason_codes(tuple(blocked_reasons) + ("WINDOWS_AFTER_MAC",)))
    if any(getattr(readiness, field) in (EvidenceState.FAILED,) for field in QualityEvidenceReadiness._MAC_FIELDS):
        phase = "FAIL"
        reasons = blocked_reasons
    elif not readiness.mac_release_ready:
        reasons_list = list(blocked_reasons)
        for field in QualityEvidenceReadiness._MAC_FIELDS:
            state = getattr(readiness, field)
            if state is not EvidenceState.READY:
                reasons_list.append(f"{field}_{state.value}")
        phase = "BLOCKED"
        reasons = tuple(reasons_list)
    elif frozen_verdict == "PASS":
        phase = "PASS"
        reasons = blocked_reasons
    elif frozen_verdict == "FAIL":
        phase = "FAIL"
        reasons = blocked_reasons
    else:
        return _closed_envelope(readiness, production_pollution, ("CONTRADICTORY_GATE_RESULT",))
    if phase != "PASS":
        windows = "BLOCKED"
        reasons = tuple(reasons) + ("WINDOWS_AFTER_MAC",)
    elif readiness.windows_release is EvidenceState.READY:
        windows = "PASS"
    elif readiness.windows_release is EvidenceState.FAILED:
        windows = "FAIL"
    else:
        windows = "BLOCKED"
        reasons = tuple(reasons) + (f"windows_release_{readiness.windows_release.value}",)
    return QualityRunEnvelope(readiness, production_pollution, evaluation_report, "PASS", phase, windows, _reason_codes(reasons))
