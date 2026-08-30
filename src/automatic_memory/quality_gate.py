"""Real automatic-memory quality and scale gates.

The quality runner intentionally sits above the existing ingestion, source
read-model, promotion, retrieval, gateway and MCP contracts.  It does not
manufacture retrieval answers from the frozen question expectations.
"""

from __future__ import annotations

import hashlib
import asyncio
import inspect
import json
import os
import re
import secrets
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from src.extraction.adapters.generic_ai_history import HISTORY_SCHEMA, HISTORY_VERSION
from src.extraction.adapters.generic_ai_history import GenericAIHistoryAdapter
from src.extraction.models import ExtractionRequest
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.queue import SQLiteExtractionQueue
from src.extraction.registry import AdapterRegistry
from src.extraction.sink import VaultExtractionSink
from src.extraction.structured_sink import StructuredReadModelSink
from src.gateway.memory_gateway import MemoryGateway
from src.gateway.profiles import AIClientProfile, AIProfileRegistry, PROPOSAL_TOOLS
from src.memory.lifecycle import MemoryLifecycleService
from src.memory.vault_layout import VaultLayout
from src.retrieval.context_pack import ContextPackBuilder, ContextPackRequest
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.memory_db import MemoryDatabase
from src.retrieval.source_authority import SourceAuthorityResolver
from src.sources.read_model import SourceReadModel
from src.sources.service import SourceQueryService
from src.storage.state_db import StateDatabase
from .evidence_identity import EvidenceIdentityError, build_identity_registry, select_context_evidence

from .evaluation import (
    AutomaticMemoryAcceptanceGate,
    CorpusRecord,
    EvaluationQuestion,
    EvaluationReport,
)
from .quality_evidence import (
    EvidenceState,
    CanonicalFunctionalEvidence,
    ExpectedImportedRow,
    QualityRunEnvelope,
    ImportedEvidenceAudit,
    QualityPublicationError,
    ProtectedTreeSentinel,
    QualityEvidenceReadiness,
    finalize_quality_envelope,
    write_quality_json_atomic,
    _read_ingestion_rows,
    build_expected_import_rows,
    cleanup_inventory_before_delete,
    cleanup_inventory_after_delete,
    count_memory_projection_duplicates,
)
from .quality_degradation import measure_context_baseline, measure_mcp_parity, measure_corruption_isolation_from_runtime, measure_semantic_degradation
from .quality_promotion import activation_measurement, measure_promotion_fixtures
from .quality_oracle import (
    FrozenQuestionOracle,
    QuestionCheckpointStore,
    load_frozen_fixtures,
    observation_from_context_pack,
)
from .scale_benchmark import readiness_from_envelope, generate_history_fixture


FUNCTIONAL_BLOCKED_REASONS = (
    "owner_review_not_run_in_automated_gate",
    "reboot_recovery_not_run_in_automated_gate",
    "mac_m5_p95_reserved_for_task_6",
    "mac_idle_cpu_reserved_for_task_6",
)
CORPUS_SHA256 = "2a3ea2c14af9e1705a39673efb50826579f35b484f9d6c5442cb40f5f8f2347a"
QUESTIONS_SHA256 = "35000a5cc56de84ef3caa82114a1b9168e46c1d3b31fd89ba0f2a740ce6f9e31"
_SELECTOR_LIMIT = 2  # One fixed, question-independent selector for every query.
EXPECTED_QUESTION_COUNT = 100


class AcceptanceCleanupError(RuntimeError):
    """The isolated acceptance tree could not be removed safely."""

    def __init__(self, code: str = "TEMP_CLEANUP_FAILED") -> None:
        self.code = str(code)
        super().__init__(self.code)


class QualityScaleBlockedError(RuntimeError):
    """The 100k scale benchmark is not available during the reset phase."""


_RUNNER_STAGES = (
    "admission", "root", "sentinel", "fixture", "import", "gateway",
    "promotion", "audit", "scoring", "evaluator", "publication_pre", "cleanup",
)


class _RunnerStageTracker:
    """Track the last bounded runner stage without retaining exception data."""

    def __init__(self, hook: Callable[[str], None] | None = None) -> None:
        self.current = "admission"
        self._hook = hook

    def mark(self, stage: str) -> None:
        if stage not in _RUNNER_STAGES:
            stage = "root"
        self.current = stage
        if self._hook is not None:
            self._hook(stage)


@dataclass(frozen=True)
class AcceptanceRoots:
    root: Path
    storage_root: Path
    vault_root: Path
    output_root: Path
    lease_marker: Path
    allowed_base: Path | None = None
    lease_token: str | None = None
    cleanup_inventory: dict[str, Any] | None = None

    def validate_temporary_isolation(self) -> None:
        declared_root = self.root.expanduser()
        if not declared_root.is_absolute() or declared_root.is_symlink():
            raise ValueError("invalid acceptance root")
        root = declared_root.resolve(strict=False)
        if not root.name.startswith("lingji-task4r-"):
            raise ValueError("invalid acceptance root")
        base = (self.allowed_base or Path(tempfile.gettempdir())).expanduser().resolve()
        try:
            root.relative_to(base)
        except ValueError as exc:
            raise ValueError("acceptance root outside allowed temporary base") from exc
        if not root.exists() or not root.is_dir() or root.is_symlink():
            raise ValueError("acceptance root unavailable")
        root_mode = root.stat().st_mode
        if root_mode & 0o444 == 0 or root_mode & 0o111 == 0:
            raise ValueError("acceptance root lacks read/traverse access")
        try:
            os.listdir(root)
        except OSError as exc:
            raise ValueError("acceptance root is not readable/traversable") from exc
        children = (self.storage_root, self.vault_root, self.output_root, self.lease_marker)
        for child in children:
            path = child.expanduser()
            if any(part.is_symlink() for part in (Path(path.anchor), *path.parents, path) if part.exists()):
                raise ValueError("acceptance path cannot be a symlink")
            resolved = path.resolve(strict=False)
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise ValueError("acceptance path escapes root") from exc
        for directory in (self.storage_root, self.vault_root, self.output_root):
            if not directory.exists() or not directory.is_dir():
                raise ValueError("acceptance child unavailable")
            mode = directory.stat().st_mode
            # Do not rely on os.access: the acceptance runner may execute as
            # root, for which mode-000 paths can still appear accessible.
            if mode & 0o444 == 0 or mode & 0o111 == 0:
                raise ValueError("acceptance child lacks read/traverse access")
            try:
                os.listdir(directory)
            except OSError as exc:
                raise ValueError("acceptance child is not readable/traversable") from exc
        if not self.lease_marker.exists() or not self.lease_marker.is_file():
            raise ValueError("acceptance lease marker unavailable")
        if self.lease_marker.stat().st_mode & 0o444 == 0:
            raise ValueError("acceptance lease marker is not readable")
        if self.lease_token is None:
            raise ValueError("acceptance lease token unavailable")
        if self.lease_marker.read_text(encoding="utf-8") != self.lease_token:
            raise ValueError("acceptance lease marker invalid")
        if hasattr(os, "getuid") and self.lease_marker.stat().st_uid != os.getuid():
            raise ValueError("acceptance lease owner invalid")


