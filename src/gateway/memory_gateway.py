from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from src.gateway.profiles import AIProfileRegistry
from src.memory.lifecycle import MemoryLifecycleService
from src.retrieval.context_pack import ContextPackBuilder, ContextPackRequest
from src.retrieval.hybrid import HybridRetriever, SearchFilters
from src.retrieval.index_coordinator import MemoryIndexCoordinator
from src.retrieval.memory_db import MemoryDatabase
from src.retrieval.temporal import TemporalQuery


class MemoryGateway:
    """Single permission-aware memory interface shared by all AI clients."""

    def __init__(
        self,
        database: MemoryDatabase,
        retriever: HybridRetriever,
        context_builder: ContextPackBuilder,
        lifecycle: MemoryLifecycleService,
        profiles: AIProfileRegistry | None = None,
        state_db=None,
        *,
        index_coordinator: MemoryIndexCoordinator | None = None,
        workspace: Any | None = None,
        runtime_warnings: list[dict[str, Any]] | None = None,
        closeables: Iterable[Any] | None = None,
    ):
        self.database = database
        self.retriever = retriever
        self.context_builder = context_builder
        self.lifecycle = lifecycle
        self.profiles = profiles or AIProfileRegistry()
        self.state_db = state_db
        self.workspace = workspace
        self.index_coordinator = index_coordinator or MemoryIndexCoordinator(
            database,
            retriever.semantic_provider,
            state_db=state_db,
        )
        self.runtime_warnings = list(runtime_warnings or [])
        self.statistics = None
        self._closeables = list(closeables or [])

    def search_memory(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        project: str | None = None,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        include_archived: bool = False,
        mode: str = "current",
        as_of: str | None = None,
    ) -> dict[str, Any]:
        profile = self.profiles.require_tool(agent_id, "search_memory")
        results = self.retriever.search(
            query,
            limit=min(max(int(limit), 1), 50),
            filters=SearchFilters(
                project=project,
                memory_types=tuple(memory_types or ()),
                privacy=profile.allowed_privacy,
                agent_id=profile.agent_id,
                tags=tuple(tags or ()),
                include_archived=include_archived,
                mode=mode,
                as_of=as_of,
            ),
        )
        self._event("memory_searched", profile.agent_id, {"query": query, "count": len(results)})
        return {
            "query": query,
            "agent_id": profile.agent_id,
            "memory_revision": self.database.revision,
            "results": results,
            "query_mode": mode,
            "as_of": as_of,
        }

    def fetch_memory(
        self,
        agent_id: str,
        memory_id: str | None = None,
        relative_path: str | None = None,
        mode: str = "current",
        as_of: str | None = None,
    ) -> dict[str, Any] | None:
        profile = self.profiles.require_tool(agent_id, "fetch_memory")
        if not memory_id and not relative_path:
            raise ValueError("memory_id or relative_path is required")
        memory = (
            self.database.fetch_memory(memory_id, include_chunks=True)
            if memory_id
            else self.database.fetch_by_path(str(relative_path), include_chunks=True)
        )
        if not memory:
            return None
        allowed, _ = TemporalQuery.from_values(mode, as_of).allows(memory)
        if not allowed:
            return None
        if memory.get("privacy") not in profile.allowed_privacy:
            raise PermissionError(f"{profile.display_name} cannot read {memory.get('privacy')} memory")
        scopes = memory.get("agent_scope") or []
        if scopes and profile.agent_id not in scopes and "all" not in scopes:
            raise PermissionError(f"Memory is not scoped to {profile.display_name}")
        self._event("memory_fetched", profile.agent_id, {"memory_id": memory.get("memory_id")})
        return memory

    def get_core_memory(
        self,
        agent_id: str,
        project: str | None = None,
        limit: int = 50,
        mode: str = "current",
        as_of: str | None = None,
    ) -> dict[str, Any]:
        profile = self.profiles.require_tool(agent_id, "get_core_memory")
        memories = self.database.list_core_memories(
            agent_id=profile.agent_id,
            project=project,
            privacy=profile.allowed_privacy,
            limit=min(max(int(limit), 1), 100),
            mode=mode,
            as_of=as_of,
        )
        return {
            "agent_id": profile.agent_id,
            "project": project,
            "memory_revision": self.database.revision,
            "memories": memories,
        }

    def build_context_pack(
        self,
        agent_id: str,
        query: str = "",
        project: str | None = None,
        max_chars: int | None = None,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        include_core: bool = True,
        mode: str = "current",
        as_of: str | None = None,
    ) -> dict[str, Any]:
        profile = self.profiles.require_tool(agent_id, "build_context_pack")
        requested_chars = max_chars if max_chars is not None else profile.max_context_chars
        bounded_chars = min(max(int(requested_chars), 1000), profile.max_context_chars)
        pack = self.context_builder.build(
            ContextPackRequest(
                agent_id=profile.agent_id,
                query=query,
                project=project,
                max_chars=bounded_chars,
                privacy=profile.allowed_privacy,
                memory_types=tuple(memory_types or ()),
                tags=tuple(tags or ()),
                include_core=include_core,
                mode=mode,
                as_of=as_of,
            )
        )
        self._event(
            "context_pack_built",
            profile.agent_id,
            {"query": query, "project": project, "sections": len(pack["sections"])},
        )
        return pack

    def propose_memory(
        self,
        agent_id: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = self.profiles.require_tool(agent_id, "propose_memory")
        if not profile.can_propose_memory:
            raise PermissionError(f"{profile.display_name} cannot propose permanent memory")
        values = dict(metadata or {})
        privacy = str(values.get("privacy") or "private")
        if privacy not in profile.allowed_privacy:
            raise PermissionError(f"{profile.display_name} cannot create {privacy} memory candidates")
        values["agent_scope"] = values.get("agent_scope") or [profile.agent_id]
        result = self.lifecycle.propose_memory(profile.agent_id, title, content, values)
        self._event("memory_candidate_created", profile.agent_id, result)
        return result

    def recent_changes(self, agent_id: str, limit: int = 30) -> dict[str, Any]:
        profile = self.profiles.require_tool(agent_id, "recent_changes")
        return {
            "agent_id": profile.agent_id,
            "memory_revision": self.database.revision,
            "memories": self.database.list_recent(
                limit=min(max(int(limit), 1), 100),
                privacy=profile.allowed_privacy,
            ),
            "events": self.state_db.recent_events(limit=min(max(int(limit), 1), 100)) if self.state_db else [],
        }

    def memory_health(self, agent_id: str) -> dict[str, Any]:
        profile = self.profiles.require_tool(agent_id, "memory_health")
        if self.statistics is not None:
            snapshot = self.statistics.snapshot()
            return {
                "agent_id": profile.agent_id,
                **snapshot,
                "profiles": self.profiles.list(),
            }
        workspace_name = getattr(getattr(self, "workspace", None), "name", None)
        return {
            "agent_id": profile.agent_id,
            "workspace": getattr(workspace_name, "value", workspace_name),
            "database": self.database.stats(),
            "integrity": self.database.integrity_check(),
            "profiles": self.profiles.list(),
            "runtime_warnings": list(self.runtime_warnings),
        }

    def memory_status(self) -> dict[str, Any]:
        if self.statistics is None:
            raise RuntimeError("Memory statistics service is not configured")
        return self.statistics.memory_status()

    def vector_status(self) -> dict[str, Any]:
        if self.statistics is None:
            raise RuntimeError("Memory statistics service is not configured")
        return self.statistics.vector_status()

    def vector_coverage(self) -> dict[str, Any]:
        if self.statistics is None:
            raise RuntimeError("Memory statistics service is not configured")
        return self.statistics.vector_coverage()

    def publish_statistics(self) -> dict[str, Any] | None:
        if self.statistics is None:
            return None
        try:
            return self.statistics.publish()
        except Exception as exc:
            self.runtime_warnings.append(
                {
                    "code": "memory_status_publish_failed",
                    "stage": "statistics",
                    "message": f"{type(exc).__name__}: {exc}"[:500],
                }
            )
            return None

    def rebuild(
        self,
        entries: list[dict[str, Any]],
        vault_root: Path | str,
        chunker=None,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        result = self.index_coordinator.sync(
            entries,
            vault_root,
            chunker,
            force=force,
        )
        if result.get("added") or result.get("updated") or result.get("removed") or result.get("full_rebuild"):
            self.retriever.clear_cache()
        event_type = "memory_index_rebuilt" if result.get("full_rebuild") else "memory_index_synced"
        self._event(event_type, "lingji", result)
        self.publish_statistics()
        return result

    def close(self) -> None:
        seen: set[int] = set()
        for resource in reversed(self._closeables):
            if resource is None or id(resource) in seen:
                continue
            seen.add(id(resource))
            close = getattr(resource, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    continue
        self._closeables.clear()

    def _event(self, event_type: str, entity_id: str, payload: dict[str, Any]) -> None:
        if self.state_db:
            self.state_db.append_event(event_type, "memory_gateway", entity_id, payload)
