from __future__ import annotations

import json
from pathlib import Path

from src.auto_review.shadow import ShadowDecision, ShadowDecisionStore
from src.capture.models import CaptureRequest
from src.capture.service import CaptureService
from src.config import Settings
from src.extraction.adapters.base import stable_adapter_version
from src.extraction.ids import canonicalize_import
from src.extraction.models import ExtractionJob, ExtractedDocument
from src.extraction.structured_sink import StructuredReadModelSink
from src.project_context.service import ProjectContextService
from src.project_memory.models import ProjectMemoryState
from src.project_memory.service import ProjectMemoryService
from src.sources.models import SourceUpsert
from src.sources.read_model import SourceReadModel
from src.storage.state_db import StateDatabase

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        vault_dir=str(tmp_path / "vault"),
        storage_dir=str(tmp_path / "storage"),
        log_dir=str(tmp_path / "logs"),
        backup_dir=str(tmp_path / "backup"),
        startup_min_free_gb=0,
    )


def test_capture_canonicalization_matches_ingestion_and_structured_read_model(tmp_path: Path):
    settings = make_settings(tmp_path)
    state_db = StateDatabase(settings.state_db_path)
    memory_db_path = settings.storage_path / "state" / "lingji_memory.db"
    read_model = SourceReadModel(memory_db_path)
    structured_sink = StructuredReadModelSink(read_model, state_db=state_db)
    service = CaptureService(settings, state_db=state_db)

    request = CaptureRequest(
        source_type="chatgpt",
        title="Project Thread",
        content="User: hello\nAssistant: hi",
        source_ref="https://example.com/thread?token=secret",
        project="alpha",
        privacy="private",
        options={"source_name": "Project Thread"},
    )
    material = service.materialize(request)
    canonical = canonicalize_import(
        source_type=material.source_type,
        adapter_name=material.adapter_name,
        adapter_version=material.adapter_version,
        input_path=material.raw_path,
        payload=material.payload,
        options=material.options,
    )
    assert canonical.source_id == material.source_id
    assert canonical.import_id == material.import_id

    document = ExtractedDocument(
        source_type=material.source_type,
        source_id=material.source_id,
        title=material.title,
        body=material.content,
        privacy=material.privacy,
        projects=(material.project,) if material.project else (),
        metadata={
            "source_ref": material.source_ref,
            "source_name": material.title,
            "import_id": material.import_id,
        },
    )
    job = ExtractionJob(
        job_id="job-canonical",
        source_type=material.source_type,
        input_path=str(material.raw_path),
        payload=material.payload,
        options=material.options,
        adapter_name=material.adapter_name,
        adapter_version=material.adapter_version,
    )
    structured_sink([document], job, None)

    source = read_model.get_source(material.source_id)
    assert source is not None
    assert source.source_id == material.source_id
    assert source.projects == ("alpha",)
    assert source.privacy == "private"


def test_shadow_decision_store_never_mutates_memory_state(tmp_path: Path):
    settings = make_settings(tmp_path)
    state_db = StateDatabase(settings.state_db_path)
    project_memory = ProjectMemoryService(settings.vault_path, state_db=state_db)
    project = project_memory.ensure_project("alpha")
    before = ProjectMemoryState.from_dict(project_memory.project_state(project.project_id))

    shadow_store = ShadowDecisionStore(state_db)
    decision = ShadowDecision(
        decision_id="shadow-1",
        candidate_id="candidate-1",
        predicted_action="approve",
        confidence=0.91,
        reason="fixture",
        mode="SHADOW",
    )
    shadow_store.record(decision)

    after = ProjectMemoryState.from_dict(project_memory.project_state(project.project_id))
    assert before == after
    rows = state_db.recent_events(limit=20, entity_type="auto_review_shadow")
    assert any(row["entity_id"] == "shadow-1" for row in rows)


def test_project_context_and_source_ids_remain_stable(tmp_path: Path):
    settings = make_settings(tmp_path)
    state_db = StateDatabase(settings.state_db_path)
    project_context = ProjectContextService(settings.vault_path, state_db=state_db)
    project_context.ensure_project("alpha")

    source = SourceUpsert(
        source_type="chatgpt",
        display_name="Thread",
        origin_ref="thread-1",
        privacy="private",
        projects=("alpha",),
    )
    first = source.stable_source_id()
    second = source.stable_source_id()
    assert first == second

    material = CaptureService(settings, state_db=state_db).materialize(
        CaptureRequest(
            source_type="chatgpt",
            title="Thread",
            content="hello",
            source_ref="thread-1",
            project="alpha",
            privacy="private",
        )
    )
    adapter_version = stable_adapter_version("chatgpt", "markdown")
    queued = canonicalize_import(
        source_type=material.source_type,
        adapter_name=material.adapter_name,
        adapter_version=material.adapter_version,
        input_path=material.raw_path,
        payload=material.payload,
        options=material.options,
    )
    canonical = canonicalize_import(
        material.source_type,
        material.raw_path,
        material.payload,
        material.options,
        material.adapter_name,
        material.adapter_version,
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
    assert "/api/work/pending-actions" in attention
    assert "pending_review_count" not in attention
    assert "不能按 0 项处理" in attention
    assert "/api/auto-review/metrics" not in attention
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
