from __future__ import annotations

from src.memory import VaultLayout
from src.storage import StateDatabase

from .adapters.chatgpt import ChatGPTExportAdapter
from .adapters.codex import CodexWorkReportAdapter
from .adapters.media import MediaExtractionAdapter
from .adapters.web import WebCaptureAdapter
from .pipeline import DocumentsWrittenCallback, ExtractionPipeline
from .queue import SQLiteExtractionQueue
from .registry import AdapterRegistry
from .sink import VaultExtractionSink


def build_extraction_pipeline(
    settings,
    *,
    on_documents_written: DocumentsWrittenCallback | None = None,
) -> ExtractionPipeline:
    layout = VaultLayout(settings.vault_path)
    layout.ensure()
    state_db = StateDatabase(settings.state_db_path)
    queue = SQLiteExtractionQueue(settings.state_db_path)
    registry = AdapterRegistry()
    registry.register(ChatGPTExportAdapter())
    registry.register(CodexWorkReportAdapter())
    registry.register(WebCaptureAdapter())
    registry.register(MediaExtractionAdapter(settings.storage_path))
    sink = VaultExtractionSink(layout, settings.storage_path, state_db=state_db)
    return ExtractionPipeline(
        queue,
        registry,
        sink,
        default_max_attempts=settings.extraction_max_attempts,
        lease_heartbeat_seconds=settings.extraction_lease_heartbeat_seconds,
        stale_after_seconds=settings.extraction_stale_after_seconds,
        on_documents_written=on_documents_written,
    )
