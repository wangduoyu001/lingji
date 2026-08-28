"""Auditable evidence primitives for the automatic-memory quality gate."""
from __future__ import annotations

import hashlib
import errno
import json
import os
import secrets
import stat as stat_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.models import ExtractionBatch
from src.sources import ExternalMessageKey, SourceReadModel, SourceReadModelError
from src.auto_review.models import PromotionEvidence, PromotionPersistenceAudit, PromotionProjectionState
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


def audit_promotion_persistence(memory_db: Any, *, promotion_evidence: Sequence[PromotionEvidence]) -> PromotionPersistenceAudit:
    """Compare durable active derived rows with verified activation evidence."""
    active = [item.memory_id for item in promotion_evidence if item.state is PromotionProjectionState.VISIBLE_ACTIVE or str(item.state) == PromotionProjectionState.VISIBLE_ACTIVE.value]
    expected = tuple(sorted(active))
    if len(active) != len(set(active)):
        expected = tuple(sorted(active))
    rows = tuple(memory_db.list_derived_projection_identity_rows())
    persisted = tuple(sorted(str(row.get("memory_id") or "") for row in rows))
    distinct = set(persisted)
    return PromotionPersistenceAudit(
        expected_memory_ids=expected,
        persisted_memory_ids=persisted,
        missing_memory_ids=tuple(sorted(set(expected) - distinct)),
        extra_memory_ids=tuple(sorted(distinct - set(expected))),
        duplicate_memory_records=max(0, len(persisted) - len(distinct)),
    )


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
        """Capture a finite descriptor-anchored snapshot.

        The snapshot point is the successful final no-follow root descriptor
        identity observation and its comparison with the initial observation.
        A mutation strictly after that observation belongs to a later capture;
        this operation performs no unbounded post-snapshot retries.
        """
        if not roots:
            raise ProtectedTreeUnavailableError("ROOTS_EMPTY")

        canonical: list[Path] = []
        admitted: dict[Path, os.stat_result] = {}
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
            admitted[resolved] = root_stat

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
            fd = _open_anchored_directory(root)
            try:
                try:
                    root_identity = os.fstat(fd)
                except Exception as exc:
                    raise ProtectedTreeInvalidError("ROOT_FSTAT_FAILED") from exc
                if not _metadata_matches(admitted[root], root_identity):
                    raise ProtectedTreeInvalidError("ROOT_RACE")
                _capture_directory_fd(fd, root_id, "", entries, is_root=True)
                try:
                    final_fd = _open_anchored_directory(root)
                    try:
                        try:
                            final_identity = os.fstat(final_fd)
                        except Exception as exc:
                            raise ProtectedTreeInvalidError("ROOT_FSTAT_FAILED") from exc
                    finally:
                        owned_final_fd = final_fd
                        final_fd = -1
                        try:
                            os.close(owned_final_fd)
                        except Exception as exc:
                            raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc
                except ProtectedTreeSentinelError as exc:
                    if isinstance(exc, ProtectedTreeInvalidError) and exc.code == "ROOT_FSTAT_FAILED":
                        raise
                    raise ProtectedTreeInvalidError("ROOT_RACE") from exc
                if not _metadata_matches(root_identity, final_identity, include_size=False):
                    raise ProtectedTreeInvalidError("ROOT_RACE")
            finally:
                owned_fd = fd
                fd = -1
                try:
                    os.close(owned_fd)
                except Exception as exc:
                    raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc
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


def _metadata_matches(first: os.stat_result, second: os.stat_result, *, include_size: bool = True) -> bool:
    fields = ("st_dev", "st_ino", "st_mode")
    if include_size:
        fields += ("st_size",)
    return all(
        not hasattr(first, field) or getattr(first, field) == getattr(second, field)
        for field in fields + ("st_mtime_ns", "st_ctime_ns")
    )


def _safe_traversal_available() -> bool:
    return bool(
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "supports_dir_fd")
        and any(getattr(fn, "__name__", "") == "open" for fn in os.supports_dir_fd)
        and any(getattr(fn, "__name__", "") == "stat" for fn in os.supports_dir_fd)
    )


