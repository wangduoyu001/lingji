from __future__ import annotations

from typing import Any

from src.gateway.memory_inspector import MemoryInspectorFacade
from src.gateway.profiles import AIProfileRegistry
from src.retrieval.memory_db import MemoryDatabase
from src.sources import SourceQueryService, SourceReadModel


def build_memory_inspector(settings: Any, control: Any) -> MemoryInspectorFacade:
    """Build the read-only inspector without opening a second Qdrant client."""

    existing = getattr(control, "memory_inspector", None)
    if existing is not None:
        return existing

    gateway = getattr(control, "memory_gateway", None)
    database = getattr(gateway, "database", None) or MemoryDatabase(settings.memory_db_path)
    workspace = getattr(gateway, "workspace", None)
    workspace_name = getattr(getattr(workspace, "name", None), "value", None)
    workspace_name = str(
        workspace_name
        or getattr(settings, "workspace_name", None)
        or "production"
    )
    vault_path = getattr(workspace, "vault_path", None) or settings.vault_path
    raw_path = getattr(workspace, "raw_path", None) or (settings.storage_path / "raw")
    profiles = getattr(gateway, "profiles", None) or AIProfileRegistry()
    source_service = SourceQueryService(
        SourceReadModel(database),
        workspace=workspace_name,
        vault_path=vault_path,
        raw_path=raw_path,
        profiles=profiles,
    )
    return MemoryInspectorFacade(
        database,
        source_service,
        control.memory_statistics,
        gateway=gateway,
        workspace=workspace_name,
    )
