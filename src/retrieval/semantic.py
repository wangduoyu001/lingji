from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from .hybrid import SemanticProvider as SemanticSearchProvider


@dataclass(frozen=True)
class SemanticPoint:
    """One rebuildable semantic chunk prepared for provider indexing."""

    chunk_id: str
    memory_id: str
    text: str
    payload: dict[str, Any] = field(default_factory=dict)


class SemanticIndexProvider(Protocol):
    def upsert(self, point: SemanticPoint) -> str: ...

    def upsert_many(self, points: Sequence[SemanticPoint]) -> list[str]: ...

    def delete(self, chunk_id: str) -> None: ...

    def delete_memory(self, memory_id: str) -> None: ...


class SemanticDiagnosticsProvider(Protocol):
    def status(self) -> dict[str, Any]: ...

    def count(self, kind: str | None = None) -> int: ...

    def exists(self, chunk_id: str) -> bool: ...

    def coverage(self, expected_chunk_ids: Sequence[str]) -> dict[str, Any]: ...


class SemanticProvider(
    SemanticSearchProvider,
    SemanticIndexProvider,
    SemanticDiagnosticsProvider,
    Protocol,
):
    """Combined provider contract used by the unified semantic mainline."""
