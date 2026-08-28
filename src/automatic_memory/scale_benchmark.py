"""Isolated scale-fixture and readiness helpers.

The actual 100k run remains opt-in and is never performed while functional
quality is unavailable.  This module deliberately has no product imports.
"""
from __future__ import annotations

import json
import hashlib
import shutil
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .quality_evidence import EvidenceState, QualityEvidenceReadiness
from src.extraction.adapters.generic_ai_history import HISTORY_SCHEMA, HISTORY_VERSION


# These are the only fixtures admitted by the frozen Task 7 quality gate.
# Keeping the identity contract here avoids making the scale loader depend on
# the runner module (which imports this module).
CORPUS_SHA256 = "bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94"
QUESTIONS_SHA256 = "338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612"


def build_quality_run_id(code_commit: str, corpus_hash: str, questions_hash: str) -> str:
    """Build the stable identity used by the frozen quality runner."""
    return f"quality:{corpus_hash[:16]}:{questions_hash[:16]}:{code_commit[:16]}"


_READINESS_FIELDS = QualityEvidenceReadiness._FUNCTIONAL_FIELDS + QualityEvidenceReadiness._MAC_FIELDS + ("windows_release",)
_STATUS_VALUES = {state.value for state in EvidenceState}


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} has a non-string key")
    return value


def _require_keys(value: Mapping[str, Any], required: set[str], label: str, *, allow: set[str] = frozenset()) -> None:
    keys = set(value)
    if not required <= keys or keys - required - allow:
        raise ValueError(f"{label} schema mismatch")


