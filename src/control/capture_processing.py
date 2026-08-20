from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from src.extraction.bootstrap import build_extraction_pipeline
from src.extraction.worker import ExtractionWorker
from src.memory.vault_layout import VaultLayout
from src.obsidian.frontmatter import FrontmatterError, split_frontmatter
from src.retrieval.chunker import MarkdownChunker
from src.retrieval.memory_db import MemoryDatabase

logger = logging.getLogger("lingji.control.capture_processing")


class PackagedCaptureProcessingRuntime:
    """Consume the packaged Desktop Capture queue without becoming a Qdrant owner.

    Vault + Git remains the permanent authority. This runtime updates only the
    rebuildable lexical Memory DB after the existing extraction sink writes Vault
    documents. Semantic Qdrant ownership stays outside the 8766 Control API.
    """

    def __init__(self, settings: Any, *, state_db: Any, runtime_settings: Any):
        self.settings = settings
        self.state_db = state_db
        self.layout = VaultLayout(settings.vault_path)
        if bool(getattr(settings, "vault_auto_init", False)):
            self.layout.ensure()
        self.memory_db = MemoryDatabase(settings.memory_db_path)
        self.chunker = MarkdownChunker(
            settings.memory_chunk_max_chars,
            settings.memory_chunk_overlap_chars,
        )
        self.pipeline = build_extraction_pipeline(
            settings,
            on_documents_written=self._on_documents_written,
            runtime_settings=runtime_settings,
        )
        self.worker = ExtractionWorker(
            self.pipeline,
            poll_seconds=settings.extraction_poll_seconds,
            batch_size=settings.extraction_batch_size,
            worker_id="packaged-control-capture",
        )
        # CaptureControlService reads this attribute only for truthful owner status.
        self.pipeline.owner_worker = self.worker

    def start(self) -> None:
        self.worker.start()
        self._event("packaged_capture_processor_started", {"worker_id": self.worker.worker_id})

    def stop(self, timeout: float = 10.0) -> None:
        self.worker.stop(timeout=timeout)
        self._event("packaged_capture_processor_stopped", {"worker_id": self.worker.worker_id})

    def status(self) -> dict[str, Any]:
        state = self.worker.status()
        return {
            "running": bool(state.get("running")),
            "worker_id": self.worker.worker_id,
            "queue": dict(state.get("queue") or {}),
        }

    def _on_documents_written(self, result: Mapping[str, Any]) -> None:
        synchronized: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        seen_paths: set[str] = set()

        for bucket in ("created", "updated", "skipped"):
            rows = result.get(bucket)
            if not isinstance(rows, list):
                continue
            for item in rows:
                if not isinstance(item, Mapping):
                    continue
                raw_path = str(item.get("path") or "").strip()
                if not raw_path or raw_path in seen_paths:
                    continue
                seen_paths.add(raw_path)
                path = Path(raw_path)
                try:
                    entry = self._memory_entry(path, item)
                    if entry is None:
                        continue
                    indexed = self.memory_db.upsert_from_entry(entry, path, self.chunker)
                    synchronized.append(
                        {
                            "memory_id": indexed["memory_id"],
                            "chunks": int(indexed["chunks"]),
                            "revision": int(indexed["revision"]),
                        }
                    )
                except Exception as exc:
                    logger.exception("Packaged Capture lexical sync failed for %s", path.name)
                    failures.append(
                        {
                            "object_id": str(item.get("id") or path.stem),
                            "error_type": type(exc).__name__,
                        }
                    )

        event_payload = {
            "documents": len(synchronized),
            "failed": len(failures),
            "memory_revision": self.memory_db.revision,
            "objects": synchronized[:50],
            "failures": failures[:20],
            "semantic_sync": "deferred_to_semantic_owner",
        }
        self._event("packaged_capture_lexical_sync", event_payload)
        if failures:
            raise RuntimeError(f"Lexical memory sync failed for {len(failures)} extracted document(s)")

    def _memory_entry(self, path: Path, sink_item: Mapping[str, Any]) -> dict[str, Any] | None:
        if not path.exists() or path.suffix.lower() != ".md":
            return None
        if not self.layout.should_index(path, include_private=bool(self.settings.index_private)):
            return None
        text = path.read_text(encoding="utf-8-sig")
        try:
            metadata, _ = split_frontmatter(text)
        except FrontmatterError as exc:
            raise ValueError(f"Invalid extracted frontmatter: {path.name}") from exc
        classification = self.layout.classify(path)
        memory_id = str(metadata.get("id") or sink_item.get("id") or classification.relative_path)
        if not memory_id:
            raise ValueError("Extracted document has no stable memory id")
        stat = path.stat()
        memory_type = str(metadata.get("memory_type") or metadata.get("type") or "source")
        return {
            "id": memory_id,
            "type": memory_type,
            "memory_type": memory_type,
            "title": str(metadata.get("title") or path.stem),
            "aliases": self._list(metadata.get("aliases")),
            "content_hash": str(metadata.get("content_hash") or hashlib.sha256(text.encode("utf-8")).hexdigest()),
            "created": metadata.get("created_at") or metadata.get("created") or "",
            "updated": metadata.get("updated_at") or datetime.now().isoformat(timespec="seconds"),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "source": metadata.get("source", "vault"),
            "source_type": metadata.get("source_type") or classification.source_type,
            "source_id": metadata.get("source_id", ""),
            "source_path": metadata.get("source_path", ""),
            "source_url": metadata.get("source_url", ""),
            "project": self._list(metadata.get("project") or metadata.get("project_id")),
            "project_id": metadata.get("project_id", ""),
            "status": metadata.get("status", "active"),
            "privacy": metadata.get("privacy") or classification.privacy,
            "importance": metadata.get("importance", ""),
            "review_status": metadata.get("review_status", ""),
            "tags": self._list(metadata.get("tags")),
            "people": self._list(metadata.get("people")),
            "organizations": self._list(metadata.get("organizations")),
            "tools": self._list(metadata.get("tools")),
            "models": self._list(metadata.get("models")),
            "sources": self._list(metadata.get("sources")),
            "tasks": self._list(metadata.get("tasks")),
            "decisions": self._list(metadata.get("decisions")),
            "related": self._list(metadata.get("related") or metadata.get("related_ids")),
            "related_ids": self._list(metadata.get("related_ids")),
            "relative_path": classification.relative_path,
            "is_private": classification.is_private,
            "properties": dict(metadata),
        }

    def _event(self, event_type: str, payload: Mapping[str, Any]) -> None:
        try:
            self.state_db.append_event(event_type, "capture_processing", "packaged", dict(payload))
        except Exception:
            logger.exception("Capture processing audit event failed: %s", event_type)

    @staticmethod
    def _list(value: Any) -> list[Any]:
        if value in (None, "", []):
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]
