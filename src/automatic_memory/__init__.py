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
]
