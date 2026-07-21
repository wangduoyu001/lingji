from __future__ import annotations

import pytest

from src.auto_review import (
    AutoReviewAction,
    AutoReviewMode,
    DeterministicAutoReviewEvaluator,
    ReviewCandidate,
    ReviewContext,
    ShadowAutoReviewService,
    build_shadow_audit_payload,
    verify_shadow_audit_payload,
)


def candidate(**overrides):
    values = {
        "memory_id": "LJ-MEM-1",
        "title": "Stable fact",
        "content": "A durable fact with a cited source.",
        "memory_type": "knowledge",
        "privacy": "private",
        "project_ids": ("lingji",),
        "source_refs": ("source-1",),
        "content_hash": "abc",
    }
    values.update(overrides)
    return ReviewCandidate(**values)


def test_shadow_low_risk_candidate_only_suggests_approval():
    decision = DeterministicAutoReviewEvaluator().evaluate(
        candidate(),
        ReviewContext(mode=AutoReviewMode.SHADOW, evidence_sufficient=True),
    )
    assert decision.action is AutoReviewAction.WOULD_AUTO_APPROVE
    assert decision.mutation_performed is False


def test_active_mode_is_rejected():
    with pytest.raises(ValueError, match="ACTIVE"):
        DeterministicAutoReviewEvaluator().evaluate(
            candidate(),
            ReviewContext(mode=AutoReviewMode.ACTIVE, evidence_sufficient=True),
        )


@pytest.mark.parametrize(
    ("candidate_overrides", "context_overrides", "reason_code"),
    [
        ({"memory_type": "core"}, {}, "core_memory_requires_owner"),
        ({"privacy": "restricted"}, {}, "restricted_content_requires_owner"),
        ({}, {"requested_operation": "delete"}, "destructive_operation_requires_owner"),
        ({}, {"permission_or_privacy_change": True}, "privacy_change_requires_owner"),
        ({}, {"has_conflict": True}, "knowledge_conflict_requires_owner"),
        ({}, {"owner_authored": True}, "owner_authored_requires_owner"),
        (
            {"metadata": {"source_type": "codex", "status": "unverified"}},
            {"development_report_status": "unverified"},
            "unverified_work_report_requires_owner",
        ),
    ],
)
def test_hard_rules_never_auto_approve(candidate_overrides, context_overrides, reason_code):
    context = ReviewContext(
        mode=AutoReviewMode.SHADOW,
        evidence_sufficient=True,
        **context_overrides,
    )
    decision = DeterministicAutoReviewEvaluator().evaluate(candidate(**candidate_overrides), context)
    assert decision.action is AutoReviewAction.REQUIRES_OWNER_REVIEW
    assert reason_code in {item.code for item in decision.reasons}
    assert decision.mutation_performed is False


def test_cross_project_merge_requires_owner():
    decision = DeterministicAutoReviewEvaluator().evaluate(
        candidate(project_ids=("project-a",)),
        ReviewContext(
            mode=AutoReviewMode.SHADOW,
            target_project_id="project-b",
            evidence_sufficient=True,
        ),
    )
    assert decision.action is AutoReviewAction.REQUIRES_OWNER_REVIEW


def test_same_scope_evidence_only_duplicate_is_append_proposal():
    decision = DeterministicAutoReviewEvaluator().evaluate(
        candidate(),
        ReviewContext(
            mode=AutoReviewMode.SHADOW,
            evidence_sufficient=True,
            duplicate_memory_id="LJ-CORE-1",
            duplicate_same_project=True,
            duplicate_same_type=True,
            evidence_only_change=True,
        ),
    )
    assert decision.action is AutoReviewAction.WOULD_APPEND_EVIDENCE
    assert decision.target_memory_id == "LJ-CORE-1"
    assert decision.mutation_performed is False


def test_external_risk_can_only_raise_score():
    evaluator = DeterministicAutoReviewEvaluator()
    baseline = evaluator.evaluate(
        candidate(),
        ReviewContext(mode=AutoReviewMode.SHADOW, evidence_sufficient=True),
    )
    raised = evaluator.evaluate(
        candidate(),
        ReviewContext(
            mode=AutoReviewMode.SHADOW,
            evidence_sufficient=True,
            external_risk_points=40,
        ),
    )
    assert raised.risk_score >= baseline.risk_score


def test_audit_hash_detects_tampering():
    decision = DeterministicAutoReviewEvaluator().evaluate(
        candidate(),
        ReviewContext(mode=AutoReviewMode.SHADOW, evidence_sufficient=True),
    )
    payload = build_shadow_audit_payload(
        decision,
        previous_hash="previous",
        evaluated_at="2026-07-22T00:00:00+00:00",
    )
    assert verify_shadow_audit_payload(payload)
    payload["decision"]["action"] = "would_auto_reject_noise"
    assert not verify_shadow_audit_payload(payload)


class _StateDB:
    def __init__(self):
        self.events = []

    def append_event(self, *args):
        self.events.append(args)


def test_shadow_service_uses_existing_event_sink_without_mutating_candidate():
    state_db = _StateDB()
    raw = {
        "memory_id": "LJ-MEM-1",
        "title": "Stable fact",
        "content": "A fact",
        "memory_type": "note",
        "project_ids": ["lingji"],
    }
    result = ShadowAutoReviewService(state_db=state_db).evaluate(
        raw,
        ReviewContext(mode=AutoReviewMode.SHADOW, evidence_sufficient=True),
    )
    assert result["mutation_performed"] is False
    assert state_db.events[0][0] == "auto_review_shadow_decision"
    assert raw["content"] == "A fact"
