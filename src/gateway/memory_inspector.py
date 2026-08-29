from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from src.sources.service import SourceQueryService, ViewerContext
from .owner_memory_cards import OwnerMemoryCardProjector


logger = logging.getLogger("lingji.gateway.memory_inspector")
VECTOR_ERROR_MESSAGE = "Vector status unavailable; see local logs"


class ReadModelUnavailableError(RuntimeError):
    """Raised when the inspector's rebuildable SQLite read model is unavailable."""


class MemoryInspectorFacade:
    """Read-only facade for canonical memory, source records and vector diagnostics."""

    def __init__(
        self,
        database: Any,
        source_service: SourceQueryService,
        statistics: Any,
        *,
        gateway: Any | None = None,
        state_db: Any | None = None,
        workspace: str = "production",
    ):
        self.database = database
        self.source_service = source_service
        self.statistics = statistics
        self.gateway = gateway
        self.workspace = str(workspace or "production")
        self.card_projector = OwnerMemoryCardProjector(
            database,
            source_service,
            statistics,
            gateway=gateway,
            state_db=state_db if state_db is not None else getattr(gateway, "state_db", None),
            workspace=self.workspace,
        )

    def status(self) -> dict[str, Any]:
        try:
            source_status = self.source_service.status()
            memory_status = self.statistics.memory_status()
            vector_status = self.statistics.vector_status()
        except Exception as exc:
            raise ReadModelUnavailableError(self._safe_error(exc)) from exc
        return self._envelope(
            {
                "state": self._overall_state(memory_status, vector_status),
                "authority": {
                    "permanent_memory": "obsidian_vault_git",
                    "raw_sources": "workspace_raw",
                    "lexical_read_model": "lingji_memory_db",
                    "semantic_index": "qdrant",
                },
                "memory": memory_status,
                "vector": vector_status,
                "sources": {
                    key: value
                    for key, value in source_status.items()
                    if key not in {"as_of", "workspace", "viewer_scope", "viewer_agent_id"}
                },
            }
        )

    def list_sources(self, **filters: Any) -> dict[str, Any]:
        return self.source_service.list_sources(**filters)

    def get_source(self, source_id: str) -> dict[str, Any]:
        return self.source_service.get_source(source_id)

    def list_conversations(self, **filters: Any) -> dict[str, Any]:
        return self.source_service.list_conversations(**filters)

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        return self.source_service.get_conversation(conversation_id)

    def list_messages(self, **filters: Any) -> dict[str, Any]:
        return self.source_service.list_messages(**filters)

    def get_message(self, message_id: str) -> dict[str, Any]:
        return self.source_service.get_message(message_id)

    def list_memories(
        self,
        *,
        viewer: ViewerContext | None = None,
        memory_type: str | None = None,
        status: str | None = None,
        privacy: str | None = None,
        project: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        selected = viewer or self.source_service.owner_viewer()
        selected_limit, selected_offset = self._page_values(limit, offset)
        allowed_privacy = selected.allowed_privacy
        if privacy:
            allowed_privacy = (privacy,) if privacy in allowed_privacy else ()
        where: list[str] = []
        params: list[Any] = []
        if allowed_privacy:
            where.append(f"privacy IN ({','.join('?' for _ in allowed_privacy)})")
            params.extend(allowed_privacy)
        else:
            where.append("1 = 0")
        if memory_type:
            where.append("memory_type = ?")
            params.append(memory_type)
        if status:
            where.append("status = ?")
            params.append(status)
        if project:
            where.append("EXISTS (SELECT 1 FROM json_each(project_json) WHERE value = ?)")
            params.append(project)
        if not selected.owner:
            where.append(
                """(
                    json_array_length(agent_scope_json) = 0 OR
                    EXISTS (
                        SELECT 1 FROM json_each(agent_scope_json)
                        WHERE value IN (?, 'all')
                    )
                )"""
            )
            params.append(selected.agent_id)
        clean_query = " ".join(str(q or "").strip().split())
        if clean_query:
            escaped = clean_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            where.append(
                "(title LIKE ? ESCAPE '\\' OR relative_path LIKE ? ESCAPE '\\' "
                "OR tags_json LIKE ? ESCAPE '\\')"
            )
            params.extend([f"%{escaped}%"] * 3)
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        try:
            with self.database._connection() as connection:
                total = int(
                    connection.execute(
                        f"SELECT COUNT(*) AS count FROM memory_documents{where_sql}", params
                    ).fetchone()["count"]
                )
                rows = connection.execute(
                    f"""
                    SELECT *
                    FROM memory_documents
                    {where_sql}
                    ORDER BY COALESCE(modified_at, updated_at, '') DESC, memory_id DESC
                    LIMIT ? OFFSET ?
                    """,
                    [*params, selected_limit, selected_offset],
                ).fetchall()
        except Exception as exc:
            raise ReadModelUnavailableError(self._safe_error(exc)) from exc
        items = [self._memory_summary(row) for row in rows]
        return self._envelope(
            {
                "viewer_scope": selected.viewer_scope,
                "viewer_agent_id": selected.agent_id,
                "items": items,
                "pagination": {
                    "limit": selected_limit,
                    "offset": selected_offset,
                    "total": total,
                    "has_more": selected_offset + len(items) < total,
                },
            }
        )

    def list_cards(
        self,
        *,
        viewer: ViewerContext | None = None,
        state: str | None = None,
        action: str | None = None,
        source: str | None = None,
        source_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
        include_evidence: bool = False,
    ) -> dict[str, Any]:
        """Return concise owner cards over the same read authorities."""
        return self.card_projector.list_cards(
            viewer=viewer,
            state=state,
            action=action,
            source=source,
            source_id=source_id,
            limit=limit,
            offset=offset,
            include_evidence=include_evidence,
        )

    def get_card(
        self,
        memory_id: str,
        *,
        viewer: ViewerContext | None = None,
        include_evidence: bool = True,
    ) -> dict[str, Any]:
        return self.card_projector.get_card(
            memory_id, viewer=viewer, include_evidence=include_evidence
        )

    def get_memory(
        self, memory_id: str, *, viewer: ViewerContext | None = None
    ) -> dict[str, Any]:
        selected = viewer or self.source_service.owner_viewer()
        try:
            if selected.owner:
                memory = self.database.fetch_memory(memory_id, include_chunks=True)
            elif self.gateway is not None and selected.agent_id:
                memory = self.gateway.fetch_memory(selected.agent_id, memory_id=memory_id)
            else:
                memory = self.database.fetch_memory(memory_id, include_chunks=True)
                self._check_memory_visibility(memory, selected)
        except PermissionError:
            raise
        except Exception as exc:
            raise ReadModelUnavailableError(self._safe_error(exc)) from exc
        if not memory:
            raise LookupError("memory not found")
        self._check_memory_visibility(memory, selected)
        detail = dict(memory)
        detail["citations"] = [
            {
                "chunk_id": chunk.get("chunk_id"),
                "relative_path": memory.get("relative_path"),
                "start_line": chunk.get("start_line"),
                "end_line": chunk.get("end_line"),
            }
            for chunk in detail.get("chunks") or []
        ]
        return self._envelope(
            {
                "viewer_scope": selected.viewer_scope,
                "viewer_agent_id": selected.agent_id,
                "item": detail,
            }
        )

    def memory_source(
        self, memory_id: str, *, viewer: ViewerContext | None = None
    ) -> dict[str, Any]:
        memory_response = self.get_memory(memory_id, viewer=viewer)
        source_response = self.source_service.memory_sources(memory_id, viewer=viewer)
        memory = memory_response["item"]
        return self._envelope(
            {
                "viewer_scope": source_response.get("viewer_scope", "owner"),
                "viewer_agent_id": source_response.get("viewer_agent_id"),
                "memory_id": memory_id,
                "canonical": {
                    "relative_path": memory.get("relative_path"),
                    "citations": memory.get("citations") or [],
                },
                "links": source_response.get("links") or [],
            }
        )

    def memory_vector(
        self, memory_id: str, *, viewer: ViewerContext | None = None
    ) -> dict[str, Any]:
        detail = self.get_memory(memory_id, viewer=viewer)
        memory = detail["item"]
        chunks = list(memory.get("chunks") or [])
        snapshot = self.statistics.vector_status()
        semantic = getattr(getattr(self.gateway, "retriever", None), "semantic_provider", None)
        rebuild_required = snapshot.get("rebuild_required")
        snapshot_error = self._safe_vector_error(snapshot.get("last_error"))
        output = []
        for chunk in chunks:
            chunk_id = str(chunk.get("chunk_id") or "")
            exists: bool | None = None
            source = "unavailable"
            last_error = snapshot_error
            if semantic is not None:
                try:
                    exists = bool(semantic.exists(chunk_id))
                    source = "live"
                    last_error = None
                except Exception:
                    logger.exception("Vector existence check failed for chunk %s", chunk_id)
                    exists = None
                    source = "unavailable"
                    last_error = VECTOR_ERROR_MESSAGE
            output.append(
                {
                    "memory_id": memory_id,
                    "chunk_id": chunk_id,
                    "expected": True,
                    "exists": exists,
                    "source": source,
                    "collection": snapshot.get("collection"),
                    "dimension": snapshot.get("dimension"),
                    "rebuild_required": rebuild_required,
                    "last_error": last_error,
                }
            )
        return self._envelope(
            {
                "memory_id": memory_id,
                "vector": {
                    "state": snapshot.get("state"),
                    "source": snapshot.get("source"),
                    "collection": snapshot.get("collection"),
                    "dimension": snapshot.get("dimension"),
                    "rebuild_required": rebuild_required,
                    "last_error": snapshot_error,
                    "chunks": output,
                },
            }
        )

    def _memory_summary(self, row: Any) -> dict[str, Any]:
        item = dict(row)
        item["aliases"] = self._loads(item.pop("aliases_json", "[]"), [])
        item["projects"] = self._loads(item.pop("project_json", "[]"), [])
        item["tags"] = self._loads(item.pop("tags_json", "[]"), [])
        item["relationships"] = self._loads(item.pop("relationships_json", "{}"), {})
        item["agent_scope"] = self._loads(item.pop("agent_scope_json", "[]"), [])
        item["pin_to_context"] = bool(item.get("pin_to_context"))
        return item

    @staticmethod
    def _check_memory_visibility(
        memory: dict[str, Any] | None, viewer: ViewerContext
    ) -> None:
        if not memory:
            return
        if memory.get("privacy") not in viewer.allowed_privacy:
            raise PermissionError("memory privacy is not visible to this viewer")
        if viewer.owner:
            return
        scopes = list(memory.get("agent_scope") or [])
        if scopes and "all" not in scopes and viewer.agent_id not in scopes:
            raise PermissionError("memory is not scoped to this viewer")

    @staticmethod
    def _page_values(limit: int, offset: int) -> tuple[int, int]:
        selected_limit = int(limit)
        selected_offset = int(offset)
        if selected_limit < 1 or selected_limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if selected_offset < 0:
            raise ValueError("offset must be greater than or equal to zero")
        return selected_limit, selected_offset

    def _envelope(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "workspace": self.workspace,
            **payload,
        }

    @staticmethod
    def _overall_state(memory: dict[str, Any], vector: dict[str, Any]) -> str:
        states = {str(memory.get("state") or ""), str(vector.get("state") or "")}
        if "unavailable" in states or "degraded" in states:
            return "degraded"
        if "configuration_required" in states:
            return "configuration_required"
        return "healthy"

    @staticmethod
    def _loads(value: Any, fallback: Any) -> Any:
        if value in (None, ""):
            return fallback
        try:
            return json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return fallback

    @staticmethod
    def _safe_vector_error(value: Any) -> str | None:
        return VECTOR_ERROR_MESSAGE if value else None

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        return f"{type(exc).__name__}: {exc}"[:500]
