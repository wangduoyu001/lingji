from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from .deduplication import CaptureDeduplicator
from .manual import ManualCaptureKind, build_manual_envelope
from .models import CaptureCapability, CaptureEnvelope, CaptureResult, CaptureStatus
from .policy import CaptureMode, CapturePolicy

_ALLOWED_METHODS = {
    "manual_text", "manual_web", "manual_file", "manual_media",
    "manual_chatgpt_export", "manual_codex_report", "manual_upload",
    "mobile_share", "browser_extension", "clipboard", "folder_watch",
    "local_control_share", "scheduled_import",
}
_SENSITIVE_KEYS = {
    "token", "access_token", "cookie", "api_key", "apikey", "authorization",
    "password", "secret", "credential", "session",
}
_RESERVED_METADATA_KEYS = {
    "source_type", "capture_method", "adapter_name", "input_path", "privacy",
    "project_ids", "tags", "priority", "title", "url", "author", "account_name",
    "published_at", "media_url", "cover_url", "transcript", "ocr_text",
}
_SOURCE_ADAPTERS = {
    "chatgpt": "chatgpt_export",
    "chatgpt_export": "chatgpt_export",
    "codex": "codex_work_report",
    "codex_report": "codex_work_report",
    "web": "web_capture",
    "browser": "web_capture",
    "wechat_article": "web_capture",
    "video_channel": "web_capture",
    "douyin": "web_capture",
    "xiaohongshu": "web_capture",
    "media": "media_local",
    "video": "media_local",
    "audio": "media_local",
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
        call = self.pipeline.enqueue if queue else self.pipeline.execute
        common = {
            "input_path": envelope.input_path,
            "payload": payload,
            "options": options,
            "adapter_name": envelope.adapter_name or None,
        }
        if queue:
            outcome = call(
                envelope.source_type,
                **common,
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
            outcome = call(
                envelope.source_type,
                **common,
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

    def submit_text(self, text: str, *, source_type: str = "web", **kwargs: Any) -> CaptureResult:
        kwargs = self._manual_defaults(kwargs)
        envelope = self._manual_envelope(text, selected_kind=ManualCaptureKind.TEXT, source_type=source_type, **kwargs)
        return self.submit(envelope)

    def submit_web(self, url: str, **kwargs: Any) -> CaptureResult:
        kwargs = self._manual_defaults(kwargs)
        envelope = self._manual_envelope(url, selected_kind=ManualCaptureKind.WEB, **kwargs)
        return self.submit(envelope)

    def submit_file(self, path: Path | str, **kwargs: Any) -> CaptureResult:
        kwargs = self._manual_defaults(kwargs)
        envelope = self._manual_envelope(Path(path), **kwargs)
        return self.submit(self._replace_capture_method(envelope, "manual_file"))

    def submit_media(self, path: Path | str, **kwargs: Any) -> CaptureResult:
        kwargs = self._manual_defaults(kwargs)
        return self.submit(self._manual_envelope(Path(path), selected_kind=ManualCaptureKind.MEDIA, **kwargs))

    def submit_chatgpt_export(self, path: Path | str, **kwargs: Any) -> CaptureResult:
        kwargs = self._manual_defaults(kwargs)
        return self.submit(
            self._manual_envelope(Path(path), selected_kind=ManualCaptureKind.CHATGPT_EXPORT, **kwargs)
        )

    def submit_codex_report(self, path: Path | str, **kwargs: Any) -> CaptureResult:
        kwargs = self._manual_defaults(kwargs)
        return self.submit(
            self._manual_envelope(Path(path), selected_kind=ManualCaptureKind.CODEX_REPORT, **kwargs)
        )

    def status(self) -> dict[str, Any]:
        return {"paused": self._paused, "mode": self.policy.mode.value, "submitted": self._submitted}

    def capabilities(self) -> tuple[CaptureCapability, ...]:
        deferred = "disabled / deferred"
        return (
            CaptureCapability("manual_text", True, description="manual queued text import"),
            CaptureCapability("manual_web", True, description="manual queued web import"),
            CaptureCapability("manual_file", True, description="manual queued supported-file import"),
            CaptureCapability("manual_media", True, description="manual queued media import"),
            CaptureCapability("manual_chatgpt_export", True, description="manual queued ChatGPT export import"),
            CaptureCapability("manual_codex_report", True, description="manual queued Codex report import"),
            CaptureCapability("local_control_share", True, description="compatibility manual share entry"),
            CaptureCapability("mobile_share", False, description=deferred),
            CaptureCapability("browser_extension", False, description=deferred),
            CaptureCapability("clipboard", False, description=deferred),
            CaptureCapability("folder_watch", False, description=deferred),
            CaptureCapability("global_keyboard_listener", False, description="disabled"),
            CaptureCapability("fullscreen_capture_listener", False, description="disabled"),
        )

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    @staticmethod
    def _manual_defaults(kwargs: Mapping[str, Any]) -> dict[str, Any]:
        result = dict(kwargs)
        result.setdefault("process_later", True)
        result.setdefault("privacy", "private")
        return result

    @staticmethod
    def _manual_envelope(value: Path | str, **kwargs: Any) -> CaptureEnvelope:
        kwargs.setdefault("capture_id", f"LJ-CAP-{uuid4().hex[:16].upper()}")
        return build_manual_envelope(value, **kwargs)

    @staticmethod
    def _replace_capture_method(envelope: CaptureEnvelope, capture_method: str) -> CaptureEnvelope:
        values = dict(envelope.__dict__)
        values["capture_method"] = capture_method
        return CaptureEnvelope(**values)

    def _validate(self, envelope: CaptureEnvelope) -> None:
        if not envelope.capture_id.strip() or not envelope.source_type.strip():
            raise ValueError("capture_id and source_type are required")
        if envelope.capture_method not in _ALLOWED_METHODS:
            raise ValueError(f"unsupported capture_method: {envelope.capture_method}")
        expected_adapter = _SOURCE_ADAPTERS.get(envelope.source_type)
        if envelope.adapter_name and envelope.adapter_name != expected_adapter:
            raise ValueError("capture source_type conflicts with adapter_name")
        if envelope.input_path:
            if not envelope.input_path.exists():
                raise ValueError("CAPTURE_FILE_NOT_FOUND")
            if not (envelope.input_path.is_file() or envelope.input_path.is_dir()):
                raise ValueError("CAPTURE_UNSUPPORTED_TYPE")
            if envelope.input_path.is_file() and envelope.input_path.stat().st_size > self.policy.max_file_bytes:
                raise ValueError("CAPTURE_FILE_TOO_LARGE")
        self._validate_metadata(envelope.metadata)
        collisions = {str(key).lower() for key in envelope.metadata} & _RESERVED_METADATA_KEYS
        if collisions:
            raise ValueError("capture metadata cannot override reserved capture fields")
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
            "capture_id": envelope.capture_id,
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
        heavy_allowed = self.policy.permits_heavy_media()
        options = {
            "project": list(envelope.project_ids),
            "tags": list(envelope.tags),
            "privacy": envelope.privacy,
            "allow_ocr": bool(envelope.allow_ocr and self.policy.allow_ocr),
            "allow_video_transcription": bool(
                envelope.allow_transcription and self.policy.allow_video_transcription
            ),
            "allow_vectorization": self.policy.allow_vectorization,
            "extract_audio": bool(envelope.extract_audio and heavy_allowed),
            "extract_keyframes": bool(envelope.extract_keyframes and heavy_allowed),
        }
        return {key: value for key, value in payload.items() if value not in (None, "", [], {})}, options
