from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from src.automatic_memory import AuthorizationScope, AutomaticMemoryRuntime, SourceRegistry
from src.extraction.bootstrap import build_extraction_pipeline
from src.storage import StateDatabase


def _settings(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        storage_path=root / "storage", state_db_path=root / "storage" / "lingji_state.db",
        memory_db_path=root / "storage" / "lingji_memory.db", vault_path=root / "vault",
        runtime_settings_file="runtime_settings.json", scheduler_poll_seconds=0.02,
        automatic_memory_debounce_seconds=1, automatic_memory_reconciliation_seconds=60,
        automatic_memory_integrity_seconds=3600, extraction_poll_seconds=0.02,
        extraction_batch_size=2, extraction_max_attempts=1, extraction_lease_heartbeat_seconds=2,
        extraction_stale_after_seconds=30, embedding_enabled=False, semantic_enabled=False,
    )


def test_authorized_rollout_scan_replay_is_idempotent_and_revocation_hides_source(tmp_path: Path):
    settings = _settings(tmp_path)
    source_root = tmp_path / "home" / ".codex" / "sessions"
    path = source_root / "2026/08/29/rollout-one.jsonl"
    path.parent.mkdir(parents=True)
    rows = [
        {"type": "session_meta", "payload": {"id": "session-one", "timestamp": "2026-08-29T00:00:00Z"}},
        {"type": "event_msg", "id": "u", "payload": {"type": "user_message", "message": "保留这个计划"}, "timestamp": "2026-08-29T00:00:01Z"},
        {"type": "response_item", "id": "a", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "好的，已记录。"}]}, "timestamp": "2026-08-29T00:00:02Z"},
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    pipeline = build_extraction_pipeline(settings)
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    source = registry.register(AuthorizationScope("grant-rollout", ("codex_rollout",), (str(source_root),), datetime.now(timezone.utc), None, True), "codex_rollout", str(source_root))
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    runtime.start()
    try:
        runtime.scan_now(source.source_id)
        deadline = time.time() + 8
        while time.time() < deadline:
            jobs = pipeline.queue.list_page(source_type="automatic_memory_snapshot", limit=20)
            if jobs and jobs[0]["status"] in {"completed", "failed"}:
                break
            time.sleep(0.03)
        assert jobs and jobs[0]["status"] == "completed", jobs
        assert jobs[0]["status"] == "completed", jobs[0].get("last_error") or jobs[0].get("error") or jobs[0]
        messages = pipeline.structured_sink.read_model.list_messages(owner=True, limit=20, offset=0)["items"]
        assert len(messages) == 2
        assert pipeline.registry.resolve("codex_rollout", path, {}) .name == "codex_rollout"
        before = len(pipeline.structured_sink.read_model.list_messages(owner=True, limit=20, offset=0)["items"])
        runtime.scan_now(source.source_id)
        time.sleep(0.2)
        assert len(pipeline.structured_sink.read_model.list_messages(owner=True, limit=20, offset=0)["items"]) == before
        registry.revoke(source.source_id)
        assert registry.list_sources()[0].status == "revoked"
    finally:
        runtime.stop()
