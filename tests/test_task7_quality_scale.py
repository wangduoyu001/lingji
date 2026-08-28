from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.automatic_memory.quality_gate import (
    QualityScaleBlockedError,
    ensure_4r2_ready_for_scale,
    generate_100k_history,
    run_release_preflight,
)
from src.automatic_memory.quality_evidence import EvidenceState, QualityEvidenceReadiness


def _functional_ready(*, scale: EvidenceState = EvidenceState.NOT_MEASURED) -> QualityEvidenceReadiness:
    return QualityEvidenceReadiness(
        import_audit=EvidenceState.READY,
        promotion_provenance=EvidenceState.READY,
        gateway_selection=EvidenceState.READY,
        production_sentinel=EvidenceState.READY,
        mcp_parity=EvidenceState.READY,
        qdrant_degradation=EvidenceState.READY,
        corruption_isolation=EvidenceState.READY,
        context_baseline=EvidenceState.READY,
        scale=scale,
        owner_review=EvidenceState.NOT_MEASURED,
        reboot_recovery=EvidenceState.NOT_MEASURED,
        mac_release=EvidenceState.NOT_MEASURED,
        windows_release=EvidenceState.NOT_MEASURED,
    )


def test_scale_readiness_does_not_require_mac_owner_or_windows_evidence() -> None:
    ensure_4r2_ready_for_scale(_functional_ready())


def test_scale_readiness_rejects_unmeasured_functional_evidence() -> None:
    readiness = _functional_ready()
    readiness = QualityEvidenceReadiness(
        **{**readiness.__dict__, "mcp_parity": EvidenceState.NOT_MEASURED}
    )
    with pytest.raises(QualityScaleBlockedError, match="BLOCKED_4R2_REQUIRED"):
        ensure_4r2_ready_for_scale(readiness)


def test_release_preflight_never_constructs_or_invokes_scale_when_blocked() -> None:
    calls: list[str] = []
    ready = _functional_ready()
    readiness = QualityEvidenceReadiness(
        **{**ready.__dict__, "context_baseline": EvidenceState.NOT_MEASURED}
    )
    with pytest.raises(QualityScaleBlockedError, match="BLOCKED_4R2_REQUIRED"):
        run_release_preflight(
            readiness,
            prepare_scale_environment=lambda: calls.append("environment"),
            run_scale_command=lambda: calls.append("command"),
        )
    assert calls == []


def test_100k_fixture_reports_measured_identity_counts_and_hash(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    report = generate_100k_history(path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    messages = [row for row in rows if row.get("type") == "message"]
    assert report["messages"] == 100_000
    assert report["unique_message_ids"] == 100_000
    assert report["unique_content_hashes"] == 100_000
    assert len({row["message_id"] for row in messages}) == 100_000
    assert len({row["content_hash"] for row in messages}) == 100_000
    assert report["message_rows"] == 100_000
    assert report["fixture_sha256"]
