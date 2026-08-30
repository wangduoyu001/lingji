from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.automatic_memory.quality_evidence import CanonicalFunctionalEvidence


def _canonical() -> dict[str, object]:
    return CanonicalFunctionalEvidence.complete_for_test().to_mapping()


def _envelope() -> dict[str, object]:
    payload = _canonical()
    payload["evidence_details"] = copy.deepcopy(payload)
    return payload


@pytest.mark.parametrize("mutate", [
    lambda payload: payload.update(unknown_top_level=1),
    lambda payload: payload["import_audit"]["stable_duplicates"].update(unknown_nested=1),
    lambda payload: payload.__setitem__("run_id", ""),
    lambda payload: payload.__setitem__("code_commit", ""),
    lambda payload: payload["fixture_hashes"].__setitem__("corpus", ""),
    lambda payload: payload["mcp_parity"].__setitem__("attempts", True),
    lambda payload: payload["mcp_parity"].__setitem__("strict_rate", float("nan")),
    lambda payload: payload["mcp_parity"].__setitem__("strict_rate", float("inf")),
])
def test_canonical_loader_rejects_hostile_mutations(mutate):
    payload = _canonical()
    mutate(payload)
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(payload)


def test_canonical_loader_accepts_only_exact_round_trip():
    artifact = CanonicalFunctionalEvidence.complete_for_test()
    assert CanonicalFunctionalEvidence.from_mapping(artifact.to_mapping()) == artifact


@pytest.mark.parametrize("mutate", [
    lambda payload: payload["import_audit"].__setitem__("actual_rows", 1),
    lambda payload: payload["evidence_details"]["promotion_outcomes"].__setitem__("active", 1),
])
def test_runner_envelope_rejects_contradictory_views(tmp_path: Path, mutate):
    from src.automatic_memory.scale_benchmark import readiness_from_envelope

    payload = _envelope()
    mutate(payload)
    path = tmp_path / "quality.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        readiness_from_envelope(path)


def test_runner_envelope_rejects_unknown_top_level_field(tmp_path: Path):
    from src.automatic_memory.scale_benchmark import readiness_from_envelope

    payload = _envelope()
    payload["unknown_top_level"] = 1
    path = tmp_path / "quality.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        readiness_from_envelope(path)


def test_published_canonical_artifact_retains_code_commit(tmp_path: Path):
    from src.automatic_memory.quality_evidence import QualityRunEnvelope, QualityEvidenceReadiness, EvidenceState
    from src.automatic_memory.quality_gate import publish_quality_envelope

    canonical = _canonical()
    values = {field: EvidenceState.READY for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS}
    values.update({field: EvidenceState.NOT_MEASURED for field in QualityEvidenceReadiness._MAC_FIELDS})
    values["windows_release"] = EvidenceState.NOT_MEASURED
    envelope = QualityRunEnvelope(
        QualityEvidenceReadiness(**values), None, None, "PASS", "BLOCKED", "NOT_EVALUATED", (),
        evidence_details=canonical, run_id=canonical["run_id"], fixture_hashes=canonical["fixture_hashes"],
        quality_evidence_readiness=canonical["quality_evidence_readiness"],
    )
    output = tmp_path / "quality.json"
    publish_quality_envelope(envelope, repository_output_path=output)
    assert json.loads(output.read_text(encoding="utf-8"))["code_commit"] == canonical["code_commit"]


def _promotion_payload():
    return {
        "outcomes": [
            {"memory_id": "m-active", "category": "low-risk-user", "expected_status": "pending_owner_review", "status": "active"},
            {"memory_id": "m-pending", "category": "high-risk", "expected_status": "pending_owner_review", "status": "pending_owner_review"},
        ],
        "projection_ids": ["m-active"],
        "audit_ids": ["m-active", "m-pending"],
        "memory_link_keys": [("msg-active", "m-active")],
    }


