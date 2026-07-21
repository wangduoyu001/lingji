from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from src.extraction.adapters.media import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS

from .models import CaptureEnvelope


CAPTURE_UNSUPPORTED_TYPE = "CAPTURE_UNSUPPORTED_TYPE"


class ManualCaptureKind(str, Enum):
    TEXT = "text"
    WEB = "web"
    CHATGPT_EXPORT = "chatgpt_export"
    CODEX_REPORT = "codex_report"
    MEDIA = "media"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ManualCaptureClassification:
    kind: ManualCaptureKind
    source_type: str = ""
    capture_method: str = ""
    adapter_name: str = ""
    input_path: Path | None = None
    url: str = ""
    text: str = ""
    html: str = ""
    supported: bool = True
    error_code: str = ""
    reason: str = ""


class ManualCaptureError(ValueError):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(code if not message else f"{code}: {message}")


def classify_manual_input(
    value: Path | str,
    *,
    selected_kind: ManualCaptureKind | str | None = None,
) -> ManualCaptureClassification:
    kind = _normalize_kind(selected_kind)
    if isinstance(value, Path):
        return _classify_path(value.expanduser(), kind)

    raw = str(value or "").strip()
    if not raw:
        return _unsupported("empty manual input")
    if _is_http_url(raw):
        if kind not in (None, ManualCaptureKind.WEB):
            return _unsupported("selected mode conflicts with URL input")
        return ManualCaptureClassification(
            ManualCaptureKind.WEB,
            source_type="web",
            capture_method="manual_web",
            adapter_name="web_capture",
            url=raw,
        )

    candidate = Path(raw).expanduser()
    try:
        candidate_exists = candidate.exists()
        candidate_suffix = candidate.suffix
    except OSError:
        candidate_exists = False
        candidate_suffix = ""
    if candidate_exists or candidate_suffix:
        classification = _classify_path(candidate, kind)
        if classification.supported or candidate_exists:
            return classification

    if kind in (ManualCaptureKind.CHATGPT_EXPORT, ManualCaptureKind.CODEX_REPORT, ManualCaptureKind.MEDIA):
        return _unsupported("selected mode requires a supported local file")
    if _looks_like_html(raw):
        return ManualCaptureClassification(
            ManualCaptureKind.WEB,
            source_type="web",
            capture_method="manual_web",
            adapter_name="web_capture",
            html=raw,
        )
    return ManualCaptureClassification(
        ManualCaptureKind.TEXT,
        source_type="web",
        capture_method="manual_text",
        adapter_name="web_capture",
        text=raw,
    )


def build_manual_envelope(
    value: Path | str,
    *,
    selected_kind: ManualCaptureKind | str | None = None,
    **kwargs: Any,
) -> CaptureEnvelope:
    classification = classify_manual_input(value, selected_kind=selected_kind)
    if not classification.supported:
        raise ManualCaptureError(classification.error_code or CAPTURE_UNSUPPORTED_TYPE)

    requested_source = str(kwargs.pop("source_type", "") or "")
    requested_adapter = str(kwargs.pop("adapter_name", "") or "")
    if requested_source and requested_source != classification.source_type:
        raise ValueError("capture source_type conflicts with manual classification")
    if requested_adapter and requested_adapter != classification.adapter_name:
        raise ValueError("capture adapter_name conflicts with manual classification")

    kwargs.setdefault("process_later", True)
    kwargs.setdefault("privacy", "private")
    kwargs.setdefault("title", _default_title(classification))
    return CaptureEnvelope(
        capture_id=str(kwargs.pop("capture_id", f"LJ-CAP-{uuid4().hex[:16].upper()}")),
        source_type=classification.source_type,
        capture_method=classification.capture_method,
        adapter_name=classification.adapter_name,
        input_path=classification.input_path,
        url=classification.url,
        text=classification.text,
        html=classification.html,
        **kwargs,
    )


