from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .chunker import MarkdownChunker
from .memory_db import MemoryDatabase


class IncrementalMemorySynchronizer:
    """Synchronize the rebuildable Memory DB without deleting unchanged chunks."""

    def __init__(self, database: MemoryDatabase):
        self.database = database

    def sync(
        self,
        entries: Iterable[dict[str, Any]],
        vault_root: Path | str,
        chunker: MarkdownChunker | None = None,
        memory_scope: Any | None = None,
    ) -> dict[str, int | bool]:
        root = Path(vault_root)
        chunker = chunker or MarkdownChunker()
        target = {
            str(entry.get("relative_path")): entry
            for entry in entries
            if entry.get("relative_path")
            and not entry.get("is_private")
            and (
                memory_scope is None
                or memory_scope.classify(root / str(entry.get("relative_path"))).eligible
            )
        }
        current = self._current_documents()
        added = 0
        updated = 0
        removed = 0
        unchanged = 0
        chunks = 0

        for relative_path in sorted(set(current) - set(target)):
            if memory_scope is not None:
                # A scoped Vault sync must not retire chat/file/media records
                # owned by another source.  Only paths that canonicalize into
                # this Vault and are currently outside the memory scope are
                # candidates for removal.
                try:
                    decision = memory_scope.classify(root / relative_path)
                except Exception:
                    continue
                candidate = root / relative_path
                if (
                    decision.reason == "outside_vault"
                    or not candidate.is_file()
                    or candidate.suffix.casefold() != ".md"
                ):
                    continue
            if self.database.remove_by_path(relative_path):
                removed += 1

        for relative_path, entry in target.items():
            path = root / relative_path
            if not path.is_file() or path.suffix.lower() != ".md":
                if relative_path in current and self.database.remove_by_path(relative_path):
                    removed += 1
                continue
            existing = current.get(relative_path)
            memory_id = str(entry.get("id") or relative_path)
            content_hash = str(entry.get("content_hash") or "")
            if (
                existing
                and existing["memory_id"] == memory_id
                and existing["content_hash"] == content_hash
            ):
                unchanged += 1
                chunks += int(existing["chunk_count"])
                continue
            if existing and existing["memory_id"] != memory_id:
                self.database.remove_by_path(relative_path)
            result = self.database.upsert_from_entry(entry, path, chunker)
            chunks += int(result.get("chunks") or 0)
            if existing:
                updated += 1
            else:
                added += 1

        stats = self.database.stats()
        return {
            "full_rebuild": False,
            "documents": int(stats.get("documents") or 0),
            "chunks": int(stats.get("chunks") or chunks),
            "added": added,
            "updated": updated,
            "removed": removed,
            "unchanged": unchanged,
            "revision": int(stats.get("revision") or self.database.revision),
        }

    def _current_documents(self) -> dict[str, dict[str, Any]]:
        with self.database._connection() as connection:  # Reuse the database's lock/PRAGMA contract.
            rows = connection.execute(
                """
                SELECT d.memory_id, d.relative_path, d.content_hash,
                       COUNT(c.chunk_id) AS chunk_count
                FROM memory_documents d
                LEFT JOIN memory_chunks c ON c.memory_id = d.memory_id
                GROUP BY d.memory_id, d.relative_path, d.content_hash
                """
            ).fetchall()
        return {
            str(row["relative_path"]): {
                "memory_id": str(row["memory_id"]),
                "content_hash": str(row["content_hash"] or ""),
                "chunk_count": int(row["chunk_count"] or 0),
            }
            for row in rows
        }