@contextmanager
def temporary_acceptance_roots(*, base_directory: Path | None = None):
    """Create and always remove one isolated reset acceptance tree."""
    base = Path(base_directory).expanduser().resolve() if base_directory is not None else None
    root: Path | None = None
    try:
        root = Path(tempfile.mkdtemp(prefix="lingji-task4r-", dir=str(base) if base else None)).resolve()
        token = secrets.token_hex(32)
        roots = AcceptanceRoots(
            root=root,
            storage_root=root / "storage",
            vault_root=root / "vault",
            output_root=root / "output",
            lease_marker=root / ".lease",
            allowed_base=base,
            lease_token=token,
        )
        roots.storage_root.mkdir()
        roots.vault_root.mkdir()
        roots.output_root.mkdir()
        roots.lease_marker.write_text(token, encoding="utf-8")
        roots.validate_temporary_isolation()
        yield roots
    finally:
        if root is not None and root.exists():
            object.__setattr__(roots, "cleanup_inventory", cleanup_inventory_before_delete(root))
            try:
                shutil.rmtree(root, ignore_errors=False)
                roots.cleanup_inventory.update(cleanup_inventory_after_delete(root))
                roots.cleanup_inventory["cleaned"] = not bool(roots.cleanup_inventory.get("root_exists"))
            except Exception as exc:
                if roots.cleanup_inventory is None:
                    object.__setattr__(roots, "cleanup_inventory", {"root_exists": True, "error": "TEMP_CLEANUP_FAILED"})
                else:
                    roots.cleanup_inventory.update(cleanup_inventory_after_delete(root))
                    roots.cleanup_inventory["cleaned"] = False
                raise AcceptanceCleanupError() from exc


def cleanup_failure_envelope(
    _report: Any, error: AcceptanceCleanupError, *, roots: AcceptanceRoots | None = None,
) -> QualityRunEnvelope:
    values = {field: EvidenceState.NOT_MEASURED for field in (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
        "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
    )}
    readiness = QualityEvidenceReadiness(**values)
    known_codes = {"TEMP_CLEANUP_FAILED", "TEMP_CLEANUP_INCOMPLETE"}
    code = error.code if type(error.code) is str and error.code in known_codes else "UNTRUSTED_BLOCKED_REASON"
    return QualityRunEnvelope(
        readiness, None, None, "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED", (code,),
        _cleanup_inventory(roots),
    )


def _cleanup_inventory(roots: AcceptanceRoots | None) -> dict[str, Any]:
    """Return path-free cleanup facts suitable for a failure envelope."""
    if roots is None:
        return {
            "root_exists": False, "storage_exists": False, "vault_exists": False,
            "output_exists": False, "lease_marker_exists": False, "cleaned": False,
        }
    if roots.cleanup_inventory is not None:
        return dict(roots.cleanup_inventory)
    return {"root_exists": os.path.lexists(os.fspath(roots.root)), "cleaned": False}


def load_quality_readiness(path: Path) -> QualityEvidenceReadiness:
    """Load the persisted functional readiness used by the scale admission gate."""
    try:
        return readiness_from_envelope(Path(path))
    except ValueError as exc:
        raise QualityScaleBlockedError("BLOCKED_4R2_REQUIRED") from exc


def runner_failure_envelope(
    stage: str = "root", *, roots: AcceptanceRoots | None = None,
) -> QualityRunEnvelope:
    """Build a sanitized fail-closed envelope for any runner-stage exception."""
    normalized = stage.upper() if stage in _RUNNER_STAGES else "FAILED"
    reason = f"RUNNER_{normalized}_FAILED"
    readiness = QualityEvidenceReadiness(**{
        field: EvidenceState.NOT_MEASURED for field in (
            "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
            "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
            "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
        )
    })
    return QualityRunEnvelope(
        readiness, None, None, "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED",
        (reason,), _cleanup_inventory(roots),
    )


def verify_acceptance_cleanup(roots: AcceptanceRoots) -> None:
    leftovers = tuple(
        path for path in (
            roots.storage_root, roots.vault_root, roots.output_root,
            roots.lease_marker, roots.root,
        ) if os.path.lexists(os.fspath(path))
    )
    if leftovers:
        raise AcceptanceCleanupError("TEMP_CLEANUP_INCOMPLETE")


def ensure_4r2_ready_for_scale(readiness: QualityEvidenceReadiness) -> None:
    """Allow scale only after the measured functional 4R2 prerequisites.

    Scale is a Task7 evidence run. Owner review, reboot and platform release
    evidence belong to the later Task8/Mac gates and must not be part of this
    admission check (otherwise the release gate becomes circular).
    """
    if not isinstance(readiness, QualityEvidenceReadiness) or not readiness.scale_ready:
        raise QualityScaleBlockedError("BLOCKED_4R2_REQUIRED")


