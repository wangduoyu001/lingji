from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.automatic_memory import AuthorizationScope, AutomaticMemoryRuntime, SourceRegistry
from src.control.api import create_control_app
from src.control.service import LocalControlService
from src.extraction.base import ExtractionAdapter
from src.extraction.models import ExtractedDocument, ExtractionBatch
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.extraction.bootstrap import build_extraction_pipeline
from src.memory import VaultLayout
from src.obsidian.discovery import discover_memory_paths
from src.storage import StateDatabase
from src.work.models import WorkItem
from src.work.store import WorkStore


def _settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        storage_path=tmp_path / "storage",
        state_db_path=tmp_path / "storage" / "lingji_state.db",
        memory_db_path=tmp_path / "storage" / "lingji_memory.db",
        vault_path=tmp_path / "vault",
        runtime_settings_file="runtime_settings.json",
        extraction_max_attempts=1,
        extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30,
        extraction_poll_seconds=0.02,
        extraction_batch_size=1,
        scheduler_poll_seconds=0.02,
        automatic_memory_debounce_seconds=1,
        automatic_memory_reconciliation_seconds=60,
        automatic_memory_integrity_seconds=3600,
        embedding_enabled=False,
        semantic_enabled=False,
    )


def _generic_source(tmp_path: Path, filename: str = "history.json") -> tuple[SimpleNamespace, StateDatabase, SourceRegistry, object, Path]:
    settings = _settings(tmp_path)
    root = tmp_path / "generic"
    root.mkdir()
    path = root / filename
    path.write_text(json.dumps({
        "schema": "lingji.history.inbox",
        "schema_version": "1",
        "conversations": [{
            "conversation_id": "conversation-1",
            "title": "Synthetic",
            "messages": [{"message_id": "message-1", "role": "user", "content": "hello", "timestamp": "2026-08-27T00:00:00Z"}],
        }],
    }), encoding="utf-8")
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope("grant", ("generic_ai_history",), (str(root),), datetime.now(timezone.utc), None, True),
        "generic_ai_history", str(root),
    )
    return settings, state, registry, source, path


def test_unauthorized_internal_snapshot_is_terminal_and_does_not_starve_valid_job(tmp_path: Path):
    layout = VaultLayout(tmp_path / "vault")
    layout.ensure()
    queue = SQLiteExtractionQueue(tmp_path / "state.db")
    adapters = AdapterRegistry()

    class Ordinary(ExtractionAdapter):
        name = "ordinary"
        version = "1"
        source_types = ("ordinary",)

        def extract(self, request):
            return ExtractionBatch((ExtractedDocument("ordinary-1", "ordinary", "body", "ordinary"),))

    adapters.register(Ordinary())
    invalid = queue.enqueue("automatic_memory_snapshot", payload={"source_id": "missing"})
    valid = queue.enqueue("ordinary")
    pipeline = ExtractionPipeline(queue, adapters, VaultExtractionSink(layout, tmp_path / "storage"))

    result = pipeline.process_pending(limit=2, worker_id="repair-worker")

    assert result["processed"] == 2
    assert queue.get(invalid["job_id"])["status"] == "failed"
    assert queue.get(valid["job_id"])["status"] == "completed"
    assert pipeline.process_pending(limit=2, worker_id="repair-worker")["processed"] == 0


