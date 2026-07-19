from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4


class BackupManager:
    """Create verified ZIP backups and restore only into an isolated staging area."""

    SCHEMA_VERSION = 1

    def __init__(self, settings: Any, state_db: Any | None = None):
        self.settings = settings
        self.state_db = state_db
        self.backup_root = settings.backup_path
        self.restore_root = settings.storage_path / "restore-staging"

    def create_backup(
        self,
        *,
        profile: str = "metadata",
        include_raw: bool = False,
        include_derived: bool = False,
    ) -> dict[str, Any]:
        profile = str(profile or "metadata").lower()
        if profile not in {"metadata", "full"}:
            raise ValueError("Backup profile must be metadata or full")
        if profile == "full":
            include_raw = True
            include_derived = True

        backup_id = f"LJ-BACKUP-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
        self.backup_root.mkdir(parents=True, exist_ok=True)
        target = self.backup_root / f"{backup_id}.zip"
        temporary = target.with_suffix(".zip.partial")

        sources = self._sources(include_raw=include_raw, include_derived=include_derived)
        manifest_files: list[dict[str, Any]] = []
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for label, root in sources:
                if not root.exists():
                    continue
                if root.is_file():
                    arcname = f"data/{label}/{root.name}"
                    archive.write(root, arcname)
                    manifest_files.append(self._manifest_row(root, arcname))
                    continue
                for path in self._iter_files(root):
                    relative = path.relative_to(root).as_posix()
                    arcname = f"data/{label}/{relative}"
                    archive.write(path, arcname)
                    manifest_files.append(self._manifest_row(path, arcname))

            manifest = {
                "schema_version": self.SCHEMA_VERSION,
                "backup_id": backup_id,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "profile": profile,
                "include_raw": include_raw,
                "include_derived": include_derived,
                "files": manifest_files,
                "summary": {
                    "files": len(manifest_files),
                    "bytes": sum(int(row["size"]) for row in manifest_files),
                },
            }
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

        temporary.replace(target)
        verification = self.verify_backup(target)
        if not verification["valid"]:
            target.unlink(missing_ok=True)
            raise IOError(f"Backup verification failed: {verification['errors']}")
        result = {
            "backup_id": backup_id,
            "path": str(target),
            "profile": profile,
            "summary": manifest["summary"],
            "sha256": self._sha256(target),
            "verification": verification,
        }
        self._event("backup_created", backup_id, result)
        return result

    def list_backups(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.backup_root.exists():
            return []
        rows: list[dict[str, Any]] = []
        for path in sorted(self.backup_root.glob("LJ-BACKUP-*.zip"), reverse=True)[: max(int(limit), 1)]:
            try:
                with zipfile.ZipFile(path) as archive:
                    manifest = json.loads(archive.read("manifest.json").decode("utf-8-sig"))
                rows.append(
                    {
                        "backup_id": manifest.get("backup_id") or path.stem,
                        "created_at": manifest.get("created_at"),
                        "profile": manifest.get("profile"),
                        "summary": manifest.get("summary") or {},
                        "path": str(path),
                        "archive_bytes": path.stat().st_size,
                    }
                )
            except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError):
                rows.append({"backup_id": path.stem, "path": str(path), "invalid": True})
        return rows

    def verify_backup(self, backup: Path | str) -> dict[str, Any]:
        path = self._resolve_backup(backup)
        errors: list[str] = []
        checked = 0
        try:
            with zipfile.ZipFile(path) as archive:
                bad_member = archive.testzip()
                if bad_member:
                    errors.append(f"ZIP CRC failed: {bad_member}")
                manifest = json.loads(archive.read("manifest.json").decode("utf-8-sig"))
                members = {item.filename: item for item in archive.infolist()}
                for row in manifest.get("files") or []:
                    arcname = str(row.get("archive_path") or "")
                    if arcname not in members:
                        errors.append(f"Missing member: {arcname}")
                        continue
                    data = archive.read(arcname)
                    checked += 1
                    if len(data) != int(row.get("size") or -1):
                        errors.append(f"Size mismatch: {arcname}")
                    if hashlib.sha256(data).hexdigest() != str(row.get("sha256") or ""):
                        errors.append(f"Hash mismatch: {arcname}")
        except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(str(exc))
        return {"valid": not errors, "path": str(path), "checked_files": checked, "errors": errors}

    def stage_restore(self, backup: Path | str, confirmation: str) -> dict[str, Any]:
        path = self._resolve_backup(backup)
        verification = self.verify_backup(path)
        if not verification["valid"]:
            raise IOError(f"Backup is invalid: {verification['errors']}")
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8-sig"))
            backup_id = str(manifest.get("backup_id") or path.stem)
            expected = f"STAGE_RESTORE:{backup_id}"
            if confirmation != expected:
                raise PermissionError("Restore confirmation does not match")
            target = self.restore_root / backup_id
            if target.exists():
                raise FileExistsError(target)
            target.mkdir(parents=True, exist_ok=False)
            for member in archive.infolist():
                if member.is_dir():
                    continue
                destination = self._safe_destination(target, member.filename)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
        result = {
            "backup_id": backup_id,
            "backup_path": str(path),
            "staging_path": str(target),
            "manifest": manifest,
            "verification": verification,
            "warning": "Restore is staged only; current Vault and databases were not overwritten.",
        }
        self._event("backup_restore_staged", backup_id, {"staging_path": str(target)})
        return result

    def _sources(self, *, include_raw: bool, include_derived: bool) -> list[tuple[str, Path]]:
        storage = self.settings.storage_path
        rows = [
            ("vault", self.settings.vault_path),
            ("runtime_settings", self.settings.runtime_settings_path),
            ("state_db", self.settings.state_db_path),
            ("memory_db", self.settings.memory_db_path),
            ("index", storage / "pemis_index.json"),
            ("versions", storage / "versions"),
        ]
        if include_raw:
            rows.append(("raw", storage / "raw"))
        if include_derived:
            rows.append(("derived", storage / "derived"))
        return rows

    @staticmethod
    def _iter_files(root: Path) -> Iterable[Path]:
        return (path for path in root.rglob("*") if path.is_file() and not path.is_symlink())

    @staticmethod
    def _manifest_row(path: Path, archive_path: str) -> dict[str, Any]:
        stat = path.stat()
        return {
            "archive_path": archive_path,
            "size": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
            "sha256": BackupManager._sha256(path),
        }

    def _resolve_backup(self, backup: Path | str) -> Path:
        candidate = Path(str(backup)).expanduser()
        if not candidate.is_absolute():
            candidate = self.backup_root / candidate
        candidate = candidate.resolve(strict=False)
        boundary = self.backup_root.resolve(strict=False)
        try:
            candidate.relative_to(boundary)
        except ValueError as exc:
            raise PermissionError("Backup path is outside configured backup directory") from exc
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate

    @staticmethod
    def _safe_destination(root: Path, member_name: str) -> Path:
        normalized = member_name.replace("\\", "/")
        if normalized.startswith("/") or ".." in Path(normalized).parts:
            raise PermissionError(f"Unsafe backup member: {member_name}")
        destination = (root / normalized).resolve(strict=False)
        try:
            destination.relative_to(root.resolve(strict=False))
        except ValueError as exc:
            raise PermissionError(f"Unsafe backup member: {member_name}") from exc
        return destination

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _event(self, event_type: str, entity_id: str, payload: Mapping[str, Any]) -> None:
        if self.state_db:
            self.state_db.append_event(event_type, "backup", entity_id, dict(payload))
