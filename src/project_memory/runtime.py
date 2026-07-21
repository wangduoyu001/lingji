from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.codex_sessions import CodexSessionArchive, CodexSessionService
from src.indexer.index import PEMISIndex
from src.project_context import ProjectRegistry, ProjectResolver
from src.retrieval import MarkdownChunker
from src.sources import SourceReadModel

from .context_service import ProjectContextService
from .review_service import MemoryReviewService


@dataclass(frozen=True)
class CodexMemoryLoopServices:
    project_resolver: ProjectResolver
    codex_sessions: CodexSessionService
    project_context: ProjectContextService
    memory_review: MemoryReviewService


def build_codex_memory_loop(
    settings: Any,
    *,
    gateway: Any,
    pipeline: Any,
    state_db: Any | None = None,
) -> CodexMemoryLoopServices:
    """Build the single Codex-first memory loop shared by Control API and MCP."""

    registry = ProjectRegistry(Path(settings.storage_path) / "project_registry.json")
    resolver = ProjectResolver(registry)
    archive = CodexSessionArchive(settings.storage_path)
    sessions = CodexSessionService(
        resolver,
        archive,
        pipeline,
        state_db=state_db,
    )

    def session_provider(
        *,
        project_id: str,
        session_id: str = "",
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        page = sessions.list_sessions(project_id=project_id, limit=limit, offset=0)
        output: list[dict[str, Any]] = []
        for summary in page.get("items") or []:
            selected_id = str(summary.get("session_id") or "")
            if session_id and selected_id != session_id:
                continue
            full = sessions.get_session(selected_id)
            events = list(full.get("events") or [])
            last = events[-1] if events else {}
            source_id = SourceReadModel.stable_id(
                "source", "codex_session", f"codex:{project_id}"
            )
            conversation_id = SourceReadModel.stable_id(
                "conversation", source_id, selected_id
            )
            output.append(
                {
                    "session_id": selected_id,
                    "conversation_id": conversation_id,
                    "source_id": source_id,
                    "project_ids": [project_id],
                    "agent_scope": ["codex", "lingji-local"],
                    "privacy": str(full.get("privacy") or "private"),
                    "status": str(full.get("status") or "completed"),
                    "title": str(full.get("title") or selected_id),
                    "summary": str(last.get("summary") or full.get("title") or ""),
                    "text": str(last.get("summary") or full.get("title") or ""),
                    "started_at": str(full.get("created_at") or ""),
                    "ended_at": str(full.get("ended_at") or ""),
                    "branch": str(full.get("branch") or ""),
                }
            )
        return output

    project_context = ProjectContextService(
        gateway.database,
        gateway.retriever,
        profiles=gateway.profiles,
        session_provider=session_provider,
    )

    indexer = PEMISIndex(
        getattr(getattr(gateway, "workspace", None), "vault_path", None)
        or settings.vault_path,
        settings.storage_path,
        include_private=False,
    )
    chunker = MarkdownChunker(
        settings.memory_chunk_max_chars,
        settings.memory_chunk_overlap_chars,
    )

    def sync_memory_index(_path: Path) -> None:
        entries = indexer.build_index(force=False)
        gateway.rebuild(entries, indexer.vault_dir, chunker)

    memory_review = MemoryReviewService(
        gateway.lifecycle,
        database=gateway.database,
        index_sync=sync_memory_index,
        state_db=state_db,
    )
    return CodexMemoryLoopServices(
        project_resolver=resolver,
        codex_sessions=sessions,
        project_context=project_context,
        memory_review=memory_review,
    )
