from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence

from .models import ReviewCandidate

_SPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_content(value: str) -> str:
    lowered = str(value or "").strip().lower()
    return _SPACE.sub(" ", _PUNCTUATION.sub(" ", lowered)).strip()


def normalized_content_hash(value: str) -> str:
    return hashlib.sha256(normalize_content(value).encode("utf-8")).hexdigest()


class NormalizedDuplicateDetector:
    """Detect exact normalized duplicates without reading or mutating a second store."""

    def inspect(
        self,
        candidate: ReviewCandidate,
        possible_matches: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any] | None:
        candidate_hash = normalized_content_hash(candidate.content)
        for item in possible_matches:
            content = str(item.get("content") or item.get("content_preview") or "")
            if not content or normalized_content_hash(content) != candidate_hash:
                continue
            project_ids = item.get("project_ids") or item.get("project") or []
            if not isinstance(project_ids, (list, tuple, set)):
                project_ids = [project_ids]
            return {
                "memory_id": item.get("memory_id") or item.get("id"),
                "same_project": bool(set(candidate.project_ids) & {str(value) for value in project_ids}),
                "same_type": str(item.get("memory_type") or "knowledge") == candidate.memory_type,
                "content_hash": candidate_hash,
            }
        return None