def _classify_path(path: Path, selected_kind: ManualCaptureKind | None) -> ManualCaptureClassification:
    if path.is_dir():
        if selected_kind not in (None, ManualCaptureKind.CHATGPT_EXPORT):
            return _unsupported("selected mode conflicts with directory input")
        if any(path.glob("conversations*.json")):
            return _file_classification(
                ManualCaptureKind.CHATGPT_EXPORT,
                "chatgpt_export",
                "manual_chatgpt_export",
                "chatgpt_export",
                path,
            )
        return _unsupported("directory does not contain conversations*.json")

    suffix = path.suffix.lower()
    if selected_kind is ManualCaptureKind.CODEX_REPORT:
        if suffix != ".json":
            return _unsupported("Codex report must be JSON")
        return _file_classification(
            ManualCaptureKind.CODEX_REPORT,
            "codex_report",
            "manual_codex_report",
            "codex_work_report",
            path,
        )
    if selected_kind is ManualCaptureKind.CHATGPT_EXPORT:
        if suffix not in {".zip", ".json"}:
            return _unsupported("ChatGPT export must be ZIP, JSON, or export directory")
        return _file_classification(
            ManualCaptureKind.CHATGPT_EXPORT,
            "chatgpt_export",
            "manual_chatgpt_export",
            "chatgpt_export",
            path,
        )
    if selected_kind is ManualCaptureKind.MEDIA:
        if suffix not in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS:
            return _unsupported("selected media mode conflicts with file extension")
        return _file_classification(
            ManualCaptureKind.MEDIA,
            "media",
            "manual_media",
            "media_local",
            path,
        )
    if selected_kind is ManualCaptureKind.WEB and suffix not in {".html", ".htm", ".json", ".txt", ".md"}:
        return _unsupported("selected web mode conflicts with file extension")

    if suffix in VIDEO_EXTENSIONS | AUDIO_EXTENSIONS:
        return _file_classification(
            ManualCaptureKind.MEDIA,
            "media",
            "manual_media",
            "media_local",
            path,
        )
    if suffix == ".zip":
        return _file_classification(
            ManualCaptureKind.CHATGPT_EXPORT,
            "chatgpt_export",
            "manual_chatgpt_export",
            "chatgpt_export",
            path,
        )
    if suffix == ".json":
        if path.name.lower().startswith("conversations") or _looks_like_chatgpt_json(path):
            return _file_classification(
                ManualCaptureKind.CHATGPT_EXPORT,
                "chatgpt_export",
                "manual_chatgpt_export",
                "chatgpt_export",
                path,
            )
        return _file_classification(
            ManualCaptureKind.WEB,
            "web",
            "manual_file",
            "web_capture",
            path,
        )
    if suffix in {".html", ".htm", ".txt", ".md"}:
        return _file_classification(
            ManualCaptureKind.WEB,
            "web",
            "manual_file",
            "web_capture",
            path,
        )
    return _unsupported("unsupported manual file type")


def _file_classification(
    kind: ManualCaptureKind,
    source_type: str,
    capture_method: str,
    adapter_name: str,
    path: Path,
) -> ManualCaptureClassification:
    return ManualCaptureClassification(
        kind,
        source_type=source_type,
        capture_method=capture_method,
        adapter_name=adapter_name,
        input_path=path,
    )


def _unsupported(reason: str) -> ManualCaptureClassification:
    return ManualCaptureClassification(
        ManualCaptureKind.UNSUPPORTED,
        supported=False,
        error_code=CAPTURE_UNSUPPORTED_TYPE,
        reason=reason,
    )


def _normalize_kind(value: ManualCaptureKind | str | None) -> ManualCaptureKind | None:
    if value in (None, ""):
        return None
    if isinstance(value, ManualCaptureKind):
        return value
    aliases = {
        "text": ManualCaptureKind.TEXT,
        "web": ManualCaptureKind.WEB,
        "chatgpt": ManualCaptureKind.CHATGPT_EXPORT,
        "chatgpt_export": ManualCaptureKind.CHATGPT_EXPORT,
        "codex": ManualCaptureKind.CODEX_REPORT,
        "codex_report": ManualCaptureKind.CODEX_REPORT,
        "media": ManualCaptureKind.MEDIA,
    }
    try:
        return aliases[str(value).strip().lower()]
    except KeyError as exc:
        raise ValueError("unknown manual capture mode") from exc


def _is_http_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _looks_like_html(value: str) -> bool:
    lowered = value.lstrip().lower()
    return lowered.startswith("<!doctype html") or lowered.startswith("<html")


def _looks_like_chatgpt_json(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if isinstance(payload, list) and payload:
        first = payload[0]
        return isinstance(first, dict) and "mapping" in first and ("id" in first or "title" in first)
    if isinstance(payload, dict):
        conversations = payload.get("conversations")
        return isinstance(conversations, list)
    return False


def _default_title(classification: ManualCaptureClassification) -> str:
    if classification.input_path:
        return classification.input_path.name
    if classification.url:
        return classification.url
    return "Manual capture"
