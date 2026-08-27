from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.automatic_memory import AuthorizationScope, AutomaticMemoryRuntime, SourceRegistry
from src.extraction.adapters.generic_ai_history import GenericAIHistoryAdapter
from src.extraction.bootstrap import build_extraction_pipeline
from src.extraction.models import ExtractionRequest
from src.extraction.structured_sink import StructuredReadModelSink
from src.sources import SourceReadModel
from src.storage import StateDatabase


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


def _history_payload(conversation_id: str = "conversation-1") -> dict[str, object]:
    return {
        "schema": "lingji.history.inbox",
        "schema_version": "1",
        "conversations": [{
            "conversation_id": conversation_id,
            "title": "Synthetic",
            "messages": [{
                "message_id": "message-1",
                "role": "user",
                "content": "hello",
                "timestamp": "2026-08-27T00:00:00Z",
            }],
        }],
    }


def test_managed_frontmatter_line_endings_are_bounded_and_explicit_deny_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    vault = tmp_path / "vault"
    managed = vault / "_LingJi" / "Memory Inbox"
    managed.mkdir(parents=True)
    files = {
        "false-crlf.md": b"---\r\nlingji_memory: false\r\n---\r\nFALSE_BODY_SENTINEL",
        "false-bom-crlf.md": b"\xef\xbb\xbf---\r\nlingji_memory: false\r\n---\r\nBOM_FALSE_BODY_SENTINEL",
        "true-crlf.md": b"---\r\nlingji_memory: true\r\n---\r\nTRUE_BODY_SENTINEL",
        "malformed.md": b"---\r\nlingji_memory: [\r\n---\r\nMALFORMED_BODY_SENTINEL",
        "unclosed.md": b"---\r\nlingji_memory: true\r\n" + b"x" * 9000 + b"UNCLOSED_BODY_SENTINEL",
    }
    for name, content in files.items():
        (managed / name).write_bytes(content)
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
    from src.obsidian.discovery import discover_memory_paths

    selected = {decision.path.name for decision in discover_memory_paths(vault)}
    assert selected == {"true-crlf.md"}
    for name, content in files.items():
        consumed = b"".join(chunk for path, chunk in reads if path.name == name)
        assert len(consumed) <= 8192
        sentinel = content.split(b"---\r\n", 1)[-1].split(b"\r\n---\r\n", 1)[-1]
        assert sentinel not in consumed


def test_automatic_generic_history_namespaces_structured_rows_by_authorized_source(
    tmp_path: Path,
):
    path = tmp_path / "history.json"
    path.write_text(json.dumps(_history_payload()), encoding="utf-8")
    adapter = GenericAIHistoryAdapter()
    batches = [
        adapter.extract(ExtractionRequest(
            f"job-{source_id}",
            "generic_ai_history",
            input_path=path,
            payload={"source_id": source_id},
            options={"automatic_memory": True},
        ))
        for source_id in ("authorized-source-a", "authorized-source-b")
    ]
    read_model = SourceReadModel(tmp_path / "memory.db")
    sink = StructuredReadModelSink(read_model, storage_path=tmp_path / "storage")
    for index, batch in enumerate(batches):
        sink.write_batch(
            batch,
            raw_snapshot={"raw_path": f"raw-{index}", "sha256": "a" * 64, "size": 1},
            vault_results={"paths": []},
            execution_id=f"job-{index}",
            adapter_name=adapter.name,
            adapter_version=adapter.version,
            indexing_succeeded=False,
        )
    sources = read_model.list_sources(limit=20, offset=0)["items"]
    conversations = read_model.list_conversations(limit=20, offset=0)["items"]
    messages = read_model.list_messages(limit=20, offset=0)["items"]
    assert len(sources) == len(conversations) == len(messages) == 2
    assert {item["metadata"].get("automatic_memory_source_id") for item in sources} == {
        "authorized-source-a", "authorized-source-b"
    }
    assert len({item["external_id"] for item in sources}) == 2
    assert len({item["external_id"] for item in conversations}) == 2
    assert len({item["external_id"] for item in messages}) == 2


@pytest.mark.parametrize("crash_at", ["30%", "70%"])
def test_pause_resume_work_fact_uses_truthful_scan_total(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, crash_at: str
):
    settings = _settings(tmp_path)
    root = tmp_path / "generic"
    root.mkdir()
    for index in range(10):
        (root / f"history-{index:02d}.json").write_text(
            json.dumps(_history_payload(f"conversation-{index}")), encoding="utf-8"
        )
    state = StateDatabase(settings.state_db_path)
    registry = SourceRegistry(state)
    source = registry.register(
        AuthorizationScope(
            "grant",
            ("generic_ai_history",),
            (str(root),),
            datetime.now(timezone.utc),
            None,
            True,
        ),
        "generic_ai_history",
        str(root),
    )
    scan = registry.start_scan(source.source_id)
    pipeline = build_extraction_pipeline(settings)
    runtime = AutomaticMemoryRuntime(state_db=state, pipeline=pipeline, settings=settings, registry=registry)
    original_run = runtime.runner.run
    point = crash_at
    monkeypatch.setattr(runtime.runner, "run", lambda scan_id, crash_at="none": original_run(scan_id, crash_at=point))
    paused = runtime._run_scan(scan.scan_id, source.source_id, reason="repair")
    assert paused.status == "paused"
    expected_paused = 3 if crash_at == "30%" else 7
    deadline = time.time() + 2
    while time.time() < deadline and pipeline.queue.stats()["pending"] < expected_paused:
        time.sleep(0.01)
    assert pipeline.queue.stats()["pending"] == expected_paused
    monkeypatch.setattr(runtime.runner, "run", original_run)
    resumed = runtime._run_scan(scan.scan_id, source.source_id, reason="resume")
    assert resumed.status == "completed"
    pipeline.process_pending(limit=20, worker_id="repair-resume")
    work = runtime.work_store.get_work(f"automatic-memory:{scan.scan_id}")
    assert work is not None
    fact = runtime.work_projector.fact(work.work_id)
    assert fact["outcome"]["status"] == "completed"
    assert "已检查 0 个" not in fact["outcome"]["summary"]
    assert "已检查 10 个" in fact["outcome"]["summary"]
    assert runtime._scan_reports == {}


def test_task_three_repair_round_one_report_attributes_all_three_commits():
    report = Path(".superpowers/sdd/2026-08-27-phase1-product-landing/task-3-repair-1-report.md").read_text(encoding="utf-8")
    log = Path("docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md").read_text(encoding="utf-8")
    for text in ("f2f7312", "4e5d744", "95cfc90"):
        assert text in report
        assert text in log
