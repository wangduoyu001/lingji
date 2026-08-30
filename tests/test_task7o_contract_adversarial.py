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
        {"category": category, "fixture_category": category, "expected_category": category,
         "expected_status": "pending_owner_review", "status": "pending_owner_review",
         "service_status": "pending_owner_review", "persisted_status": "pending_owner_review",
         "durable_status": "pending_owner_review",
         "service_category": category, "durable_category": category,
         "reason_codes": ["automatic_activation_quarantined"],
         "service_reason_codes": ["automatic_activation_quarantined"],
         "durable_reason_codes": ["automatic_activation_quarantined"]}
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


@pytest.mark.parametrize("mutate", [
    lambda payload: payload["import_audit"]["intentional_content_hash_groups"].append({
        "content_hash": "",
        "member_external_keys": [{
            "source_external_id": "source-1",
            "conversation_external_id": "conversation-1",
            "message_external_id": "message-1",
        }],
    }),
    lambda payload: payload["import_audit"]["intentional_content_hash_groups"].append({
        "content_hash": "hash-1",
        "member_external_keys": [{
            "source_external_id": "   ",
            "conversation_external_id": "conversation-1",
            "message_external_id": "message-1",
        }],
    }),
    lambda payload: payload["import_audit"]["intentional_content_hash_groups"].append({
        "content_hash": "hash-1",
        "member_external_keys": [{
            "source_external_id": "source-1",
            "conversation_external_id": "conversation-1",
            "message_external_id": "message-1",
        }] * 2,
    }),
])
def test_canonical_loader_rejects_blank_or_duplicate_hash_group_members(mutate):
    payload = _canonical()
    mutate(payload)
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(payload)


def test_runner_projection_comparison_is_strict_about_bool_vs_integer():
    payload = _envelope()
    payload["promotion_outcomes"]["active"] = True
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_runner_payload(payload)


@pytest.mark.parametrize("mutate", [
    lambda payload: payload.__setitem__("run_id", "wrong"),
    lambda payload: payload.__setitem__("code_commit", "b" * 40),
    lambda payload: payload["fixture_hashes"].__setitem__("corpus", "g" * 64),
    lambda payload: payload["fixture_hashes"].__setitem__("corpus", "d" * 64),
])
def test_canonical_loader_validates_identity_format_and_consistency(mutate):
    payload = _canonical()
    mutate(payload)
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(payload)


def _measurement_record():
    from types import SimpleNamespace

    return SimpleNamespace(
        fact_id="fact-1", memory_kind="stable_preference", risk="low", privacy="synthetic",
        authority="owner-confirmed", lifecycle="active", project_id="project-lingji",
        agent_scope=("agent-synthetic",), topic_key="topic", content="content",
        content_hash="hash-1", occurred_at="2026-01-01T00:00:00Z",
    )


class _MeasurementService:
    def __init__(self, **_kwargs):
        pass

    def evaluate(self, candidate):
        return {
            "status": "pending_owner_review",
            "candidate_id": candidate.memory_id,
            "decision_id": "decision-1",
            "reason_codes": ["confidence_below_threshold"],
        }


def _measurement_stores(*, message_id="message-1", projection_rows=(), event_payload=None, links=()):
    import src.automatic_memory.quality_promotion as promotion
    from types import SimpleNamespace

    memory_db = SimpleNamespace(list_derived_projection_identity_rows=lambda: list(projection_rows))
    read_model = SimpleNamespace(message_links=lambda _message_id: list(links))
    event_payload = event_payload or {
        "candidate_id": "LJ-MEM-1", "decision_id": "decision-1", "memory_id": "LJ-MEM-1",
        "status": "pending_owner_review", "reason_codes": ["confidence_below_threshold"],
        "category": "low-risk-user",
    }
    state_db = SimpleNamespace(recent_events=lambda **_kwargs: [{
        "event_type": "memory_promotion_decision",
        "payload_json": json.dumps(event_payload),
    }])
    message_map = {"fact-1": {"message_id": message_id, "content_hash": "hash-1", "promotion_memory_id": "LJ-MEM-1"}}
    return promotion, message_map, memory_db, read_model, state_db


def test_measurement_does_not_filter_orphan_projection_rows(monkeypatch):
    promotion, message_map, memory_db, read_model, state_db = _measurement_stores(
        projection_rows=({"memory_id": "orphan"},),
        links=(),
    )
    monkeypatch.setattr(promotion, "AutoMemoryPromotionService", _MeasurementService)
    result = promotion.measure_promotion_fixtures(
        [_measurement_record()], message_map, memory_db, read_model, state_db,
    )
    assert result.status == "failed"
    assert result.provenance["status"] == "failed"


def test_measurement_surfaces_empty_imported_message_relationship_identity(monkeypatch):
    promotion, message_map, memory_db, read_model, state_db = _measurement_stores(
        links=({"message_id": "", "memory_id": "LJ-MEM-1"},),
    )
    monkeypatch.setattr(promotion, "AutoMemoryPromotionService", _MeasurementService)
    result = promotion.measure_promotion_fixtures(
        [_measurement_record()], message_map, memory_db, read_model, state_db,
    )
    assert result.status == "failed"
    assert result.provenance["status"] == "failed"


