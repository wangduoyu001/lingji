from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any


class CoverageGuardedSemanticProvider:
    """Disable semantic search whenever Qdrant is not an exact mirror of Memory DB chunks.

    The permanent source of truth remains Vault + Git. Memory DB and Qdrant are
    rebuildable projections. A lexical update may legitimately arrive before the
    semantic index catches up; during that window stale vectors must never be
    fused into current retrieval results.
    """

    def __init__(self, database: Any, provider: Any):
        self.database = database
        self.provider = provider
        self._lock = threading.RLock()
        self._checked_revision: int | None = None
        self._ready = False
        self._reason = "not_checked"
        self._expected = 0
        self._indexed = 0

    def search(self, query: str, limit: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not self.is_fresh():
            return []
        return self.provider.search(query, limit, filters)

    def is_fresh(self) -> bool:
        revision = int(self.database.revision)
        with self._lock:
            # A proven-fresh semantic mirror may be cached for the current Memory
            # DB revision. A stale mirror is rechecked so it can recover as soon
            # as the semantic owner catches up without requiring another DB write.
            if self._checked_revision == revision and self._ready:
                return True
            self._refresh_locked(revision)
            return self._ready

    def freshness_status(self) -> dict[str, Any]:
        self.is_fresh()
        with self._lock:
            return {
                "ready": self._ready,
                "reason": self._reason,
                "memory_revision": self._checked_revision,
                "expected_chunks": self._expected,
                "indexed_points": self._indexed,
            }

    def status(self) -> dict[str, Any]:
        status = dict(self.provider.status())
        status["freshness"] = self.freshness_status()
        if not status["freshness"]["ready"]:
            status["ready"] = False
            status["freshness_required"] = True
        return status

    def coverage(self, expected_chunk_ids):
        return self.provider.coverage(expected_chunk_ids)

    def count(self, *args, **kwargs):
        return self.provider.count(*args, **kwargs)

    def exists(self, *args, **kwargs):
        return self.provider.exists(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self.provider, name)

    def _refresh_locked(self, revision: int) -> None:
        try:
            expected = self._current_chunk_ids()
            indexed = int(self.provider.count())
            coverage = self.provider.coverage(expected)
            missing = int(coverage.get("missing") or 0)
            coverage_indexed = int(coverage.get("indexed") or 0)
            exact_count = indexed == len(expected)
            exact_coverage = missing == 0 and coverage_indexed == len(expected)
            self._ready = exact_count and exact_coverage
            self._reason = "fresh" if self._ready else (
                "point_count_mismatch" if not exact_count else "missing_current_chunks"
            )
            self._expected = len(expected)
            self._indexed = indexed
        except Exception:
            self._ready = False
            self._reason = "semantic_status_unavailable"
            self._expected = self._safe_chunk_count()
            self._indexed = 0
        finally:
            self._checked_revision = revision

    def _current_chunk_ids(self) -> list[str]:
        path = Path(self.database.path)
        uri = f"file:{path.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=5)
        try:
            rows = connection.execute("SELECT chunk_id FROM memory_chunks ORDER BY chunk_id").fetchall()
            return [str(row[0]) for row in rows if row and row[0]]
        finally:
            connection.close()

    def _safe_chunk_count(self) -> int:
        try:
            return len(self._current_chunk_ids())
        except Exception:
            return 0