def test_obsidian_policy_does_not_read_ordinary_body_and_reads_only_bounded_frontmatter(tmp_path: Path, monkeypatch):
    vault = tmp_path / "vault"
    ordinary = vault / "03-Knowledge" / "ordinary.md"
    enabled = vault / "03-Knowledge" / "enabled.md"
    managed = vault / "_LingJi" / "Memory Inbox" / "managed.md"
    managed_false = vault / "_LingJi" / "Memory Library" / "managed-false.md"
    ordinary.parent.mkdir(parents=True)
    enabled.write_text("---\nlingji_memory: true\n---\n" + ("x" * 10000) + "BODY_SENTINEL", encoding="utf-8")
    ordinary.write_text(("ordinary " + "x" * 10000) + "BODY_SENTINEL", encoding="utf-8")
    managed.parent.mkdir(parents=True)
    managed.write_text("# managed", encoding="utf-8")
    managed_false.parent.mkdir(parents=True)
    managed_false.write_text("---\nlingji_memory: false\n---\nMANAGED_FALSE_BODY", encoding="utf-8")
    reads: list[tuple[Path, bytes]] = []

    original_open = Path.open

    class TrackedReader:
        def __init__(self, path: Path, stream):
            self.path = path
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self, size=-1):
            chunk = self.stream.read(size)
            reads.append((self.path, chunk))
            return chunk

        def readline(self, size=-1):
            chunk = self.stream.readline(size)
            reads.append((self.path, chunk))
            return chunk

        def __getattr__(self, name):
            return getattr(self.stream, name)

    def track_read(self, *args, **kwargs):
        return TrackedReader(self, original_open(self, *args, **kwargs))

    monkeypatch.setattr(Path, "open", track_read)
    selected = discover_memory_paths(vault)
    frontmatter_max_bytes = 8192
    assert sum(len(chunk) for path, chunk in reads if path == ordinary) <= 4
    assert sum(len(chunk) for path, chunk in reads if path == enabled) <= frontmatter_max_bytes
    assert b"BODY_SENTINEL" not in b"".join(chunk for path, chunk in reads if path == ordinary)
    assert b"BODY_SENTINEL" not in b"".join(chunk for path, chunk in reads if path == enabled)
    selected_paths = [decision.path for decision in selected]
    assert managed in [path for path, _chunk in reads]
    assert b"MANAGED_FALSE_BODY" not in b"".join(chunk for path, chunk in reads if path == managed_false)
    assert managed_false not in selected_paths
    assert managed in selected_paths
    assert enabled in selected_paths
    assert ordinary not in selected_paths


def test_generic_sensitive_filename_variants_are_excluded_without_overblocking_safe_history(tmp_path: Path):
    from src.automatic_memory.path_policy import enumerate_authorized_files
    root = tmp_path / "authorized"
    root.mkdir()
    for name in ("credentials.json", "AUTH-token.json", "cookie.json", "private.json", "auth_token.json", "safe-history.json"):
        (root / name).write_text("{}", encoding="utf-8")
    source = __import__("src.automatic_memory.models", fromlist=["SourceRecord"]).SourceRecord(
        "source-1", "generic_ai_history", str(root), "authorized", "metadata_discovery", "v1"
    )
    files = enumerate_authorized_files(source)
    assert files == (root / "safe-history.json",)


def test_real_two_scan_flow_reports_reuse_and_exact_structured_identity_set(tmp_path: Path):
    settings, state, registry, source, _ = _generic_source(tmp_path)
    pipeline = build_extraction_pipeline(settings)
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    runtime.start()
    try:
        first = runtime.scan_now(source.source_id)
        second = runtime.scan_now(source.source_id)
        deadline = time.time() + 5
        while time.time() < deadline and pipeline.queue.stats()["pending"]:
            time.sleep(0.03)
        jobs = pipeline.queue.list_page(source_type="automatic_memory_snapshot", limit=20)
        assert first["complete"] and second["complete"]
        assert first["queued"] == 1
        assert second["queued"] == 0
        assert second["reused"] == 1
        assert len(jobs) == 1
        read_model = pipeline.structured_sink.read_model
        assert len(read_model.list_sources(limit=20, offset=0)["items"]) == 1
        assert len(read_model.list_conversations(limit=20, offset=0)["items"]) == 1
        assert len(read_model.list_messages(limit=20, offset=0)["items"]) == 1
        scans = state.list_automatic_memory_scans(source.source_id)
        assert len(scans) == 2 and {row["status"] for row in scans} == {"completed"}
        works = runtime.work_store.list_work(limit=10)
        assert {work.source_id for work in works} == {source.source_id}
        assert all(work.status == "completed" for work in works)
        assert all(runtime.work_projector.fact(work.work_id)["outcome"]["status"] == "completed" for work in works)
        assert all("0 个" not in (runtime.work_projector.fact(work.work_id)["outcome"]["summary"] or "") for work in works)
        assert runtime._scan_reports == {}
    finally:
        runtime.stop()


