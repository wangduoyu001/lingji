from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.automatic_memory import AuthorizationScope, AutomaticMemoryRuntime, SourceRegistry
from src.automatic_memory.checkpoint import SnapshotJobRunner
from src.extraction.bootstrap import build_extraction_pipeline
from src.storage import StateDatabase
from src.work.models import WorkItem


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


def test_authorized_rollout_scan_replay_is_idempotent_and_revocation_hides_source(tmp_path: Path, monkeypatch):
    settings = _settings(tmp_path)
    settings.home_dir = tmp_path / "configured-home"
    source_root = settings.home_dir / ".codex" / "sessions"
    monkeypatch.setenv("HOME", str(tmp_path / "host-home"))
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
    source = registry.register(AuthorizationScope("grant-rollout", ("codex_rollout",), (str(source_root),), datetime.now(timezone.utc), None, True, str(settings.home_dir)), "codex_rollout", str(source_root))
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
        raw_id = str(jobs[0]["payload"]["raw_id"])
        raw_path = pipeline.sink.raw_root / raw_id
        assert raw_path.is_file()
        assert messages[0]["raw_reference"] == str(raw_path)
        work = runtime.work_store.list_work(limit=10)
        assert any(item.work_id == "automatic-memory:" + str(jobs[0]["payload"]["scan_id"]) for item in work)
        assert pipeline.registry.resolve("codex_rollout", path, {}) .name == "codex_rollout"
        before = len(pipeline.structured_sink.read_model.list_messages(owner=True, limit=20, offset=0)["items"])
        runtime.scan_now(source.source_id)
        time.sleep(0.2)
        assert len(pipeline.structured_sink.read_model.list_messages(owner=True, limit=20, offset=0)["items"]) == before
        registry.revoke(source.source_id)
        assert registry.list_sources()[0].status == "revoked"
        assert pipeline.structured_sink.read_model.list_sources(status="active", owner=True, limit=20, offset=0)["items"] == []
    finally:
        runtime.stop()


@pytest.mark.parametrize("crash_at", ["30%", "70%"])
def test_rollout_scan_crash_restart_preserves_identity_and_third_party_sentinel(tmp_path: Path, monkeypatch, crash_at: str):
    settings = _settings(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    source_root = home / ".codex" / "sessions"
    third_party = tmp_path / "third-party-sentinel.jsonl"
    third_party.write_text("do not touch", encoding="utf-8")
    third_party.chmod(0o640)
    sentinel_before = (third_party.read_bytes(), third_party.stat().st_mtime_ns, third_party.stat().st_mode)
    for index in range(3):
        path = source_root / "2026" / "08" / "29" / f"rollout-{index}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {"type": "session_meta", "payload": {"id": f"s-{index}"}},
            {"type": "event_msg", "id": f"u-{index}", "payload": {"type": "user_message", "message": f"user-{index}"}, "timestamp": f"2026-08-29T00:00:0{index}Z"},
            {"type": "response_item", "id": f"a-{index}", "payload": {"type": "message", "role": "assistant", "content": f"assistant-{index}"}, "timestamp": f"2026-08-29T00:00:1{index}Z"},
        ]
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    pipeline = build_extraction_pipeline(settings)
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    source = registry.register(AuthorizationScope("grant-crash", ("codex_rollout",), (str(source_root),), datetime.now(timezone.utc), None, True), "codex_rollout", str(source_root))
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    scan = registry.start_scan(source.source_id)
    work_id = "automatic-memory:" + scan.scan_id
    runtime.work_store.create_work(WorkItem(work_id=work_id, title="Codex rollout scan", source_id=source.source_id, status="accepted", owner_approved=True))
    first = runtime.runner.run(scan.scan_id, crash_at=crash_at)
    assert first.status == "paused"
    restarted = SnapshotJobRunner(runtime.snapshot, pipeline.queue, state, path_provider=runtime._authorized_paths)
    final = restarted.run(scan.scan_id)
    assert final.status == "completed"
    assert final.progress == final.total == 3
    assert len(list((pipeline.sink.raw_root).iterdir())) == 3
    for _ in range(3):
        pipeline.process_pending(limit=10)
    jobs = pipeline.queue.list_page(source_type="automatic_memory_snapshot", limit=20)
    assert len(jobs) == 3
    assert all(job["status"] == "completed" for job in jobs)
    messages = pipeline.structured_sink.read_model.list_messages(owner=True, limit=20, offset=0)["items"]
    assert len(messages) == 6
    assert {item["external_id"] for item in messages} == {
        f"codex-rollout:message:s-{index}:{role}-{index}"
        for index in range(3)
        for role in ("u", "a")
    }
    source = pipeline.structured_sink.read_model.list_sources(source_type="codex_rollout", owner=True, limit=20, offset=0)
    assert source["pagination"]["total"] == 1
    conversations = pipeline.structured_sink.read_model.list_conversations(source_type="codex_rollout", owner=True, limit=20, offset=0)
    assert conversations["pagination"]["total"] == 3
    work_before = runtime.work_store.get_work(work_id)
    assert work_before is not None
    replay = restarted.run(scan.scan_id)
    assert replay.status == "completed"
    pipeline.process_pending(limit=10)
    assert len(pipeline.structured_sink.read_model.list_messages(owner=True, limit=20, offset=0)["items"]) == 6
    assert runtime.work_store.get_work(work_id).work_id == work_before.work_id
    sentinel_after = (third_party.read_bytes(), third_party.stat().st_mtime_ns, third_party.stat().st_mode)
    assert sentinel_after == sentinel_before
