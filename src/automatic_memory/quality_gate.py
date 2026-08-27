"""Real automatic-memory quality and scale gates.

The quality runner intentionally sits above the existing ingestion, source
read-model, promotion, retrieval, gateway and MCP contracts.  It does not
manufacture retrieval answers from the frozen question expectations.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import statistics
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from src.auto_review.models import ReviewCandidate
from src.auto_review.promotion import AutoMemoryPromotionService
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
from src.retrieval.context_pack import ContextPackBuilder
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.memory_db import MemoryDatabase
from src.sources.read_model import SourceReadModel
from src.sources.service import SourceQueryService
from src.storage.state_db import StateDatabase
from .evidence_identity import EvidenceIdentityError, build_identity_registry, select_context_evidence

from .evaluation import (
    AutomaticMemoryAcceptanceGate,
    CorpusRecord,
    EvaluationQuestion,
    EvaluationReport,
    QuestionResult,
    evaluate_run,
    load_corpus,
    load_questions,
    score_question,
)
from .quality_evidence import (
    EvidenceState,
    ExpectedImportedRow,
    QualityRunEnvelope,
    ImportedEvidenceAudit,
    ProtectedTreeSentinel,
    QualityEvidenceReadiness,
    finalize_quality_envelope,
    write_quality_json_atomic,
    _read_ingestion_rows,
    build_expected_import_rows,
)


FUNCTIONAL_BLOCKED_REASONS = (
    "owner_review_not_run_in_automated_gate",
    "reboot_recovery_not_run_in_automated_gate",
    "mac_m5_p95_reserved_for_task_6",
    "mac_idle_cpu_reserved_for_task_6",
)
CORPUS_SHA256 = "bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94"
QUESTIONS_SHA256 = "338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612"
_SELECTOR_LIMIT = 2  # One fixed, question-independent selector for every query.
EXPECTED_QUESTION_COUNT = 100


class AcceptanceCleanupError(RuntimeError):
    """The isolated acceptance tree could not be removed safely."""

    def __init__(self, code: str = "TEMP_CLEANUP_FAILED") -> None:
        self.code = str(code)
        super().__init__(self.code)


class QualityScaleBlockedError(RuntimeError):
    """The 100k scale benchmark is not available during the reset phase."""


@dataclass(frozen=True)
class AcceptanceRoots:
    root: Path
    storage_root: Path
    vault_root: Path
    output_root: Path
    lease_marker: Path

    def validate_temporary_isolation(self) -> None:
        declared_root = self.root.expanduser()
        if not declared_root.is_absolute() or declared_root.is_symlink():
            raise ValueError("invalid acceptance root")
        root = declared_root.resolve(strict=False)
        if not root.name.startswith("lingji-task4r-"):
            raise ValueError("invalid acceptance root")
        if not root.exists() or not root.is_dir() or root.is_symlink():
            raise ValueError("acceptance root unavailable")
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
        if not self.lease_marker.exists() or not self.lease_marker.is_file():
            raise ValueError("acceptance lease marker unavailable")
        if not self.lease_marker.read_text(encoding="utf-8").strip():
            raise ValueError("acceptance lease marker invalid")


@contextmanager
def temporary_acceptance_roots(*, base_directory: Path | None = None):
    """Create and always remove one isolated reset acceptance tree."""
    base = Path(base_directory).expanduser().resolve() if base_directory is not None else None
    root = Path(tempfile.mkdtemp(prefix="lingji-task4r-", dir=str(base) if base else None)).resolve()
    roots = AcceptanceRoots(
        root=root,
        storage_root=root / "storage",
        vault_root=root / "vault",
        output_root=root / "output",
        lease_marker=root / ".lease",
    )
    roots.storage_root.mkdir()
    roots.vault_root.mkdir()
    roots.output_root.mkdir()
    roots.lease_marker.write_text(secrets.token_hex(16), encoding="utf-8")
    roots.validate_temporary_isolation()
    try:
        yield roots
    finally:
        try:
            shutil.rmtree(root, ignore_errors=False)
        except Exception as exc:
            raise AcceptanceCleanupError() from exc


def cleanup_failure_envelope(_report: Any, error: AcceptanceCleanupError) -> QualityRunEnvelope:
    values = {field: EvidenceState.NOT_MEASURED for field in (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
        "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
    )}
    readiness = QualityEvidenceReadiness(**values)
    return QualityRunEnvelope(
        readiness, None, None, "NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED", (error.code,)
    )


def ensure_4r2_ready_for_scale(readiness: QualityEvidenceReadiness) -> None:
    if not isinstance(readiness, QualityEvidenceReadiness) or not readiness.mac_release_ready:
        raise QualityScaleBlockedError("BLOCKED_4R2_REQUIRED")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _all_messages(read_model: SourceReadModel) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = read_model.list_messages(owner=True, limit=200, offset=offset)
        rows.extend(page.get("items") or [])
        if not page.get("next_offset"):
            return rows
        offset = int(page["next_offset"])


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


def _build_gateway(root: Path, memory_db: MemoryDatabase, read_model: SourceReadModel, state_db: StateDatabase) -> tuple[MemoryGateway, AIProfileRegistry]:
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
    retriever = HybridRetriever(memory_db, semantic_provider=None)
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


def _promote_fixtures(
    corpus: Sequence[CorpusRecord],
    message_map: Mapping[str, Mapping[str, Any]],
    memory_db: MemoryDatabase,
    read_model: SourceReadModel,
    state_db: StateDatabase,
) -> tuple[dict[str, dict[str, Any]], int, int, dict[str, str]]:
    promotion_plan: list[tuple[CorpusRecord, str]] = []
    promotion_bindings: dict[str, str] = {}
    bound_facts: set[str] = set()
    for record in corpus:
        memory_id = _opaque_memory_id(record)
        fact_id = str(record.fact_id or "").strip()
        if not fact_id:
            raise ValueError("promotion fact binding requires a fact ID")
        if memory_id in promotion_bindings:
            raise ValueError(f"opaque memory ID collision: {memory_id}")
        if fact_id in bound_facts:
            raise ValueError(f"promotion fact binding collision: {fact_id}")
        promotion_bindings[memory_id] = fact_id
        bound_facts.add(fact_id)
        promotion_plan.append((record, memory_id))
    if len(promotion_bindings) != len(corpus):
        raise ValueError("promotion identity bindings are not one-to-one")

    service = AutoMemoryPromotionService(
        state_db=state_db,
        memory_db=memory_db,
        evidence_store=read_model,
    )
    decisions: dict[str, dict[str, Any]] = {}
    activation_total = 0
    activation_correct = 0
    for record, memory_id in promotion_plan:
        message = message_map.get(record.fact_id)
        if message is None:
            continue
        is_eligible = record.risk != "high" and record.authority == "owner-confirmed"
        if is_eligible:
            activation_total += 1
        candidate = ReviewCandidate(
            memory_id=memory_id,
            title=record.topic_key,
            content=record.content,
            memory_type=record.memory_kind,
            privacy=record.privacy,
            project_ids=(record.project_id,),
            source_refs=(str(message["message_id"]),),
            confidence=0.99 if is_eligible else 0.80,
            authority="user_explicit" if record.authority == "owner-confirmed" else "assistant_suggestion",
            source_kind="current_project_document" if record.authority == "owner-confirmed" else "assistant_inference",
            extractor_version="automatic-memory-v1",
            metadata={
                "direct_user_evidence": record.authority == "owner-confirmed",
                "memory_type": record.memory_kind,
                "project_ids": [record.project_id],
                "privacy": record.privacy,
                "agent_scope": list(record.agent_scope),
                "valid_from": record.occurred_at,
                "modified_at": record.occurred_at,
                    "risk_flags": ["security"] if record.risk == "high" else [],
            },
        )
        decision = service.evaluate(candidate)
        decisions[record.fact_id] = decision
        if is_eligible and decision.get("status") == "active":
            activation_correct += 1

    # Lifecycle replacement links are owned by the real application workflow.
    # The evaluation fixture remains process-local and must not write
    # fixture-driven supersession or other lifecycle overrides to storage.
    return decisions, activation_correct, activation_total, promotion_bindings


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
) -> tuple[EvaluationReport, dict[str, Any]]:
    """Run the frozen 100-question contracts inside admitted roots."""
    corpus_path = Path(corpus_path).expanduser()
    questions_path = Path(questions_path).expanduser()
    output_path = Path(output_path).expanduser()
    acceptance_roots.validate_temporary_isolation()
    try:
        output_path.resolve(strict=False).relative_to(acceptance_roots.output_root.resolve())
    except ValueError as exc:
        raise ValueError("quality output must be inside Acceptance output root") from exc
    corpus = load_corpus(corpus_path)
    questions = load_questions(questions_path, corpus=corpus)
    fixture_hashes = {"corpus": _sha256(corpus_path), "questions": _sha256(questions_path)}
    if fixture_hashes != {"corpus": CORPUS_SHA256, "questions": QUESTIONS_SHA256}:
        raise ValueError("frozen fixture hash mismatch")

    temporary_root = acceptance_roots.root
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Production sentinel evidence is intentionally unavailable in reset:
    # reading configured production paths would violate the authority boundary.
    protected_before: ProtectedTreeSentinel | None = None
    protected_tree_capture_error = "NOT_MEASURED_IN_RESET"
    production_sentinels_before: dict[str, str] = {}
    production_sentinels_after: dict[str, str] = {}
    message_map: dict[str, dict[str, Any]] = {}
    decisions: dict[str, dict[str, Any]] = {}
    question_results: list[QuestionResult] = []
    mcp_attempts = 0
    mcp_successes = 0
    mcp_cases: list[dict[str, Any]] = []
    stale_leaks = 0
    duplicate_records = 0
    ordered_role_matches = 0
    expected_ordered_roles = len(corpus)
    imported_messages = 0
    activation_correct = 0
    activation_total = 0
    rendered_context_chars = 0
    baseline_context_chars = 0
    gateway_calls_completed = 0
    gateway_selector_calls = 0
    gateway_empty_responses = 0
    gateway_selected_evidence = 0
    try:
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
        audit = ImportedEvidenceAudit.from_read_model(
            read_model,
            ingestion_batch_id=ingestion_batch_id,
            expected_rows=expected_rows,
        )
        imported_messages = audit.actual_rows
        ordered_role_matches = audit.role_matches
        decisions, activation_correct, activation_total, promotion_bindings = _promote_fixtures(
            corpus, message_map, memory_db, read_model, state_db
        )
        duplicate_records = audit.stable_duplicates.total
        gateway, _profiles = _build_gateway(temporary_root, memory_db, read_model, state_db)
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
        fact_by_memory = {item.fact_id: item for item in corpus}
        citation_ids = {item.citation_id for item in corpus}
        baseline_unit = sum(len(item.content) for item in corpus) + sum(len(item.topic_key) for item in corpus)
        baseline_context_chars = baseline_unit * len(questions)
        for question in questions:
            arguments = {
                "query": question.query,
                "agent_id": "agent-synthetic",
                "project": "project-lingji",
                "max_chars": 4000,
                "include_core": False,
                "mode": question.mode,
                "as_of": question.as_of,
            }
            gateway_pack = gateway.build_context_pack(**arguments)
            gateway_calls_completed += 1
            if not isinstance(gateway_pack, Mapping):
                raise ValueError("malformed Gateway response")
            gateway_sections = gateway_pack.get("sections")
            if isinstance(gateway_sections, (str, bytes)) or not isinstance(gateway_sections, Sequence):
                raise ValueError("malformed Gateway sections")
            gateway_empty_responses += int(not gateway_sections)
            rendered_context_chars += len(str(gateway_pack.get("markdown") or ""))
            # MCP parity is a Task 4R2 measurement.  Keep a row per verbatim
            # Gateway call without fabricating transport success.
            mcp_attempts += 1
            mcp_cases.append({"question_id": question.question_id, "status": "NOT_MEASURED"})
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
            recalled = tuple(fact_id for fact_id in selected_evidence.fact_ids if fact_id in fact_by_memory)
            citations = tuple(citation_id for citation_id in selected_evidence.citation_ids if citation_id in citation_ids)
            for memory_id in recalled:
                record = fact_by_memory[memory_id]
                if record.lifecycle != "active" and question.mode == "current":
                    stale_leaks += 1
            validate_selected_evidence(
                recalled=recalled,
                citations=citations,
                expected=question.expected_fact_ids,
                forbidden=question.forbidden_fact_ids,
                expected_citations=question.expected_citation_ids,
            )
            try:
                question_results.append(
                    score_question(
                        question,
                        fact_by_memory,
                        recalled,
                        citations,
                        context_chars=len(str(gateway_pack.get("markdown") or "")),
                    )
                )
            except Exception:
                raise
        protected_after = None
        production_changes = (
            protected_before.diff(protected_after)
            if protected_before is not None and protected_after is not None and not protected_tree_capture_error
            else ()
        )
        production_pollution = len(production_changes) if protected_before is not None and protected_after is not None and not protected_tree_capture_error else None
        report = evaluate_run(
            fact_by_memory,
            questions,
            question_results,
            imported_messages=imported_messages,
            expected_messages=len(corpus),
            ordered_role_matches=ordered_role_matches,
            expected_ordered_roles=expected_ordered_roles,
            automatic_activation_correct=activation_correct,
            automatic_activation_total=activation_total,
            protected_false_promotions=sum(
                int(record.risk == "high" and decisions.get(record.fact_id, {}).get("status") == "active")
                for record in corpus
            ),
            stale_current_leaks=stale_leaks,
            duplicate_records=duplicate_records,
            baseline_context_chars=max(baseline_context_chars, rendered_context_chars),
            rendered_context_chars=rendered_context_chars,
            mcp_successes=mcp_successes,
            mcp_attempts=mcp_attempts,
            # The evaluator's historical report schema accepts an integer.
            # Keep its arithmetic valid, then replace the returned/envelope
            # value with ``None`` when sentinel evidence is unavailable.
            production_pollution=production_pollution if production_pollution is not None else 0,
            owner_review_success=None,
            reboot_recovery=None,
            blocked_reasons=FUNCTIONAL_BLOCKED_REASONS,
        )
        if production_pollution is None:
            report = replace(report, production_pollution=None)
        readiness = QualityEvidenceReadiness(
            import_audit=EvidenceState.READY if audit.ready else EvidenceState.FAILED,
            promotion_provenance=EvidenceState.READY if all(
                decision.get("status") != "active" or bool(read_model.memory_links(decision.get("candidate_id", "")))
                for decision in decisions.values()
            ) else EvidenceState.FAILED,
            gateway_selection=EvidenceState.READY if (
                gateway_calls_completed == EXPECTED_QUESTION_COUNT
                and gateway_selector_calls == EXPECTED_QUESTION_COUNT
            ) else EvidenceState.FAILED,
            production_sentinel=(
                EvidenceState.NOT_MEASURED if production_pollution is None else
                (EvidenceState.READY if production_pollution == 0 else EvidenceState.FAILED)
            ),
            mcp_parity=EvidenceState.NOT_MEASURED,
            qdrant_degradation=EvidenceState.NOT_MEASURED,
            corruption_isolation=EvidenceState.NOT_MEASURED,
            context_baseline=EvidenceState.NOT_MEASURED,
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
        production_sentinels_after = {}
        envelope = {
            "fixture_hashes": fixture_hashes,
            "code_commit": _git_commit(),
            "temporary_root": str(temporary_root),
            "import_counts": {"expected_messages": len(corpus), "imported_messages": imported_messages},
            "role_order_counts": {"expected": expected_ordered_roles, "matched": ordered_role_matches},
            "import_audit": asdict(audit),
            "per_question": [asdict(item) for item in question_results],
            "raw_evaluation_report": asdict(report),
            "functional_status": functional_status,
            "phase_status": phase_status,
            "mcp_attempts": mcp_attempts,
            "mcp_successes": mcp_successes,
            "mcp_cases": mcp_cases,
            "gateway_selection": {
                "status": "READY" if readiness.gateway_selection else "INCOMPLETE",
                "calls_completed": gateway_calls_completed,
                "selector_calls": gateway_selector_calls,
                "empty_responses": gateway_empty_responses,
                "selected_evidence": gateway_selected_evidence,
                "empty_response_is_retrieval_miss": gateway_empty_responses > 0,
            },
            "mcp_parity": {"status": "NOT_MEASURED", "task": "4R2"},
            "context_baseline": {"status": "NOT_MEASURED", "task": "4R2"},
            "semantic_degradation": {"status": "NOT_MEASURED", "task": "4R2"},
            "corruption_isolation": {"status": "NOT_MEASURED", "task": "4R2"},
            "quality_evidence_readiness": {
                **asdict(readiness),
                "functional_status": readiness.functional_status,
                "should_run_acceptance_gate": readiness.should_run_acceptance_gate,
            },
            "production_pollution": production_pollution,
            "protected_tree_changes": [asdict(change) for change in production_changes],
            "protected_tree_capture_error": protected_tree_capture_error,
            "production_vault_sentinels": {
                "before": production_sentinels_before,
                "after": production_sentinels_after,
                "available": protected_before is not None and protected_after is not None and not protected_tree_capture_error,
                "unchanged": (
                    production_sentinels_before == production_sentinels_after
                    if protected_before is not None and protected_after is not None and not protected_tree_capture_error
                    else None
                ),
            },
            "cleanup_inventory": {"temporary_root": str(temporary_root), "cleaned": False},
            "blocked_physical_evidence": list(FUNCTIONAL_BLOCKED_REASONS),
        }
        envelope["cleanup_inventory"]["cleaned"] = False
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
    _atomic_json(Path(repository_output_path), payload)


def run_quality_gate(
    corpus_path: Path,
    questions_path: Path,
    *,
    output_path: Path,
    acceptance_roots: AcceptanceRoots | None = None,
) -> QualityRunEnvelope | EvaluationReport:
    """Run the frozen gate in isolated roots and return truthful readiness.

    The optional legacy path exists only for historical reset tests.  The
    public reset CLI always supplies an admitted ``AcceptanceRoots`` object.
    """
    if acceptance_roots is None:
        # Compatibility-only path: no production roots are read, and the
        # temporary tree is still isolated before the old report is returned.
        with temporary_acceptance_roots() as roots:
            report, raw = _run_quality_gate_impl(
                corpus_path, questions_path,
                output_path=roots.output_root / "quality.json",
                acceptance_roots=roots,
            )
        legacy_output = Path(output_path).expanduser()
        legacy_output.parent.mkdir(parents=True, exist_ok=True)
        legacy_output.write_text(
            json.dumps(_jsonable(raw), ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return report

    report, raw = _run_quality_gate_impl(
        corpus_path, questions_path, output_path=output_path, acceptance_roots=acceptance_roots
    )
    readiness_payload = raw.get("quality_evidence_readiness") or {}
    fields = (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
        "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
    )
    readiness = QualityEvidenceReadiness(**{
        field: (
            readiness_payload.get(field).value
            if isinstance(readiness_payload.get(field), EvidenceState)
            else str(readiness_payload.get(field, EvidenceState.NOT_MEASURED.value)).removeprefix("EvidenceState.").lower()
        )
        for field in fields
    })
    envelope = finalize_quality_envelope(
        readiness=readiness,
        production_pollution=raw.get("production_pollution"),
        evaluation_report=report,
        acceptance_gate=AutomaticMemoryAcceptanceGate,
        blocked_reasons=tuple(raw.get("blocked_physical_evidence") or ()),
    )
    # The temporary machine report is deliberately written beneath the
    # acceptance output root; the caller publishes it only after cleanup.
    payload = dict(raw)
    payload.update(_jsonable(asdict(envelope)))
    _atomic_json(Path(output_path), payload)
    return envelope


def _git_commit() -> str:
    try:
        import subprocess

        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return "unknown"


def generate_100k_history(path: Path, *, count: int = 100_000, seed: int = 20260826) -> dict[str, Any]:
    """Create deterministic unique History Inbox messages without Production writes."""
    if count != 100_000:
        raise ValueError("Task 4 scale gate requires exactly 100,000 messages")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        header = {"schema": HISTORY_SCHEMA, "schema_version": HISTORY_VERSION, "type": "header", "seed": seed}
        stream.write(json.dumps(header, sort_keys=True) + "\n")
        stream.write(json.dumps({"type": "conversation", "conversation_id": "scale-conversation", "title": "Scale benchmark"}, sort_keys=True) + "\n")
        for index in range(count):
            message_id = f"scale-message-{index:06d}"
            content = f"Deterministic scale message {index:06d} seed {seed}."
            occurred_at = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat().replace("+00:00", "Z")
            row = {
                "type": "message",
                "conversation_id": "scale-conversation",
                "message_id": message_id,
                "role": "user" if index % 2 == 0 else "assistant",
                "content": content,
                "timestamp": occurred_at,
            }
            encoded = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
            digest.update(encoded)
            stream.write(encoded.decode("utf-8"))
    return {"seed": seed, "messages": count, "unique_message_ids": count, "content_hash": digest.hexdigest(), "path": str(path)}


def run_100k_benchmark(*, output_path: Path) -> dict[str, Any]:
    """Opt-in bounded benchmark, unavailable until Task 4R2 readiness."""
    values = {field: EvidenceState.NOT_MEASURED for field in (
        "import_audit", "promotion_provenance", "gateway_selection", "production_sentinel",
        "mcp_parity", "qdrant_degradation", "corruption_isolation", "context_baseline",
        "scale", "owner_review", "reboot_recovery", "mac_release", "windows_release",
    )}
    ensure_4r2_ready_for_scale(QualityEvidenceReadiness(**values))
    output_path = Path(output_path)
    _reject_protected_output(output_path)
    started = time.perf_counter()
    root = Path(tempfile.mkdtemp(prefix="lingji-acceptance-scale-", dir=str(output_path.parent)))
    try:
        generated = generate_100k_history(root / "generic-history-scale.jsonl")
        input_path = Path(generated["path"])
        memory_db = MemoryDatabase(root / "storage" / "index" / "lingji_memory.db")
        state_db = StateDatabase(root / "storage" / "state" / "lingji_state.db")
        read_model = SourceReadModel(memory_db)
        pipeline = _build_pipeline(root, memory_db, read_model, state_db)
        result = pipeline.execute(
            "generic_ai_history",
            input_path=input_path,
            adapter_name="generic_ai_history",
            execution_id="LJ-SCALE-100K",
        )
        indexer_class = __import__("src.indexer.index", fromlist=["PEMISIndex"]).PEMISIndex
        indexer = indexer_class(root / "vault", root / "storage")
        indexer.build_index()
        index_stats = memory_db.rebuild_from_index(indexer.get_all(), root / "vault")
        imported_count = int(
            (read_model.list_messages(owner=True, limit=1, offset=0).get("total") or 0)
        )
        gateway, _profiles = _build_gateway(root, memory_db, read_model, state_db)
        latencies: list[float] = []
        context_sizes: list[int] = []
        for _ in range(10):
            before = time.perf_counter()
            pack = gateway.build_context_pack(
                "agent-synthetic",
                query="Deterministic scale message",
                project=None,
                max_chars=4000,
                include_core=False,
            )
            latencies.append((time.perf_counter() - before) * 1000)
            context_sizes.append(len(str(pack.get("markdown") or "")))
        elapsed = time.perf_counter() - started
        ordered = sorted(latencies)
        report = {
            **generated,
            "imported_messages": imported_count,
            "pipeline_result": {
                "documents": int(result.get("documents") or 0),
                "structured_messages": int((result.get("structured_read_model") or {}).get("messages") or 0),
                "index_documents": int(index_stats.get("documents") or 0),
                "index_chunks": int(index_stats.get("chunks") or 0),
            },
            "elapsed_seconds": elapsed,
            "p50_ms": ordered[len(ordered) // 2],
            "p95_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))],
            "hot_retrieval_ms": latencies,
            "context_pack_sizes": context_sizes,
            "peak_message_count": imported_count,
            "production_pollution": 0,
            "vault_mutation": 0,
            "cleanup_result": "pending",
            "temporary_root": str(root),
        }
        shutil.rmtree(root, ignore_errors=False)
        report["cleanup_result"] = "cleaned"
        _atomic_json(output_path, report)
        return report
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


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
