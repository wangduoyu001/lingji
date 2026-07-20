from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ExtractionRequest:
    job_id: str
    source_type: str
    adapter_name: str | None = None
    input_path: Path | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    options: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass(frozen=True)
class ExtractedDocument:
    stable_id: str
    title: str
    body: str
    source_type: str
    destination: str = "source_archive"
    external_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionBatch:
    documents: tuple[ExtractedDocument, ...]
    summary: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