def run_release_preflight(
    readiness: QualityEvidenceReadiness,
    *,
    prepare_scale_environment: Any | None = None,
    run_scale_command: Any | None = None,
) -> None:
    """Authorize release sequencing before constructing scale callbacks.

    PowerShell 5.1 calls the Python CLI preflight.  Keeping the admission
    check and callback ordering here makes the boundary directly testable on
    hosts without PowerShell and guarantees a blocked release cannot invoke
    the 100k environment or command callbacks.
    """
    ensure_4r2_ready_for_scale(readiness)
    if prepare_scale_environment is not None:
        prepare_scale_environment()
    if run_scale_command is not None:
        run_scale_command()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_protected_output(output_path: Path) -> None:
    """Reject benchmark output inside an admitted temporary acceptance tree."""
    candidate = Path(output_path).expanduser().resolve(strict=False)
    temp_root = Path(tempfile.gettempdir()).resolve()
    if candidate.is_relative_to(temp_root) and any(
        part.startswith("lingji-task4r-") for part in candidate.parts
    ):
        raise ValueError("quality output cannot be written inside Acceptance roots")


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_quality_json_atomic(path, value, protected_roots=())


def _history_fixture(corpus: Sequence[CorpusRecord], path: Path) -> None:
    conversations = [
        {
            "conversation_id": record.conversation_id,
            "title": record.topic_key,
            "messages": [
                {
                    "message_id": record.message_id,
                    "role": record.role,
                    "content": record.content,
                    "timestamp": record.occurred_at,
                }
            ],
        }
        for record in corpus
    ]
    payload = {"schema": HISTORY_SCHEMA, "schema_version": HISTORY_VERSION, "conversations": conversations}
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _opaque_memory_id(record: CorpusRecord) -> str:
    """Derive a private persisted identity from production evidence inputs."""
    material = {
        "source_id": record.source_id,
        "conversation_id": record.conversation_id,
        "message_id": record.message_id,
        "content_hash": record.content_hash,
    }
    digest = hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()
    return f"LJ-MEM-{digest[:32]}"


def _build_pipeline(root: Path, memory_db: MemoryDatabase, read_model: SourceReadModel, state_db: StateDatabase) -> ExtractionPipeline:
    layout = VaultLayout(root / "vault")
    layout.ensure()
    registry = AdapterRegistry()
    registry.register(GenericAIHistoryAdapter())
    queue = SQLiteExtractionQueue(root / "storage" / "state" / "lingji_state.db")
    sink = VaultExtractionSink(layout, root / "storage", state_db=state_db)
    structured_sink = StructuredReadModelSink(
        read_model,
        storage_path=root / "storage",
        state_db=state_db,
        memory_database=memory_db,
    )
    return ExtractionPipeline(queue, registry, sink, structured_sink=structured_sink)


def _build_gateway(
    root: Path,
    memory_db: MemoryDatabase,
    read_model: SourceReadModel,
    state_db: StateDatabase,
    *,
    semantic_provider: Any | None = None,
) -> tuple[MemoryGateway, AIProfileRegistry]:
    profile = AIClientProfile(
        "agent-synthetic",
        "Synthetic Evaluation Agent",
        "internal",
        PROPOSAL_TOOLS,
        ("public", "private", "restricted", "synthetic"),
        12000,
        can_read_other_projects=False,
        local_only=True,
    )
    profiles = AIProfileRegistry([profile])
    retriever = HybridRetriever(
        memory_db,
        semantic_provider=semantic_provider,
        source_authority=SourceAuthorityResolver(state_db),
    )
    source_service = SourceQueryService(
        read_model,
        workspace="acceptance",
        vault_path=root / "vault",
        raw_path=root / "storage" / "raw",
        profiles=profiles,
    )
    gateway = MemoryGateway(
        memory_db,
        retriever,
        ContextPackBuilder(memory_db, retriever, source_read_model=read_model, source_query_service=source_service),
        MemoryLifecycleService(VaultLayout(root / "vault"), state_db),
        profiles=profiles,
        state_db=state_db,
    )
    return gateway, profiles


def _promote_fixtures(
    corpus: Sequence[CorpusRecord],
    message_map: Mapping[str, Mapping[str, Any]],
    memory_db: MemoryDatabase,
    read_model: SourceReadModel,
    state_db: StateDatabase,
) -> tuple[dict[str, dict[str, Any]], int | None, int | None, dict[str, str], dict[str, int]]:
    """Compatibility shim for historical evaluator callers.

    The runner no longer calls this legacy orchestration helper; promotion
    measurement lives in :mod:`quality_promotion`.  Keep the old import
    contract while delegating without maintaining a second implementation.
    """
    bindings = {_opaque_memory_id(record): str(record.fact_id) for record in corpus}
    if len(bindings) != len(corpus):
        raise ValueError("opaque memory ID collision")
    measured_map = {
        str(record.fact_id): {**dict(message_map.get(str(record.fact_id)) or {}), "promotion_memory_id": _opaque_memory_id(record)}
        for record in corpus
    }
    measurement = measure_promotion_fixtures(corpus, measured_map, memory_db, read_model, state_db)
    decisions = {item["fact_id"]: item for item in measurement.outcomes}
    outcomes = {status: 0 for status in ("active", "pending_owner_review", "rejected", "error")}
    for item in measurement.outcomes:
        status = str(item.get("status") or "error")
        outcomes[status] = outcomes.get(status, 0) + 1
    return decisions, None, None, bindings, outcomes


def _build_formal_mcp_server(gateway: MemoryGateway, pipeline: ExtractionPipeline) -> Any:
    """Build the production MCP registration, rather than a test closure."""
    from src.mcp_server import create_mcp_server

    # A context service is not exercised by the quality query, but supplying a
    # sentinel keeps this runner from silently constructing another gateway.
    return create_mcp_server(
        gateway=gateway,
        extraction_pipeline=pipeline,
        codex_service=object(),
        project_context_service=object(),
        default_agent_id="agent-synthetic",
    )


