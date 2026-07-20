from __future__ import annotations

from src.config import settings as default_settings
from src.gateway.memory_gateway import MemoryGateway
from src.gateway.profiles import AIProfileRegistry
from src.indexer.index import PEMISIndex
from src.memory import MemoryLifecycleService, VaultLayout
from src.retrieval import HybridRetriever, MarkdownChunker, MemoryDatabase
from src.retrieval.context_pack import ContextPackBuilder
from src.runtime.workspace import WorkspaceContext
from src.storage import StateDatabase


def build_memory_gateway(
    settings=default_settings,
    rebuild_if_empty: bool = True,
    workspace: WorkspaceContext | None = None,
) -> MemoryGateway:
    """Build the memory gateway without starting schedulers, watchdogs or LLM jobs.

    Passing a WorkspaceContext opts this gateway into the new isolated path contract.
    Existing callers retain the transition mapping through Settings until later phases
    explicitly migrate their runtime wiring.
    """
    vault_path = workspace.vault_path if workspace else settings.vault_path
    storage_path = workspace.storage_path if workspace else settings.storage_path
    state_db_path = workspace.state_db_path if workspace else settings.state_db_path
    memory_db_path = workspace.memory_db_path if workspace else settings.memory_db_path

    layout = VaultLayout(vault_path)
    if settings.vault_auto_init:
        layout.ensure()
    state_db = StateDatabase(state_db_path)
    memory_db = MemoryDatabase(memory_db_path)
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
            vault_path,
            storage_path,
            include_private=settings.index_private,
        )
        indexer.build_index()
        gateway.rebuild(indexer.get_all(), vault_path, chunker)
    return gateway
