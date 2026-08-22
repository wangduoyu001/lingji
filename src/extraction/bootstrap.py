from __future__ import annotations

from typing import Any, Mapping

from src.control.runtime_settings import RuntimeSettingsStore
from src.memory import VaultLayout
from src.retrieval.memory_db import MemoryDatabase
from src.sources import SourceReadModel
from src.storage import StateDatabase
from src.work.capture_bridge import CaptureWorkBridge
from src.work.store import WorkStore

from .adapters.chatgpt import ChatGPTExportAdapter
from .adapters.codex import CodexWorkReportAdapter
from .adapters.codex_session import CodexSessionAdapter
from .adapters.media import MediaExtractionAdapter
from .adapters.web import WebCaptureAdapter
from .pipeline import DocumentsWrittenCallback, ExtractionPipeline
from .queue import SQLiteExtractionQueue
from .registry import AdapterRegistry
from .sink import VaultExtractionSink
from .structured_sink import StructuredReadModelSink

_WORK_ID_OPTION = "_lingji_work_id"


def _job_work_id(job: Mapping[str, Any]) -> str:
    options = job.get("options") if isinstance(job.get("options"), Mapping) else {}
    return str(options.get(_WORK_ID_OPTION) or "")


def _result_evidence(job: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {"job_id": str(job.get("job_id") or "")}
    structured = result.get("structured_read_model")
    containers = (result, structured if isinstance(structured, Mapping) else {})
    refs: dict[str, str] = {}
    for container in containers:
        for key in ("memory_id", "source_id", "conversation_id", "message_id"):
            value = container.get(key)
            if isinstance(value, str) and value:
                refs[key] = value
    if refs:
        evidence["result_refs"] = refs
    for key in ("source_type", "adapter", "adapter_version", "indexed", "document_count", "memory_count"):
        value = result.get(key)
        if isinstance(value, (str, int, float, bool, type(None))) and value is not None:
            evidence[key] = value
    return evidence


def build_extraction_pipeline(
    settings,
    *,
    on_documents_written: DocumentsWrittenCallback | None = None,
    runtime_settings: RuntimeSettingsStore | None = None,
) -> ExtractionPipeline:
    layout = VaultLayout(settings.vault_path)
    layout.ensure()
    state_db = StateDatabase(settings.state_db_path)
    runtime_settings = runtime_settings or RuntimeSettingsStore(settings, state_db=state_db)
    memory_database = MemoryDatabase(settings.memory_db_path)
    source_read_model = SourceReadModel(memory_database)
    structured_sink = StructuredReadModelSink(
        source_read_model,
        storage_path=settings.storage_path,
        state_db=state_db,
        memory_database=memory_database,
    )
    queue = SQLiteExtractionQueue(settings.state_db_path)
    registry = AdapterRegistry()
    registry.register(ChatGPTExportAdapter())
    registry.register(CodexWorkReportAdapter(), structured_fallback=True)
    registry.register(CodexSessionAdapter())
    registry.register(WebCaptureAdapter(), structured_fallback=True)
    registry.register(MediaExtractionAdapter(settings.storage_path), structured_fallback=True)
    sink = VaultExtractionSink(layout, settings.storage_path, state_db=state_db)

    work_bridge = CaptureWorkBridge(WorkStore(state_db))

    def on_job_started(job: Mapping[str, Any]) -> None:
        work_id = _job_work_id(job)
        if not work_id:
            return
        work_bridge.start_extraction(
            work_id,
            detail={
                "job_id": str(job.get("job_id") or ""),
                "attempt": int(job.get("attempts") or 0),
                "adapter": str(job.get("adapter_name") or ""),
            },
        )

    def on_job_completed(job: Mapping[str, Any], result: Mapping[str, Any]) -> None:
        work_id = _job_work_id(job)
        if not work_id:
            return
        if work_bridge.store.get_outcome(work_id) is not None:
            return
        work_bridge.complete_extraction(
            work_id,
            "Capture 提取已完成",
            evidence=_result_evidence(job, result),
        )

    def on_job_failed(job: Mapping[str, Any], _error: str) -> None:
        work_id = _job_work_id(job)
        if not work_id:
            return
        status = str(job.get("status") or "")
        detail = {
            "job_id": str(job.get("job_id") or ""),
            "attempts": int(job.get("attempts") or 0),
            "max_attempts": int(job.get("max_attempts") or 0),
        }
        if status == "retrying":
            work_bridge.retry_extraction(work_id, detail=detail)
            return
        if status == "failed" and work_bridge.store.get_outcome(work_id) is None:
            work_bridge.fail_extraction(
                work_id,
                "Capture 提取失败；详细原因请查看本机诊断日志",
                evidence={"job_id": detail["job_id"], "error_code": "CAPTURE_JOB_FAILED"},
            )

    return ExtractionPipeline(
        queue,
        registry,
        sink,
        structured_sink=structured_sink,
        default_max_attempts=settings.extraction_max_attempts,
        lease_heartbeat_seconds=settings.extraction_lease_heartbeat_seconds,
        stale_after_seconds=settings.extraction_stale_after_seconds,
        on_documents_written=on_documents_written,
        default_options_provider=runtime_settings.options_for_source,
        default_priority_provider=runtime_settings.priority_for_source,
        on_job_started=on_job_started,
        on_job_completed=on_job_completed,
        on_job_failed=on_job_failed,
    )
