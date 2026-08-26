"""Safe migration of LingJi-owned Obsidian derived projections.

This module never mutates the Vault.  It removes only records from the
rebuildable lexical/Qdrant projections and, when explicitly configured, raw
copies under a LingJi-owned raw root.  Every operation is represented by a
content-free manifest so a user can inspect and verify the scope first.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from src.retrieval.memory_db import MemoryDatabase

from .frontmatter import FrontmatterError, split_frontmatter
from .memory_scope import ObsidianMemoryScope

ManifestAction = Literal["retain", "remove-derived", "restore-derived"]
MigrationState = Literal["planned", "applied", "rolled_back"]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except (OSError, ValueError):
        return ""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    before_hash: str
    managed: bool
    action: ManifestAction
    reason: str = ""
    source: str = "obsidian"

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "before_hash": self.before_hash,
            "managed": self.managed,
            "action": self.action,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass(frozen=True)
class MigrationManifest:
    entries: tuple[ManifestEntry, ...]
    vault_hash: str
    generated_at: datetime
    _provided_hash: str = field(default="", compare=False, repr=False)

    @property
    def manifest_hash(self) -> str:
        # Timestamp is audit metadata, not operation identity. Excluding it
        # makes repeated plans over an unchanged Vault converge to one
        # idempotent migration/audit key.
        return _sha256_bytes(
            _canonical_json(
                {
                    "entries": [entry.to_dict() for entry in self.entries],
                    "vault_hash": self.vault_hash,
                }
            )
        )

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "entries": [entry.to_dict() for entry in self.entries],
            "vault_hash": self.vault_hash,
            "generated_at": self.generated_at.astimezone(timezone.utc).isoformat(),
        }
        if include_hash:
            payload["manifest_hash"] = self.manifest_hash
        return payload

    def validate(self) -> bool:
        return bool(self.vault_hash) and (
            not self._provided_hash or self.manifest_hash == self._provided_hash
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MigrationManifest":
        generated = datetime.fromisoformat(str(payload["generated_at"]))
        entries = tuple(
            ManifestEntry(
                path=str(item["path"]),
                before_hash=str(item.get("before_hash") or ""),
                managed=bool(item.get("managed")),
                action=item.get("action", "retain"),
                reason=str(item.get("reason") or ""),
                source=str(item.get("source") or "obsidian"),
            )
            for item in payload.get("entries", [])
        )
        manifest = cls(
            entries,
            str(payload.get("vault_hash") or ""),
            generated,
            str(payload.get("manifest_hash") or ""),
        )
        return manifest


@dataclass(frozen=True)
class MigrationResult:
    manifest_hash: str
    state: MigrationState
    removed_derived: tuple[str, ...]
    pending_rebuild: bool = False
    errors: tuple[str, ...] = ()
    audit_count: int = 0


@dataclass
class _Snapshot:
    record: dict[str, Any]


class ObsidianMemoryMigration:
    """Plan and apply body-preserving derived-index migration."""

    def __init__(
        self,
        memory_database: MemoryDatabase | None = None,
        semantic_provider: Any | None = None,
        raw_root: Path | str | None = None,
        *,
        manifest_dir: Path | str | None = None,
    ) -> None:
        self.database = memory_database
        self.semantic_provider = semantic_provider
        self.raw_root = Path(raw_root).expanduser().resolve(strict=False) if raw_root else None
        self.manifest_dir = Path(manifest_dir).expanduser() if manifest_dir else None
        self._vault_root: Path | None = None
        self._scopes: dict[str, ObsidianMemoryScope] = {}
        self._snapshots: dict[str, dict[str, _Snapshot]] = {}
        self._results: dict[str, MigrationResult] = {}
        self._pending_qdrant: dict[str, dict[str, str]] = {}

    def plan(self, vault_root: Path | str, dry_run: bool = True) -> MigrationManifest:
        # ``dry_run`` is retained in the public contract.  Planning is always
        # read-only, even when a caller passes False by mistake.
        del dry_run
        root = Path(vault_root).expanduser().resolve(strict=False)
        self._vault_root = root
        scope = ObsidianMemoryScope(root)
        self._scopes[str(root)] = scope
        entries: list[ManifestEntry] = []
        snapshots: dict[str, _Snapshot] = {}

        for record in self.database.list_documents(include_chunks=True) if self.database else []:
            relative = str(record.get("relative_path") or "")
            if not relative:
                continue
            path = root / relative
            decision = scope.classify(path)
            # ``memory_documents`` also stores chat/file/media projections. A
            # Vault migration may only touch an existing Markdown path inside
            # this Vault; opaque or missing paths are retained conservatively.
            in_vault_markdown = (
                decision.reason != "outside_vault"
                and path.is_file()
                and path.suffix.casefold() == ".md"
            )
            if not in_vault_markdown:
                action = "retain"
                reason = "non_obsidian_source"
            elif self._protected_record(record, path):
                action: ManifestAction = "retain"
                reason = "owner_confirmed_core"
            elif decision.eligible:
                action = "retain"
                reason = decision.reason
            else:
                action = "remove-derived"
                reason = decision.reason
                snapshots[relative] = _Snapshot(record)
            entries.append(
                ManifestEntry(
                    path=relative,
                    before_hash=_sha256_file(path),
                    managed=True,
                    action=action,
                    reason=reason,
                    source="memory_db",
                )
            )

        if self.raw_root and self.raw_root.is_dir():
            raw_files = self._owned_raw_files()
            for path in raw_files:
                relative = path.relative_to(self.raw_root).as_posix()
                entries.append(
                    ManifestEntry(
                        path=f"raw:{relative}",
                        before_hash=_sha256_file(path),
                        managed=True,
                        action="remove-derived",
                        reason="excluded_observable_copy",
                        source="raw",
                    )
                )

        manifest = MigrationManifest(
            entries=tuple(sorted(entries, key=lambda item: (item.source, item.path))),
            vault_hash=self._vault_hash(root),
            generated_at=datetime.now(timezone.utc),
        )
        self._snapshots[manifest.manifest_hash] = snapshots
        self._write_manifest(manifest)
        return manifest

    def apply(self, manifest: MigrationManifest, owner_confirmed: bool) -> MigrationResult:
        if not owner_confirmed:
            raise PermissionError("Obsidian derived-index migration requires explicit owner confirmation")
        if not manifest.validate():
            raise ValueError("Migration manifest checksum mismatch")
        if self._vault_root is not None and self._vault_hash(self._vault_root) != manifest.vault_hash:
            raise RuntimeError("Vault changed since migration manifest was generated")
        existing = self._results.get(manifest.manifest_hash)
        if existing and existing.state == "applied" and not existing.errors:
            return existing

        removed: list[str] = list(existing.removed_derived) if existing else []
        errors: list[str] = []
        pending_qdrant = False
        pending_vectors = dict(self._pending_qdrant.get(manifest.manifest_hash, {}))
        if not pending_vectors and self.database:
            for audit in self.database.migration_audits():
                if audit.get("manifest_hash") != manifest.manifest_hash:
                    continue
                pending_vectors = {
                    str(memory_id): str(path)
                    for memory_id, path in (audit.get("pending_memory_ids") or {}).items()
                }
                break
        # Retry semantic deletion left unresolved by an earlier attempt,
        # without pretending the lexical deletion restored vector coverage.
        for memory_id, path in list(pending_vectors.items()):
            if not self.semantic_provider:
                pending_qdrant = True
                errors.append(f"qdrant:{path}:provider_unavailable")
                continue
            try:
                self.semantic_provider.delete_memory(memory_id)
                pending_vectors.pop(memory_id, None)
            except Exception as exc:
                pending_qdrant = True
                errors.append(f"qdrant:{path}:{type(exc).__name__}")
        self._pending_qdrant[manifest.manifest_hash] = pending_vectors

        for entry in manifest.entries:
            if entry.action != "remove-derived" or not entry.managed:
                continue
            if entry.source == "memory_db" and self.database:
                record = self.database.fetch_by_path(entry.path, include_chunks=False)
                if record is None:
                    continue
                memory_id = str(record.get("memory_id") or "")
                try:
                    self.database.remove_memory(memory_id)
                    removed.append(entry.path)
                except Exception as exc:
                    errors.append(f"lexical:{entry.path}:{type(exc).__name__}")
                    continue
                if self.semantic_provider and memory_id:
                    try:
                        self.semantic_provider.delete_memory(memory_id)
                        pending_vectors.pop(memory_id, None)
                    except Exception as exc:
                        pending_qdrant = True
                        pending_vectors[memory_id] = entry.path
                        errors.append(f"qdrant:{entry.path}:{type(exc).__name__}")
            elif entry.source == "raw" and self.raw_root:
                source = self.raw_root / entry.path.removeprefix("raw:")
                try:
                    self._validate_raw_before_apply(entry, source)
                    self._backup_raw(manifest, source)
                    source.unlink()
                    removed.append(entry.path)
                except (OSError, ValueError) as exc:
                    errors.append(f"raw:{entry.path}:{exc}")

        self._pending_qdrant[manifest.manifest_hash] = pending_vectors
        pending_qdrant = pending_qdrant or bool(pending_vectors)

        result = MigrationResult(
            manifest_hash=manifest.manifest_hash,
            state="planned" if errors else "applied",
            removed_derived=tuple(sorted(set(removed))),
            pending_rebuild=pending_qdrant,
            errors=tuple(errors),
            audit_count=len(removed),
        )
        self._results[manifest.manifest_hash] = result
        if self.database:
            self.database.record_migration_audit(
                manifest.manifest_hash,
                {
                    "manifest_hash": manifest.manifest_hash,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "removed_paths": list(result.removed_derived),
                    "reasons": {entry.path: entry.reason for entry in manifest.entries if entry.action == "remove-derived"},
                    "pending_rebuild": result.pending_rebuild,
                    "pending_memory_ids": dict(pending_vectors),
                    "errors": list(result.errors),
                },
            )
        return result

    def rollback(self, result: MigrationResult) -> MigrationResult:
        if result.state not in {"applied", "planned"}:
            return result
        snapshots = self._snapshots.get(result.manifest_hash, {})
        errors: list[str] = []
        restored: list[str] = []
        for relative, snapshot in snapshots.items():
            if not self.database:
                continue
            record = snapshot.record
            path = (self._vault_root / relative) if self._vault_root else None
            if path is None or not path.is_file():
                errors.append(f"vault_missing:{relative}")
                continue
            try:
                self.database.upsert_from_entry(self._record_to_entry(record), path)
                restored.append(relative)
            except Exception as exc:
                errors.append(f"restore:{relative}:{type(exc).__name__}")
        self._restore_raw(result.manifest_hash)
        rolled = MigrationResult(
            manifest_hash=result.manifest_hash,
            state="rolled_back" if not errors else "planned",
            removed_derived=tuple(sorted(restored)),
            pending_rebuild=bool(errors),
            errors=tuple(errors),
            audit_count=len(restored),
        )
        self._results[result.manifest_hash] = rolled
        return rolled

    def _protected_record(self, record: dict[str, Any], path: Path) -> bool:
        properties: dict[str, Any] = {}
        try:
            metadata, _ = split_frontmatter(path.read_text(encoding="utf-8-sig"))
            properties = dict(metadata)
        except (OSError, UnicodeError, FrontmatterError, ValueError):
            properties = {}
        return bool(
            str(record.get("memory_tier") or properties.get("memory_tier") or "").casefold() == "core"
            or "03-Knowledge/Core-Memory" in path.as_posix()
            or properties.get("owner_confirmed") is True
            or properties.get("formal_knowledge") is True
        )

    @staticmethod
    def _record_to_entry(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record.get("memory_id"),
            "relative_path": record.get("relative_path"),
            "title": record.get("title"),
            "memory_type": record.get("memory_type"),
            "memory_tier": record.get("memory_tier"),
            "status": record.get("status"),
            "review_status": record.get("review_status"),
            "privacy": record.get("privacy"),
            "importance": record.get("importance"),
            "confidence": record.get("confidence"),
            "project": record.get("project", []),
            "tags": record.get("tags", []),
            "modified_at": record.get("modified_at"),
            "content_hash": record.get("content_hash"),
            "properties": {
                "memory_tier": record.get("memory_tier"),
                "agent_scope": record.get("agent_scope", []),
                "valid_from": record.get("valid_from"),
                "valid_to": record.get("valid_to"),
                "superseded_by": record.get("superseded_by"),
                "pin_to_context": record.get("pin_to_context"),
                "recall_weight": record.get("recall_weight"),
            },
        }

    def _vault_hash(self, root: Path) -> str:
        rows: list[str] = []
        if not root.is_dir():
            return _sha256_bytes(b"")
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                relative = path.relative_to(root).as_posix()
                rows.append(f"{relative}\0{_sha256_file(path)}")
            except (OSError, ValueError):
                continue
        return _sha256_bytes("\n".join(rows).encode("utf-8"))

    def _write_manifest(self, manifest: MigrationManifest) -> None:
        if not self.manifest_dir:
            return
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        (self.manifest_dir / f"OBSIDIAN_MEMORY_{manifest.manifest_hash}.json").write_text(
            manifest.to_json(), encoding="utf-8"
        )

    def _owned_raw_files(self) -> list[Path]:
        """Resolve an explicit, body-safe raw ownership declaration.

        A broad ``storage/raw`` may contain chat, media and file imports.  It
        is not safe to infer Obsidian ownership from that directory alone.  A
        dedicated ``obsidian`` root, a LingJi raw manifest, or a per-file
        ``.meta.json`` marker is required before a raw copy can be removed.
        """
        if not self.raw_root or not self.raw_root.is_dir():
            return []
        declared: set[str] | None = None
        manifest_path = self.raw_root / "manifest.json"
        if manifest_path.is_file():
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                values = payload.get("obsidian_paths") if isinstance(payload, dict) else None
                if isinstance(values, list):
                    declared = {str(value).replace("\\", "/") for value in values}
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                declared = set()
        dedicated_root = self.raw_root.name.casefold() in {
            "obsidian",
            "obsidian_raw",
            "obsidian-vault",
        }
        output: list[Path] = []
        try:
            candidates = sorted(
                path for path in self.raw_root.rglob("*")
                if path.is_file() and not path.is_symlink() and path.name != "manifest.json"
            )
        except OSError:
            return []
        for path in candidates:
            relative = path.relative_to(self.raw_root).as_posix()
            if self._is_owned_raw_path(path, relative, dedicated_root=dedicated_root, declared=declared):
                output.append(path)
        return output

    def _is_owned_raw_path(
        self,
        path: Path,
        relative: str | None = None,
        *,
        dedicated_root: bool | None = None,
        declared: set[str] | None = None,
    ) -> bool:
        if not self.raw_root:
            return False
        relative = relative or path.relative_to(self.raw_root).as_posix()
        if dedicated_root is None:
            dedicated_root = self.raw_root.name.casefold() in {
                "obsidian", "obsidian_raw", "obsidian-vault"
            }
        if declared is None:
            manifest_path = self.raw_root / "manifest.json"
            declared = set()
            if manifest_path.is_file():
                try:
                    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                    values = payload.get("obsidian_paths") if isinstance(payload, dict) else None
                    if isinstance(values, list):
                        declared = {str(value).replace("\\", "/") for value in values}
                except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                    declared = set()
        if dedicated_root or relative in declared:
            return True
        marker = path.with_name(path.name + ".meta.json")
        try:
            metadata = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else {}
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            return False
        return isinstance(metadata, dict) and str(
            metadata.get("source_type") or metadata.get("source") or ""
        ).casefold() == "obsidian"

    def _validate_raw_before_apply(self, entry: ManifestEntry, source: Path) -> None:
        if not self.raw_root:
            raise ValueError("raw root is unavailable")
        root_lexical = Path(os.path.abspath(str(self.raw_root)))
        source_lexical = Path(os.path.abspath(str(source)))
        try:
            relative = source_lexical.relative_to(root_lexical).as_posix()
        except ValueError as exc:
            raise ValueError("raw path is outside managed root") from exc
        current = root_lexical
        for part in Path(relative).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("raw source became a symlink")
        if not source.is_file() or source.is_symlink():
            raise ValueError("raw source is not a regular file")
        if not self._is_owned_raw_path(source, relative):
            raise ValueError("raw ownership declaration changed")
        if _sha256_file(source) != entry.before_hash:
            raise ValueError("raw source hash changed")

    def _backup_raw(self, manifest: MigrationManifest, source: Path) -> None:
        if not self.manifest_dir or not self.raw_root:
            return
        target = self.manifest_dir / "rollback" / manifest.manifest_hash / source.relative_to(self.raw_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    def _restore_raw(self, manifest_hash: str) -> None:
        if not self.manifest_dir or not self.raw_root:
            return
        backup = self.manifest_dir / "rollback" / manifest_hash
        if not backup.is_dir():
            return
        for source in sorted(backup.rglob("*")):
            if not source.is_file():
                continue
            target = self.raw_root / source.relative_to(backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source, target)


__all__ = [
    "ManifestEntry",
    "MigrationManifest",
    "MigrationResult",
    "ObsidianMemoryMigration",
]