@pytest.mark.parametrize("mutate", [
    lambda payload: payload["outcomes"][0].__setitem__("memory_id", ""),
    lambda payload: payload["outcomes"][0].__setitem__("memory_id", "   "),
    lambda payload: payload["outcomes"].append(dict(payload["outcomes"][0])),
    lambda payload: payload["projection_ids"].append("m-active"),
    lambda payload: payload["audit_ids"].append("m-active"),
    lambda payload: payload["memory_link_keys"].append(("msg-active", "m-active")),
    lambda payload: payload["memory_link_keys"].append(("msg-pending", "m-pending")),
    lambda payload: payload["memory_link_keys"].append(("msg-orphan", "m-orphan")),
    lambda payload: payload["audit_ids"].remove("m-pending"),
    lambda payload: payload["audit_ids"].append("m-extra"),
])
def test_promotion_identity_and_links_fail_closed(mutate):
    from src.automatic_memory.quality_promotion import validate_promotion_measurement

    payload = _promotion_payload()
    mutate(payload)
    with pytest.raises(ValueError, match="promotion_provenance"):
        validate_promotion_measurement(payload)


def test_promotion_unique_active_link_and_protected_pending_pass():
    from src.automatic_memory.quality_promotion import validate_promotion_measurement

    result = validate_promotion_measurement(_promotion_payload())
    assert result["status"] == "ready"
    assert result["active"] == 1
    assert result["pending"] == 1


def test_measurement_scans_orphan_links_outside_candidate_filter(monkeypatch):
    import src.automatic_memory.quality_promotion as promotion
    from types import SimpleNamespace

    class FakeService:
        def __init__(self, **_kwargs):
            pass

        def evaluate(self, candidate):
            return {
                "status": "pending_owner_review",
                "candidate_id": candidate.memory_id,
                "decision_id": "decision-1",
                "reason_codes": ["automatic_activation_quarantined"],
            }

    monkeypatch.setattr(promotion, "AutoMemoryPromotionService", FakeService)
    record = SimpleNamespace(
        fact_id="fact-1", memory_kind="stable_preference", risk="low", privacy="synthetic",
        authority="owner-confirmed", lifecycle="active", project_id="project-lingji",
        agent_scope=("agent-synthetic",), topic_key="topic", content="content",
        content_hash="hash-1", occurred_at="2026-01-01T00:00:00Z",
    )
    message_map = {"fact-1": {"message_id": "message-1", "content_hash": "hash-1"}}
    memory_db = SimpleNamespace(list_derived_projection_identity_rows=lambda: [])
    read_model = SimpleNamespace(message_links=lambda _message_id: [{"memory_id": "orphan-external"}])
    state_db = SimpleNamespace(recent_events=lambda **_kwargs: [{
        "event_type": "memory_promotion_decision",
        "payload_json": json.dumps({"candidate_id": "LJ-MEM-1"}),
    }])
    result = promotion.measure_promotion_fixtures([record], message_map, memory_db, read_model, state_db)
    assert result.status == "failed"
    assert result.provenance["status"] == "failed"


def _activation_outcomes():
    return [
        {"category": category, "expected_category": category,
         "expected_status": "pending_owner_review", "status": "pending_owner_review",
         "persisted_status": "pending_owner_review",
         "reason_codes": ["automatic_activation_quarantined"]}
        for category in ("core/protected", "high-risk", "authority-conflict", "assistant-only", "low-risk-user")
    ]


def test_activation_measurement_uses_actual_status_category_and_reason():
    from src.automatic_memory.quality_promotion import activation_measurement

    result = activation_measurement(_activation_outcomes())
    assert result == {"status": "not_applicable", "correct": None, "total": None, "accuracy": None}


@pytest.mark.parametrize("mutate", [
    lambda outcomes: outcomes[0].__setitem__("persisted_status", "active"),
    lambda outcomes: outcomes[1].__setitem__("category", "low-risk-user"),
    lambda outcomes: outcomes[2].__setitem__("reason_codes", []),
    lambda outcomes: outcomes[3].__setitem__("actual_status", "active"),
    lambda outcomes: outcomes[3].__setitem__("status", "error"),
])
def test_activation_measurement_rejects_false_or_incomplete_truth(mutate):
    from src.automatic_memory.quality_promotion import activation_measurement

    outcomes = _activation_outcomes()
    mutate(outcomes)
    with pytest.raises(ValueError, match="activation"):
        activation_measurement(outcomes)
