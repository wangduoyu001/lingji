from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import Settings
from src.gateway.bootstrap import build_memory_gateway
from src.indexer.index import PEMISIndex
from src.obsidian.frontmatter import render_frontmatter
from src.retrieval import MarkdownChunker
from src.runtime import WorkspaceContext, WorkspaceResolver

FUTURE_SEMANTIC_CONTRACTS = (
    "semantic results include citations",
    "semantic outage preserves lexical retrieval with a warning",
    "active and core chunks have matching semantic points",
    "semantic payloads enforce privacy and agent scope",
    "semantic collections remain isolated by workspace",
)


@dataclass
class LexicalMemoryCapabilityFixture:
    """Implementation adapter for the directory-independent capability contract."""

    context: WorkspaceContext
    settings: Settings
    semantic_enabled: bool = False
    gateway: Any = field(init=False)
    chunker: MarkdownChunker = field(init=False)

    def __post_init__(self) -> None:
        self.context.vault_path.mkdir(parents=True, exist_ok=True)
        self.context.storage_path.mkdir(parents=True, exist_ok=True)
        self.chunker = MarkdownChunker(
            self.settings.memory_chunk_max_chars,
            self.settings.memory_chunk_overlap_chars,
        )
        self.gateway = build_memory_gateway(
            self.settings,
            rebuild_if_empty=False,
            workspace=self.context,
        )

    @property
    def capabilities(self) -> dict[str, bool]:
        return {
            "lexical_enabled": True,
            "semantic_enabled": self.semantic_enabled,
            "compatibility_database_required": False,
            "compatibility_api_required": False,
            "qdrant_required": False,
        }

    def write_memory(
        self,
        relative_path: str,
        memory_id: str,
        title: str,
        body: str,
        **metadata: Any,
    ) -> Path:
        path = self.context.vault_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        values: dict[str, Any] = {
            "schema_version": 1,
            "id": memory_id,
            "title": title,
            "memory_type": "knowledge",
            "memory_tier": "archival",
            "status": "active",
            "review_status": "approved",
            "privacy": "private",
            "importance": "medium",
            "project": [],
            "tags": [],
            "agent_scope": ["all"],
        }
        values.update(metadata)
        path.write_text(render_frontmatter(values, body), encoding="utf-8")
        return path

    def rebuild(self) -> dict[str, Any]:
        indexer = PEMISIndex(
            self.context.vault_path,
            self.context.storage_path,
            include_private=self.settings.index_private,
        )
        indexer.build_index(force=True)
        return self.gateway.rebuild(
            indexer.get_all(),
            self.context.vault_path,
            self.chunker,
            force=True,
        )

    def search(
        self,
        query: str,
        *,
        agent_id: str = "lingji-local",
        **filters: Any,
    ) -> list[dict[str, Any]]:
        return self.gateway.search_memory(agent_id, query, **filters)["results"]

    def fetch(
        self,
        memory_id: str,
        *,
        agent_id: str = "lingji-local",
    ) -> dict[str, Any] | None:
        return self.gateway.fetch_memory(agent_id, memory_id=memory_id)

    def core(self, *, agent_id: str = "lingji-local") -> list[dict[str, Any]]:
        return self.gateway.get_core_memory(agent_id)["memories"]

    def context_pack(
        self,
        query: str,
        *,
        agent_id: str = "lingji-local",
        max_chars: int = 1200,
    ) -> dict[str, Any]:
        return self.gateway.build_context_pack(
            agent_id,
            query=query,
            max_chars=max_chars,
        )


def build_workspace_memory_fixtures(
    root: Path,
) -> dict[str, LexicalMemoryCapabilityFixture]:
    settings = Settings(
        _env_file=None,
        workspace_name="production",
        workspace_root=str(root / "workspace-data"),
        production_qdrant_collection="lingji_memory_production_test",
        acceptance_qdrant_collection="lingji_memory_acceptance_test",
        semantic_enabled=False,
        vault_auto_init=False,
        index_private=False,
        memory_chunk_max_chars=500,
        memory_chunk_overlap_chars=60,
        memory_search_cache_size=16,
        memory_search_cache_ttl_seconds=0,
    )
    contexts = WorkspaceResolver.resolve_all(
        settings,
        environ={},
        project_root=root,
    )
    return {
        name.value: LexicalMemoryCapabilityFixture(context, settings)
        for name, context in contexts.items()
    }