def _call_formal_mcp(server: Any, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
    """Call the registered production tool and normalize its result."""
    call_tool = getattr(server, "call_tool", None)
    if not callable(call_tool):
        raise TypeError("formal MCP server does not expose call_tool")
    result = call_tool("build_context_pack", dict(arguments))
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    # FastMCP's public call path returns ``(content, metadata)`` while the
    # registered function itself returns a mapping. Metadata is diagnostics,
    # never a substitute for the tool payload.
    if (
        isinstance(result, tuple)
        and len(result) == 2
        and isinstance(result[0], Sequence)
        and not isinstance(result[0], (str, bytes))
    ):
        result = result[0]
    if isinstance(result, Mapping):
        return result
    # FastMCP returns ContentBlocks for the registered invocation.  Only a
    # JSON text block is accepted; arbitrary repr/text is not evidence.
    if isinstance(result, Sequence) and not isinstance(result, (str, bytes)):
        for block in result:
            text_value = getattr(block, "text", None)
            if not isinstance(text_value, str):
                continue
            try:
                decoded = json.loads(text_value)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, Mapping):
                return decoded
    raise ValueError("formal MCP returned no structured context pack")


def _match_persisted_messages(
    corpus: Sequence[CorpusRecord],
    read_model: SourceReadModel,
    *,
    ingestion_batch_id: str,
    expected_rows: Sequence[ExpectedImportedRow],
) -> dict[str, dict[str, Any]]:
    """Resolve one persisted row per corpus fact using its full external key."""
    if len(corpus) != len(expected_rows):
        raise ValueError("corpus and expected import rows have different lengths")
    by_key: dict[Any, dict[str, Any]] = {}
    for item in _read_ingestion_rows(read_model, ingestion_batch_id):
        if not all(str(item.get(field) or "") for field in ("source_id", "conversation_id", "message_id")):
            raise ValueError("persisted composite message row has empty primary identity")
        key = (
            str(item.get("source_external_id") or ""),
            str(item.get("conversation_external_id") or ""),
            str(item.get("message_external_id") or ""),
        )
        if key in by_key:
            raise ValueError("ambiguous duplicate persisted composite message key")
        by_key[key] = dict(item)
    matched: dict[str, dict[str, Any]] = {}
    bound_keys: set[tuple[str, str, str]] = set()
    for record, expected in zip(corpus, expected_rows):
        fact_id = str(record.fact_id or "")
        if not fact_id or fact_id in matched:
            raise ValueError("ambiguous evaluation fact binding")
        key = (
            expected.source_external_id,
            expected.conversation_external_id,
            expected.message_external_id,
        )
        if key in bound_keys:
            raise ValueError("ambiguous duplicate expected composite message key")
        bound_keys.add(key)
        item = by_key.get(key)
        if item is None:
            raise ValueError(f"missing persisted composite message key: {key}")
        matched[fact_id] = item
    return matched


def validate_selected_evidence(
    *, recalled: Sequence[str], citations: Sequence[str], expected: Sequence[str],
    forbidden: Sequence[str], expected_citations: Sequence[str],
) -> None:
    recalled_set = set(recalled)
    if len(recalled_set) != len(tuple(recalled)):
        raise ValueError("duplicate fact evidence")
    if set(recalled) & set(forbidden):
        raise ValueError("forbidden fact evidence")
    if set(recalled) - set(expected):
        raise ValueError("extra fact evidence")
    citation_set = set(citations)
    if len(citation_set) != len(tuple(citations)):
        raise ValueError("duplicate citation evidence")
    if citation_set - set(expected_citations):
        raise ValueError("extra or unknown citation evidence")


