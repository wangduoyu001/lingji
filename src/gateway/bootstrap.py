from __future__ import annotations

from src.config import settings as default_settings
from src.gateway.memory_gateway import MemoryGateway
from src.gateway.profiles import AIProfileRegistry
from src.indexer.index import PEMISIndex
from src.memory import MemoryLifecycleService, VaultLayout
from src.retrieval import HybridRetriever, MarkdownChunker, MemoryDatabase
from src.retrieval.context_pack import ContextPackBuilder
from src.storage import StateDatabase


def build_memory_gateway(settings=default_settings, rebuild_if_empty: bool = True) -> MemoryGateway:
    """Build the memory gateway without starting schedulers, watchdogs or LLM jobs."""
    layout = VaultLayout(settings.vault_path)
    if settings.vault_auto_init:
        layout.ensure()
    state_db = StateDatabase(settings.state_db_path)
    memory_db = MemoryDatabase(settings.memory_db_path)
    chunker = MarkdownChunker(
        settings.memory_chunk_max_chars,
        settings.memory_chunk_overlap_chars,
    )
    retriever = HybridRetriever(
        memory_db,
        semantic_provider=None,
        cache_size=settings.memory_search_cache_size,
        cache_ttl_seconds=settings.memory_search_cache_ttl_seconds,
    )
    lifecycle = MemoryLifecycleService(layout, state_db)
    gateway = MemoryGateway(
        memory_db,
        retriever,
        ContextPackBuilder(memory_db, retriever),
        lifecycle,
        profiles=AIProfileRegistry(),
        state_db=state_db,
    )
    if rebuild_if_empty and memory_db.stats()["documents"] == 0:
        indexer = PEMISIndex(
            settings.vault_path,
            settings.storage_path,
            include_private=settings.index_private,
        )
        indexer.build_index()
        gateway.rebuild(indexer.get_all(), settings.vault_path, chunker)
    return gateway
