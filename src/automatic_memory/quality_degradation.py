"""Small, fail-closed measurement primitives used by the quality runner.

This module contains no retrieval or promotion policy.  It only turns already
produced product payloads into immutable, auditable measurements.
"""
from __future__ import annotations

import json
import hashlib
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from dataclasses import dataclass, field
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
    target_source_ids: tuple[str, ...] = ()
    target_scan_ids: tuple[str, ...] = ()
    target_job_ids: tuple[str, ...] = ()
    queue_status_counts: Mapping[str, int] = field(default_factory=dict)
    work_outcome_counts: Mapping[str, int] = field(default_factory=dict)
    valid_retrieval_identities: tuple[tuple[str, ...], ...] = ()
    bad_leakage_count: int = 0
    reason: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        """Provide a read-only mapping-compatible view for the runner."""
        value = getattr(self, key, default)
        return default if value is None else value

    def __getitem__(self, key: str) -> Any:
        value = self.get(key, None)
        if value is None:
            raise KeyError(key)
        return value


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
        # A declared bound is only evidence when the rendered payload agrees
        # with it.  This catches adapters that report a bound without actually
        # returning the bounded representation.
        for pack in (gateway_pack, mcp_pack):
            markdown = pack.get("markdown")
            if markdown is not None and (not isinstance(markdown, str) or len(markdown) != pack.get("used_chars")):
                return MCPParityMeasurement(False, "bounds_mismatch", gateway_identity, mcp_identity, gateway_used, mcp_used, gateway_max)
        if not gateway_identity and not mcp_identity:
            return MCPParityMeasurement(False, "retrieval_empty", gateway_identity, mcp_identity, gateway_used, mcp_used, gateway_max)
        top_fields = ("schema_version", "agent_id", "query", "project", "query_mode", "mode", "as_of", "scope", "lifecycle", "request")
        for field in top_fields:
            if gateway_pack.get(field) != mcp_pack.get(field):
                return MCPParityMeasurement(False, "schema_mismatch", gateway_identity, mcp_identity, gateway_used, mcp_used, gateway_max)
        if not gateway_identity or gateway_identity != mcp_identity:
            return MCPParityMeasurement(False, "schema_mismatch", gateway_identity, mcp_identity, gateway_used, mcp_used, gateway_max)
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


