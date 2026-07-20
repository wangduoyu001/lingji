from __future__ import annotations

from typing import Any

from .memory_inspector import MemoryInspectorFacade as _BaseMemoryInspectorFacade


class MemoryInspectorFacade(_BaseMemoryInspectorFacade):
    """P2-03 facade contract fixes without creating a second retrieval path."""

    def memory_vector(self, memory_id: str, *, viewer: Any | None = None) -> dict[str, Any]:
        detail = self.get_memory(memory_id, viewer=viewer)
        memory = detail["item"]
        chunks = list(memory.get("chunks") or [])
        snapshot = self.statistics.vector_status()
        semantic = getattr(getattr(self.gateway, "retriever", None), "semantic_provider", None)
        rebuild_required = snapshot.get("rebuild_required")
        output = []
        for chunk in chunks:
            chunk_id = str(chunk.get("chunk_id") or "")
            exists: bool | None = None
            source = "unavailable"
            last_error = snapshot.get("last_error")
            if semantic is not None:
                try:
                    exists = bool(semantic.exists(chunk_id))
                    source = "live"
                    last_error = None
                except Exception as exc:  # internal diagnostic only
                    exists = None
                    source = "unavailable"
                    last_error = self._safe_error(exc)
            output.append(
                {
                    "memory_id": memory_id,
                    "chunk_id": chunk_id,
                    "expected": True,
                    "exists": exists,
                    "source": source,
                    "collection": snapshot.get("collection"),
                    "dimension": snapshot.get("dimension"),
                    "rebuild_required": rebuild_required,
                    "last_error": last_error,
                }
            )
        return self._envelope(
            {
                "memory_id": memory_id,
                "vector": {
                    "state": snapshot.get("state"),
                    "source": snapshot.get("source"),
                    "collection": snapshot.get("collection"),
                    "dimension": snapshot.get("dimension"),
                    "rebuild_required": rebuild_required,
                    "last_error": snapshot.get("last_error"),
                    "chunks": output,
                },
            }
        )