def _run_quality_gate_impl(
    corpus_path: Path,
    questions_path: Path,
    *,
    output_path: Path,
    acceptance_roots: AcceptanceRoots,
    stage_tracker: _RunnerStageTracker | None = None,
) -> tuple[EvaluationReport | None, dict[str, Any]]:
    """Run the frozen 100-question contracts inside admitted roots."""
    tracker = stage_tracker or _RunnerStageTracker()
    corpus_path = Path(corpus_path).expanduser()
    questions_path = Path(questions_path).expanduser()
    output_path = Path(output_path).expanduser()
    tracker.mark("admission")
    acceptance_roots.validate_temporary_isolation()
    try:
        output_path.resolve(strict=False).relative_to(acceptance_roots.output_root.resolve())
    except ValueError as exc:
        raise ValueError("quality output must be inside Acceptance output root") from exc
    tracker.mark("root")
    tracker.mark("sentinel")
    tracker.mark("fixture")
    frozen_fixture = load_frozen_fixtures(corpus_path, questions_path)
    corpus = frozen_fixture.corpus
    questions = frozen_fixture.questions
    fixture_hashes = dict(frozen_fixture.file_hashes)
    if fixture_hashes != {"corpus": CORPUS_SHA256, "questions": QUESTIONS_SHA256}:
        raise ValueError("frozen fixture hash mismatch")

    temporary_root = acceptance_roots.root
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # The protected tree is an acceptance-only stand-in for the production
    # boundary. It is never the owner's Vault or a third-party application
    # directory, but it gives this run an actual recursive no-write receipt.
    protected_root = temporary_root / "protected-boundary"
    protected_root.mkdir()
    (protected_root / "sentinel.txt").write_text("unchanged\\n", encoding="utf-8")
    protected_before: ProtectedTreeSentinel | None = ProtectedTreeSentinel.capture((protected_root,))
    protected_tree_capture_error: str | None = None
    production_sentinels_before: dict[str, str] = {}
    production_sentinels_after: dict[str, str] = {}
    message_map: dict[str, dict[str, Any]] = {}
    decisions: dict[str, dict[str, Any]] = {}
    stale_leaks = 0
    duplicate_records = 0
    ordered_role_matches = 0
    expected_ordered_roles = len(corpus)
    imported_messages = 0
    activation_correct = 0
    activation_total = 0
    gateway_calls_completed = 0
    gateway_selector_calls = 0
    gateway_empty_responses = 0
    gateway_selected_evidence = 0
    mcp_attempts = 0
    mcp_successes = 0
    mcp_parity_failures: list[str] = []
    question_results: list[Any] = []
    question_diagnostics: list[Any] = []
    grouped_question_metrics: dict[str, dict[str, int]] = {}
    baseline_context_chars = 0
    baseline_available = True
    rendered_context_chars = 0
    semantic_degradation: dict[str, Any] = {"status": "not_measured"}
    corruption_isolation: dict[str, Any] = {"status": "not_measured"}
    try:
        tracker.mark("fixture")
        fixture_input = temporary_root / "generic-history-inbox.json"
        _history_fixture(corpus, fixture_input)
        adapter_batch = GenericAIHistoryAdapter().extract(ExtractionRequest(
            job_id="quality-expected-projection",
            source_type="generic_ai_history",
            input_path=fixture_input,
        ))
        ingestion_batch_id = "quality-expected-projection"
        expected_rows = build_expected_import_rows(adapter_batch)
        memory_db = MemoryDatabase(temporary_root / "storage" / "index" / "lingji_memory.db")
        state_db = StateDatabase(temporary_root / "storage" / "state" / "lingji_state.db")
        read_model = SourceReadModel(memory_db)
        tracker.mark("import")
        pipeline = _build_pipeline(temporary_root, memory_db, read_model, state_db)
        pipeline.execute(
            "generic_ai_history",
            input_path=fixture_input,
            adapter_name="generic_ai_history",
            execution_id=ingestion_batch_id,
        )
        indexer = __import__("src.indexer.index", fromlist=["PEMISIndex"]).PEMISIndex(
            temporary_root / "vault", temporary_root / "storage"
        )
        indexer.build_index()
        memory_db.rebuild_from_index(indexer.get_all(), temporary_root / "vault")
        message_map = _match_persisted_messages(
            corpus,
            read_model,
            ingestion_batch_id=ingestion_batch_id,
            expected_rows=expected_rows,
        )
        tracker.mark("audit")
        audit = ImportedEvidenceAudit.from_read_model(
            read_model,
            ingestion_batch_id=ingestion_batch_id,
            expected_rows=expected_rows,
        )
        imported_messages = audit.actual_rows
        ordered_role_matches = audit.role_matches
        tracker.mark("promotion")
        promotion_map = {
            str(record.fact_id): {**dict(message_map.get(str(record.fact_id)) or {}), "promotion_memory_id": _opaque_memory_id(record)}
            for record in corpus
        }
        promotion_measurement = measure_promotion_fixtures(
            corpus, promotion_map, memory_db, read_model, state_db
        )
        decisions = {item["fact_id"]: item for item in promotion_measurement.outcomes}
        activation = activation_measurement(promotion_measurement.outcomes)
        activation_correct = activation["correct"]
        activation_total = activation["total"]
        promotion_outcomes: dict[str, int] = {"active": 0, "pending_owner_review": 0, "rejected": 0, "error": 0}
        for item in promotion_measurement.outcomes:
            status = str(item.get("status") or "error")
            promotion_outcomes[status] = promotion_outcomes.get(status, 0) + 1
        promotion_category_outcomes = dict(promotion_measurement.category_outcomes)
        promotion_provenance = dict(promotion_measurement.provenance)
        promotion_bindings = {
            _opaque_memory_id(record): str(record.fact_id)
            for record in corpus
        }
        duplicate_records = audit.stable_duplicates.total + count_memory_projection_duplicates(memory_db)
        tracker.mark("gateway")
        gateway, _profiles = _build_gateway(temporary_root, memory_db, read_model, state_db)
        formal_mcp = _build_formal_mcp_server(gateway, pipeline)
        persisted_identity_rows: list[dict[str, Any]] = []
        for record in corpus:
            row = message_map.get(record.fact_id)
            if row is None:
                raise ValueError(f"missing promoted persisted message for {record.fact_id}")
            identity_row = dict(row)
            # The composite binding is an in-memory bridge between the frozen
            # corpus identity and the real persisted row; it never enters
            # SourceReadModel or candidate metadata.
            identity_row.update({
                "corpus_source_id": record.source_id,
                "corpus_conversation_id": record.conversation_id,
                "corpus_message_id": record.message_id,
            })
            persisted_identity_rows.append(identity_row)
        message_links: list[dict[str, Any]] = []
        for row in persisted_identity_rows:
            message_links.extend(read_model.message_links(str(row["message_id"])))
        identity_registry = build_identity_registry(
            corpus=corpus,
            persisted_messages=persisted_identity_rows,
            promotion_bindings=promotion_bindings,
            message_links=message_links,
        )
        runtime_bindings = {
            (identity.source_id, identity.conversation_id, identity.message_id): binding
            for identity, binding in identity_registry.message_to_fact_citation.items()
        }
        fact_by_memory = {item.fact_id: item for item in corpus}
        citation_ids = {item.citation_id for item in corpus}
        oracle = FrozenQuestionOracle(frozen_fixture, runtime_bindings=runtime_bindings)
        checkpoint_store = QuestionCheckpointStore(
            temporary_root / "output" / "question-results",
            fixture_hashes=fixture_hashes,
            run_id=f"quality:{fixture_hashes['corpus'][:16]}:{fixture_hashes['questions'][:16]}:{_git_commit()[:16]}",
            code_commit=_git_commit(),
            questions=questions,
        )
        for question in questions:
            checkpoint = checkpoint_store.load(question.question_id, question=question)
            if checkpoint is not None:
                # A restart reuses the atomic result and does not invoke either
                # production surface again.  Aggregate counters are recovered
                # from the bounded diagnostic rather than from caller state.
                question_diagnostics.append(checkpoint)
                question_results.append(checkpoint)
                gateway_calls_completed += 1
                gateway_selector_calls += 1
                gateway_selected_evidence += len(checkpoint.gateway_identities)
                mcp_attempts += 1
                mcp_successes += int(not checkpoint.mcp_reason.startswith("mcp_parity:"))
                continue
            arguments = {
                "query": question.query,
                "agent_id": "agent-synthetic",
                "project": "project-lingji",
                "max_chars": question.max_chars,
                "include_core": False,
                "mode": question.mode,
                "as_of": question.as_of,
            }
            try:
                # Capture the formal builder's selection-before-bound seam.  This
                # is the same query/filter path used by build_context_pack and is
                # intentionally observed before render_markdown applies max_chars.
                observation = gateway.context_builder.observe_candidates(ContextPackRequest(
                    agent_id=str(arguments["agent_id"]), query=str(arguments["query"]),
                    project=arguments.get("project"), max_chars=int(arguments["max_chars"]),
                    privacy=("public", "private", "restricted", "synthetic"), include_core=False,
                    mode=str(arguments.get("mode") or "current"), as_of=arguments.get("as_of"),
                ))
                baseline_payload = list(observation.get("sections") or []) if isinstance(observation, Mapping) else []
                if not baseline_payload:
                    baseline_available = False
                else:
                    baseline_measurement = measure_context_baseline(baseline_payload, bounded_pack=None)
                    baseline_context_chars += baseline_measurement.baseline_chars
                gateway_pack = gateway.build_context_pack(**arguments)
                gateway_calls_completed += 1
                if not isinstance(gateway_pack, Mapping):
                    raise ValueError("malformed Gateway response")
                gateway_sections = gateway_pack.get("sections")
                if isinstance(gateway_sections, (str, bytes)) or not isinstance(gateway_sections, Sequence):
                    raise ValueError("malformed Gateway sections")
                gateway_empty_responses += int(not gateway_sections)
                tracker.mark("scoring")
                selected_evidence = select_context_evidence(gateway_pack, identity_registry, limit=_SELECTOR_LIMIT)
                gateway_selector_calls += 1
                unknown_facts = tuple(fact_id for fact_id in selected_evidence.fact_ids if fact_id not in fact_by_memory)
                unknown_citations = tuple(citation_id for citation_id in selected_evidence.citation_ids if citation_id not in citation_ids)
                if unknown_facts or unknown_citations:
                    raise EvidenceIdentityError(
                        "selector returned unknown evidence identities: "
                        f"facts={unknown_facts!r}, citations={unknown_citations!r}"
                    )
                gateway_selected_evidence += len(selected_evidence.fact_ids)
                gateway_used = gateway_pack.get("used_chars")
                if not isinstance(gateway_used, int) or isinstance(gateway_used, bool) or gateway_used < 0:
                    raise ValueError("Gateway ContextPack used_chars is not measured")
                if gateway_used > int(arguments["max_chars"]):
                    raise ValueError("Gateway ContextPack exceeds its declared bound")
                rendered_context_chars += gateway_used
                mcp_attempts += 1
                mcp_pack = _call_formal_mcp(formal_mcp, arguments)
                mcp_used = mcp_pack.get("used_chars")
                if not isinstance(mcp_used, int) or isinstance(mcp_used, bool) or mcp_used < 0:
                    raise ValueError("formal MCP ContextPack used_chars is not measured")
                if mcp_used > int(arguments["max_chars"]):
                    raise ValueError("formal MCP ContextPack exceeds its declared bound")
                parity = measure_mcp_parity(gateway_pack, mcp_pack)
                if not parity.success:
                    mcp_parity_failures.append(parity.reason)
                mcp_selected = select_context_evidence(mcp_pack, identity_registry, limit=_SELECTOR_LIMIT)
                selected_parity = (
                    mcp_selected.fact_ids == selected_evidence.fact_ids
                    and mcp_selected.citation_ids == selected_evidence.citation_ids
                )
                if not selected_parity:
                    mcp_parity_failures.append("selected_evidence_mismatch")
                if parity.success and selected_parity:
                    mcp_successes += 1
                gateway_observation = observation_from_context_pack(
                    gateway_pack, frozen_fixture, selected_evidence.fact_ids, selected_evidence.citation_ids,
                    runtime_bindings=runtime_bindings,
                )
                mcp_observation = observation_from_context_pack(
                    mcp_pack, frozen_fixture, mcp_selected.fact_ids, mcp_selected.citation_ids,
                    reason_override=(
                        f"mcp_parity:{parity.reason}"
                        if not parity.success or not selected_parity else None
                    ),
                    runtime_bindings=runtime_bindings,
                )
                diagnostic = oracle.evaluate(
                    question, gateway=gateway_observation, mcp=mcp_observation
                )
            except Exception as exc:
                diagnostic = oracle.exception_diagnostic(question, exc)
            question_diagnostics.append(diagnostic)
            checkpoint_store.save(diagnostic, question=question)
            question_results.append(diagnostic)
        semantic_degradation = measure_semantic_degradation(
            temporary_root, memory_db, read_model, state_db, questions[0].query,
            gateway_builder=_build_gateway,
        )
        corruption_measurement = measure_corruption_isolation_from_runtime(
            temporary_root, pipeline, read_model, state_db, gateway=gateway,
        )
        corruption_isolation = asdict(corruption_measurement)
        protected_after = ProtectedTreeSentinel.capture((protected_root,))
        acceptance_sentinels_before = {
            key: asdict(value) for key, value in protected_before.entries.items()
        }
        acceptance_sentinels_after = {
            key: asdict(value) for key, value in protected_after.entries.items()
        }
        acceptance_changes = (
            protected_before.diff(protected_after)
            if protected_before is not None and protected_after is not None and not protected_tree_capture_error
            else ()
        )
        # The protected tree is an Acceptance-only boundary.  It is not the
        # owner's Vault or a third-party production directory, so this run can
        # never produce a production-pollution integer.
        production_pollution = None
        tracker.mark("evaluator")
        if len(question_results) != EXPECTED_QUESTION_COUNT:
            raise ValueError("quality evaluation did not execute all frozen questions")
        by_question_id = {item.question_id: item for item in questions}
        valid_fact_hits = sum(
            len(set(item.mcp_fact_ids) & set(by_question_id[item.question_id].expected_fact_ids))
            for item in question_results
        )
        valid_fact_total = sum(len(item.expected_fact_ids) for item in questions)
        # Citation accuracy is intentionally computed from the immutable
        # identity stream rather than rendered text.  A selected identity is
        # citation-correct only when its fixture citation is expected.
        citation_hits = sum(
            sum(1 for identity in item.mcp_identities
                if identity.citation_id in set(by_question_id[item.question_id].expected_citation_ids))
            for item in question_results
        )
        citation_total = sum(len(item.expected_citation_ids) for item in questions)
        grouped_question_metrics = {}
        for item in question_results:
            group = grouped_question_metrics.setdefault(item.category, {"questions": 0, "passed": 0, "failed": 0})
            group["questions"] += 1
            group["passed"] += int(item.passed)
            group["failed"] += int(not item.passed)
            for bucket in item.failure_buckets:
                group[bucket] = group.get(bucket, 0) + 1
        # A missing selection-before-bound observation is not a zero-length
        # baseline.  Keep the unavailable measurement nullable all the way to
        # the persisted envelope so downstream admission cannot mistake it
        # for a measured result.
        measured_baseline_chars = baseline_context_chars if baseline_available and baseline_context_chars > 0 else None
        measured_rendered_chars = rendered_context_chars if measured_baseline_chars is not None else None
        context_reduction = (
            (1 - measured_rendered_chars / measured_baseline_chars) * 100
            if measured_baseline_chars is not None and measured_rendered_chars is not None
            else None
        )
        measured_quality_failure = (
            valid_fact_total <= 0 or 100 * valid_fact_hits / valid_fact_total < 90
            or citation_total <= 0 or 100 * citation_hits / citation_total < 95
            or mcp_attempts <= 0 or 100 * mcp_successes / mcp_attempts < 95
            or context_reduction is None or context_reduction < 90
        )
        # EvaluationReport deliberately requires a production integer.  Since
        # production is not measurable from this isolated run, preserve the
        # raw per-question counters below and leave the frozen report absent.
        report = None
        readiness = QualityEvidenceReadiness(
            import_audit=EvidenceState.READY if audit.ready else EvidenceState.FAILED,
            promotion_provenance=EvidenceState.READY if promotion_measurement.status == "ready" else EvidenceState.FAILED,
            gateway_selection=EvidenceState.READY if (
                gateway_calls_completed == EXPECTED_QUESTION_COUNT
                and gateway_selector_calls == EXPECTED_QUESTION_COUNT
            ) else EvidenceState.FAILED,
            # Production/Vault is outside the isolated Acceptance root and is
            # intentionally not read by this automated measurement.
            production_sentinel=EvidenceState.NOT_MEASURED,
            # Keep the legacy readiness field as transport/readability status;
            # strict identity parity is separately measured below and only its
            # successes may enter the frozen quality counters.
            mcp_parity=EvidenceState.READY if (
                mcp_attempts == EXPECTED_QUESTION_COUNT
                and mcp_successes == EXPECTED_QUESTION_COUNT
            ) else EvidenceState.FAILED,
            qdrant_degradation=(
                EvidenceState.READY if semantic_degradation.get("status") == "ready"
                else EvidenceState.FAILED
            ),
            corruption_isolation=(
                EvidenceState.READY if corruption_isolation.get("status") == "ready"
                else EvidenceState.FAILED
            ),
            # Legacy readiness denotes that every baseline probe ran.  The
            # actual selection-before-bound measurement remains explicit in
            # evidence_details and is NOT_MEASURED when the product returned
            # no complete pre-bound session.
            context_baseline=EvidenceState.READY if baseline_available and gateway_calls_completed == EXPECTED_QUESTION_COUNT else EvidenceState.NOT_MEASURED,
            scale=EvidenceState.NOT_MEASURED,
            owner_review=EvidenceState.NOT_MEASURED,
            reboot_recovery=EvidenceState.NOT_MEASURED,
            mac_release=EvidenceState.NOT_MEASURED,
            windows_release=EvidenceState.NOT_MEASURED,
        )
        # 4R1 deliberately cannot publish a functional/full gate result: 4R2
        # owns MCP, degradation, corruption and measured baseline evidence.
        functional_status = readiness.functional_status
        phase_status = "NOT_EVALUATED"
        envelope = {
            "run_id": f"quality:{fixture_hashes['corpus'][:16]}:{fixture_hashes['questions'][:16]}:{_git_commit()[:16]}",
            "fixture_hashes": fixture_hashes,
            "code_commit": _git_commit(),
            "acceptance_root": "isolated_acceptance_root",
            "import_counts": {"expected_messages": len(corpus), "imported_messages": imported_messages},
            "role_order_counts": {"expected": expected_ordered_roles, "matched": ordered_role_matches},
            "import_audit": asdict(audit),
            "promotion_outcomes": promotion_outcomes,
            "promotion_category_outcomes": promotion_category_outcomes,
            "promotion_provenance": promotion_provenance,
            "functional_status": "FAIL" if measured_quality_failure else "NOT_EVALUATED",
            "phase_status": "FAIL" if measured_quality_failure else "NOT_EVALUATED",
            "gateway_selection": {
                "status": "READY" if readiness.gateway_selection is EvidenceState.READY else "INCOMPLETE",
                "calls_completed": gateway_calls_completed,
                "selector_calls": gateway_selector_calls,
                "empty_responses": gateway_empty_responses,
                "selected_evidence": gateway_selected_evidence,
                "empty_response_is_retrieval_miss": gateway_empty_responses > 0,
            },
            "mcp_parity": {"status": readiness.mcp_parity.value, "attempts": mcp_attempts, "successes": mcp_successes, "failures": mcp_parity_failures},
            "context_baseline": {
                "status": readiness.context_baseline.value,
                "baseline_chars": measured_baseline_chars,
                "rendered_chars": measured_rendered_chars,
                "reduction": context_reduction,
            },
            "semantic_degradation": semantic_degradation,
            "corruption_isolation": corruption_isolation,
            "quality_evidence_readiness": {
                **asdict(readiness),
                "functional_status": readiness.functional_status,
                "should_run_acceptance_gate": readiness.should_run_acceptance_gate,
            },
            "production_pollution": None,
            "protected_tree_changes": [asdict(change) for change in acceptance_changes],
            "protected_tree_capture_error": protected_tree_capture_error,
            "acceptance_boundary": {
                "scope": "acceptance_protected_boundary_only",
                "before": acceptance_sentinels_before,
                "after": acceptance_sentinels_after,
                "available": protected_before is not None and protected_after is not None and not protected_tree_capture_error,
                "unchanged": (
                    acceptance_sentinels_before == acceptance_sentinels_after
                    if protected_before is not None and protected_after is not None and not protected_tree_capture_error
                    else None
                ),
            },
            "measured_quality": {
                "answered_questions": len(question_results),
                "valid_fact_hits": valid_fact_hits, "valid_fact_total": valid_fact_total,
                "citation_hits": citation_hits, "citation_total": citation_total,
                "automatic_activation_correct": activation_correct, "automatic_activation_total": activation_total,
                "automatic_activation_accuracy": None,
                "mcp_successes": mcp_successes, "mcp_attempts": mcp_attempts,
                "baseline_context_chars": measured_baseline_chars,
                "rendered_context_chars": measured_rendered_chars,
                "context_reduction": context_reduction,
                "status": "FAIL" if measured_quality_failure else "PASS",
            },
            # The canonical Task 2 envelope remains the aggregate authority;
            # this additional accepted projection carries the immutable
            # per-question diagnostic stream for Task 3 review.
            "evaluation_report": {
                "schema_version": 1,
                "question_diagnostics": [item.to_mapping() for item in question_diagnostics],
                "grouped_metrics": grouped_question_metrics,
            },
            "cleanup_inventory": {"root_exists": True, "cleaned": False},
            "blocked_physical_evidence": list(FUNCTIONAL_BLOCKED_REASONS),
        }
        envelope["cleanup_inventory"]["cleaned"] = False
        tracker.mark("publication_pre")
        _atomic_json(output_path, envelope)
        return report, envelope
    except Exception:
        raise


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    if isinstance(value, Enum):
        return value.value
    return value


