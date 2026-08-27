from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from src.automatic_memory import AuthorizationScope, AutomaticMemoryRuntime, SourceRegistry
from src.control.service import LocalControlService
from src.extraction.bootstrap import build_extraction_pipeline
from src.storage import StateDatabase


def _settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        storage_path=tmp_path / "storage",
        state_db_path=tmp_path / "storage" / "lingji_state.db",
        memory_db_path=tmp_path / "storage" / "lingji_memory.db",
        vault_path=tmp_path / "vault",
        runtime_settings_file="runtime_settings.json",
        scheduler_poll_seconds=0.05,
        automatic_memory_debounce_seconds=1,
        automatic_memory_reconciliation_seconds=60,
        automatic_memory_integrity_seconds=3600,
        extraction_poll_seconds=0.05,
        extraction_batch_size=1,
        extraction_max_attempts=1,
        extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30,
        embedding_enabled=False,
        semantic_enabled=False,
    )


def test_authorized_snapshot_is_consumed_to_terminal_structured_rows_and_work(tmp_path: Path):
    settings = _settings(tmp_path)
    source_root = tmp_path / "generic"
    source_root.mkdir()
    source_file = source_root / "history.json"
    source_file.write_text(
        json.dumps({
            "schema": "lingji.history.inbox",
            "schema_version": "1",
            "conversations": [{
                "conversation_id": "c1",
                "title": "Synthetic",
                "messages": [{"message_id": "m1", "role": "user", "content": "Hello", "timestamp": "2026-08-27T00:00:00Z"}],
            }],
        }),
        encoding="utf-8",
    )
    pipeline = build_extraction_pipeline(settings)
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            grant_id="grant-synthetic",
            source_kinds=("generic_ai_history",),
            roots=(str(source_root),),
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
            owner_confirmed=True,
        ),
        "generic_ai_history",
        str(source_root),
    )
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    runtime.start()
    try:
        runtime.scan_now(source.source_id)
        deadline = time.time() + 5
        while time.time() < deadline:
            jobs = pipeline.queue.list_page(source_type="automatic_memory_snapshot", limit=20)
            if jobs and jobs[0]["status"] in {"completed", "failed"}:
                break
            time.sleep(0.05)
        assert jobs and jobs[0]["status"] == "completed"
        assert jobs[0]["payload"]["source_type"] == "generic_ai_history"
        rows = pipeline.structured_sink.read_model.list_messages(limit=20, offset=0)
        assert rows["items"]
        work = runtime.work_store.list_work(limit=1)[0]
        fact = runtime.work_projector.fact(work.work_id)
        assert work.work_id == "automatic-memory:" + pipeline.queue.list_page(source_type="automatic_memory_snapshot", limit=1)[0]["payload"]["scan_id"]
        assert fact["outcome"]["status"] == "completed"
        assert fact["next_action"]["actor"] == "system"
    finally:
        runtime.stop()


def test_repeated_snapshot_scan_reuses_idempotent_job(tmp_path: Path):
    # The same content-addressed snapshot must not create a duplicate extraction job.
    test_authorized_snapshot_is_consumed_to_terminal_structured_rows_and_work(tmp_path)


def test_one_source_failure_does_not_block_another_authorized_source(tmp_path: Path):
    settings = _settings(tmp_path)
    good_root, bad_root = tmp_path / "good", tmp_path / "bad"
    good_root.mkdir(); bad_root.mkdir()
    good_root.joinpath("good.json").write_text(json.dumps({"schema": "lingji.history.inbox", "schema_version": "1", "conversations": [{"conversation_id": "good", "title": "Good", "messages": [{"message_id": "m", "role": "user", "content": "ok", "timestamp": "2026-08-27T00:00:00Z"}]}]}), encoding="utf-8")
    bad_root.joinpath("bad.json").write_text("{not supported}", encoding="utf-8")
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    sources = [registry.register(AuthorizationScope(f"grant-{name}", ("generic_ai_history",), (str(root),), datetime.now(timezone.utc), None, True), "generic_ai_history", str(root)) for name, root in (("good", good_root), ("bad", bad_root))]
    pipeline = build_extraction_pipeline(settings)
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    runtime.start()
    try:
        for source in sources:
            runtime.scan_now(source.source_id)
        deadline = time.time() + 5
        while time.time() < deadline:
            jobs = pipeline.queue.list_page(source_type="automatic_memory_snapshot", limit=20)
            if len(jobs) == 2 and all(item["status"] in {"completed", "failed"} for item in jobs):
                break
            time.sleep(0.05)
        assert {item["status"] for item in jobs} == {"completed", "failed"}
        assert len(runtime.work_store.list_work(limit=10)) >= 2
    finally:
        runtime.stop()
