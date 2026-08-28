"""Small, fail-closed measurement primitives used by the quality runner.

This module contains no retrieval or promotion policy.  It only turns already
produced product payloads into immutable, auditable measurements.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class MCPParityMeasurement:
    success: bool
    reason: str
    gateway_identity: tuple[Any, ...]
    mcp_identity: tuple[Any, ...]
    gateway_used_chars: int | None
    mcp_used_chars: int | None
    max_chars: int | None


@dataclass(frozen=True)
class ContextBaselineMeasurement:
    baseline_chars: int
    section_count: int
    complete_payload_sha256: str


@dataclass(frozen=True)
class CorruptionIsolationMeasurement:
    status: str
    attempted: int
    completed: int
    failed: int
    continued: int
    retrievable: int
    reasons: tuple[str, ...] = ()


_IDENTITY_FIELDS = (
    "kind", "memory_id", "source_id", "conversation_id", "message_id",
    "content_hash", "fact_id", "citation_id", "scope", "lifecycle",
    "query_mode", "mode", "as_of",
)


def _section_identity(section: Any) -> tuple[Any, ...]:
    if not isinstance(section, Mapping):
        raise ValueError("MCP section is not an object")
    citation = section.get("citation")
    citation = citation if isinstance(citation, Mapping) else {}
    values: list[Any] = []
    for field in _IDENTITY_FIELDS:
        value = section.get(field)
        if value in (None, ""):
            value = citation.get(field)
        values.append(value)
    # A parity measurement is only successful when the returned section is
    # independently attributable.  Memory-only sections may omit message
    # identity, but must still expose fact/citation identity for this gate.
    required = ("memory_id", "fact_id", "citation_id")
    if str(section.get("kind") or "") in {"raw_message_evidence", "structured_message_evidence"}:
        required = required + ("source_id", "conversation_id", "message_id", "content_hash")
    if any(section.get(field) in (None, "") and citation.get(field) in (None, "") for field in required):
        raise ValueError("MCP section identity is incomplete")
    return tuple(values)


def _pack_identity(pack: Any) -> tuple[tuple[Any, ...], ...]:
    if not isinstance(pack, Mapping):
        raise ValueError("MCP payload is not an object")
    sections = pack.get("sections")
    if isinstance(sections, (str, bytes)) or not isinstance(sections, Sequence):
        raise ValueError("MCP sections are malformed")
    # Preserve order: ordering is part of the Gateway/FastMCP contract.
    return tuple(_section_identity(section) for section in sections)


def measure_mcp_parity(gateway_pack: Mapping[str, Any], mcp_pack: Mapping[str, Any]) -> MCPParityMeasurement:
    """Compare full ordered identity and bounds of two independently obtained packs."""
    try:
        gateway_identity = _pack_identity(gateway_pack)
        mcp_identity = _pack_identity(mcp_pack)
        gateway_used = gateway_pack.get("used_chars")
        mcp_used = mcp_pack.get("used_chars")
        gateway_max = gateway_pack.get("max_chars")
        mcp_max = mcp_pack.get("max_chars")
        if any(type(value) is not int or value < 0 for value in (gateway_used, mcp_used, gateway_max, mcp_max)):
            return MCPParityMeasurement(False, "bounds_unmeasured", gateway_identity, mcp_identity, None, None, None)
        if gateway_max != mcp_max or gateway_used > gateway_max or mcp_used > mcp_max:
            return MCPParityMeasurement(False, "bounds_mismatch", gateway_identity, mcp_identity, gateway_used, mcp_used, gateway_max)
        top_fields = ("query_mode", "mode", "as_of", "scope", "lifecycle")
        for field in top_fields:
            if gateway_pack.get(field) != mcp_pack.get(field):
                return MCPParityMeasurement(False, f"top_level_{field}_mismatch", gateway_identity, mcp_identity, gateway_used, mcp_used, gateway_max)
        if not gateway_identity or gateway_identity != mcp_identity:
            return MCPParityMeasurement(False, "ordered_identity_mismatch", gateway_identity, mcp_identity, gateway_used, mcp_used, gateway_max)
        return MCPParityMeasurement(True, "identity_and_bounds_equal", gateway_identity, mcp_identity, gateway_used, mcp_used, gateway_max)
    except (TypeError, ValueError, AttributeError):
        return MCPParityMeasurement(False, "malformed_payload", (), (), None, None, None)


def measure_context_baseline(complete_sections: Sequence[Mapping[str, Any]], *, bounded_pack: Mapping[str, Any] | None) -> ContextBaselineMeasurement:
    """Measure the pre-bound selection payload, never a bounded ContextPack.

    The current product does not expose a pre-bound seam yet.  Requiring the
    caller to pass ``None`` prevents a bounded pack from being relabelled as a
    baseline and makes that missing seam explicit in the quality evidence.
    """
    if bounded_pack is not None:
        raise ValueError("selection-before-bound baseline required; bounded pack is not a baseline")
    if isinstance(complete_sections, (str, bytes)) or not isinstance(complete_sections, Sequence) or not complete_sections:
        raise ValueError("selection-before-bound payload is empty or malformed")
    payload = {"sections": [dict(section) for section in complete_sections]}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib
    return ContextBaselineMeasurement(len(encoded), len(complete_sections), hashlib.sha256(encoded).hexdigest())


def measure_corruption_isolation(*, valid_source_id: str, corrupt_source_id: str, run_source: Any) -> CorruptionIsolationMeasurement:
    """Run two authorized source callbacks and count their real outcomes."""
    if not valid_source_id or not corrupt_source_id or valid_source_id == corrupt_source_id:
        raise ValueError("two distinct authorized source IDs are required")
    attempted = completed = failed = continued = retrievable = 0
    reasons: list[str] = []
    for source_id in (valid_source_id, corrupt_source_id):
        attempted += 1
        try:
            result = run_source(source_id)
            if not isinstance(result, Mapping) or result.get("completed") is not True:
                raise ValueError("source did not publish completed outcome")
            completed += 1
            if bool(result.get("retrievable")):
                retrievable += 1
            if source_id == valid_source_id:
                continued += 1
        except Exception as exc:
            failed += 1
            reasons.append(type(exc).__name__)
    status = "ready" if (attempted == 2 and completed == 1 and failed == 1 and continued == 1 and retrievable == 1) else "failed"
    return CorruptionIsolationMeasurement(status, attempted, completed, failed, continued, retrievable, tuple(reasons))


__all__ = [
    "ContextBaselineMeasurement", "CorruptionIsolationMeasurement", "MCPParityMeasurement",
    "measure_context_baseline", "measure_corruption_isolation", "measure_mcp_parity",
]
