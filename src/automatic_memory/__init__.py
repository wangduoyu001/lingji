"""Persistent authorization and scan controls for automatic memory inputs."""

from .models import AuthorizationScope, ScanRun, SourceRecord
from .source_registry import SourceRegistry
from .snapshot import ConsistentSnapshot, FileStat, SnapshotResult
from .checkpoint import CheckpointStore, ResumeToken, SnapshotJobRunner
from .watcher import AutomaticMemoryWatcher
from .scheduler import AutomaticMemoryScheduler, ReconciliationReport
from .evaluation import (
    AcceptanceGate,
    AutomaticMemoryAcceptanceGate,
    CorpusRecord,
    EvaluationInputError,
    EvaluationQuestion,
    EvaluationReport,
    QuestionResult,
    evaluate_run,
    load_corpus,
    load_questions,
    score_question,
)
from .quality_gate import (
    AutomaticMemoryFunctionalGate,
    build_expected_import_rows,
    EXPECTED_QUESTION_COUNT,
    generate_100k_history,
    run_100k_benchmark,
    run_quality_gate,
    validate_selected_evidence,
)
from .evidence_identity import (
    EvidenceIdentityError,
    EvaluationIdentityRegistry,
    MemorySectionIdentity,
    MessageIdentity,
    RawMessageSectionIdentity,
    SectionIdentity,
    SelectedEvidence,
    build_identity_registry,
    select_context_evidence,
)

__all__ = [
    "AuthorizationScope",
    "ScanRun",
    "SourceRecord",
    "SourceRegistry",
    "ConsistentSnapshot",
    "FileStat",
    "SnapshotResult",
    "CheckpointStore",
    "ResumeToken",
    "SnapshotJobRunner",
    "AutomaticMemoryWatcher",
    "AutomaticMemoryScheduler",
    "ReconciliationReport",
    "AcceptanceGate",
    "AutomaticMemoryAcceptanceGate",
    "CorpusRecord",
    "EvaluationInputError",
    "EvaluationQuestion",
    "EvaluationReport",
    "QuestionResult",
    "evaluate_run",
    "load_corpus",
    "load_questions",
    "score_question",
    "AutomaticMemoryFunctionalGate",
    "build_expected_import_rows",
    "EXPECTED_QUESTION_COUNT",
    "generate_100k_history",
    "run_100k_benchmark",
    "run_quality_gate",
    "validate_selected_evidence",
    "MessageIdentity",
    "EvaluationIdentityRegistry",
    "SelectedEvidence",
    "MemorySectionIdentity",
    "RawMessageSectionIdentity",
    "SectionIdentity",
    "EvidenceIdentityError",
    "build_identity_registry",
    "select_context_evidence",
]
