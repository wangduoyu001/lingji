from __future__ import annotations

from .models import ReviewCandidate


def evidence_is_sufficient(candidate: ReviewCandidate, *, minimum_sources: int = 1) -> bool:
    if candidate.memory_type in {"note", "noise", "transient"}:
        return True
    unique = {str(item).strip() for item in candidate.source_refs if str(item).strip()}
    return len(unique) >= max(int(minimum_sources), 1)
