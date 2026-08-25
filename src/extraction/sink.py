from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from src.obsidian.frontmatter import (
    atomic_write,
    content_hash,
    render_frontmatter,
    split_frontmatter,
)

from .models import ExtractedDocument, ExtractionBatch


DESTINATION_ROOTS = {
    "work_report": "05-Operations/Work-Reports",
    "error": "05-Operations/Errors",
    "decision": "05-Operations/Decisions/Candidates",
    "task": "05-Operations/Tasks/Inbox",
}

OWNER_PROTECTED_FIELDS = {
    "owner_confirmed",
    "review_status",
    "pin_to_context",
    "importance",
    "valid_from",
    "valid_to",
    "supersedes",
    "superseded_by",
    "agent_scope",
    "manual_notes",
}

MANUAL_START = "<!-- LINGJI:MANUAL:START -->"
MANUAL_END = "<!-- LINGJI:MANUAL:END -->"


class VaultExtractionSink:
    """Persist raw snapshots and normalized documents without erasing owner edits."""

    def __init__(self, layout, storage_path: Path | str, state_db=None):
        self.layout = layout
        self.storage_path = Path(storage_path)
        self.raw_root = self.storage_path / "raw"
        self.version_root = self.storage_path / "versions"
        self.state_db = state_db

    def content_addressed_raw_path(self, sha256: str) -> Path:
        """Return the single durable raw object path for a content hash."""

        digest = str(sha256).strip().lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("raw content address must be a SHA-256 digest")
        return self.raw_root / digest

    def commit_raw_temp(self, temporary: Path | str, sha256: str) -> Path:
        """Atomically commit a fully fsynced temporary raw object.

        Existing content-addressed objects are retained and the temporary copy
        is removed, making repeated scans safe and cheap.
        """

        temporary_path = Path(temporary)
        target = self.content_addressed_raw_path(sha256)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            temporary_path.unlink(missing_ok=True)
            return target
        os.replace(temporary_path, target)
        try:
            directory_fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Directory fsync is not available on every supported platform;
            # the atomic rename remains the safety boundary there.
            pass
        return target

    def preserve_raw(self, input_path: Path | str | None, source_type: str) -> dict[str, Any]:
        if not input_path:
            return {}
        source = Path(input_path).expanduser()
        if not source.exists():
            raise FileNotFoundError(source)
        if source.is_file():
            manifest = self._preserve_file(source, source_type)
        else:
            manifest = self._preserve_directory(source, source_type)
        self._event("raw_snapshot_preserved", manifest["sha256"], manifest)
        return manifest

    def _preserve_file(self, source: Path, source_type: str) -> dict[str, Any]:
        digest = self._sha256_file(source)
        target_dir = self.raw_root / self._safe_segment(source_type) / digest
        target = target_dir / self.layout.sanitize_filename(source.name)
        target_dir.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temporary = target.with_suffix(target.suffix + ".tmp")
            shutil.copy2(source, temporary)
            temporary.replace(target)
        return {
            "kind": "file",
            "source_path": str(source),
            "raw_path": str(target),
            "sha256": digest,
            "size": source.stat().st_size,
        }

    def _preserve_directory(self, source: Path, source_type: str) -> dict[str, Any]:
        entries = []
        for path in sorted(source.rglob("*")):
            if path.is_file() and not path.is_symlink():
                entries.append(
                    {
                        "relative_path": path.relative_to(source).as_posix(),
                        "size": path.stat().st_size,
                        "sha256": self._sha256_file(path),
                    }
                )
        digest = hashlib.sha256(
            json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        target_dir = self.raw_root / self._safe_segment(source_type) / digest
        target_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = target_dir / "directory_manifest.json"
        archive_path = target_dir / "directory_snapshot.zip"
        if not manifest_path.exists():
            atomic_write(
                manifest_path,
                json.dumps(
                    {"source_path": str(source), "sha256": digest, "files": entries},
                    ensure_ascii=False,
                    indent=2,
                ),
            )
        if not archive_path.exists():
            temporary = archive_path.with_suffix(".zip.tmp")
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for item in entries:
                    relative = Path(item["relative_path"])
                    archive.write(source / relative, relative.as_posix())
            temporary.replace(archive_path)
        return {
            "kind": "directory_archive",
            "source_path": str(source),
            "raw_path": str(archive_path),
            "manifest_path": str(manifest_path),
            "sha256": digest,
            "files": len(entries),
            "size": archive_path.stat().st_size,
        }

    def write_batch(
        self,
        batch: ExtractionBatch,
        *,
        adapter_name: str,
        adapter_version: str,
        raw_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        actions = {"created": [], "updated": [], "skipped": []}
        for document in batch.documents:
            result = self.write_document(
                document,
                adapter_name=adapter_name,
                adapter_version=adapter_version,
                raw_snapshot=raw_snapshot,
            )
            actions[result["action"]].append(result)
        paths = [
            item["path"]
            for action in ("created", "updated", "skipped")
            for item in actions[action]
        ]
        return {
            "documents": len(batch.documents),
            **actions,
            "paths": paths,
            "warnings": list(batch.warnings),
            "summary": dict(batch.summary),
            "raw_snapshot": raw_snapshot or {},
        }

    def write_document(
        self,
        document: ExtractedDocument,
        *,
        adapter_name: str,
        adapter_version: str,
        raw_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target = self._target_path(document)
        now = datetime.now().isoformat(timespec="seconds")
        body_hash = content_hash(document.body)
        metadata = {
            "schema_version": 1,
            "id": document.stable_id,
            "title": document.title,
            "memory_type": self._memory_type(document.destination),
            "source_type": document.source_type,
            "external_id": document.external_id,
            "status": document.metadata.get("status", "active"),
            "privacy": document.metadata.get(
                "privacy", "restricted" if document.destination == "private_source" else "private"
            ),
            "project": self._as_list(
                document.metadata.get("project") or document.metadata.get("project_id")
            ),
            "created_at": document.created_at or now,
            "updated_at": document.updated_at or now,
            "captured_at": document.metadata.get("captured_at")
            or document.updated_at
            or document.created_at
            or now,
            "extractor": adapter_name,
            "extractor_version": adapter_version,
            "content_hash": body_hash,
            "tags": self._as_list(document.metadata.get("tags")),
            "related": self._as_list(
                document.metadata.get("related") or document.metadata.get("related_ids")
            ),
        }
        for key, value in document.metadata.items():
            if key not in metadata and value not in (None, "", [], {}):
                metadata[key] = value
        if raw_snapshot:
            metadata["raw_snapshot_path"] = raw_snapshot.get("raw_path", "")
            metadata["raw_sha256"] = raw_snapshot.get("sha256", "")

        body = document.body.rstrip() + "\n\n" + MANUAL_START + "\n\n## 人工备注\n\n" + MANUAL_END
        existing_text = ""
        if target.exists():
            existing_text = target.read_text(encoding="utf-8-sig")
            metadata, body = self._merge_owner_edits(existing_text, metadata, body)
        rendered = render_frontmatter(metadata, body)

        if existing_text:
            if existing_text == rendered:
                action = "skipped"
            else:
                self._preserve_previous_version(document.stable_id, existing_text)
                atomic_write(target, rendered)
                action = "updated"
        else:
            atomic_write(target, rendered)
            action = "created"

        result = {
            "action": action,
            "id": document.stable_id,
            "path": str(target),
            "relative_path": self.layout.relative(target).as_posix(),
            "content_hash": body_hash,
            "privacy": metadata.get("privacy", "private"),
        }
        self._event(f"extraction_document_{action}", document.stable_id, result)
        return result

    def _merge_owner_edits(
        self,
        existing_text: str,
        generated_metadata: dict[str, Any],
        generated_body: str,
    ) -> tuple[dict[str, Any], str]:
        existing_metadata, existing_body = split_frontmatter(existing_text)
        metadata = dict(generated_metadata)
        for key in OWNER_PROTECTED_FIELDS:
            if key in existing_metadata:
                metadata[key] = existing_metadata[key]
        if existing_metadata.get("owner_confirmed") is True:
            for key in ("status", "review_status"):
                if key in existing_metadata:
                    metadata[key] = existing_metadata[key]
        for key in ("tags", "related", "project"):
            metadata[key] = self._merge_lists(existing_metadata.get(key), metadata.get(key))
        manual = self._manual_section(existing_body)
        if manual:
            generated_body = generated_body.replace(
                MANUAL_START + "\n\n## 人工备注\n\n" + MANUAL_END,
                MANUAL_START + manual + MANUAL_END,
            )
        return metadata, generated_body

    @staticmethod
    def _manual_section(body: str) -> str:
        start = body.find(MANUAL_START)
        end = body.find(MANUAL_END)
        if start == -1 or end == -1 or end <= start:
            return ""
        return body[start + len(MANUAL_START) : end]

    @classmethod
    def _merge_lists(cls, first: Any, second: Any) -> list[Any]:
        result = []
        for item in [*cls._as_list(first), *cls._as_list(second)]:
            if item not in result:
                result.append(item)
        return result

    def _preserve_previous_version(self, stable_id: str, text: str) -> None:
        digest = content_hash(text)
        target = self.version_root / self._safe_segment(stable_id) / f"{digest}.md"
        if not target.exists():
            atomic_write(target, text)

    def _target_path(self, document: ExtractedDocument) -> Path:
        created = self._parse_datetime(document.created_at) or datetime.now()
        filename = self._filename(document.stable_id, document.title)
        if document.destination == "source_archive":
            return self.layout.archive_path(document.source_type, filename, created)
        if document.destination == "private_source":
            target_dir = (
                self.layout.root
                / "08-Private"
                / "Imports"
                / self._safe_segment(document.source_type)
                / created.strftime("%Y")
                / created.strftime("%m")
            )
            target_dir.mkdir(parents=True, exist_ok=True)
            return target_dir / filename
        try:
            root = DESTINATION_ROOTS[document.destination]
        except KeyError as exc:
            raise ValueError(f"Unsupported extraction destination: {document.destination}") from exc
        project = self._project_segment(document.metadata)
        target_dir = self.layout.root / root / project / created.strftime("%Y") / created.strftime("%m")
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename

    def _filename(self, stable_id: str, title: str) -> str:
        del title
        safe_id = self._safe_segment(stable_id)[:120]
        return f"{safe_id}.md"

    def _project_segment(self, metadata: Any) -> str:
        if not isinstance(metadata, dict):
            metadata = dict(metadata)
        value = metadata.get("project_id") or metadata.get("project") or "General"
        if isinstance(value, (list, tuple)):
            value = value[0] if value else "General"
        return self._safe_segment(str(value)) or "General"

    @staticmethod
    def _memory_type(destination: str) -> str:
        return {
            "source_archive": "source",
            "private_source": "source",
            "work_report": "work_report",
            "error": "error",
            "decision": "decision_candidate",
            "task": "task_candidate",
        }.get(destination, destination)

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if value in (None, "", []):
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _safe_segment(value: str) -> str:
        cleaned = "".join(
            char if char.isalnum() or char in "-_." else "_" for char in str(value).strip()
        )
        return cleaned.strip("._") or "unknown"

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _event(self, event_type: str, entity_id: str, payload: Any) -> None:
        if self.state_db:
            self.state_db.append_event(event_type, "extraction", entity_id, payload)
