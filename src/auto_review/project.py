from __future__ import annotations

from .models import ReviewCandidate


def same_project(candidate: ReviewCandidate, target_project_id: str | None) -> bool:
    if not target_project_id:
        return len(candidate.project_ids) <= 1
    return target_project_id in set(candidate.project_ids)


def project_scope(candidate: ReviewCandidate) -> tuple[str, ...]:
    return tuple(sorted({item for item in candidate.project_ids if item}))
