from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.automatic_memory.quality_degradation import measure_mcp_parity
from src.automatic_memory.quality_evidence import EvidenceState, QualityEvidenceReadiness
from src.automatic_memory.scale_benchmark import readiness_from_envelope
from src.retrieval.context_pack import ContextPackBuilder, ContextPackRequest


def _readiness(**overrides: EvidenceState) -> dict[str, str]:
    fields = (
        *QualityEvidenceReadiness._FUNCTIONAL_FIELDS,
        *QualityEvidenceReadiness._MAC_FIELDS,
        "windows_release",
    )
    values = {field: "not_measured" for field in fields}
    for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS:
        values[field] = "ready"
    values.update({key: value.value for key, value in overrides.items()})
    return values


def test_mcp_empty_pack_has_retrieval_empty_reason_and_schema_mismatch_is_distinct() -> None:
    empty = {"sections": [], "used_chars": 0, "max_chars": 100, "query": "q", "query_mode": "current"}
    result = measure_mcp_parity(empty, dict(empty))
    assert result.success is False
    assert result.reason == "retrieval_empty"
    section = {
        "kind": "structured_message_evidence", "memory_id": "m", "fact_id": "f", "citation_id": "c",
        "source_id": "s", "conversation_id": "cv", "message_id": "msg", "content_hash": "h",
    }
    good = {"sections": [section], "used_chars": 1, "max_chars": 100, "query": "q", "query_mode": "current"}
    bad = json.loads(json.dumps(good)); bad["sections"][0]["message_id"] = "other"
    assert measure_mcp_parity(good, bad).reason == "schema_mismatch"


def test_readiness_loader_rejects_missing_or_contradictory_run_contract(tmp_path: Path) -> None:
    path = tmp_path / "quality.json"
    path.write_text(json.dumps({"quality_evidence_readiness": _readiness()}), encoding="utf-8")
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        readiness_from_envelope(path)
    payload = {
        "run_id": "run-a", "fixture_hashes": {"corpus": "c", "questions": "q"},
        "functional_status": "PASS", "phase_status": "NOT_EVALUATED",
        "measured_quality": {"status": "PASS", "mcp_successes": 100, "mcp_attempts": 100},
        "context_baseline": {"status": "ready", "baseline_chars": 100},
        "quality_evidence_readiness": _readiness(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert readiness_from_envelope(path).scale_ready
    payload["functional_status"] = "FAIL"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        readiness_from_envelope(path)


def test_context_builder_exposes_unbounded_candidates_without_changing_build() -> None:
    class Database:
        revision = 1
        def list_core_memories(self, **kwargs): return []
        def fetch_memory(self, memory_id, include_chunks=True):
            return {"memory_id": memory_id, "title": "title", "content": "full content", "chunks": [{"text": "full content", "start_line": 1, "end_line": 1}], "memory_type": "knowledge"}

    class Retriever:
        semantic_provider = None
        def search_with_diagnostics(self, query, limit, filters):
            return {"results": [{"memory_id": "m1", "title": "title", "snippet": "snippet"}], "diagnostics": {}}

    builder = ContextPackBuilder(Database(), Retriever())
    request = ContextPackRequest(agent_id="a", query="q", include_core=False, max_chars=1000)
    pack = builder.build(request)
    observation = builder.observe_candidates(request)
    assert observation["sections"]
    assert observation["sections"][0]["text"] == "full content"
    assert pack["sections"] == observation["sections"]
    assert pack["used_chars"] == len(pack["markdown"])
