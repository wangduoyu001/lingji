from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from src.config import settings as default_settings
from src.gateway.memory_gateway import MemoryGateway
from src.gateway.profiles import AIProfileRegistry
from src.indexer.index import PEMISIndex
from src.memory import MemoryLifecycleService, VaultLayout
from src.model_center import build_embedding_provider
from src.retrieval import (
    HybridRetriever,
    MarkdownChunker,
    MemoryDatabase,
    MemoryIndexCoordinator,
    QdrantSemanticProvider,
)
from src.retrieval.context_pack import ContextPackBuilder
from src.runtime.workspace import (
    WorkspaceContext,
    WorkspaceName,
    WorkspaceResolver,
)
from src.storage import StateDatabase


def build_memory_gateway(
    settings=default_settings,
    rebuild_if_empty: bool = True,
    workspace: WorkspaceContext | None = None,
    runtime_values: Mapping[str, Any] | None = None,
) -> MemoryGateway:
    """Build the unified memory gateway without starting background services.

    Existing production Vault and SQLite paths remain the transition mapping when
    no explicit WorkspaceContext is supplied. Semantic construction is optional:
    any configuration failure leaves a lexical-only gateway with a structured
    runtime warning instead of failing startup.
    """

    values = dict(runtime_values or {})
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

    runtime_warnings: list[dict[str, Any]] = []
    closeables: list[Any] = []
    semantic_provider = None
    semantic_workspace = workspace

    if _as_bool(values.get("semantic_enabled", getattr(settings, "semantic_enabled", True))):
        try:
            semantic_workspace = _resolve_semantic_workspace(settings, workspace)
            embedding_provider = build_embedding_provider(
                settings,
                values,
            )
            if embedding_provider is not None:
                semantic_provider = QdrantSemanticProvider(
                    semantic_workspace,
                    embedding_provider,
                    distance=str(values.get("qdrant_distance", settings.qdrant_distance)),
                    timeout_seconds=float(
                        values.get("qdrant_timeout_seconds", settings.qdrant_timeout_seconds)
                    ),
                    collection_schema=str(
                        values.get("qdrant_collection_schema", settings.qdrant_collection_schema)
                    ),
                )
                closeables.extend([semantic_provider, embedding_provider])
        except Exception as exc:
            warning = {
                "code": "semantic_runtime_initialization_failed",
                "stage": "bootstrap",
                "message": _safe_error(exc),
                "workspace": _workspace_name(workspace, settings),
            }
            runtime_warnings.append(warning)
            state_db.append_event(
                "semantic_runtime_degraded",
                "memory_gateway",
                "bootstrap",
                warning,
            )
            semantic_provider = None

    retriever = HybridRetriever(
        memory_db,
        semantic_provider=semantic_provider,
        cache_size=settings.memory_search_cache_size,
        cache_ttl_seconds=settings.memory_search_cache_ttl_seconds,
    )
    coordinator = MemoryIndexCoordinator(
        memory_db,
        semantic_provider,
        state_db=state_db,
        semantic_batch_size=int(
            values.get("semantic_batch_size", settings.semantic_batch_size)
        ),
    )
    lifecycle = MemoryLifecycleService(layout, state_db)
    gateway = MemoryGateway(
        memory_db,
        retriever,
        ContextPackBuilder(memory_db, retriever),
        lifecycle,
        profiles=AIProfileRegistry(),
        state_db=state_db,
        index_coordinator=coordinator,
        runtime_warnings=runtime_warnings,
        closeables=closeables,
    )
    gateway.workspace = semantic_workspace

    if rebuild_if_empty and memory_db.stats()["documents"] == 0:
        indexer = PEMISIndex(
            vault_path,
            storage_path,
            include_private=settings.index_private,
        )
        indexer.build_index()
        gateway.rebuild(indexer.get_all(), vault_path, chunker)
    return gateway


def _resolve_semantic_workspace(
    settings: Any,
    workspace: WorkspaceContext | None,
) -> WorkspaceContext:
    if workspace is not None:
        workspace.validate()
        return workspace

    name = WorkspaceName.parse(getattr(settings, "workspace_name", "production"))
    resolved = WorkspaceResolver.resolve(settings, name)
    if name is not WorkspaceName.PRODUCTION:
        return resolved

    storage_path = Path(settings.storage_path).expanduser().resolve(strict=False)
    qdrant_mode = resolved.qdrant_mode
    configured_path = str(getattr(settings, "production_qdrant_path", "") or "").strip()
    qdrant_path = (
        Path(configured_path).expanduser().resolve(strict=False)
        if configured_path and qdrant_mode == "embedded"
        else storage_path / "qdrant"
        if qdrant_mode == "embedded"
        else None
    )
    transition = replace(
        resolved,
        vault_path=Path(settings.vault_path).expanduser().resolve(strict=False),
        raw_path=(storage_path / "raw").resolve(strict=False),
        storage_path=storage_path,
        state_db_path=Path(settings.state_db_path).expanduser().resolve(strict=False),
        memory_db_path=Path(settings.memory_db_path).expanduser().resolve(strict=False),
        qdrant_path=qdrant_path,
        log_path=Path(settings.log_path).expanduser().resolve(strict=False),
        cache_path=(storage_path / "cache").resolve(strict=False),
        runtime_settings_path=Path(settings.runtime_settings_path).expanduser().resolve(strict=False),
        queue_db_path=Path(settings.state_db_path).expanduser().resolve(strict=False),
        backup_path=(storage_path / "backups").resolve(strict=False),
        derived_path=(storage_path / "derived").resolve(strict=False),
        temp_path=(storage_path / "temp").resolve(strict=False),
        reports_path=(storage_path / "reports").resolve(strict=False),
    )
    transition.validate()
    return transition


def _workspace_name(workspace: WorkspaceContext | None, settings: Any) -> str:
    if workspace is not None:
        return workspace.name.value
    return str(getattr(settings, "workspace_name", "production") or "production")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _safe_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:500]