def test_scan_route_requires_composed_runtime_and_dispatches_scheduler_scan_now(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.storage_path.mkdir()
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    root = tmp_path / "generic"
    root.mkdir()
    source = registry.register(AuthorizationScope("grant", ("generic_ai_history",), (str(root),), datetime.now(timezone.utc), None, True), "generic_ai_history", str(root))
    control = LocalControlService.__new__(LocalControlService)
    control.settings = settings
    control.state_db = state
    control.automatic_memory_registry = registry
    control.runtime = None
    app = create_control_app(settings, service=control, token="secret")
    with TestClient(app) as client:
        response = client.post("/api/automatic-memory/scan", headers={"X-LingJi-Token": "secret"}, json={"source_id": source.source_id})
    assert response.status_code == 409
    assert state.list_automatic_memory_scans(source.source_id) == []

    calls: list[str] = []
    class Runtime:
        def scan_now(self, source_id: str) -> dict[str, object]:
            calls.append(source_id)
            return {"scan_id": "scan-now", "source_id": source_id, "status": "completed", "work_id": "automatic-memory:scan-now"}

    control.runtime = Runtime()
    app = create_control_app(settings, service=control, token="secret")
    with TestClient(app) as client:
        dispatched = client.post("/api/automatic-memory/scan", headers={"X-LingJi-Token": "secret"}, json={"source_id": source.source_id})
    assert dispatched.status_code == 200
    assert dispatched.json()["work_id"] == "automatic-memory:scan-now"
    assert calls == [source.source_id]


def test_work_transition_updates_item_source_and_terminal_status(tmp_path: Path):
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    work = store.create_work(WorkItem(title="scan", source_id="source-real", status="accepted", owner_approved=True))
    store.apply_extraction_transition(work.work_id, "completed", summary="done", evidence={})
    completed = store.get_work(work.work_id)
    assert completed and completed.source_id == "source-real" and completed.status == "completed"
    failed_work = store.create_work(WorkItem(title="failed scan", source_id="source-failed", status="accepted", owner_approved=True))
    store.apply_extraction_transition(failed_work.work_id, "failed", summary="bad input", evidence={}, retryable=False)
    failed = store.get_work(failed_work.work_id)
    assert failed and failed.source_id == "source-failed" and failed.status == "failed"


def test_repair_docs_do_not_leave_pending_metadata_or_trailing_whitespace():
    report = Path(".superpowers/sdd/2026-08-27-phase1-product-landing/task-3-report.md").read_text(encoding="utf-8")
    log = Path("docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md").read_text(encoding="utf-8")
    assert "Evidence/docs commit: pending" not in report
    assert "Task 3 Repair Round 1" not in log or "报告/文档提交：待提交" not in log.split("Task 3 Repair Round 1", 1)[1]
    assert all(not line.endswith((" ", "\t")) for line in report.splitlines())


def test_automatic_snapshot_never_mutates_configured_vault_or_calls_document_sink(tmp_path: Path, monkeypatch):
    settings, state, registry, source, _ = _generic_source(tmp_path)
    pipeline = build_extraction_pipeline(settings)
    before = sorted(str(path.relative_to(settings.vault_path)) for path in settings.vault_path.rglob("*"))
    def fail_write(*args, **kwargs):
        raise AssertionError("automatic snapshot must not call VaultExtractionSink.write_batch")
    monkeypatch.setattr(pipeline.sink, "write_batch", fail_write)
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    runtime.start()
    try:
        runtime.scan_now(source.source_id)
        deadline = time.time() + 5
        while time.time() < deadline:
            jobs = pipeline.queue.list_page(source_type="automatic_memory_snapshot", limit=20)
            if jobs and jobs[0]["status"] in {"completed", "failed"}:
                break
            time.sleep(0.03)
        assert jobs[0]["status"] == "completed"
        assert sorted(str(path.relative_to(settings.vault_path)) for path in settings.vault_path.rglob("*")) == before
        assert pipeline.structured_sink.read_model.list_messages(limit=20, offset=0)["items"]
    finally:
        runtime.stop()