def test_measurement_surfaces_malformed_message_relationship_identity(monkeypatch):
    promotion, message_map, memory_db, read_model, state_db = _measurement_stores(
        projection_rows=({"memory_id": "LJ-MEM-1"},),
        event_payload={
            "candidate_id": "LJ-MEM-1", "decision_id": "decision-1", "memory_id": "LJ-MEM-1",
            "status": "active", "reason_codes": [], "category": "low-risk-user",
        },
        links=({"message_id": "", "memory_id": "LJ-MEM-1"},),
    )

    class ActiveService(_MeasurementService):
        def evaluate(self, candidate):
            return {
                "status": "active", "candidate_id": candidate.memory_id,
                "decision_id": "decision-1", "reason_codes": [],
            }

    monkeypatch.setattr(promotion, "AutoMemoryPromotionService", ActiveService)
    result = promotion.measure_promotion_fixtures(
        [_measurement_record()], message_map, memory_db, read_model, state_db,
    )
    assert result.status == "failed"
    assert result.provenance["status"] == "failed"


@pytest.mark.parametrize("message", [
    {"message_id": "message-1", "content_hash": "hash-1"},
    {"message_id": "message-1", "content_hash": "hash-1", "promotion_memory_id": ""},
])
def test_measurement_rejects_missing_promotion_memory_identity(monkeypatch, message):
    promotion, _message_map, memory_db, read_model, state_db = _measurement_stores(links=())
    monkeypatch.setattr(promotion, "AutoMemoryPromotionService", _MeasurementService)
    result = promotion.measure_promotion_fixtures(
        [_measurement_record()], {"fact-1": message}, memory_db, read_model, state_db,
    )
    assert result.status == "failed"
    assert result.provenance["status"] == "failed"


def test_measurement_rejects_service_result_without_candidate_identity(monkeypatch):
    promotion, message_map, memory_db, read_model, state_db = _measurement_stores(links=())

    class MissingCandidateService(_MeasurementService):
        def evaluate(self, _candidate):
            return {"status": "pending_owner_review", "decision_id": "decision-1", "reason_codes": ["confidence_below_threshold"]}

    monkeypatch.setattr(promotion, "AutoMemoryPromotionService", MissingCandidateService)
    result = promotion.measure_promotion_fixtures(
        [_measurement_record()], message_map, memory_db, read_model, state_db,
    )
    assert result.status == "failed"
    assert result.provenance["status"] == "failed"


def test_activation_rejects_self_consistent_wrong_category():
    from src.automatic_memory.quality_promotion import activation_measurement

    outcomes = _activation_outcomes()
    outcomes[1]["category"] = outcomes[1]["expected_category"] = "low-risk-user"
    with pytest.raises(ValueError, match="activation"):
        activation_measurement(outcomes)


def test_activation_rejects_arbitrary_reason_code():
    from src.automatic_memory.quality_promotion import activation_measurement

    outcomes = _activation_outcomes()
    outcomes[0]["reason_codes"] = ["other"]
    with pytest.raises(ValueError, match="activation"):
        activation_measurement(outcomes)


def test_measurement_rejects_state_db_truth_disagreeing_with_service(monkeypatch):
    promotion, message_map, memory_db, read_model, state_db = _measurement_stores(
        event_payload={
            "candidate_id": "LJ-MEM-1", "decision_id": "decision-1", "memory_id": "LJ-MEM-1",
            "status": "error", "reason_codes": ["promotion_persist_failed"],
            "category": "low-risk-user",
        },
        links=(),
    )
    monkeypatch.setattr(promotion, "AutoMemoryPromotionService", _MeasurementService)
    result = promotion.measure_promotion_fixtures(
        [_measurement_record()], message_map, memory_db, read_model, state_db,
    )
    assert result.status == "failed"
    assert result.provenance["status"] == "failed"


def test_measurement_rejects_state_db_category_disagreeing_with_service(monkeypatch):
    promotion, message_map, memory_db, read_model, state_db = _measurement_stores(
        event_payload={
            "candidate_id": "LJ-MEM-1", "decision_id": "decision-1", "memory_id": "LJ-MEM-1",
            "status": "pending_owner_review", "reason_codes": ["confidence_below_threshold"],
            "category": "high-risk",
        },
        links=(),
    )

    class CategorizedService(_MeasurementService):
        def evaluate(self, candidate):
            result = super().evaluate(candidate)
            result["category"] = "low-risk-user"
            return result

    monkeypatch.setattr(promotion, "AutoMemoryPromotionService", CategorizedService)
    result = promotion.measure_promotion_fixtures(
        [_measurement_record()], message_map, memory_db, read_model, state_db,
    )
    assert result.status == "failed"
    assert result.provenance["status"] == "failed"


def test_canonical_promotion_provenance_requires_per_outcome_truth():
    payload = _canonical()
    assert "outcomes" in payload["promotion_provenance"]


def test_canonical_per_outcome_truth_rejects_missing_durable_fields():
    payload = _canonical()
    payload["promotion_provenance"]["outcomes"] = [{
        "memory_id": "m1", "decision_id": "d1", "category": "low-risk-user",
        "expected_category": "low-risk-user", "expected_status": "pending_owner_review",
        "service_status": "pending_owner_review", "durable_status": "pending_owner_review",
        "service_category": "low-risk-user", "durable_category": "low-risk-user",
        "service_reason_codes": ["confidence_below_threshold"],
        "durable_reason_codes": ["confidence_below_threshold"],
    }]
    payload["promotion_provenance"]["outcomes"][0].pop("durable_status", None)
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        CanonicalFunctionalEvidence.from_mapping(payload)
