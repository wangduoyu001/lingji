from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Mapping

from .models import ExtractionBatch, ExtractionRequest


class ExtractionAdapter(ABC):
    name = "base"
    version = "1"
    source_types: tuple[str, ...] = ()

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        return source_type in self.source_types

    @abstractmethod
    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        raise NotImplementedError
