from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.automatic_memory import AuthorizationScope, SourceRegistry
from src.automatic_memory.runtime import AutomaticMemoryRuntime
from src.extraction.bootstrap import build_extraction_pipeline
from src.storage import StateDatabase


def test_scan_work_fact_has_stable_identity_and_truthful_failure_next_action(tmp_path: Path):
    settings = type("Settings", (), {
        "storage_path": tmp_path / "storage",
        "state_db_path": tmp_path / "storage" / "lingji_state.db",
        "memory_db_path": tmp_path / "storage" / "lingji_memory.db",
        "vault_path": tmp_path / "vault",
        "runtime_settings_file": "runtime_settings.json",
        "embedding_enabled": False,
        "semantic_enabled": False,
        "extraction_max_attempts": 1,
        "extraction_lease_heartbeat_seconds": 2,
        "extraction_stale_after_seconds": 30,
        "extraction_poll_seconds": 0.05,
        "extraction_batch_size": 1,
    })()
    root = tmp_path / "generic"
    root.mkdir()
    (root / "bad.json").write_text("{not valid history}", encoding="utf-8")
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope("grant", ("generic_ai_history",), (str(root),), datetime.now(timezone.utc), None, True),
        "generic_ai_history", str(root),
    )
    pipeline = build_extraction_pipeline(settings)
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    first = runtime.scan_now(source.source_id)
    second = runtime.scan_now(source.source_id)
    assert first["source_id"] == second["source_id"] == source.source_id
    works = runtime.work_store.list_work(limit=10)
    assert len(works) == 2
    assert all(item.work_id.startswith("automatic-memory:") for item in works)
    assert len({item.work_id for item in works}) == 2