def _safe_publication_available() -> bool:
    return bool(
        _safe_traversal_available()
        and any(getattr(fn, "__name__", "") == "rename" for fn in os.supports_dir_fd)
        and any(getattr(fn, "__name__", "") == "unlink" for fn in os.supports_dir_fd)
    )


def _open_anchored_directory(path: Path) -> int:
    if not _safe_traversal_available():
        raise ProtectedTreeUnavailableError("SAFE_TRAVERSAL_UNAVAILABLE")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = -1
    try:
        fd = os.open(path.anchor, flags)
        for component in path.parts[1:]:
            child_fd = os.open(component, flags, dir_fd=fd)
            previous_fd = fd
            fd = -1
            try:
                os.close(previous_fd)
            except Exception as exc:
                owned_child_fd = child_fd
                child_fd = -1
                try:
                    os.close(owned_child_fd)
                except Exception:
                    pass
                raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc
            fd = child_fd
        return fd
    except ProtectedTreeSentinelError:
        owned_fd = fd
        fd = -1
        if owned_fd >= 0:
            try:
                os.close(owned_fd)
            except Exception:
                pass
        raise
    except OSError as exc:
        owned_fd = fd
        fd = -1
        if owned_fd >= 0:
            try:
                os.close(owned_fd)
            except Exception:
                pass
        raise ProtectedTreeUnavailableError("ROOT_OPEN_FAILED") from exc


def _hash_fd(fd: int) -> str:
    digest = hashlib.sha256()
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            return digest.hexdigest()
        digest.update(chunk)


def _capture_file_fd(
    parent_fd: int,
    name: str,
    key: str,
    before: os.stat_result,
    entries: dict[str, SentinelEntry],
) -> None:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    fd = -1
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
        opened = os.fstat(fd)
        if not stat_module.S_ISREG(opened.st_mode) or not _metadata_matches(before, opened):
            raise ProtectedTreeInvalidError("FILE_REPLACED")
        first_digest = _hash_fd(fd)
        first_after = os.fstat(fd)
        second_digest = _hash_fd(fd)
        second_after = os.fstat(fd)
        if first_digest != second_digest:
            raise ProtectedTreeInvalidError("FILE_CONTENT_RACE")
        for observed in (first_after, second_after):
            if not stat_module.S_ISREG(observed.st_mode) or not _metadata_matches(before, observed):
                raise ProtectedTreeInvalidError("FILE_RACE")
        entries[key] = SentinelEntry(key, "file", stat_module.S_IMODE(before.st_mode), before.st_size, first_digest)
    except ProtectedTreeSentinelError:
        raise
    except OSError as exc:
        raise ProtectedTreeUnavailableError("FILE_UNREADABLE") from exc
    finally:
        if fd >= 0:
            owned_fd = fd
            fd = -1
            try:
                os.close(owned_fd)
            except Exception as exc:
                raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc


