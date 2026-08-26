from __future__ import annotations

import math
from dataclasses import replace

import pytest

from src.automatic_memory.evaluation import AutomaticMemoryAcceptanceGate, EvaluationReport


def passing_report(**changes: object) -> EvaluationReport:
    values: dict[str, object] = {
        "answered_questions": 100,
        "imported_messages": 100,
        "expected_messages": 100,
        "ordered_role_matches": 100,
        "expected_ordered_roles": 100,
        "valid_fact_hits": 90,
        "valid_fact_total": 100,
        "citation_hits": 95,
        "citation_total": 100,
        "automatic_activation_correct": 95,
        "automatic_activation_total": 100,
        "valid_fact_recall": 90.0,
        "citation_accuracy": 95.0,
        "automatic_activation_accuracy": 95.0,
        "protected_false_promotions": 0,
        "stale_current_leaks": 0,
        "duplicate_records": 0,
        "baseline_context_chars": 1000,
        "rendered_context_chars": 100,
        "context_reduction": 90.0,
        "mcp_successes": 95,
        "mcp_attempts": 100,
        "mcp_success_rate": 95.0,
        "production_pollution": 0,
        "owner_review_success": 100.0,
        "reboot_recovery": 100.0,
        "blocked_reasons": (),
    }
    values.update(changes)
    return EvaluationReport(**values)


def test_gate_passes_only_when_all_measured_thresholds_and_external_evidence_exist() -> None:
    assert AutomaticMemoryAcceptanceGate.evaluate(passing_report()) == "PASS"


@pytest.mark.parametrize(
    "field,value",
    [
        ("valid_fact_recall", 89.999),
        ("citation_accuracy", 94.999),
        ("automatic_activation_accuracy", 94.999),
        ("mcp_success_rate", 94.999),
        ("context_reduction", 89.999),
        ("protected_false_promotions", 1),
        ("stale_current_leaks", 1),
        ("duplicate_records", 1),
        ("production_pollution", 1),
        ("answered_questions", 99),
        ("imported_messages", 99),
        ("ordered_role_matches", 99),
        ("valid_fact_total", 0),
        ("citation_total", 0),
        ("automatic_activation_total", 0),
        ("mcp_attempts", 0),
        ("owner_review_success", 99.0),
        ("reboot_recovery", 99.0),
        ("valid_fact_recall", math.nan),
    ],
)
def test_gate_returns_fail_for_any_measured_failure(field: str, value: object) -> None:
    report = passing_report(**{field: value})
    assert AutomaticMemoryAcceptanceGate.evaluate(report) == "FAIL"


@pytest.mark.parametrize("field", ["owner_review_success", "reboot_recovery"])
def test_gate_blocks_when_external_evidence_is_missing(field: str) -> None:
    assert AutomaticMemoryAcceptanceGate.evaluate(passing_report(**{field: None})) == "BLOCKED"


def test_measured_failure_has_precedence_over_blocked_evidence() -> None:
    report = passing_report(valid_fact_recall=89.999, owner_review_success=None)
    assert AutomaticMemoryAcceptanceGate.evaluate(report) == "FAIL"


def test_explicit_block_reason_has_blocked_result_after_measured_pass() -> None:
    assert AutomaticMemoryAcceptanceGate.evaluate(
        passing_report(blocked_reasons=("mac evidence missing",))
    ) == "BLOCKED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("answered_questions", True),
        ("imported_messages", 100.0),
        ("valid_fact_hits", -1),
        ("valid_fact_hits", 101),
        ("citation_hits", 101),
        ("automatic_activation_correct", 101),
        ("mcp_successes", 101),
        ("expected_messages", True),
        ("baseline_context_chars", 0),
        ("rendered_context_chars", 1001),
    ],
)
def test_gate_fails_closed_for_invalid_raw_counters(field: str, value: object) -> None:
    assert AutomaticMemoryAcceptanceGate.evaluate(passing_report(**{field: value})) == "FAIL"


@pytest.mark.parametrize(
    "field,value",
    [
        ("valid_fact_recall", math.nan),
        ("citation_accuracy", math.inf),
        ("automatic_activation_accuracy", -1.0),
        ("mcp_success_rate", 100.001),
        ("context_reduction", True),
        ("owner_review_success", math.inf),
        ("reboot_recovery", -0.001),
    ],
)
def test_gate_fails_closed_for_nonfinite_or_out_of_range_percentages(field: str, value: object) -> None:
    assert AutomaticMemoryAcceptanceGate.evaluate(passing_report(**{field: value})) == "FAIL"


def test_gate_does_not_accept_a_forged_context_reduction() -> None:
    report = passing_report(baseline_context_chars=1000, rendered_context_chars=500, context_reduction=90.0)
    assert AutomaticMemoryAcceptanceGate.evaluate(report) == "FAIL"