def _counter(value: Any, label: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < 0 or (positive and value <= 0):
        raise ValueError(f"{label} must be a measured integer")
    return value


def _percentage(value: Any, label: str) -> float:
    import math
    if type(value) not in (int, float) or not math.isfinite(float(value)) or not 0 <= float(value) <= 100:
        raise ValueError(f"{label} must be a finite percentage")
    return float(value)


def _detail(payload: Mapping[str, Any], details: Mapping[str, Any], *names: str) -> Mapping[str, Any]:
    for name in names:
        value = payload.get(name)
        if value is None:
            value = details.get(name)
        if value is not None:
            return _require_mapping(value, name)
    raise ValueError(f"missing evidence detail: {names[0]}")


def _validate_import(payload: Mapping[str, Any], details: Mapping[str, Any]) -> None:
    audit = _detail(payload, details, "import_audit")
    _require_keys(audit, {
        "expected_rows", "actual_rows", "missing_external_keys", "extra_external_keys",
        "stable_duplicates", "ordered_external_key_matches", "role_matches", "sequence_matches",
        "timestamp_matches", "content_hash_matches", "source_matches", "conversation_matches",
        "intentional_content_hash_groups",
    }, "import_audit")
    expected = _counter(audit["expected_rows"], "import_audit.expected_rows", positive=True)
    if _counter(audit["actual_rows"], "import_audit.actual_rows") != expected:
        raise ValueError("import audit count mismatch")
    for field in ("missing_external_keys", "extra_external_keys"):
        value = audit[field]
        if not isinstance(value, list) or value:
            raise ValueError("import audit has missing or extra rows")
    duplicates = _require_mapping(audit["stable_duplicates"], "import_audit.stable_duplicates")
    _require_keys(duplicates, {"source_records", "conversation_records", "message_records", "memory_records"}, "stable_duplicates")
    if any(_counter(duplicates[field], f"stable_duplicates.{field}") != 0 for field in duplicates):
        raise ValueError("import audit duplicate records")
    for field in ("ordered_external_key_matches", "role_matches", "sequence_matches", "timestamp_matches", "content_hash_matches", "source_matches", "conversation_matches"):
        if _counter(audit[field], f"import_audit.{field}") != expected:
            raise ValueError("import audit field mismatch")
    if not isinstance(audit["intentional_content_hash_groups"], list):
        raise ValueError("import audit duplicate groups malformed")
    counts = _require_mapping(payload.get("import_counts"), "import_counts")
    _require_keys(counts, {"expected_messages", "imported_messages"}, "import_counts")
    if _counter(counts["expected_messages"], "import_counts.expected_messages") != expected or _counter(counts["imported_messages"], "import_counts.imported_messages") != expected:
        raise ValueError("import count projection mismatch")
    order = _require_mapping(payload.get("role_order_counts"), "role_order_counts")
    _require_keys(order, {"expected", "matched"}, "role_order_counts")
    if _counter(order["expected"], "role_order_counts.expected") != expected or _counter(order["matched"], "role_order_counts.matched") != expected:
        raise ValueError("role/order count projection mismatch")


def _validate_promotion(payload: Mapping[str, Any], details: Mapping[str, Any], expected: int) -> None:
    outcomes = _require_mapping(payload.get("promotion_outcomes"), "promotion_outcomes")
    _require_keys(outcomes, {"active", "pending_owner_review", "rejected", "error"}, "promotion_outcomes")
    outcome_total = sum(_counter(value, f"promotion_outcomes.{key}") for key, value in outcomes.items())
    if outcome_total != expected or outcomes["error"] != 0:
        raise ValueError("promotion outcomes are incomplete")
    provenance = _detail(payload, details, "promotion_provenance")
    _require_keys(provenance, {
        "status", "expected", "actual", "links_expected", "links_actual", "missing_links",
        "extra_links", "duplicate_links", "duplicate_records",
    }, "promotion_provenance")
    if provenance["status"] != EvidenceState.READY.value:
        raise ValueError("promotion provenance is not ready")
    if _counter(provenance["expected"], "promotion_provenance.expected") != expected or _counter(provenance["actual"], "promotion_provenance.actual") != expected:
        raise ValueError("promotion provenance count mismatch")
    if _counter(provenance["links_expected"], "promotion_provenance.links_expected") != expected or _counter(provenance["links_actual"], "promotion_provenance.links_actual") != expected:
        raise ValueError("promotion link count mismatch")
    for field in ("missing_links", "extra_links", "duplicate_links", "duplicate_records"):
        if _counter(provenance[field], f"promotion_provenance.{field}") != 0:
            raise ValueError("promotion provenance has invalid links")


def _validate_gateway(payload: Mapping[str, Any], details: Mapping[str, Any]) -> None:
    gateway = _detail(payload, details, "gateway_selection")
    _require_keys(gateway, {"status", "calls_completed", "selector_calls", "unknown", "duplicates"}, "gateway_selection",
                  allow={"empty_responses", "selected_evidence", "empty_response_is_retrieval_miss"})
    if gateway["status"] != EvidenceState.READY.value:
        raise ValueError("gateway selection is not ready")
    if _counter(gateway["calls_completed"], "gateway calls") != 100 or _counter(gateway["selector_calls"], "gateway selectors") != 100:
        raise ValueError("gateway counts are incomplete")
    if _counter(gateway["unknown"], "gateway unknown") != 0 or _counter(gateway["duplicates"], "gateway duplicates") != 0:
        raise ValueError("gateway evidence is contaminated")


def _validate_mcp(payload: Mapping[str, Any], details: Mapping[str, Any]) -> None:
    mcp = _detail(payload, details, "mcp_parity")
    _require_keys(mcp, {"status", "attempts", "successes", "strict_rate"}, "mcp_parity", allow={"failures"})
    if mcp["status"] != EvidenceState.READY.value:
        raise ValueError("MCP parity is not ready")
    attempts = _counter(mcp["attempts"], "MCP attempts", positive=True)
    successes = _counter(mcp["successes"], "MCP successes")
    if attempts != 100 or successes != 100 or _percentage(mcp["strict_rate"], "MCP strict rate") < 95 or float(mcp["strict_rate"]) != 100.0 * successes / attempts:
        raise ValueError("strict MCP measurement is incomplete")


def _validate_qdrant(payload: Mapping[str, Any], details: Mapping[str, Any]) -> None:
    qdrant = _detail(payload, details, "qdrant_degradation", "semantic_degradation")
    _require_keys(qdrant, {"status", "semantic", "lexical", "lexical_ids", "degraded_ids"}, "qdrant_degradation",
                  allow={"diagnostics", "lexical_results", "degraded_results"})
    if qdrant["status"] != EvidenceState.READY.value or qdrant["semantic"] != "degraded" or qdrant["lexical"] != "available":
        raise ValueError("Qdrant degradation evidence is incomplete")
    lexical_ids, degraded_ids = qdrant["lexical_ids"], qdrant["degraded_ids"]
    if not isinstance(lexical_ids, list) or not lexical_ids or lexical_ids != degraded_ids or any(not isinstance(item, str) or not item for item in lexical_ids):
        raise ValueError("Qdrant lexical fallback identity is incomplete")


def _validate_corruption(payload: Mapping[str, Any], details: Mapping[str, Any]) -> None:
    corruption = _detail(payload, details, "corruption_isolation")
    _require_keys(corruption, {
        "status", "terminal_tasks", "attempted", "completed", "failed", "continued", "retrievable",
        "bad_source_messages", "bad_source_leaks", "queue_status_counts",
    }, "corruption_isolation", allow={"other_source_completed", "valid_source_messages", "scan_ids", "source_statuses", "scan_statuses", "work_outcomes", "read_model_messages", "reasons"})
    if corruption["status"] != EvidenceState.READY.value:
        raise ValueError("corruption isolation is not ready")
    expected = {"terminal_tasks": 2, "attempted": 2, "completed": 1, "failed": 1, "continued": 1, "retrievable": 1, "bad_source_messages": 0, "bad_source_leaks": 0}
    if any(_counter(corruption[field], f"corruption.{field}") != value for field, value in expected.items()):
        raise ValueError("corruption terminal counts mismatch")
    queue = _require_mapping(corruption["queue_status_counts"], "corruption.queue_status_counts")
    if set(queue) != {"completed", "failed"} or _counter(queue["completed"], "queue.completed") != 1 or _counter(queue["failed"], "queue.failed") != 1:
        raise ValueError("corruption queue terminal set mismatch")


def _validate_context(payload: Mapping[str, Any], details: Mapping[str, Any]) -> None:
    context = _detail(payload, details, "context_baseline")
    _require_keys(context, {"status", "baseline_chars", "rendered_chars", "reduction"}, "context_baseline")
    if context["status"] != EvidenceState.READY.value:
        raise ValueError("context baseline is not ready")
    baseline = _counter(context["baseline_chars"], "context baseline", positive=True)
    rendered = _counter(context["rendered_chars"], "rendered context")
    reduction = _percentage(context["reduction"], "context reduction")
    if rendered > baseline or abs(reduction - (1 - rendered / baseline) * 100) > 1e-9:
        raise ValueError("context reduction is not reproducible")
    measured = _require_mapping(payload.get("measured_quality"), "measured_quality")
    if measured.get("status") != "PASS":
        raise ValueError("measured quality is not passing")
    if _counter(measured.get("mcp_attempts"), "measured MCP attempts") != 100 or _counter(measured.get("mcp_successes"), "measured MCP successes") != 100:
        raise ValueError("measured MCP counts disagree")
    if measured.get("baseline_context_chars") != baseline or measured.get("rendered_context_chars") != rendered or measured.get("context_reduction") != context["reduction"]:
        raise ValueError("measured context baseline disagrees")


def readiness_from_envelope(path: Path) -> QualityEvidenceReadiness:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        payload = _require_mapping(payload, "quality envelope")
        code_commit = payload.get("code_commit")
        if not isinstance(code_commit, str) or len(code_commit) != 40 or any(char not in "0123456789abcdefABCDEF" for char in code_commit):
            raise ValueError("invalid code commit")
        fixture_hashes = _require_mapping(payload.get("fixture_hashes"), "fixture_hashes")
        _require_keys(fixture_hashes, {"corpus", "questions"}, "fixture_hashes")
        if fixture_hashes != {"corpus": CORPUS_SHA256, "questions": QUESTIONS_SHA256}:
            raise ValueError("frozen fixture hashes do not match")
        if payload.get("run_id") != build_quality_run_id(code_commit, CORPUS_SHA256, QUESTIONS_SHA256):
            raise ValueError("run identity does not match code and fixtures")
        functional_status = payload.get("functional_status")
        phase_status = payload.get("phase_status")
        if functional_status != "PASS" or phase_status not in {"BLOCKED", "NOT_EVALUATED"}:
            raise ValueError("scale verdict is not admissible")
        raw = payload.get("quality_evidence_readiness")
        if raw is None:
            raw = payload.get("readiness")
        raw = _require_mapping(raw, "quality_evidence_readiness")
        _require_keys(raw, set(_READINESS_FIELDS), "quality_evidence_readiness", allow={"functional_status", "should_run_acceptance_gate"})
        values: dict[str, EvidenceState] = {}
        for field in _READINESS_FIELDS:
            value = raw.get(field)
            if not isinstance(value, str) or value.removeprefix("EvidenceState.").lower() not in _STATUS_VALUES:
                raise ValueError
            values[field] = EvidenceState(value.removeprefix("EvidenceState.").lower())
        result = QualityEvidenceReadiness(**values)
        persisted = payload.get("readiness")
        if persisted is not None:
            persisted = _require_mapping(persisted, "readiness")
            if any(persisted.get(field) not in (raw.get(field), EvidenceState(str(raw.get(field)).removeprefix("EvidenceState.").lower())) for field in _READINESS_FIELDS):
                raise ValueError("readiness projections disagree")
        details = _require_mapping(payload.get("evidence_details", {}), "evidence_details")
        if result.production_sentinel not in {EvidenceState.NOT_MEASURED, EvidenceState.READY}:
            raise ValueError("production sentinel is not admissible for scale")
        if result.production_sentinel is EvidenceState.NOT_MEASURED and payload.get("production_pollution") is not None:
            raise ValueError("unmeasured production sentinel must remain null")
        if result.production_sentinel is EvidenceState.READY and payload.get("production_pollution") != 0:
            raise ValueError("production sentinel count mismatch")
        for field in QualityEvidenceReadiness._FUNCTIONAL_FIELDS:
            if field != "production_sentinel" and getattr(result, field) is not EvidenceState.READY:
                raise ValueError(f"functional evidence is not ready: {field}")
        _validate_import(payload, details)
        expected = _counter(_require_mapping(payload["import_counts"], "import_counts")["expected_messages"], "expected import count", positive=True)
        _validate_promotion(payload, details, expected)
        _validate_gateway(payload, details)
        _validate_mcp(payload, details)
        _validate_qdrant(payload, details)
        _validate_corruption(payload, details)
        _validate_context(payload, details)
        if not result.scale_ready:
            raise ValueError("functional readiness is incomplete")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("BLOCKED_4R2_REQUIRED") from exc
    if not result.scale_ready:
        raise ValueError("BLOCKED_4R2_REQUIRED")
    return result


def generate_history_fixture(path: Path, *, count: int = 100_000, seed: int = 41041) -> dict[str, Any]:
    """Generate and measure a deterministic fixture; small counts are test-only."""
    if type(count) is not int or count <= 0:
        raise ValueError("scale fixture count must be a positive integer")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    ids: set[str] = set()
    hashes: set[str] = set()
    rows = 0
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        header = {"schema": HISTORY_SCHEMA, "schema_version": HISTORY_VERSION, "type": "header", "seed": seed}
        conversation = {"type": "conversation", "conversation_id": "scale-conversation", "title": "Scale benchmark"}
        for value in (header, conversation):
            encoded = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
            digest.update(encoded)
            stream.write(encoded.decode("utf-8"))
        for index in range(count):
            message_id = f"scale-message-{index:06d}"
            content = f"Deterministic scale message {index:06d} seed {seed}."
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            row = {
                "type": "message", "conversation_id": "scale-conversation",
                "message_id": message_id, "role": "user" if index % 2 == 0 else "assistant",
                "content": content, "content_hash": content_hash,
                "timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat().replace("+00:00", "Z"),
            }
            encoded = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
            digest.update(encoded)
            stream.write(encoded.decode("utf-8"))
            rows += 1; ids.add(message_id); hashes.add(content_hash)
    if rows != count or len(ids) != count or len(hashes) != count:
        raise ValueError("scale fixture identity validation failed during generation")
    return {"seed": seed, "messages": count, "message_rows": rows,
            "unique_message_ids": len(ids), "unique_content_hashes": len(hashes),
            "fixture_sha256": digest.hexdigest(), "content_hash": digest.hexdigest(),
            "path": str(path)}


def validate_history_fixture(path: Path, *, expected_count: int, expected_seed: int) -> dict[str, Any]:
    digest = hashlib.sha256(); ids: set[str] = set(); hashes: set[str] = set(); rows = 0
    observed_seed: int | None = None
    with Path(path).open("rb") as stream:
        for raw in stream:
            digest.update(raw); value = json.loads(raw.decode("utf-8"))
            if value.get("type") == "header":
                observed_seed = value.get("seed")
            if value.get("type") != "message":
                continue
            rows += 1; message_id = value.get("message_id"); content = value.get("content")
            content_hash = value.get("content_hash")
            if not isinstance(message_id, str) or not message_id or not isinstance(content, str) or not content:
                raise ValueError("scale fixture contains invalid identity/content")
            if content_hash != hashlib.sha256(content.encode("utf-8")).hexdigest():
                raise ValueError("scale fixture content hash mismatch")
            ids.add(message_id); hashes.add(content_hash)
    if observed_seed != expected_seed or rows != expected_count or len(ids) != expected_count or len(hashes) != expected_count:
        raise ValueError("scale fixture persisted identity counts do not match")
    return {"message_rows": rows, "unique_message_ids": len(ids),
            "unique_content_hashes": len(hashes), "fixture_sha256": digest.hexdigest(),
            "seed": expected_seed}


def run_100k_benchmark(*, output_path: Path, readiness_path: Path | None = None) -> dict[str, Any]:
    """Run the opt-in scale benchmark; quality_gate keeps only a compatibility alias."""
    # Delayed imports keep this isolated helper free of runner import cycles.
    from .quality_gate import (
        _atomic_json, _build_gateway, _build_pipeline, _read_ingestion_rows,
        _reject_protected_output, ensure_4r2_ready_for_scale, load_quality_readiness,
    )
    from src.retrieval.memory_db import MemoryDatabase
    from src.sources.read_model import SourceReadModel
    from src.storage.state_db import StateDatabase
    from .quality_evidence import ProtectedTreeSentinel, cleanup_inventory_after_delete, cleanup_inventory_before_delete
    if readiness_path is None:
        readiness_path = Path(__file__).resolve().parents[2] / "output" / "validation" / "automatic-memory-quality.json"
    ensure_4r2_ready_for_scale(load_quality_readiness(Path(readiness_path)))
    output_path = Path(output_path)
    _reject_protected_output(output_path)
    started = time.perf_counter()
    root = Path(tempfile.mkdtemp(prefix="lingji-acceptance-scale-", dir=str(output_path.parent)))
    try:
        generated = generate_history_fixture(root / "generic-history-scale.jsonl")
        input_path = Path(generated["path"])
        generated.update(validate_history_fixture(input_path, expected_count=100_000, expected_seed=int(generated["seed"])))
        memory_db = MemoryDatabase(root / "storage" / "index" / "lingji_memory.db")
        state_db = StateDatabase(root / "storage" / "state" / "lingji_state.db")
        read_model = SourceReadModel(memory_db)
        pipeline = _build_pipeline(root, memory_db, read_model, state_db)
        protected = root / "protected-boundary"
        protected.mkdir()
        (protected / "sentinel.txt").write_text("scale-boundary\n", encoding="utf-8")
        protected_before = ProtectedTreeSentinel.capture((protected,))
        result = pipeline.execute("generic_ai_history", input_path=input_path, adapter_name="generic_ai_history", execution_id="LJ-SCALE-100K")
        replay = pipeline.execute("generic_ai_history", input_path=input_path, adapter_name="generic_ai_history", execution_id="LJ-SCALE-100K")
        indexer_class = __import__("src.indexer.index", fromlist=["PEMISIndex"]).PEMISIndex
        indexer = indexer_class(root / "vault", root / "storage")
        indexer.build_index()
        index_stats = memory_db.rebuild_from_index(indexer.get_all(), root / "vault")
        ingestion_rows = _read_ingestion_rows(read_model, "LJ-SCALE-100K")
        identity_keys = {(str(row.get("source_external_id") or ""), str(row.get("conversation_external_id") or ""), str(row.get("message_external_id") or "")) for row in ingestion_rows}
        identity_hashes = {str(row.get("content_hash") or "") for row in ingestion_rows}
        replay_rows = _read_ingestion_rows(read_model, "LJ-SCALE-100K")
        replay_identity_keys = {(str(row.get("source_external_id") or ""), str(row.get("conversation_external_id") or ""), str(row.get("message_external_id") or "")) for row in replay_rows}
        imported_count = len(ingestion_rows)
        if imported_count != 100_000 or len(identity_keys) != 100_000 or len(identity_hashes) != 100_000 or identity_keys != replay_identity_keys:
            raise ValueError("scale import/replay identity parity failed")
        gateway, _profiles = _build_gateway(root, memory_db, read_model, state_db)
        latencies: list[float] = []
        context_sizes: list[int] = []
        resident_samples: list[int] = []
        try:
            import resource
            resident_samples.append(int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        except (ImportError, AttributeError, OSError):
            resource = None
        for _ in range(10):
            before = time.perf_counter()
            pack = gateway.build_context_pack("agent-synthetic", query="Deterministic scale message", project=None, max_chars=4000, include_core=False)
            latencies.append((time.perf_counter() - before) * 1000)
            context_sizes.append(len(str(pack.get("markdown") or "")))
            if resource is not None:
                resident_samples.append(int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        ordered = sorted(latencies)
        protected_changes = protected_before.diff(ProtectedTreeSentinel.capture((protected,)))
        cleanup_before = cleanup_inventory_before_delete(root)
        report = {
            **generated, "imported_messages": imported_count,
            "pipeline_result": {"documents": int(result.get("documents") or 0), "structured_messages": int((result.get("structured_read_model") or {}).get("messages") or 0), "index_documents": int(index_stats.get("documents") or 0), "index_chunks": int(index_stats.get("chunks") or 0)},
            "elapsed_seconds": time.perf_counter() - started,
            "p50_ms": ordered[len(ordered) // 2], "p95_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))],
            "hot_retrieval_ms": latencies, "context_pack_sizes": context_sizes,
            "resident_rss_samples": resident_samples, "resident_rss_max": max(resident_samples) if resident_samples else None,
            "resident_rss_unit": "kilobytes on macOS/Linux resource.getrusage",
            "replay": {"documents": int(replay.get("documents") or 0), "structured_messages": int((replay.get("structured_read_model") or {}).get("messages") or 0), "identity_stable": identity_keys == replay_identity_keys},
            "production_pollution": None, "protected_tree_changes": [asdict(change) for change in protected_changes], "vault_mutation": None,
            "cleanup_result": "pending", "cleanup_inventory": cleanup_before,
        }
        shutil.rmtree(root, ignore_errors=False)
        report["cleanup_result"] = "cleaned"
        report["cleanup_inventory"].update(cleanup_inventory_after_delete(root))
        report["cleanup_inventory"]["cleaned"] = not bool(report["cleanup_inventory"].get("root_exists"))
        _atomic_json(output_path, report)
        return report
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


__all__ = [
    "CORPUS_SHA256", "QUESTIONS_SHA256", "build_quality_run_id",
    "readiness_from_envelope", "generate_history_fixture", "validate_history_fixture", "run_100k_benchmark",
]