def publish_quality_envelope(envelope: QualityRunEnvelope, *, repository_output_path: Path) -> None:
    """Publish only a finalized envelope, never raw acceptance stores."""
    if not isinstance(envelope, QualityRunEnvelope):
        raise TypeError("quality publication requires QualityRunEnvelope")
    payload = _jsonable(asdict(envelope))
    details = payload.get("evidence_details")
    if isinstance(details, Mapping):
        # ``code_commit`` is part of the canonical identity.  It normally
        # arrives on the envelope from ``run_quality_gate``; retaining this
        # fallback keeps direct publication of a canonical envelope honest.
        payload["code_commit"] = payload.get("code_commit") or details.get("code_commit")
        # Keep the machine-readable report convenient for existing consumers
        # while retaining one authoritative envelope and one evidence map.
        for key in ("import_audit", "promotion_outcomes", "promotion_category_outcomes",
                    "promotion_provenance", "gateway_selection", "mcp_parity",
                    "qdrant_degradation", "corruption_isolation", "context_baseline",
                    "production_pollution", "measured_quality"):
            if key in details:
                payload[key] = details[key]
        payload["quality_evidence_readiness"] = payload.get("quality_evidence_readiness") or payload.get("readiness", {})
    _atomic_json(Path(repository_output_path), payload)


