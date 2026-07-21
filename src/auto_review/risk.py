from __future__ import annotations

from .models import RiskLevel, RuleFinding


def calculate_risk(findings: tuple[RuleFinding, ...], *, external_points: int = 0) -> tuple[int, RiskLevel]:
    """Return a monotonic risk score. External reviewers may only add points."""

    score = max(int(external_points), 0)
    score += sum(max(int(item.risk_points), 0) for item in findings)
    score = min(score, 100)
    if score >= 90:
        return score, RiskLevel.CRITICAL
    if score >= 60:
        return score, RiskLevel.HIGH
    if score >= 25:
        return score, RiskLevel.MEDIUM
    return score, RiskLevel.LOW
