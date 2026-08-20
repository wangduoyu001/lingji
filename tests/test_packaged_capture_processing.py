from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.capture.models import CaptureEnvelope
from src.capture.policy import CaptureMode, CapturePolicy
from src.capture.service import CaptureService
from src.control.capture_processing import PackagedCaptureProcessingRuntime
from src.storage import StateDatabase


class RuntimeDefaults:
    def options_for_source(self, _source_type: str):
        return {}

    def priority_for_source(self, _source_type: str):
        return 100


def _settings(tmp_path: Path):
    storage = tmp_path / "storage"
    vault = tmp_path / "vault"
    storage.mkdir()
    vault.mkdir()
    return SimpleNamespace(
        storage_path=storage,
        vault_path=vault,
        state_db_path=storage / "lingji_state.db",
        memory_db_path=storage / "lingji_memory.db",
        vault_auto_init=True,
        index_private=False,
        memory_chunk_max_chars=1200,
        memory_chunk_overlap_chars=120,
        extraction_max_attempts=3,
        extraction_lease_heartbeat_seconds=15,
        extraction_stale_after_seconds=1800,
        extraction_poll_seconds=0.2,
        extraction_batch_size=4,
    )


def test_packaged_capture_text_processes_to_readable_memory_without_qdrant(tmp_path: Path):
    settings = _settings(tmp_path)
    state_db = StateDatabase(settings.state_db_path)
    processor = PackagedCaptureProcessingRuntime(
        settings,
        state_db=state_db,
        runtime_settings=RuntimeDefaults(),
    )
    capture = CaptureService(
        processor.pipeline,
        policy=CapturePolicy.for_mode(CaptureMode.LOW_POWER),
    )
    envelope = CaptureEnvelope(
        capture_id="LJ-CAP-E2E-V5",
        source_type="text",
        capture_method="manual_text",
        title="主人快速记录",
        text="V5 packaged capture must become readable memory evidence.",
        privacy="private",
        process_later=True,
    )

    submitted = capture.submit(envelope)
    assert submitted.queued is True
    assert submitted.extraction_job_id

    processed = processor.pipeline.process_pending(limit=1, worker_id="test-packaged-owner")
    assert processed["completed"] == 1
    job = processor.pipeline.queue.get(submitted.extraction_job_id)
    assert job["status"] == "completed"
    assert job["payload"]["capture_id"] == "LJ-CAP-E2E-V5"

    created = job["result"]["created"]
    assert len(created) == 1
    memory_id = created[0]["id"]
    memory = processor.memory_db.fetch_memory(memory_id, include_chunks=True)
    assert memory is not None
    assert memory["memory_id"] == memory_id
    assert memory["title"] == "主人快速记录"
    assert memory["chunks"]
    readable_text = "\n".join(str(chunk.get("text") or "") for chunk in memory["chunks"])
    assert "# 主人快速记录" in readable_text
    assert "V5 packaged capture must become readable memory evidence." in readable_text
    assert memory["relative_path"].startswith("07-Sources/")

    # The packaged processor intentionally has no semantic provider/Qdrant client.
    assert not hasattr(processor, "semantic_provider")
    assert not hasattr(processor, "qdrant")


def test_packaged_processor_background_worker_consumes_queue(tmp_path: Path):
    settings = _settings(tmp_path)
    state_db = StateDatabase(settings.state_db_path)
    processor = PackagedCaptureProcessingRuntime(
        settings,
        state_db=state_db,
        runtime_settings=RuntimeDefaults(),
    )
    capture = CaptureService(
        processor.pipeline,
        policy=CapturePolicy.for_mode(CaptureMode.LOW_POWER),
    )
    submitted = capture.submit(
        CaptureEnvelope(
            capture_id="LJ-CAP-BG-V5",
            source_type="text",
            capture_method="manual_text",
            title="主人快速记录",
            text="background packaged worker evidence",
            privacy="private",
            process_later=True,
        )
    )

    processor.start()
    try:
        import time

        deadline = time.time() + 5
        status = "queued"
        while time.time() < deadline:
            status = processor.pipeline.queue.get(submitted.extraction_job_id)["status"]
            if status == "completed":
                break
            time.sleep(0.05)
        assert status == "completed"
        assert processor.status()["running"] is True
    finally:
        processor.stop()

    assert processor.status()["running"] is False
