from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class CaptureStatus(str, Enum):
    ACCEPTED = "accepted"
    QUEUED = "queued"
    EXECUTED = "executed"
    DUPLICATE = "duplicate"
    PAUSED = "paused"
    REJECTED = "rejected"


@dataclass(frozen=True)
class CaptureCapability:
    name: str
    enabled: bool
    realtime: bool = False
    requires_idle: bool = False
    requires_ac_power: bool = False
    description: str = ""


@dataclass(frozen=True)
class CaptureEnvelope:
    capture_id: str
    source_type: str
    capture_method: str
    adapter_name: str = ""
    title: str = ""
    url: str = ""
    text: str = ""
    html: str = ""
    input_path: Path | None = None
    author: str = ""
    account_name: str = ""
    published_at: str = ""
    media_url: str = ""
    cover_url: str = ""
    transcript: str = ""
    ocr_text: str = ""
    platform: str = ""
    description: str = ""
    external_id: str = ""
    process_later: bool = False
    allow_ocr: bool = False
    allow_transcription: bool = False
    extract_keyframes: bool = False
    extract_audio: bool = False
    project_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    privacy: str = "private"
    priority: int = 100
    received_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaptureResult:
    capture_id: str
    status: CaptureStatus
    deduplication_key: str = ""
    extraction_job_id: str = ""
    reason: str = ""
    queued: bool = False
    executed: bool = False
    warnings: tuple[str, ...] = ()
