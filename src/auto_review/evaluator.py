from __future__ import annotations

import hashlib
import json

from .models import (
    AutoReviewAction,
    AutoReviewDecision,
    AutoReviewMode,
    ReviewCandidate,
    ReviewContext,
    RuleFinding,
)
from .risk import calculate_risk
from .security import hard_rule_findings


class DeterministicAutoReviewEvaluator:
    """Pure OFF/SHADOW evaluator. It never calls lifecycle or persistence writers."""

    def evaluate(self, candidate: ReviewCandidate, context: ReviewContext) -> AutoReviewDecision:
        if context.mode is AutoReviewMode.ACTIVE:
            raise ValueError("ACTIVE auto review is disabled; only OFF and SHADOW are supported")

        findings = list(hard_rule_findings(candidate, context))
        if context.mode is AutoReviewMode.OFF:
            findings.append(
                RuleFinding(
                    code="auto_review_off",
                    message="Auto Review is disabled.",
                    risk_points=0,
                    blocked=True,
                )
            )
            return self._decision(candidate, context, AutoReviewAction.BLOCKED, tuple(findings))

        blocked = any(item.blocked for item in findings)
        hard_manual = any(item.hard_manual for item in findings)
        if blocked:
            action = AutoReviewAction.BLOCKED
        elif hard_manual:
            action = AutoReviewAction.REQUIRES_OWNER_REVIEW
        elif (
            context.duplicate_memory_id
            and context.duplicate_same_project
            and context.duplicate_same_type
            and context.evidence_only_change
        ):
            findings.append(
                RuleFinding(
                    code="same_scope_evidence_only_duplicate",
                    message="Same-project, same-type duplicate can be proposed as evidence append only.",
                    risk_points=10,
                )
            )
            action = AutoReviewAction.WOULD_APPEND_EVIDENCE
        elif context.low_value_noise:
            findings.append(
                RuleFinding(
                    code="low_value_noise",
                    message="Candidate matches deterministic low-value noise criteria.",
                    risk_points=5,
                )
            )
            action = AutoReviewAction.WOULD_AUTO_REJECT_NOISE
        elif context.evidence_sufficient:
            findings.append(
                RuleFinding(
                    code="low_risk_evidence_sufficient",
                    message="Candidate passed deterministic schema, scope, security and evidence checks.",
                    risk_points=5,
                )
            )
            action = AutoReviewAction.WOULD_AUTO_APPROVE
        else:
            findings.append(
                RuleFinding(
                    code="owner_review_default",
                    message="No deterministic low-risk action is justified.",
                    risk_points=30,
                    hard_manual=True,
                )
            )
            action = AutoReviewAction.REQUIRES_OWNER_REVIEW
        return self._decision(candidate, context, action, tuple(findings))

    @staticmethod
    def _decision(
        candidate: ReviewCandidate,
        context: ReviewContext,
        action: AutoReviewAction,
        findings: tuple[RuleFinding, ...],
    ) -> AutoReviewDecision:
        score, level = calculate_risk(findings, external_points=context.external_risk_points)
        material = {
            "candidate_id": candidate.memory_id,
            "content_hash": candidate.content_hash,
            "mode": context.mode.value,
            "action": action.value,
            "finding_codes": [item.code for item in findings],
            "target": context.duplicate_memory_id,
        }
        token = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        return AutoReviewDecision(
            decision_id=f"LJ-AR-{token.upper()}",
            candidate_id=candidate.memory_id,
            mode=context.mode,
            action=action,
            risk_level=level,
            risk_score=score,
            reasons=findings,
            target_memory_id=context.duplicate_memory_id,
            reversible=all(item.reversible for item in findings),
            mutation_performed=False,
        )
