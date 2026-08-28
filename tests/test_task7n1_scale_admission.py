from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.automatic_memory.quality_gate import run_release_preflight, run_quality_gate, temporary_acceptance_roots
from src.automatic_memory.quality_evidence import EvidenceState, QualityEvidenceReadiness
from src.automatic_memory.scale_benchmark import (
    CORPUS_SHA256,
    QUESTIONS_SHA256,
    build_quality_run_id,
    readiness_from_envelope,
)


CODE_COMMIT = "a" * 40


def _readiness(*, production: str = "not_measured", context: str = "ready") -> dict[str, str]:
    values = {field: "ready" for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS}
    values["production_sentinel"] = production
    values["context_baseline"] = context
    for field in (*QualityEvidenceReadiness._MAC_FIELDS, "windows_release"):
        values[field] = "not_measured"
    return values


def _complete_payload() -> dict[str, object]:
    run_id = build_quality_run_id(CODE_COMMIT, CORPUS_SHA256, QUESTIONS_SHA256)
    return {
        "run_id": run_id,
        "code_commit": CODE_COMMIT,
        "fixture_hashes": {"corpus": CORPUS_SHA256, "questions": QUESTIONS_SHA256},
        "functional_status": "PASS",
        "phase_status": "BLOCKED",
        "production_pollution": None,
        "quality_evidence_readiness": _readiness(),
        "import_counts": {"expected_messages": 2, "imported_messages": 2},
        "role_order_counts": {"expected": 2, "matched": 2},
        "import_audit": {
            "expected_rows": 2, "actual_rows": 2,
            "missing_external_keys": [], "extra_external_keys": [],
            "stable_duplicates": {"source_records": 0, "conversation_records": 0, "message_records": 0, "memory_records": 0},
            "ordered_external_key_matches": 2, "role_matches": 2, "sequence_matches": 2,
            "timestamp_matches": 2, "content_hash_matches": 2, "source_matches": 2,
            "conversation_matches": 2, "intentional_content_hash_groups": [],
        },
        "promotion_outcomes": {"active": 2, "pending_owner_review": 0, "rejected": 0, "error": 0},
        "promotion_provenance": {
            "status": "ready", "expected": 2, "actual": 2,
            "links_expected": 2, "links_actual": 2, "missing_links": 0,
            "extra_links": 0, "duplicate_links": 0, "duplicate_records": 0,
        },
        "gateway_selection": {
            "status": "ready", "calls_completed": 100, "selector_calls": 100,
            "unknown": 0, "duplicates": 0,
        },
        "mcp_parity": {"status": "ready", "attempts": 100, "successes": 100, "strict_rate": 100.0},
        "semantic_degradation": {
            "status": "ready", "semantic": "degraded", "lexical": "available",
            "lexical_ids": ["m1"], "degraded_ids": ["m1"],
        },
        "corruption_isolation": {
            "status": "ready", "terminal_tasks": 2, "attempted": 2,
            "completed": 1, "failed": 1, "continued": 1, "retrievable": 1,
            "bad_source_messages": 0, "bad_source_leaks": 0,
            "queue_status_counts": {"completed": 1, "failed": 1},
        },
        "context_baseline": {
            "status": "ready", "baseline_chars": 1000, "rendered_chars": 50,
            "reduction": 95.0,
        },
        "measured_quality": {
            "status": "PASS", "mcp_attempts": 100, "mcp_successes": 100,
            "baseline_context_chars": 1000, "rendered_context_chars": 50,
            "context_reduction": 95.0,
        },
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_scale_loader_rejects_forged_ready_without_functional_details(tmp_path: Path) -> None:
    payload = _complete_payload()
    payload.pop("import_audit")
    payload.pop("promotion_provenance")
    payload.pop("semantic_degradation")
    payload.pop("corruption_isolation")
    payload["run_id"] = "forged-run"
    path = tmp_path / "quality.json"
    _write(path, payload)

    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        readiness_from_envelope(path)


def test_scale_loader_rejects_zero_baseline_when_not_measured(tmp_path: Path) -> None:
    payload = _complete_payload()
    payload["quality_evidence_readiness"] = _readiness(context="not_measured")
    payload["context_baseline"] = {"status": "not_measured", "baseline_chars": 0, "rendered_chars": 0, "reduction": 0.0}
    payload["measured_quality"] = {
        "status": "PASS", "mcp_attempts": 100, "mcp_successes": 100,
        "baseline_context_chars": None, "rendered_context_chars": None,
        "context_reduction": None,
    }
    path = tmp_path / "quality.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="BLOCKED_4R2_REQUIRED"):
        readiness_from_envelope(path)


def test_complete_consistent_envelope_reaches_scale_callback(tmp_path: Path) -> None:
    path = tmp_path / "quality.json"
    _write(path, _complete_payload())
    readiness = readiness_from_envelope(path)
    calls: list[str] = []
    run_release_preflight(
        readiness,
        prepare_scale_environment=lambda: calls.append("environment"),
        run_scale_command=lambda: calls.append("command"),
    )
    assert readiness.scale_ready
    assert calls == ["environment", "command"]


def test_unmeasured_runtime_baseline_is_nullable_not_zero(tmp_path: Path) -> None:
    corpus = Path(__file__).parent / "evaluation" / "fixtures" / "automatic_memory_corpus.jsonl"
    questions = Path(__file__).parent / "evaluation" / "fixtures" / "automatic_memory_questions.jsonl"
    with temporary_acceptance_roots(base_directory=tmp_path) as roots:
        run_quality_gate(corpus, questions, output_path=roots.output_root / "quality.json", acceptance_roots=roots)
        payload = json.loads((roots.output_root / "quality.json").read_text(encoding="utf-8"))
    assert payload["context_baseline"]["status"] == "not_measured"
    assert payload["context_baseline"]["baseline_chars"] is None
    assert payload["context_baseline"]["reduction"] is None
    assert payload["measured_quality"]["baseline_context_chars"] is None
    assert payload["measured_quality"]["context_reduction"] is None
