from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import CaptureEnvelope

_TRACKING_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "spm", "from", "share_source", "share_token",
}


@dataclass(frozen=True)
class DeduplicationResult:
    is_duplicate: bool
    deduplication_key: str
    matched_capture_id: str = ""
    reason: str = ""


class CaptureDeduplicator:
    def __init__(self):
        self._seen: dict[str, tuple[str, float]] = {}

    def probe(self, envelope: CaptureEnvelope, *, now: float, window_seconds: int) -> DeduplicationResult:
        key, reason = self.key_for(envelope)
        matched = self._seen.get(key)
        if matched and now - matched[1] <= max(int(window_seconds), 0):
            return DeduplicationResult(True, key, matched[0], reason)
        return DeduplicationResult(False, key, "", reason)

    def check(self, envelope: CaptureEnvelope, *, now: float, window_seconds: int) -> DeduplicationResult:
        """Backward-compatible non-mutating alias for the probe phase."""
        return self.probe(envelope, now=now, window_seconds=window_seconds)

    def remember(self, envelope: CaptureEnvelope, *, key: str, now: float) -> None:
        self._seen[key] = (envelope.capture_id, now)

    def commit(self, envelope: CaptureEnvelope, *, key: str, now: float) -> None:
        self.remember(envelope, key=key, now=now)

    def key_for(self, envelope: CaptureEnvelope) -> tuple[str, str]:
        if envelope.input_path and envelope.input_path.is_file():
            digest = self._file_hash(envelope.input_path)
            material = f"file\x1f{envelope.source_type}\x1f{digest}"
            return self._hash(material), "same file content hash"
        normalized_url = self.normalize_url(envelope.url)
        if normalized_url:
            content = envelope.text or envelope.transcript or envelope.ocr_text or envelope.html
            content_hash = self._hash(content) if content else ""
            material = f"url\x1f{envelope.source_type}\x1f{normalized_url}\x1f{content_hash}"
            return self._hash(material), "same normalized URL and content"
        content = "\x1f".join((
            envelope.source_type,
            envelope.capture_method,
            envelope.title,
            envelope.text,
            envelope.transcript,
            envelope.ocr_text,
            envelope.external_id,
        ))
        return self._hash(content), "same source content identity"

    @staticmethod
    def normalize_url(value: str) -> str:
        if not value:
            return ""
        parsed = urlsplit(value.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        query = [
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in _TRACKING_KEYS
        ]
        host = parsed.hostname.lower()
        netloc = host
        if parsed.port and parsed.port not in {80, 443}:
            netloc = f"{host}:{parsed.port}"
        path = parsed.path or "/"
        return urlunsplit((parsed.scheme.lower(), netloc, path.rstrip("/") or "/", urlencode(sorted(query)), ""))

    @staticmethod
    def _file_hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _hash(value: Any) -> str:
        return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()
