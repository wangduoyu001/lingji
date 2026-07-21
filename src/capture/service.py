from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from .deduplication import CaptureDeduplicator
from .models import CaptureCapability, CaptureEnvelope, CaptureResult, CaptureStatus
from .policy import CaptureMode, CapturePolicy

_ALLOWED_METHODS = {
    "mobile_share", "browser_extension", "clipboard", "folder_watch",
    "manual_upload", "local_control_share", "scheduled_import",
}
_SENSITIVE_KEYS = {
    "token", "access_token", "cookie", "api_key", "apikey", "authorization",
    "password", "secret", "credential", "session",
}
_RESERVED_PAYLOAD_KEYS = {
    "title", "url", "capture_method", "author", "account_name", "published_at",
    "media_url", "cover_url", "transcript", "ocr_text",
}


class CaptureService:
    def __init__(self, pipeline, *, policy: CapturePolicy | None = None, deduplicator=None):
        self.pipeline = pipeline
        self.policy = policy or CapturePolicy()
        self.deduplicator = deduplicator or CaptureDeduplicator()
        self._paused = self.policy.mode is CaptureMode.PAUSED
        self._submitted = 0

    def submit(self, envelope: CaptureEnvelope) -> CaptureResult:
        self._validate(envelope)
        if self._paused:
            return CaptureResult(envelope.capture_id, CaptureStatus.PAUSED, reason="capture service paused")
        now = time.time()
        duplicate = self.deduplicator.probe(
            envelope,
            now=now,
            window_seconds=self.policy.duplicate_window_seconds,
        )
        if duplicate.is_duplicate:
            return CaptureResult(
                envelope.capture_id,
                CaptureStatus.DUPLICATE,
                deduplication_key=duplicate.deduplication_key,
                reason=duplicate.reason,
            )
        payload, options = self._pipeline_input(envelope)
        heavy = envelope.source_type in {"media", "video", "audio"}
        queue = envelope.process_later or self.policy.queue_only or heavy or not self.policy.allow_realtime
        if queue:
            outcome = self.pipeline.enqueue(
                envelope.source_type,
                input_path=envelope.input_path,
                payload=payload,
                options=options,
                priority=envelope.priority,
                idempotency_key=duplicate.deduplication_key,
            )
            result = CaptureResult(
                envelope.capture_id,
                CaptureStatus.QUEUED,
                deduplication_key=duplicate.deduplication_key,
                extraction_job_id=str(outcome.get("job_id") or ""),
                queued=True,
            )
        else:
            outcome = self.pipeline.execute(
                envelope.source_type,
                input_path=envelope.input_path,
                payload=payload,
                options=options,
                execution_id=envelope.capture_id,
            )
            result = CaptureResult(
                envelope.capture_id,
                CaptureStatus.EXECUTED,
                deduplication_key=duplicate.deduplication_key,
                extraction_job_id=str(outcome.get("execution_id") or envelope.capture_id),
                executed=True,
            )
        self.deduplicator.commit(envelope, key=duplicate.deduplication_key, now=now)
        self._submitted += 1
        return result

    def submit_file(self, path: Path | str, *, source_type: str = "media", **kwargs: Any) -> CaptureResult:
        return self.submit(self._envelope(source_type, "manual_upload", input_path=Path(path), **kwargs))

    def submit_text(self, text: str, *, source_type: str = "web", **kwargs: Any) -> CaptureResult:
        return self.submit(self._envelope(source_type, "clipboard", text=text, **kwargs))

    def submit_web(self, url: str, **kwargs: Any) -> CaptureResult:
        return self.submit(self._envelope("web", kwargs.pop("capture_method", "browser_extension"), url=url, **kwargs))

    def submit_media(self, path: Path | str, **kwargs: Any) -> CaptureResult:
        return self.submit(self._envelope("media", kwargs.pop("capture_method", "manual_upload"), input_path=Path(path), **kwargs))

    def status(self) -> dict[str, Any]:
        return {"paused": self._paused, "mode": self.policy.mode.value, "submitted": self._submitted}

    def capabilities(self) -> tuple[CaptureCapability, ...]:
        return (
            CaptureCapability("mobile_share", True),
            CaptureCapability("browser_extension", True),
            CaptureCapability("clipboard", True, realtime=False),
            CaptureCapability("folder_watch", True, realtime=False),
            CaptureCapability("global_keyboard_listener", False),
            CaptureCapability("fullscreen_capture_listener", False),
        )

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    @staticmethod
    def _envelope(source_type: str, capture_method: str, **kwargs: Any) -> CaptureEnvelope:
        return CaptureEnvelope(
            capture_id=str(kwargs.pop("capture_id", f"LJ-CAP-{uuid4().hex[:16].upper()}")),
            source_type=source_type,
            capture_method=capture_method,
            **kwargs,
        )

    def _validate(self, envelope: CaptureEnvelope) -> None:
        if not envelope.capture_id.strip() or not envelope.source_type.strip():
            raise ValueError("capture_id and source_type are required")
        if envelope.capture_method not in _ALLOWED_METHODS:
            raise ValueError(f"unsupported capture_method: {envelope.capture_method}")
        if envelope.input_path:
            if not envelope.input_path.exists() or not envelope.input_path.is_file():
                raise FileNotFoundError(envelope.input_path)
            if envelope.input_path.stat().st_size > self.policy.max_file_bytes:
                raise ValueError("capture file exceeds policy limit")
        self._validate_metadata(envelope.metadata)
        collisions = {str(key).lower() for key in envelope.metadata} & _RESERVED_PAYLOAD_KEYS
        if collisions:
            raise ValueError("capture metadata cannot override reserved payload fields")
        if not any((envelope.url, envelope.text, envelope.html, envelope.input_path, envelope.transcript, envelope.ocr_text, envelope.media_url)):
            raise ValueError("capture has no usable content")

    @classmethod
    def _validate_metadata(cls, value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if str(key).lower() in _SENSITIVE_KEYS:
                    raise ValueError("capture metadata contains forbidden sensitive fields")
                cls._validate_metadata(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                cls._validate_metadata(item)

    def _pipeline_input(self, envelope: CaptureEnvelope) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = {
            "title": envelope.title,
            "url": envelope.url,
            "text": envelope.text,
            "html": envelope.html,
            "author": envelope.author,
            "account_name": envelope.account_name,
            "published_at": envelope.published_at,
            "media_url": envelope.media_url,
            "cover_url": envelope.cover_url,
            "transcript": envelope.transcript,
            "ocr_text": envelope.ocr_text,
            "capture_method": envelope.capture_method,
            "platform": envelope.platform,
            "description": envelope.description,
            "external_id": envelope.external_id,
            "metadata": dict(envelope.metadata),
        }
        options = {
            "project": list(envelope.project_ids),
            "tags": list(envelope.tags),
            "privacy": envelope.privacy,
            "allow_ocr": self.policy.allow_ocr,
            "allow_video_transcription": self.policy.allow_video_transcription,
            "allow_vectorization": self.policy.allow_vectorization,
            "extract_audio": False,
            "extract_keyframes": False,
        }
        return {key: value for key, value in payload.items() if value not in (None, "", [], {})}, options
