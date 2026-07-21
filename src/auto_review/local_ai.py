from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .models import ReviewCandidate


@dataclass(frozen=True)
class LocalAIAssessment:
    model: str | None
    risk_points: int
    flags: tuple[str, ...]
    summary: str
    available: bool
    error: str | None = None


def resolve_auto_review_models(assignments: Sequence[Mapping[str, Any]]) -> tuple[str | None, str | None]:
    primary = next(
        (str(item.get("model") or "").strip() for item in assignments if item.get("role") == "auto_review_primary"),
        "",
    )
    fallback = next(
        (str(item.get("model") or "").strip() for item in assignments if item.get("role") == "auto_review_fallback"),
        "",
    )
    return primary or None, fallback or None


class LocalOllamaReviewer:
    """Local-only strict JSON risk reviewer. It cannot choose or execute an action."""

    def __init__(
        self,
        *,
        base_url: str,
        primary_model: str | None,
        fallback_model: str | None = None,
        timeout_seconds: float = 20.0,
        opener: Any | None = None,
    ):
        self.base_url = str(base_url or "").rstrip("/")
        self.primary_model = primary_model
        self.fallback_model = fallback_model if fallback_model != primary_model else None
        self.timeout_seconds = max(float(timeout_seconds), 0.1)
        self.opener = opener or urllib.request.urlopen
        self._require_local_url()

    def assess(self, candidate: ReviewCandidate) -> LocalAIAssessment:
        models = [item for item in (self.primary_model, self.fallback_model) if item]
        if not models:
            return LocalAIAssessment(None, 0, (), "No Auto Review model role is configured.", False, "model_not_configured")
        errors: list[str] = []
        for model in models:
            try:
                return self._assess_with_model(candidate, model)
            except Exception as exc:
                errors.append(f"{model}: {type(exc).__name__}: {exc}"[:300])
        return LocalAIAssessment(
            models[-1],
            0,
            (),
            "Local AI review unavailable; deterministic result remains authoritative.",
            False,
            "; ".join(errors)[:500],
        )

    def _assess_with_model(self, candidate: ReviewCandidate, model: str) -> LocalAIAssessment:
        prompt = (
            "Assess only additional risk in this memory candidate. Do not approve, reject, merge, "
            "or propose an action. Return strict JSON with exactly risk_points (integer 0-40), "
            "flags (array of short strings), and summary (one short sentence).\n\n"
            f"memory_type={candidate.memory_type}\nprivacy={candidate.privacy}\n"
            f"projects={list(candidate.project_ids)}\ntitle={candidate.title}\ncontent={candidate.content[:4000]}"
        )
        body = json.dumps(
            {
                "model": model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": "You are a conservative local risk classifier. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.opener(request, timeout=self.timeout_seconds) as response:
            envelope = json.loads(response.read().decode("utf-8"))
        raw = envelope.get("message", {}).get("content")
        parsed = json.loads(str(raw or ""))
        if not isinstance(parsed, dict) or set(parsed) != {"risk_points", "flags", "summary"}:
            raise ValueError("Local AI response does not match the strict review schema")
        risk_points = max(0, min(int(parsed["risk_points"]), 40))
        flags = parsed["flags"]
        if not isinstance(flags, list) or not all(isinstance(item, str) for item in flags):
            raise ValueError("Local AI flags must be an array of strings")
        summary = str(parsed["summary"] or "").strip()
        if not summary:
            raise ValueError("Local AI summary is required")
        return LocalAIAssessment(model, risk_points, tuple(item[:80] for item in flags[:20]), summary[:300], True)

    def _require_local_url(self) -> None:
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Auto Review AI endpoint must be local loopback")
