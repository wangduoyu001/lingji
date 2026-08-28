from __future__ import annotations

from dataclasses import replace

import pytest

from src.automatic_memory.evaluation import load_corpus


def _record(**changes):
    record = load_corpus("tests/evaluation/fixtures/automatic_memory_corpus.jsonl")[0]
    return replace(record, **changes)


def test_promotion_category_comes_from_explicit_fixture_fields():
    from src.automatic_memory.quality_promotion import promotion_category

    assert promotion_category(_record(memory_kind="protected_candidate", risk="high")) == "core/protected"
    assert promotion_category(_record(memory_kind="authority_conflict", authority="assistant-suggestion")) == "authority-conflict"
    assert promotion_category(_record(authority="assistant-suggestion")) == "assistant-only"
    assert promotion_category(_record()) == "low-risk-user"


def test_promotion_measurement_fails_closed_for_invalid_outcomes():
    from src.automatic_memory.quality_promotion import validate_promotion_measurement

    with pytest.raises(ValueError, match="promotion_provenance"):
        validate_promotion_measurement({
            "outcomes": [{"category": "core/protected", "status": "active", "memory_id": "m"}],
            "projection_ids": ["m"],
            "audit_ids": ["m"],
            "memory_link_keys": [],
        })


def test_promotion_measurement_rejects_duplicate_and_orphan_evidence():
    from src.automatic_memory.quality_promotion import validate_promotion_measurement

    with pytest.raises(ValueError, match="duplicate|missing|extra"):
        validate_promotion_measurement({
            "outcomes": [
                {"category": "low-risk-user", "status": "active", "memory_id": "m"},
                {"category": "low-risk-user", "status": "active", "memory_id": "m"},
            ],
            "projection_ids": ["m", "orphan"],
            "audit_ids": ["m"],
            "memory_link_keys": [("msg", "m"), ("msg", "m")],
        })


def test_quality_gate_exports_scale_helpers_from_single_module():
    import src.automatic_memory.quality_gate as quality_gate
    import src.automatic_memory.scale_benchmark as scale_benchmark

    assert quality_gate.generate_100k_history is scale_benchmark.generate_history_fixture
