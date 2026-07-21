from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Callable, Mapping

from .audit import build_shadow_audit_payload, verify_shadow_audit_payload
from .evaluator import DeterministicAutoReviewEvaluator
from .local_ai import LocalAIAssessment, LocalOllamaReviewer, resolve_auto_review_models
from .models import (
    AutoReviewDecision,
    AutoReviewMode,
    ReviewCandidate,
    ReviewContext,
    RuleFinding,
)
from .risk import calculate_risk


class AutoReviewApplicationService:
    """Authenticated API-facing SHADOW service with no mutation executor."""

    def __init__(
        self,
        *,
        state_db: Any,
        app_settings: Any,
        model_inventory: Callable[[], Mapping[str, Any]] | None = None,
        evaluator: Any | None = None,
        ai_reviewer_factory: Callable[..., Any] = LocalOllamaReviewer,
    ):
        self.state_db = state_db
        self.settings = app_settings
        self.model_inventory = model_inventory
        self.evaluator = evaluator or DeterministicAutoReviewEvaluator()
        self.ai_reviewer_factory = ai_reviewer_factory

    def status(self) -> dict[str, Any]:
        mode = self._configured_mode()
        primary, fallback = self._model_roles()
        return {
            "mode": mode.value,
            "active_supported": False,
            "mutation_enabled": False,
            "ai_enabled": bool(getattr(self.settings, "auto_review_ai_enabled", False)),
            "ai_provider": "ollama_local",
            "primary_model": primary,
            "fallback_model": fallback,
            "decision_count": len(self.decisions(limit=1000)),
        }

    def evaluate(
        self,
        candidate_value: Mapping[str, Any],
        context_value: Mapping[str, Any] | None = None,
        *,
        use_ai: bool | None = None,
    ) -> dict[str, Any]:
        candidate = ReviewCandidate.from_mapping(candidate_value)
        if not candidate.memory_id:
            raise ValueError("candidate memory_id is required")
        context = self._context(context_value or {})
        decision: AutoReviewDecision = self.evaluator.evaluate(candidate, context)
        assessment: LocalAIAssessment | None = None
        should_use_ai = bool(getattr(self.settings, "auto_review_ai_enabled", False)) if use_ai is None else bool(use_ai)
        if should_use_ai and context.mode is AutoReviewMode.SHADOW:
            assessment = self._ai_reviewer().assess(candidate)
            if assessment.available and assessment.risk_points > 0:
                finding = RuleFinding(
                    code="local_ai_additional_risk",
                    message=assessment.summary,
                    risk_points=assessment.risk_points,
                    evidence=assessment.flags,
                )
                findings = (*decision.reasons, finding)
                score, level = calculate_risk(findings)
                decision = replace(decision, reasons=findings, risk_score=score, risk_level=level)
        audit = build_shadow_audit_payload(decision, previous_hash=self._latest_event_hash())
        audit["ai_assessment"] = self._assessment_payload(assessment)
        if context.mode is AutoReviewMode.SHADOW:
            self.state_db.append_event(
                "auto_review_shadow_decision",
                "memory_candidate",
                candidate.memory_id,
                audit,
            )
        return audit

    def decisions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for row in self.state_db.recent_events(limit=max(min(int(limit) * 4, 4000), 1)):
            item = dict(row)
            if item.get("event_type") != "auto_review_shadow_decision":
                continue
            payload = self._event_payload(item)
            if payload:
                output.append(payload)
            if len(output) >= max(int(limit), 1):
                break
        return output

    def decision(self, decision_id: str) -> dict[str, Any]:
        for item in self.decisions(limit=1000):
            decision = item.get("decision") or {}
            if decision.get("decision_id") == decision_id:
                return item
        raise LookupError(f"Unknown Auto Review decision: {decision_id}")

    def metrics(self) -> dict[str, Any]:
        decisions = self.decisions(limit=1000)
        actions: dict[str, int] = {}
        risks: dict[str, int] = {}
        ai_available = 0
        for item in decisions:
            decision = item.get("decision") or {}
            action = str(decision.get("action") or "unknown")
            risk = str(decision.get("risk_level") or "unknown")
            actions[action] = actions.get(action, 0) + 1
            risks[risk] = risks.get(risk, 0) + 1
            if (item.get("ai_assessment") or {}).get("available"):
                ai_available += 1
        return {
            "total": len(decisions),
            "actions": actions,
            "risk_levels": risks,
            "ai_assessed": ai_available,
            "mutation_count": 0,
        }

    def feedback(self, decision_id: str, *, outcome: str, notes: str = "") -> dict[str, Any]:
        decision = self.decision(decision_id)
        payload = {
            "decision_id": decision_id,
            "outcome": str(outcome or "").strip(),
            "notes": str(notes or "").strip()[:2000],
            "mutation_performed": False,
        }
        if not payload["outcome"]:
            raise ValueError("feedback outcome is required")
        self.state_db.append_event("auto_review_feedback", "auto_review_decision", decision_id, payload)
        return payload

    @staticmethod
    def verify(payload: Mapping[str, Any]) -> dict[str, Any]:
        return {"valid": verify_shadow_audit_payload(payload), "event_hash": payload.get("event_hash")}

    def _configured_mode(self) -> AutoReviewMode:
        raw = str(getattr(self.settings, "auto_review_mode", "OFF") or "OFF").strip().upper()
        try:
            mode = AutoReviewMode(raw)
        except ValueError as exc:
            raise ValueError(f"Unsupported Auto Review mode: {raw}") from exc
        if mode is AutoReviewMode.ACTIVE:
            raise ValueError("ACTIVE Auto Review is forbidden in this release")
        return mode

    def _context(self, value: Mapping[str, Any]) -> ReviewContext:
        requested = str(value.get("mode") or self._configured_mode().value).upper()
        mode = AutoReviewMode(requested)
        if mode is AutoReviewMode.ACTIVE:
            raise ValueError("ACTIVE Auto Review is forbidden in this release")
        allowed = {field.name for field in ReviewContext.__dataclass_fields__.values()}
        normalized = {key: item for key, item in value.items() if key in allowed and key != "mode"}
        return ReviewContext(mode=mode, **normalized)

    def _model_roles(self) -> tuple[str | None, str | None]:
        if self.model_inventory is None:
            return None, None
        try:
            inventory = self.model_inventory()
        except Exception:
            return None, None
        return resolve_auto_review_models(inventory.get("assignments") or [])

    def _ai_reviewer(self):
        primary, fallback = self._model_roles()
        return self.ai_reviewer_factory(
            base_url=str(getattr(self.settings, "ollama_base_url", "http://127.0.0.1:11434")),
            primary_model=primary,
            fallback_model=fallback,
            timeout_seconds=float(getattr(self.settings, "auto_review_timeout_seconds", 20.0)),
        )

    def _latest_event_hash(self) -> str:
        decisions = self.decisions(limit=1)
        return str(decisions[0].get("event_hash") or "") if decisions else ""

    @staticmethod
    def _assessment_payload(value: LocalAIAssessment | None) -> dict[str, Any] | None:
        if value is None:
            return None
        return {
            "model": value.model,
            "risk_points": value.risk_points,
            "flags": list(value.flags),
            "summary": value.summary,
            "available": value.available,
            "error": value.error,
        }

    @staticmethod
    def _event_payload(row: Mapping[str, Any]) -> dict[str, Any] | None:
        raw = row.get("payload_json")
        if isinstance(raw, str):
            try:
                payload = json.loads(raw or "{}")
            except json.JSONDecodeError:
                return None
        elif isinstance(row.get("payload"), Mapping):
            payload = dict(row["payload"])
        else:
            return None
        return payload if isinstance(payload, dict) else None
