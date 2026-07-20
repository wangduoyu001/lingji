from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .base import ExtractionAdapter


class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, ExtractionAdapter] = {}

    def register(self, adapter: ExtractionAdapter) -> None:
        name = str(adapter.name).strip().lower()
        if not name:
            raise ValueError("Adapter name is required")
        if name in self._adapters:
            raise ValueError(f"Adapter already registered: {name}")
        self._adapters[name] = adapter

    def get(self, name: str) -> ExtractionAdapter:
        key = str(name).strip().lower()
        try:
            return self._adapters[key]
        except KeyError as exc:
            raise LookupError(f"Unknown extraction adapter: {name}") from exc

    def resolve(
        self,
        source_type: str,
        input_path: Path | None = None,
        payload: Mapping[str, Any] | None = None,
        preferred: str | None = None,
    ) -> ExtractionAdapter:
        payload = payload or {}
        if preferred:
            adapter = self.get(preferred)
            if not adapter.can_handle(source_type, input_path, payload):
                raise ValueError(
                    f"Adapter {adapter.name} cannot handle source type {source_type}"
                )
            return adapter
        for adapter in self._adapters.values():
            if adapter.can_handle(source_type, input_path, payload):
                return adapter
        raise LookupError(f"No extraction adapter for source type: {source_type}")

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": adapter.name,
                "version": adapter.version,
                "source_types": list(adapter.source_types),
            }
            for adapter in self._adapters.values()
        ]
