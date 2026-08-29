from __future__ import annotations

import os

from src.control.runtime_settings import RuntimeSettingsStore
from src.memory import VaultLayout
from src.retrieval.memory_db import MemoryDatabase
from src.sources import SourceReadModel
from src.storage import StateDatabase

from .adapters.chatgpt import ChatGPTExportAdapter
from .adapters.claude_desktop import ClaudeDesktopAdapter
from .adapters.codex import CodexRolloutAdapter, CodexTranscriptAdapter, CodexWorkReportAdapter
from .adapters.codex_session import CodexSessionAdapter
from .adapters.generic_ai_history import GenericAIHistoryAdapter
from .adapters.media import MediaExtractionAdapter
from .adapters.web import WebCaptureAdapter
from .pipeline import DocumentsWrittenCallback, ExtractionPipeline
from .queue import SQLiteExtractionQueue
from .registry import AdapterRegistry
from .sink import VaultExtractionSink
from .structured_sink import StructuredReadModelSink


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
    registry.register(ClaudeDesktopAdapter())
    registry.register(CodexTranscriptAdapter())
    registry.register(CodexRolloutAdapter())
    registry.register(CodexWorkReportAdapter(), structured_fallback=True)
    registry.register(CodexSessionAdapter())
    registry.register(GenericAIHistoryAdapter())
    registry.register(WebCaptureAdapter(), structured_fallback=True)
    registry.register(MediaExtractionAdapter(settings.storage_path), structured_fallback=True)
    sink = VaultExtractionSink(layout, settings.storage_path, state_db=state_db)
    configured_env = getattr(settings, "environ", None)
    effective_home = getattr(settings, "home_dir", None) or getattr(settings, "user_home", None)
    if effective_home is None:
        effective_home = (configured_env if configured_env is not None else os.environ).get("HOME")
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
        effective_home=str(effective_home) if effective_home else None,
    )
