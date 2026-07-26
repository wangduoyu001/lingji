from __future__ import annotations

from pathlib import Path

import pytest

from src.auto_review import AutoReviewMode, DeterministicAutoReviewEvaluator, ReviewCandidate, ReviewContext
from src.config import Settings
from src.extraction.idempotency import build_extraction_idempotency_key
from src.extraction.queue import SQLiteExtractionQueue


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


def test_runtime_and_auto_review_defaults_survive_combined_merge():
    settings = Settings(_env_file=None)

    assert settings.embed_model == "bge-m3"
    assert settings.fallback_embed_model == "nomic-embed-text"
    assert settings.embed_model != settings.fallback_embed_model
    assert settings.auto_review_mode == "OFF"
    assert settings.auto_review_ai_enabled is False
    assert settings.control_api_port == 8766


def test_auto_review_remains_shadow_only_after_combined_merge():
    evaluator = DeterministicAutoReviewEvaluator()
    candidate = ReviewCandidate(
        memory_id="LJ-INTEGRATION-1",
        title="Integration candidate",
        content="Evidence-backed integration candidate.",
        memory_type="knowledge",
        source_refs=("source-1",),
    )

    decision = evaluator.evaluate(
        candidate,
        ReviewContext(mode=AutoReviewMode.SHADOW, evidence_sufficient=True),
    )

    assert decision.mutation_performed is False
    with pytest.raises(ValueError, match="ACTIVE"):
        evaluator.evaluate(
            candidate,
            ReviewContext(mode=AutoReviewMode.ACTIVE, evidence_sufficient=True),
        )


def test_control_api_registers_shadow_routes_on_existing_8766_app():
    runner = read("run_control_api.py")
    routes = read("src/control/auto_review_api.py")

    assert "register_auto_review_routes(app, settings, service, token=token)" in runner
    assert "settings.control_api_port" in runner
    for endpoint in (
        "/api/auto-review/status",
        "/api/auto-review/decisions",
        "/api/auto-review/metrics",
        "/api/auto-review/evaluate/{subject_id}",
        "/api/auto-review/feedback",
        "/api/auto-review/audit/verify",
    ):
        assert endpoint in routes
    for forbidden in (
        "/api/auto-review/approve",
        "/api/auto-review/reject",
        "/api/auto-review/delete",
        "/api/auto-review/execute",
        "/api/auto-review/active",
    ):
        assert forbidden not in routes


def test_mcp_work_report_and_web_capture_remain_queue_first():
    source = read("src/mcp_server.py")

    assert "def submit_codex_work_report(" in source
    assert "def capture_web_source(" in source
    assert source.count("enqueue_durable_submission(") >= 2
    assert source.count("process_now: bool = False") >= 3
    assert 'adapter_name="codex_work_report"' in source
    assert 'adapter_name="web_capture"' in source


def test_canonical_idempotency_contract_is_shared_with_queue():
    material = {
        "source_type": "web",
        "adapter_name": "web_capture",
        "adapter_version": "1",
        "input_identity": {"kind": "payload"},
        "payload": {"url": "https://example.test", "title": "Example"},
        "effective_options": {"allow_network_fetch": False},
    }
    canonical = build_extraction_idempotency_key(**material)
    queued = SQLiteExtractionQueue.build_idempotency_key(
        "web",
        None,
        material["payload"],
        material["effective_options"],
        material["adapter_name"],
        material["adapter_version"],
    )
    assert queued == canonical


def test_desktop_uses_shared_polling_and_shadow_dashboard_without_execution_controls():
    navigation = read("desktop/lingji-control/src/navigation.ts")
    app_pages = read("desktop/lingji-control/src/AppPages.tsx")
    dashboard = read("desktop/lingji-control/src/pages/AutoReviewPage.tsx")
    polling = read("desktop/lingji-control/src/hooks/usePollingResource.ts")
    attention = read("desktop/lingji-control/src/pages/AttentionPage.tsx")
    diagnostics = read("desktop/lingji-control/src/pages/DiagnosticsPage.tsx")

    for page_id in ("overview", "activity", "attention", "diagnostics"):
        assert f'id: "{page_id}"' in navigation
    assert navigation.count('group: "observe"') == 4
    assert "PRIMARY_NAVIGATION" in navigation
    assert "ADVANCED_NAVIGATION" in navigation
    assert 'id: "auto_review"' in navigation
    assert 'page === "auto_review"' in app_pages
    assert 'page === "attention"' in app_pages
    assert "ADVANCED_NAVIGATION" in diagnostics
    assert "pending_review_count" in attention
    assert "/api/auto-review/metrics" not in attention
    assert "SHADOW 决策目前是审计历史" in attention
    assert "usePollingResource" in dashboard
    assert "AbortController" in polling
    assert "inFlightRef" in polling
    assert "SHADOW" in dashboard
    assert "不会批准、拒绝、合并、删除或写入长期记忆" in dashboard
    for forbidden in (
        "/api/auto-review/approve",
        "/api/auto-review/reject",
        "/api/auto-review/delete",
        "/api/auto-review/execute",
        "/api/auto-review/active",
    ):
        assert forbidden not in dashboard
