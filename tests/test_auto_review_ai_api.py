from __future__ import annotations

import json
from io import BytesIO
from types import SimpleNamespace

import pytest

from src.auto_review import AutoReviewApplicationService, AutoReviewMode, ReviewCandidate
from src.auto_review.local_ai import LocalOllamaReviewer, resolve_auto_review_models


def candidate() -> dict:
    return {
        "memory_id": "LJ-MEM-AI-1",
        "title": "Local review candidate",
        "content": "A stable fact with a source.",
        "memory_type": "knowledge",
        "privacy": "private",
        "project_ids": ["lingji"],
        "source_refs": ["source-1"],
        "content_hash": "hash-1",
    }


class _Response:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


class _StateDB:
    def __init__(self):
        self.events: list[dict] = []

    def append_event(self, event_type, entity_type, entity_id, payload):
        self.events.insert(
            0,
            {
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "payload_json": json.dumps(payload),
            },
        )

    def recent_events(self, limit=100):
        return self.events[:limit]


def settings(**overrides):
    values = {
        "auto_review_mode": "SHADOW",
        "auto_review_ai_enabled": False,
        "auto_review_timeout_seconds": 5.0,
        "ollama_base_url": "http://127.0.0.1:11434",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_model_roles_are_resolved_without_hardcoded_names():
    primary, fallback = resolve_auto_review_models(
        [
            {"role": "auto_review_primary", "model": "local-primary"},
            {"role": "auto_review_fallback", "model": "local-fallback"},
        ]
    )
    assert primary == "local-primary"
    assert fallback == "local-fallback"


def test_remote_ai_endpoint_is_rejected():
    with pytest.raises(ValueError, match="loopback"):
        LocalOllamaReviewer(
            base_url="https://example.com",
            primary_model="model",
        )


def test_strict_json_local_ai_assessment():
    def opener(request, timeout):
        assert request.full_url == "http://127.0.0.1:11434/api/chat"
        assert timeout == 5.0
        return _Response(
            {
                "message": {
                    "content": json.dumps(
                        {
                            "risk_points": 12,
                            "flags": ["ambiguous source"],
                            "summary": "Additional source ambiguity was detected.",
                        }
                    )
                }
            }
        )

    assessment = LocalOllamaReviewer(
        base_url="http://127.0.0.1:11434",
        primary_model="local-primary",
        timeout_seconds=5,
        opener=opener,
    ).assess(ReviewCandidate.from_mapping(candidate()))

    assert assessment.available is True
    assert assessment.risk_points == 12
    assert assessment.model == "local-primary"
    assert assessment.flags == ("ambiguous source",)


def test_invalid_ai_json_falls_back_to_safe_unavailable_result():
    def opener(*args, **kwargs):
        return _Response({"message": {"content": "not-json"}})

    assessment = LocalOllamaReviewer(
        base_url="http://127.0.0.1:11434",
        primary_model="local-primary",
        fallback_model="local-fallback",
        opener=opener,
    ).assess(ReviewCandidate.from_mapping(candidate()))

    assert assessment.available is False
    assert assessment.risk_points == 0
    assert "local-primary" in str(assessment.error)
    assert "local-fallback" in str(assessment.error)


def test_application_records_shadow_decision_without_mutation():
    state_db = _StateDB()
    service = AutoReviewApplicationService(
        state_db=state_db,
        app_settings=settings(),
        model_inventory=lambda: {"assignments": []},
    )

    result = service.evaluate(
        candidate(),
        {"mode": "SHADOW", "evidence_sufficient": True},
        use_ai=False,
    )

    assert result["decision"]["mode"] == "SHADOW"
    assert result["decision"]["action"] == "would_auto_approve"
    assert result["mutation_performed"] is False
    assert state_db.events[0]["event_type"] == "auto_review_shadow_decision"
    assert service.metrics()["mutation_count"] == 0


def test_ai_can_raise_risk_but_cannot_change_hard_rule_action():
    class Reviewer:
        def assess(self, selected):
            from src.auto_review.local_ai import LocalAIAssessment
            return LocalAIAssessment("local", 30, ("extra-risk",), "Additional risk.", True)

    state_db = _StateDB()
    service = AutoReviewApplicationService(
        state_db=state_db,
        app_settings=settings(auto_review_ai_enabled=True),
        model_inventory=lambda: {
            "assignments": [{"role": "auto_review_primary", "model": "local"}]
        },
        ai_reviewer_factory=lambda **kwargs: Reviewer(),
    )

    result = service.evaluate(
        {**candidate(), "privacy": "restricted"},
        {"mode": "SHADOW", "evidence_sufficient": True},
    )

    assert result["decision"]["action"] == "requires_owner_review"
    assert result["decision"]["risk_score"] >= 30
    assert result["decision"]["mutation_performed"] is False


def test_active_configuration_is_forbidden():
    service = AutoReviewApplicationService(
        state_db=_StateDB(),
        app_settings=settings(auto_review_mode="ACTIVE"),
    )
    with pytest.raises(ValueError, match="ACTIVE"):
        service.status()


def test_feedback_is_an_audit_event_not_an_execution():
    state_db = _StateDB()
    service = AutoReviewApplicationService(state_db=state_db, app_settings=settings())
    decision = service.evaluate(
        candidate(),
        {"mode": "SHADOW", "evidence_sufficient": True},
        use_ai=False,
    )["decision"]

    feedback = service.feedback(decision["decision_id"], outcome="owner_disagreed", notes="Needs review")

    assert feedback["mutation_performed"] is False
    assert state_db.events[0]["event_type"] == "auto_review_feedback"


def test_audit_verify_endpoint_contract():
    state_db = _StateDB()
    service = AutoReviewApplicationService(state_db=state_db, app_settings=settings())
    payload = service.evaluate(
        candidate(),
        {"mode": "SHADOW", "evidence_sufficient": True},
        use_ai=False,
    )
    assert service.verify(payload)["valid"] is True
