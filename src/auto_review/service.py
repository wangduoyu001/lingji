from __future__ import annotations

from typing import Any, Mapping

from .audit import build_shadow_audit_payload
from .evaluator import DeterministicAutoReviewEvaluator
from .models import AutoReviewDecision, AutoReviewMode, ReviewCandidate, ReviewContext


class ShadowAutoReviewService:
    """Evaluate and append an existing StateDatabase event without mutating memory state."""

    def __init__(self, *, state_db: Any | None = None, evaluator: Any | None = None):
        self.state_db = state_db
        self.evaluator = evaluator or DeterministicAutoReviewEvaluator()

    def evaluate(
        self,
        candidate: Mapping[str, Any] | ReviewCandidate,
        context: ReviewContext | None = None,
        *,
        previous_hash: str = "",
    ) -> dict[str, Any]:
        selected = candidate if isinstance(candidate, ReviewCandidate) else ReviewCandidate.from_mapping(candidate)
        review_context = context or ReviewContext(mode=AutoReviewMode.SHADOW)
        decision: AutoReviewDecision = self.evaluator.evaluate(selected, review_context)
        audit = build_shadow_audit_payload(decision, previous_hash=previous_hash)
        if review_context.mode is AutoReviewMode.SHADOW and self.state_db is not None:
            self.state_db.append_event(
                "auto_review_shadow_decision",
                "memory_candidate",
                selected.memory_id,
                audit,
            )
        return audit
