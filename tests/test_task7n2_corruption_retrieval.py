from __future__ import annotations

from pathlib import Path

from src.automatic_memory.quality_degradation import (
    CorruptionIsolationMeasurement,
    measure_corruption_isolation_from_runtime,
)


def test_corruption_measurement_publishes_durable_identity_and_retrieval_fields(
    tmp_path: Path,
) -> None:
    """The corruption gate must expose machine-checkable chain evidence."""
    # This RED test intentionally uses the existing formal fixture builders;
    # the implementation must wire the gateway into the measurement instead
    # of treating a non-empty read-model list as retrieval evidence.
    from src.automatic_memory.quality_gate import _build_gateway, _build_pipeline
    from src.retrieval.memory_db import MemoryDatabase
    from src.sources import SourceReadModel
    from src.storage import StateDatabase

    root = tmp_path / "acceptance"
    (root / "storage" / "state").mkdir(parents=True)
    (root / "storage" / "raw").mkdir(parents=True)
    (root / "storage" / "index").mkdir(parents=True)
    (root / "vault").mkdir()
    fixture = Path(__file__).parent / "fixtures" / "automatic_memory" / "generic_ai_history.json"
    (root / "generic-history-inbox.json").write_bytes(fixture.read_bytes())
    state_db = StateDatabase(root / "storage" / "state" / "lingji_state.db")
    memory_db = MemoryDatabase(root / "storage" / "index" / "lingji_memory.db")
    read_model = SourceReadModel(memory_db)
    pipeline = _build_pipeline(root, memory_db, read_model, state_db)
    gateway, _ = _build_gateway(root, memory_db, read_model, state_db)

    result = measure_corruption_isolation_from_runtime(
        root, pipeline, read_model, state_db, gateway=gateway
    )

    assert isinstance(result, CorruptionIsolationMeasurement)
    assert len(result.target_source_ids) == 2
    assert len(result.target_scan_ids) == 2
    assert len(result.target_job_ids) == 2
    assert result.queue_status_counts == {"completed": 1, "failed": 1}
    assert result.work_outcome_counts == {"completed": 1, "failed": 1}
    assert result.valid_retrieval_identities
    assert result.bad_leakage_count == 0
    assert result.status == "ready"
