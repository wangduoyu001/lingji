"""Historical Task 4R1 takeover rejection coverage.

Old fixture-driven takeover and automatic-activation assertions remain
rejection coverage, not current product behavior.
"""
from __future__ import annotations

from src.automatic_memory.quality_gate import QualityScaleBlockedError, ensure_4r2_ready_for_scale
from src.automatic_memory.quality_evidence import EvidenceState, QualityEvidenceReadiness


def _reset_readiness() -> QualityEvidenceReadiness:
    fields = (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
        "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
    )
    return QualityEvidenceReadiness(**{field: EvidenceState.NOT_MEASURED for field in fields})


def test_round5_takeover_cannot_authorize_scale() -> None:
    try:
        ensure_4r2_ready_for_scale(_reset_readiness())
    except QualityScaleBlockedError as error:
        assert str(error) == "BLOCKED_4R2_REQUIRED"
    else:
        raise AssertionError("scale must remain blocked until 4R2")


def test_rejected_runner_apis_are_not_reintroduced() -> None:
    import src.automatic_memory.quality_gate as quality_gate

    assert not hasattr(quality_gate, "build_prequery_identity_map")
    assert not hasattr(quality_gate, "select_gateway_evidence")
