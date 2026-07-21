from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence

from .models import AutoReviewDecision, ReviewCandidate, ReviewContext, RuleFinding


class ReviewRule(Protocol):
    code: str

    def evaluate(self, candidate: ReviewCandidate, context: ReviewContext) -> RuleFinding | None:
        ...


class DuplicateDetector(Protocol):
    def inspect(
        self,
        candidate: ReviewCandidate,
        possible_matches: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any] | None:
        ...


class AuditEventSink(Protocol):
    def append_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: Mapping[str, Any],
    ) -> Any:
        ...


class AutoReviewEvaluator(Protocol):
    def evaluate(self, candidate: ReviewCandidate, context: ReviewContext) -> AutoReviewDecision:
        ...
