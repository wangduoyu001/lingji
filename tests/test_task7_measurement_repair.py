from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.automatic_memory.quality_degradation import (
    MCPParityMeasurement,
    measure_context_baseline,
    measure_mcp_parity,
)
from src.automatic_memory.quality_evidence import (
    EvidenceState,
    QualityEvidenceReadiness,
    cleanup_inventory_before_delete,
    cleanup_inventory_after_delete,
    finalize_quality_envelope,
)
from src.automatic_memory.quality_gate import (
    QualityScaleBlockedError,
    generate_100k_history,
    load_quality_readiness,
    run_100k_benchmark,
)


def _readiness(**overrides: EvidenceState) -> QualityEvidenceReadiness:
    values = {field: EvidenceState.READY for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS}
    values.update({field: EvidenceState.NOT_MEASURED for field in QualityEvidenceReadiness._MAC_FIELDS})
    values["windows_release"] = EvidenceState.NOT_MEASURED
    values.update(overrides)
    return QualityEvidenceReadiness(**values)


def test_production_unavailable_is_nullable_and_never_enters_frozen_report() -> None:
    readiness = _readiness(production_sentinel=EvidenceState.NOT_MEASURED)
    envelope = finalize_quality_envelope(
        readiness=readiness,
        production_pollution=None,
        evaluation_report=None,
        acceptance_gate=object(),
        blocked_reasons=("PRODUCTION_NOT_MEASURED",),
    )
    assert envelope.production_pollution is None
    assert envelope.evaluation_report is None
    assert envelope.functional_status == "PASS"
    assert envelope.phase_status == envelope.windows_status == "BLOCKED"


def test_cleanup_inventory_captures_machine_counts_and_post_delete_state(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.json").write_text("{}", encoding="utf-8")
    (root / "nested").mkdir()
    (root / "nested" / "b.bin").write_bytes(b"b")
    before = cleanup_inventory_before_delete(root)
    assert before["file_count"] == 2
    assert before["directory_count"] == 1
    root.rename(tmp_path / "removed")
    after = cleanup_inventory_after_delete(root)
    assert after["root_exists"] is False
    assert after["remaining_count"] == 0


def test_mcp_parity_requires_complete_identity_and_bounds() -> None:
    section = {
        "kind": "structured_message_evidence", "memory_id": "m1", "source_id": "s",
        "conversation_id": "c", "message_id": "m", "content_hash": "h",
        "fact_id": "f", "citation_id": "cit", "scope": "project-lingji",
        "lifecycle": "active", "query_mode": "current",
    }
    gateway = {"sections": [section], "used_chars": 10, "max_chars": 100,
               "query_mode": "current", "scope": "project-lingji", "lifecycle": "active"}
    mcp = json.loads(json.dumps(gateway))
    result = measure_mcp_parity(gateway, mcp)
    assert isinstance(result, MCPParityMeasurement)
    assert result.success is True
    mcp["sections"][0]["message_id"] = "other"
    assert measure_mcp_parity(gateway, mcp).success is False
    assert measure_mcp_parity({"sections": [], "used_chars": 0, "max_chars": 100},
                               {"sections": [], "used_chars": 0, "max_chars": 100}).success is False


def test_baseline_rejects_bounded_context_as_baseline() -> None:
    with pytest.raises(ValueError, match="selection-before-bound"):
        measure_context_baseline([{"memory_id": "m", "text": "x"}],
                                 bounded_pack={"used_chars": 1, "max_chars": 100})
    evidence = measure_context_baseline(
        [{"memory_id": "m", "text": "x", "citation": {"message_id": "msg"}}],
        bounded_pack=None,
    )
    assert evidence.baseline_chars > 1


def test_scale_readiness_is_loaded_from_persisted_envelope(tmp_path: Path) -> None:
    path = tmp_path / "quality.json"
    fields = QualityEvidenceReadiness._FUNCTIONAL_FIELDS + QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",)
    readiness = {
        field: ("ready" if field != "production_sentinel" and field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS else "not_measured")
        for field in fields
    }
    path.write_text(json.dumps({
        "run_id": "quality-test", "fixture_hashes": {"corpus": "c", "questions": "q"},
        "functional_status": "PASS", "phase_status": "NOT_EVALUATED",
        "quality_evidence_readiness": readiness,
        "measured_quality": {"status": "PASS", "mcp_successes": 100, "mcp_attempts": 100},
        "context_baseline": {"status": "ready", "baseline_chars": 100},
    }), encoding="utf-8")
    assert load_quality_readiness(path).scale_ready
    path.write_text(json.dumps({"quality_evidence_readiness": {}}), encoding="utf-8")
    with pytest.raises(QualityScaleBlockedError, match="BLOCKED_4R2_REQUIRED"):
        load_quality_readiness(path)


def test_scale_fixture_default_seed_is_stable_across_generation(tmp_path: Path) -> None:
    first = generate_100k_history(tmp_path / "one.jsonl", count=100, seed=41041)
    second = generate_100k_history(tmp_path / "two.jsonl", count=100, seed=41041)
    assert first["fixture_sha256"] == second["fixture_sha256"]
    assert first["seed"] == 41041
