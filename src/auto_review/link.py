from __future__ import annotations

from typing import Any

from .models import ReviewCandidate, ReviewContext


def evidence_append_proposal(candidate: ReviewCandidate, context: ReviewContext) -> dict[str, Any] | None:
    if not (
        context.duplicate_memory_id
        and context.duplicate_same_project
        and context.duplicate_same_type
        and context.evidence_only_change
    ):
        return None
    return {
        "target_memory_id": context.duplicate_memory_id,
        "candidate_id": candidate.memory_id,
        "operation": "append_evidence_proposal",
        "source_refs": list(candidate.source_refs),
        "reversible": True,
        "executed": False,
    }