def run_quality_gate(
    corpus_path: Path,
    questions_path: Path,
    *,
    output_path: Path,
    acceptance_roots: AcceptanceRoots,
    stage_hook: Callable[[str], None] | None = None,
) -> QualityRunEnvelope:
    """Run the frozen gate in an admitted Acceptance root."""
    tracker = _RunnerStageTracker(stage_hook)
    try:
        report, raw = _run_quality_gate_impl(
            corpus_path, questions_path, output_path=output_path,
            acceptance_roots=acceptance_roots, stage_tracker=tracker,
        )
        tracker.mark("evaluator")
        readiness_payload = raw.get("quality_evidence_readiness") or {}
        fields = (
            "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
            "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
            "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
        )
        readiness = QualityEvidenceReadiness(**{
            field: (
                readiness_payload.get(field)
                if isinstance(readiness_payload.get(field), EvidenceState)
                else EvidenceState(
                    str(readiness_payload.get(field, EvidenceState.NOT_MEASURED.value))
                    .removeprefix("EvidenceState.")
                    .lower()
                )
            )
            for field in fields
        })
        envelope = finalize_quality_envelope(
            readiness=readiness,
            production_pollution=raw.get("production_pollution"),
            evaluation_report=report,
            acceptance_gate=AutomaticMemoryAcceptanceGate,
            blocked_reasons=tuple(raw.get("blocked_physical_evidence") or ()),
            measured_failure=bool((raw.get("measured_quality") or {}).get("status") == "FAIL"),
        )
        canonical = CanonicalFunctionalEvidence.from_runner_payload(raw)
        canonical_details = canonical.to_mapping()
        envelope = replace(envelope, evidence_details=canonical_details,
        run_id=raw.get("run_id"), fixture_hashes=raw.get("fixture_hashes") or {},
        quality_evidence_readiness=asdict(readiness), code_commit=raw.get("code_commit"))
        # The temporary machine report is deliberately written beneath the
        # acceptance output root; the caller publishes it only after cleanup.
        payload = dict(raw)
        payload.pop("evaluation_report", None)
        payload.update(_jsonable(asdict(envelope)))
        tracker.mark("publication_pre")
        _atomic_json(Path(output_path), payload)
        return envelope
    except Exception:
        # Never let a stage exception escape with a stale/partial report.  The
        # CLI publishes this fresh envelope after the isolated tree exits.
        failure = runner_failure_envelope(tracker.current, roots=acceptance_roots)
        try:
            _atomic_json(Path(output_path), _jsonable(asdict(failure)))
        except Exception:
            # The caller still receives a stable nonzero-producing envelope;
            # publication failure is reported by the formal CLI boundary.
            pass
        return failure


def _git_commit() -> str:
    try:
        import subprocess

        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return "unknown"


generate_100k_history = generate_history_fixture


from .scale_benchmark import run_100k_benchmark


__all__ = [
    "AcceptanceCleanupError",
    "AcceptanceRoots",
    "AutomaticMemoryAcceptanceGate",
    "EvidenceState",
    "ExpectedImportedRow",
    "QualityEvidenceReadiness",
    "QualityRunEnvelope",
    "ProtectedTreeSentinel",
    "finalize_quality_envelope",
    "write_quality_json_atomic",
    "build_expected_import_rows",
    "EXPECTED_QUESTION_COUNT",
    "generate_100k_history",
    "run_100k_benchmark",
    "run_quality_gate",
    "temporary_acceptance_roots",
    "publish_quality_envelope",
    "cleanup_failure_envelope",
    "ensure_4r2_ready_for_scale",
    "QualityScaleBlockedError",
    "validate_selected_evidence",
]