def measure_corruption_isolation_from_runtime(
    root: Path, pipeline: Any, read_model: Any, state_db: Any,
    *, gateway: Any | None = None,
) -> CorruptionIsolationMeasurement:
    """Compose two authorized sources through scan admission and worker terminal state.

    This is measurement orchestration around the existing runtime contracts;
    it never calls the synchronous pipeline execute API and does not invent a
    queue, WorkStore, or read model.
    """
    from src.automatic_memory.models import AuthorizationScope
    from src.automatic_memory.runtime import AutomaticMemoryRuntime
    from src.automatic_memory.source_registry import SourceRegistry
    valid_root = Path(root) / "authorized-valid-source"
    corrupt_root = Path(root) / "authorized-corrupt-source"
    valid_root.mkdir()
    corrupt_root.mkdir()
    shutil.copyfile(Path(root) / "generic-history-inbox.json", valid_root / "history.json")
    (corrupt_root / "history.json").write_text("{ not a supported history export }\\n", encoding="utf-8")
    registry = SourceRegistry(state_db)
    now = datetime.now(timezone.utc)
    scope = AuthorizationScope(
        grant_id="quality-corruption-isolation", source_kinds=("generic_ai_history",),
        roots=(str(valid_root), str(corrupt_root)), granted_at=now,
        expires_at=None, owner_confirmed=True,
    )
    valid_source = registry.register(scope, "generic_ai_history", str(valid_root))
    corrupt_source = registry.register(scope, "generic_ai_history", str(corrupt_root))
    settings = SimpleNamespace(
        storage_path=Path(root) / "storage", scheduler_poll_seconds=60.0,
        automatic_memory_debounce_seconds=5.0, automatic_memory_reconciliation_seconds=900.0,
        automatic_memory_integrity_seconds=86400.0, automatic_memory_heartbeat_seconds=5.0,
        extraction_poll_seconds=60.0, extraction_batch_size=5,
    )
    runtime = AutomaticMemoryRuntime(state_db=state_db, queue=pipeline.queue, pipeline=pipeline,
                                     settings=settings, registry=registry)
    scan_ids: list[str] = []
    for source in (valid_source, corrupt_source):
        scan = registry.start_scan(source.source_id)
        scan_ids.append(scan.scan_id)
        runtime._run_scan(scan.scan_id, source.source_id, reason="quality-corruption")
    for _ in range(4):
        if pipeline.process_pending(limit=10, worker_id="quality-corruption-worker")["processed"] == 0:
            break
    jobs = [item for item in pipeline.queue.list_page(source_type="automatic_memory_snapshot", limit=100)
            if str((item.get("payload") or {}).get("scan_id") or "") in scan_ids]
    target_job_ids = tuple(sorted(str(item.get("job_id") or "") for item in jobs if item.get("job_id")))
    status_counts: dict[str, int] = {}
    for job in jobs:
        status = str(job.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    outcomes = [runtime.work_store.get_outcome(f"automatic-memory:{scan_id}") for scan_id in scan_ids]
    scans = [state_db.get_automatic_memory_scan(scan_id) for scan_id in scan_ids]
    source_rows = {
        str(source.source_id): source
        for source in registry.list_sources()
        if str(source.source_id) in {valid_source.source_id, corrupt_source.source_id}
    }
    messages = []
    offset = 0
    while True:
        page = read_model.list_messages(owner=True, limit=200, offset=offset)
        messages.extend(page.get("items") or [])
        if not page.get("next_offset"):
            break
        offset = int(page["next_offset"])
    sources = read_model.list_sources(owner=True, limit=100).get("items") or []
    valid_read_model_ids = {
        str(item.get("source_id") or "") for item in sources
        if str((item.get("metadata") or {}).get("automatic_memory_source_id") or "") == valid_source.source_id
    }
    corrupt_read_model_ids = {
        str(item.get("source_id") or "") for item in sources
        if str((item.get("metadata") or {}).get("automatic_memory_source_id") or "") == corrupt_source.source_id
    }
    valid_messages = [item for item in messages if str(item.get("source_id") or "") in valid_read_model_ids]
    corrupt_messages = [item for item in messages if str(item.get("source_id") or "") in corrupt_read_model_ids]

    # The expected compound identities come from the same approved adapter
    # contract as production ingestion, not from the read model being tested.
    from src.extraction.adapters.generic_ai_history import GenericAIHistoryAdapter
    from src.extraction.models import ExtractionRequest
    expected_batch = GenericAIHistoryAdapter().extract(
        ExtractionRequest(
            job_id="quality-corruption-expected",
            source_type="generic_ai_history",
            input_path=valid_root / "history.json",
            payload={"source_id": valid_source.source_id},
            options={"automatic_memory": True},
        )
    )
    expected_identities: set[tuple[str, str, str, str]] = set()
    expected_source_external = expected_batch.structured_sources[0].external_id
    for conversation in expected_batch.structured_sources[0].conversations:
        for message in conversation.messages:
            content_hash = hashlib.sha256(message.content.encode("utf-8")).hexdigest()
            expected_identities.add((
                expected_source_external,
                conversation.external_id,
                message.external_id,
                content_hash,
            ))
    actual_identities: set[tuple[str, str, str, str]] = set()
    for item in valid_messages:
        actual_identities.add((
            str(item.get("source_external_id") or ""),
            str(item.get("conversation_external_id") or ""),
            str(item.get("message_external_id") or item.get("external_id") or ""),
            str(item.get("content_hash") or ""),
        ))
    identity_complete = bool(expected_identities) and actual_identities == expected_identities

    # Exercise the formal lexical and Gateway composition independently.  A
    # fake/non-formal Gateway, an empty response, a wrong source, or a bad
    # source response is therefore a measured failure rather than a boolean
    # shortcut through read-model rows.
    query = ""
    if valid_messages:
        selected = read_model.get_message(str(valid_messages[0].get("message_id") or ""), include_content=True)
        content = str((selected or {}).get("content") or "").strip()
        # Use a stable lexical-safe term from the real message body.  Full
        # sentences can be interpreted as an AND expression by SQLite FTS;
        # selecting one sufficiently distinctive token keeps this probe about
        # source identity, not punctuation parsing.
        query = next((token for token in re.findall(r"[A-Za-z0-9_]{4,}", content)), "")
    lexical_results: list[Mapping[str, Any]] = []
    gateway_results: list[Mapping[str, Any]] = []
    retrieval_reason = "retrieval_unmeasured"
    try:
        database = getattr(read_model, "database", None)
        if not query or database is None or not callable(getattr(database, "search_fts", None)) or gateway is None:
            raise ValueError("formal retrieval composition unavailable")
        lexical_results = list(database.search_fts(
            query, limit=10, memory_types=("structured_evidence",),
            statuses=("active",), privacy=("public", "private", "restricted", "synthetic"),
        ) or [])
        response = gateway.search_memory("agent-synthetic", query, limit=10, memory_types=["structured_evidence"])
        gateway_results = list(response.get("results") or []) if isinstance(response, Mapping) else []
        if not lexical_results or not gateway_results:
            retrieval_reason = "retrieval_empty"
        else:
            retrieval_reason = "retrieval_identity_mismatch"
    except Exception:
        retrieval_reason = "retrieval_error"

    def result_identity(item: Mapping[str, Any]) -> tuple[str, str, str, str]:
        relationships = item.get("relationships")
        relationships = relationships if isinstance(relationships, Mapping) else {}
        citation = item.get("citation")
        citation = citation if isinstance(citation, Mapping) else {}
        def field(name: str) -> str:
            return str(item.get(name) or relationships.get(name) or citation.get(name) or "")
        return (field("source_external_id") or field("source_id"), field("conversation_external_id") or field("conversation_id"), field("message_external_id") or field("external_id") or field("message_id"), field("content_hash"))

    lexical_ids = {result_identity(item) for item in lexical_results if isinstance(item, Mapping)}
    gateway_ids = {result_identity(item) for item in gateway_results if isinstance(item, Mapping)}
    valid_retrieval = tuple(sorted(lexical_ids & gateway_ids & expected_identities))
    bad_external_ids = {
        str(item.get("external_id") or "") for item in sources
        if str((item.get("metadata") or {}).get("automatic_memory_source_id") or "") == corrupt_source.source_id
    }
    bad_leakage = sum(
        1 for item in (*lexical_results, *gateway_results)
        if isinstance(item, Mapping)
        and (
            result_identity(item)[0] in bad_external_ids
            or str(item.get("source_id") or "") in corrupt_read_model_ids
            or str((item.get("relationships") or {}).get("source_id") or "") in corrupt_read_model_ids
            or str((item.get("relationships") or {}).get("automatic_memory_source_id") or "") == corrupt_source.source_id
        )
    )
    retrieval_ok = bool(valid_retrieval) and lexical_ids <= expected_identities and gateway_ids <= expected_identities and bad_leakage == 0

    # Count only the two target jobs and reject any unaccounted target job or
    # non-terminal status.  The exact source-to-job mapping is part of the
    # receipt so extra queued work cannot disappear into a summary counter.
    expected_status_counts = {"completed": 1, "failed": 1}
    queue_ok = (
        len(jobs) == 2
        and len(target_job_ids) == 2
        and status_counts == expected_status_counts
        and {str((item.get("payload") or {}).get("source_id") or "") for item in jobs}
        == {valid_source.source_id, corrupt_source.source_id}
    )
    terminal_work = [outcome.status if outcome else None for outcome in outcomes]
    work_counts = {status: terminal_work.count(status) for status in {"completed", "failed"} if terminal_work.count(status)}
    work_ok = work_counts == expected_status_counts
    for scan_id, outcome, expected_status in zip(scan_ids, outcomes, ("completed", "failed")):
        evidence = outcome.evidence if outcome is not None and isinstance(outcome.evidence, Mapping) else {}
        expected_jobs = {str(item.get("job_id") or "") for item in jobs if str((item.get("payload") or {}).get("scan_id") or "") == scan_id}
        events = runtime.work_store.list_events(f"automatic-memory:{scan_id}", limit=100, ascending=True)
        event_scan = any(str(event.detail.get("scan_id") or "") == scan_id for event in events if isinstance(event.detail, Mapping))
        job_events = [
            event for event in events
            if isinstance(event.detail, Mapping)
            and str(event.detail.get("job_id") or "") in expected_jobs
            and str(event.event_type or "").startswith("extraction.")
        ]
        event_job_ids = {str(event.detail.get("job_id") or "") for event in job_events}
        event_job = len(job_events) == len(expected_jobs) and event_job_ids == expected_jobs
        failed_jobs = {str(value) for value in (evidence.get("failed_jobs") or []) if str(value)}
        raw_evidence_jobs = evidence.get("jobs")
        evidence_jobs = {str(value) for value in raw_evidence_jobs if str(value)} if isinstance(raw_evidence_jobs, (list, tuple, set)) else set()
        evidence_count_ok = isinstance(raw_evidence_jobs, int) and not isinstance(raw_evidence_jobs, bool) and raw_evidence_jobs == len(expected_jobs)
        evidence_ok = (
            ((evidence_jobs == expected_jobs or evidence_count_ok) if expected_status == "completed" else failed_jobs == expected_jobs)
            and (not failed_jobs if expected_status == "completed" else True)
        )
        if outcome is None or outcome.status != expected_status or str(evidence.get("scan_id") or "") != scan_id or not evidence_ok or not event_scan or not event_job:
            work_ok = False

    durable_sources = len(source_rows) == 2
    durable_scans = len(scans) == 2 and all(scan is not None for scan in scans)
    scans_ok = durable_scans and all(str(scan.get("source_id") or "") in {valid_source.source_id, corrupt_source.source_id} and str(scan.get("status") or "") == "completed" for scan in scans)
    conversations = []
    for source_id in valid_read_model_ids:
        page = read_model.list_conversations(source_id=source_id, owner=True, limit=100)
        conversations.extend(page.get("items") or [])
    model_ok = (
        len(sources) == 1
        and len(conversations) == len(expected_batch.structured_sources[0].conversations)
        and all(str(item.get("source_id") or "") in valid_read_model_ids for item in conversations)
        and len(corrupt_messages) == 0
        and identity_complete
    )
    attempted, completed, failed = len(scan_ids), status_counts.get("completed", 0), status_counts.get("failed", 0)
    continued = int(terminal_work.count("completed") == 1)
    retrievable = int(retrieval_ok)
    reasons: list[str] = []
    if not durable_sources or not scans_ok: reasons.append("scan_identity_invalid")
    if not queue_ok: reasons.append("queue_terminal_set_invalid")
    if not work_ok: reasons.append("work_fact_terminal_identity_invalid")
    if not model_ok: reasons.append("read_model_identity_or_leakage")
    if not retrieval_ok: reasons.append(retrieval_reason)
    status = "ready" if not reasons else "failed"
    return CorruptionIsolationMeasurement(
        status=status, attempted=attempted, completed=completed, failed=failed,
        continued=continued, retrievable=retrievable, reasons=tuple(reasons),
        target_source_ids=(valid_source.source_id, corrupt_source.source_id),
        target_scan_ids=tuple(scan_ids), target_job_ids=target_job_ids,
        queue_status_counts=dict(status_counts), work_outcome_counts=dict(work_counts),
        valid_retrieval_identities=valid_retrieval, bad_leakage_count=bad_leakage,
        reason="ready" if status == "ready" else reasons[0],
    )


__all__ = [
    "ContextBaselineMeasurement", "CorruptionIsolationMeasurement", "MCPParityMeasurement",
    "measure_context_baseline", "measure_corruption_isolation", "measure_corruption_isolation_from_runtime", "measure_mcp_parity",
]