def _capture_directory_fd(
    fd: int,
    root_id: str,
    relative: str,
    entries: dict[str, SentinelEntry],
    *,
    is_root: bool = False,
) -> None:
    try:
        before = os.fstat(fd)
    except OSError as exc:
        raise ProtectedTreeInvalidError("TREE_UNAVAILABLE") from exc
    if not stat_module.S_ISDIR(before.st_mode):
        raise ProtectedTreeInvalidError("ROOT_REPLACED" if is_root else "TREE_REPLACED")
    key = f"{root_id}:{relative}" if relative else f"{root_id}:"
    entries[key] = SentinelEntry(key, "dir", stat_module.S_IMODE(before.st_mode), before.st_size, None)
    try:
        with os.scandir(fd) as iterator:
            names = sorted((item.name for item in iterator))
    except OSError as exc:
        raise ProtectedTreeUnavailableError("TREE_UNREADABLE") from exc
    for name in names:
        try:
            child_stat = os.stat(name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise ProtectedTreeInvalidError("TREE_TRAVERSAL_RACE") from exc
        except OSError as exc:
            raise ProtectedTreeUnavailableError("TREE_UNREADABLE") from exc
        child_relative = f"{relative}/{name}" if relative else name
        child_key = f"{root_id}:{child_relative}"
        if stat_module.S_ISDIR(child_stat.st_mode):
            child_fd = -1
            try:
                child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                opened_child = os.fstat(child_fd)
                if not stat_module.S_ISDIR(opened_child.st_mode) or not _metadata_matches(child_stat, opened_child):
                    raise ProtectedTreeInvalidError("TREE_TRAVERSAL_RACE")
                _capture_directory_fd(child_fd, root_id, child_relative, entries)
            except ProtectedTreeSentinelError:
                raise
            except OSError as exc:
                raise ProtectedTreeInvalidError("TREE_TRAVERSAL_RACE") from exc
            finally:
                if child_fd >= 0:
                    owned_child_fd = child_fd
                    child_fd = -1
                    try:
                        os.close(owned_child_fd)
                    except Exception as exc:
                        raise ProtectedTreeInvalidError("FD_CLOSE_FAILED") from exc
        elif stat_module.S_ISREG(child_stat.st_mode):
            _capture_file_fd(fd, name, child_key, child_stat, entries)
        elif stat_module.S_ISLNK(child_stat.st_mode):
            raise ProtectedTreeUnavailableError("TREE_SYMLINK")
        else:
            raise ProtectedTreeUnavailableError("SPECIAL_FILE")
    try:
        with os.scandir(fd) as iterator:
            after_names = sorted((item.name for item in iterator))
        final_directory = os.fstat(fd)
    except OSError as exc:
        raise ProtectedTreeInvalidError("ROOT_RACE" if is_root else "TREE_TRAVERSAL_RACE") from exc
    if names != after_names or (
        not stat_module.S_ISDIR(final_directory.st_mode)
        or stat_module.S_IMODE(final_directory.st_mode) != stat_module.S_IMODE(before.st_mode)
        or final_directory.st_ino != before.st_ino
        or final_directory.st_dev != before.st_dev
    ):
        raise ProtectedTreeInvalidError("ROOT_RACE" if is_root else "TREE_TRAVERSAL_RACE")


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
    if not _safe_publication_available():
        raise QualityPublicationError("UNSAFE_PUBLICATION_PLATFORM")
    try:
        current = Path(parent.anchor)
        for component in Path(os.path.abspath(parent)).parts[1:]:
            current /= component
            item = os.lstat(current)
            if stat_module.S_ISLNK(item.st_mode):
                raise QualityPublicationError("PARENT_SYMLINK")
    except QualityPublicationError:
        raise
    except FileNotFoundError as exc:
        raise QualityPublicationError("PARENT_UNAVAILABLE") from exc
    except OSError as exc:
        raise QualityPublicationError("PARENT_UNAVAILABLE") from exc

    # Admission is checked lexically/canonically before opening the parent;
    # the descriptor below is the authority for all subsequent operations.
    candidate = Path(os.path.realpath(output))
    for configured in protected_roots:
        protected = Path(os.path.realpath(Path(configured).expanduser()))
        try:
            candidate.relative_to(protected)
        except ValueError:
            continue
        raise QualityPublicationError("PROTECTED_OUTPUT")
    try:
        payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except Exception as exc:
        raise QualityPublicationError("SERIALIZATION_FAILED") from exc

    temporary: Path | None = None
    fd = -1
    parent_fd = -1
    parent_identity: tuple[int, int] | None = None
    try:
        parent_fd = _open_publication_parent(parent)
        parent_stat = os.fstat(parent_fd)
        parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
        try:
            target = os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
            if stat_module.S_ISLNK(target.st_mode):
                raise QualityPublicationError("OUTPUT_SYMLINK")
        except FileNotFoundError:
            pass
        except QualityPublicationError:
            raise
        except OSError as exc:
            raise QualityPublicationError("OUTPUT_UNAVAILABLE") from exc
        for _ in range(32):
            candidate_name = f".{output.name}.{secrets.token_hex(12)}.tmp"
            try:
                fd = os.open(candidate_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
                temporary = Path(candidate_name)
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
        except Exception as exc:
            raise QualityPublicationError("WRITE_FAILED") from exc
        try:
            os.replace(temporary.name, output.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            temporary = None
        except Exception as exc:
            raise QualityPublicationError("REPLACE_FAILED") from exc
        try:
            current_parent = os.stat(parent, follow_symlinks=False)
            if parent_identity != (current_parent.st_dev, current_parent.st_ino):
                raise QualityPublicationError("PARENT_RACE_AFTER_REPLACE")
        except QualityPublicationError:
            raise
        except OSError as exc:
            raise QualityPublicationError("PARENT_RACE_AFTER_REPLACE") from exc
        try:
            os.fsync(parent_fd)
        except Exception as exc:
            unsupported = isinstance(exc, OSError) and exc.errno in {errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}
            if not unsupported:
                raise QualityPublicationError("DIRECTORY_FSYNC_FAILED_AFTER_REPLACE") from exc
    except QualityPublicationError:
        raise
    except OSError as exc:
        raise QualityPublicationError("PUBLICATION_FAILED") from exc
    finally:
        cleanup_error: QualityPublicationError | None = None
        if fd >= 0:
            owned_fd = fd
            fd = -1
            try:
                os.close(owned_fd)
            except Exception:
                pass
        if temporary is not None:
            try:
                if parent_fd >= 0:
                    os.unlink(temporary.name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            except Exception as exc:
                cleanup_error = QualityPublicationError("TEMP_CLEANUP_FAILED")
        if parent_fd >= 0:
            owned_parent_fd = parent_fd
            parent_fd = -1
            try:
                os.close(owned_parent_fd)
            except Exception:
                if cleanup_error is None:
                    cleanup_error = QualityPublicationError("FD_CLOSE_FAILED")
        if cleanup_error is not None:
            raise cleanup_error


def _open_publication_parent(path: Path) -> int:
    if not _safe_publication_available():
        raise QualityPublicationError("UNSAFE_PUBLICATION_PLATFORM")
    absolute = Path(os.path.abspath(path))
    fd = -1
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(absolute.anchor, flags)
        for component in absolute.parts[1:]:
            child = os.open(component, flags, dir_fd=fd)
            previous_fd = fd
            fd = -1
            try:
                os.close(previous_fd)
            except Exception as exc:
                owned_child = child
                child = -1
                try:
                    os.close(owned_child)
                except Exception:
                    pass
                raise QualityPublicationError("FD_CLOSE_FAILED") from exc
            fd = child
        return fd
    except QualityPublicationError:
        owned_fd = fd
        fd = -1
        if owned_fd >= 0:
            try:
                os.close(owned_fd)
            except Exception:
                pass
        raise
    except OSError as exc:
        owned_fd = fd
        fd = -1
        if owned_fd >= 0:
            try:
                os.close(owned_fd)
            except Exception:
                pass
        raise QualityPublicationError("PARENT_UNAVAILABLE") from exc


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
    # This inventory is deliberately machine-only: it reports cleanup state
    # without embedding paths, exception text, fixture content or tokens.
    cleanup_inventory: Mapping[str, Any] = field(default_factory=dict)
    # Measured, path-free functional details retained for the quality report.
    evidence_details: Mapping[str, Any] = field(default_factory=dict)


def _reason_codes(values: Sequence[str]) -> tuple[str, ...]:
    allowed = {
        "WINDOWS_AFTER_MAC", "INVALID_EVIDENCE", "PRODUCTION_SENTINEL_MISMATCH",
        "MALFORMED_EVALUATION_REPORT", "GATE_EXCEPTION", "MALFORMED_GATE_RESULT",
        "CONTRADICTORY_FUNCTIONAL_EVIDENCE", "CONTRADICTORY_GATE_RESULT",
        "TEMP_CLEANUP_FAILED", "TEMP_CLEANUP_INCOMPLETE",
        "RUNNER_FAILED",
        "OWNER_REVIEW_NOT_RUN_IN_AUTOMATED_GATE", "REBOOT_RECOVERY_NOT_RUN_IN_AUTOMATED_GATE",
        "MAC_M5_P95_RESERVED_FOR_TASK_6", "MAC_IDLE_CPU_RESERVED_FOR_TASK_6",
    }
    for field in QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",):
        for state in EvidenceState:
            allowed.add(f"{field.upper()}_{state.value.upper()}")
    for stage in (
        "ADMISSION", "ROOT", "SENTINEL", "FIXTURE", "IMPORT", "GATEWAY",
        "PROMOTION", "AUDIT", "SCORING", "EVALUATOR", "PUBLICATION_PRE",
        "CLEANUP",
    ):
        allowed.add(f"RUNNER_{stage}_FAILED")
    result: list[str] = []
    try:
        iterator = iter(values)
        while True:
            try:
                value = next(iterator)
            except StopIteration:
                break
            except Exception:
                return ("UNTRUSTED_BLOCKED_REASON",)
            if type(value) is not str:
                code = "UNTRUSTED_BLOCKED_REASON"
            else:
                code = value.upper()
                if code not in allowed:
                    code = "UNTRUSTED_BLOCKED_REASON"
            if code not in result:
                result.append(code)
    except Exception:
        return ("UNTRUSTED_BLOCKED_REASON",)
    return tuple(result)


def _closed_envelope(readiness: QualityEvidenceReadiness, pollution: int | None, reasons: Sequence[str]) -> QualityRunEnvelope:
    return QualityRunEnvelope(readiness, pollution, None, "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED", _reason_codes(reasons))


def _safe_reason_values(values: Sequence[str]) -> tuple[Any, ...]:
    try:
        return tuple(values)
    except Exception:
        return ("UNTRUSTED_BLOCKED_REASON",)


def _valid_counter(value: Any) -> bool:
    return type(value) is int and value >= 0


def _valid_percentage(value: Any) -> bool:
    import math
    return (
        type(value) in (int, float)
        and math.isfinite(float(value)) and 0 <= float(value) <= 100
    )


def _valid_ratio(numerator: Any, denominator: Any, percentage: Any) -> bool:
    import math
    return (_valid_counter(numerator) and _valid_counter(denominator) and denominator > 0
            and numerator <= denominator and _valid_percentage(percentage)
            and math.isclose(float(percentage), 100 * numerator / denominator, rel_tol=1e-9, abs_tol=1e-9))


def _valid_evaluation_report(report: EvaluationReport, pollution: int) -> bool:
    if type(report) is not EvaluationReport:
        return False
    counters = (
        "answered_questions", "imported_messages", "expected_messages", "ordered_role_matches",
        "expected_ordered_roles", "valid_fact_hits", "valid_fact_total", "citation_hits", "citation_total",
        "automatic_activation_correct", "automatic_activation_total", "protected_false_promotions",
        "stale_current_leaks", "duplicate_records", "baseline_context_chars", "rendered_context_chars",
        "mcp_successes", "mcp_attempts", "production_pollution",
    )
    if any(not _valid_counter(getattr(report, field, None)) for field in counters):
        return False
    if report.production_pollution != pollution:
        return False
    if not all(_valid_ratio(*values) for values in (
        (report.valid_fact_hits, report.valid_fact_total, report.valid_fact_recall),
        (report.citation_hits, report.citation_total, report.citation_accuracy),
        (report.automatic_activation_correct, report.automatic_activation_total, report.automatic_activation_accuracy),
        (report.mcp_successes, report.mcp_attempts, report.mcp_success_rate),
    )):
        return False
    if not _valid_counter(report.baseline_context_chars) or report.baseline_context_chars <= 0:
        return False
    if report.rendered_context_chars > report.baseline_context_chars or not _valid_percentage(report.context_reduction):
        return False
    import math
    if not math.isclose(
        float(report.context_reduction),
        (1 - report.rendered_context_chars / report.baseline_context_chars) * 100,
        rel_tol=1e-9, abs_tol=1e-9,
    ):
        return False
    for field in ("owner_review_success", "reboot_recovery"):
        value = getattr(report, field)
        if value is not None and not _valid_percentage(value):
            return False
    if type(report.blocked_reasons) is not tuple or any(
        type(reason) is not str or not reason for reason in report.blocked_reasons
    ):
        return False
    return True


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
    if type(readiness) is not QualityEvidenceReadiness:
        return _closed_envelope(readiness, None, ("INVALID_EVIDENCE",))
    try:
        readiness_valid = all(type(getattr(readiness, field)) is EvidenceState for field in fields)
    except Exception:
        return _closed_envelope(readiness, None, ("INVALID_EVIDENCE",))
    if not readiness_valid:
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
    if type(evaluation_report) is not EvaluationReport:
        return _closed_envelope(readiness, production_pollution, ("MALFORMED_EVALUATION_REPORT",))
    try:
        report_valid = _valid_evaluation_report(evaluation_report, production_pollution)
    except Exception:
        report_valid = False
    if not report_valid:
        return _closed_envelope(readiness, None, ("MALFORMED_EVALUATION_REPORT",))
    safe_reasons = _safe_reason_values(blocked_reasons)
    try:
        functional_report = replace(evaluation_report, owner_review_success=100.0, reboot_recovery=100.0, blocked_reasons=())
        functional_verdict = acceptance_gate.evaluate(functional_report)
    except Exception:
        if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
            return QualityRunEnvelope(
                readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED",
                _reason_codes(safe_reasons + ("GATE_EXCEPTION", "WINDOWS_AFTER_MAC")),
            )
        return _closed_envelope(readiness, production_pollution, ("GATE_EXCEPTION",))
    if type(functional_verdict) is not str or functional_verdict not in ("PASS", "FAIL"):
        if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
            return QualityRunEnvelope(
                readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED",
                _reason_codes(safe_reasons + ("MALFORMED_GATE_RESULT", "WINDOWS_AFTER_MAC")),
            )
        return _closed_envelope(readiness, production_pollution, ("MALFORMED_GATE_RESULT",))
    try:
        frozen_verdict = acceptance_gate.evaluate(evaluation_report)
    except Exception:
        if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
            return QualityRunEnvelope(
                readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED",
                _reason_codes(safe_reasons + ("GATE_EXCEPTION", "WINDOWS_AFTER_MAC")),
            )
        return _closed_envelope(readiness, production_pollution, ("GATE_EXCEPTION",))
    if type(frozen_verdict) is not str or frozen_verdict not in ("PASS", "FAIL", "BLOCKED"):
        if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
            return QualityRunEnvelope(
                readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED",
                _reason_codes(safe_reasons + ("MALFORMED_GATE_RESULT", "WINDOWS_AFTER_MAC")),
            )
        return _closed_envelope(readiness, production_pollution, ("MALFORMED_GATE_RESULT",))
    if any(getattr(readiness, field) is EvidenceState.FAILED for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS):
        if functional_verdict == "PASS":
            # A measured failure is authoritative even if a downstream gate
            # incorrectly claims PASS.  Preserve the report for diagnosis and
            # never downgrade a real failure into an unavailable/blocked state.
            return QualityRunEnvelope(
                readiness,
                production_pollution,
                evaluation_report,
                "FAIL",
                "FAIL",
                "BLOCKED",
                _reason_codes(safe_reasons + ("CONTRADICTORY_FUNCTIONAL_EVIDENCE", "WINDOWS_AFTER_MAC")),
            )
    if functional_verdict == "FAIL":
        return QualityRunEnvelope(readiness, production_pollution, evaluation_report, "FAIL", "FAIL", "BLOCKED", _reason_codes(safe_reasons + ("WINDOWS_AFTER_MAC",)))
    if any(getattr(readiness, field) in (EvidenceState.FAILED,) for field in QualityEvidenceReadiness._MAC_FIELDS):
        phase = "FAIL"
        reasons = safe_reasons
    elif not readiness.mac_release_ready:
        reasons_list = list(safe_reasons)
        for field in QualityEvidenceReadiness._MAC_FIELDS:
            state = getattr(readiness, field)
            if state is not EvidenceState.READY:
                reasons_list.append(f"{field}_{state.value}")
        phase = "BLOCKED"
        reasons = tuple(reasons_list)
    elif frozen_verdict == "PASS":
        phase = "PASS"
        reasons = safe_reasons
    elif frozen_verdict == "FAIL":
        phase = "FAIL"
        reasons = safe_reasons
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
