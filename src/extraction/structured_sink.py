from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping

from src.sources import SourceReadModel

from .errors import safe_extraction_error
from .models import ExtractionBatch, StructuredConversation, StructuredMessage, StructuredSource

logger = logging.getLogger("lingji.extraction.structured")


class StructuredReadModelSink:
    """Write rebuildable source data through SourceReadModel's public package contract."""

    def __init__(
        self,
        read_model: SourceReadModel,
        *,
        storage_path: Path | str,
        state_db=None,
        memory_database=None,
    ):
        self.read_model = read_model
        self.storage_path = Path(storage_path)
        self.raw_root = self.storage_path / "raw"
        self.state_db = state_db
        self.memory_database = memory_database

    def write_batch(
        self,
        batch: ExtractionBatch,
        *,
        raw_snapshot: Mapping[str, Any] | None,
        vault_results: Mapping[str, Any],
        execution_id: str,
        adapter_name: str,
        adapter_version: str,
        indexing_succeeded: bool,
    ) -> dict[str, Any]:
        if not batch.structured_sources:
            return self._result("not_applicable")
        totals = {"sources": 0, "conversations": 0, "messages": 0, "links": 0}
        warnings: list[str] = []
        vault_map = self._vault_map(vault_results)
        raw_reference, raw_metadata = self._raw_provenance(raw_snapshot)
        try:
            for source in batch.structured_sources:
                bundle, bundle_warnings = self._bundle(
                    source,
                    raw_reference=raw_reference,
                    raw_metadata=raw_metadata,
                    vault_map=vault_map,
                    execution_id=execution_id,
                    adapter_name=adapter_name,
                    adapter_version=adapter_version,
                    indexing_succeeded=indexing_succeeded,
                )
                warnings.extend(bundle_warnings)
                counts = self.read_model.upsert_bundle(bundle)
                for key in totals:
                    totals[key] += int(counts.get(key) or 0)
            state = "written"
        except Exception as exc:
            logger.exception("Structured read model write failed")
            warnings.append(
                safe_extraction_error(
                    exc,
                    message="structured read model write failed; see local logs",
                )
            )
            state = "degraded"
            totals = {key: 0 for key in totals}
        result = self._result(state, **totals, warnings=warnings)
        self._event("structured_ingestion_completed", execution_id, result)
        return result

    def _bundle(
        self,
        source: StructuredSource,
        *,
        raw_reference: str,
        raw_metadata: Mapping[str, Any],
        vault_map: Mapping[str, str],
        execution_id: str,
        adapter_name: str,
        adapter_version: str,
        indexing_succeeded: bool,
    ) -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        conversations = []
        source_vault_reference = ""
        for conversation in source.conversations:
            document_stable_id = str(conversation.metadata.get("document_stable_id") or "")
            relative_path = vault_map.get(document_stable_id, "")
            vault_reference = f"vault:{relative_path}" if relative_path else ""
            source_vault_reference = source_vault_reference or vault_reference
            record, record_warnings = self._conversation_record(
                conversation,
                source=source,
                raw_reference=raw_reference,
                vault_reference=vault_reference,
                document_stable_id=document_stable_id,
                indexing_succeeded=indexing_succeeded,
            )
            conversations.append(record)
            warnings.extend(record_warnings)
        metadata = dict(source.metadata)
        metadata.update(raw_metadata)
        metadata.update(
            import_execution_id=execution_id,
            adapter_name=adapter_name,
            adapter_version=adapter_version,
        )
        return {
            "source": {
                "source_type": source.source_type,
                "external_id": source.external_id,
                "display_name": source.display_name,
                "raw_reference": raw_reference,
                "vault_reference": source_vault_reference,
                "privacy": source.privacy,
                "projects": list(source.projects),
                "agent_scope": list(source.agent_scope),
                "status": source.status,
                "metadata": metadata,
            },
            "conversations": conversations,
        }, warnings

    def _conversation_record(
        self,
        conversation: StructuredConversation,
        *,
        source: StructuredSource,
        raw_reference: str,
        vault_reference: str,
        document_stable_id: str,
        indexing_succeeded: bool,
    ) -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        metadata = dict(conversation.metadata)
        if vault_reference:
            metadata["vault_reference"] = vault_reference
        link_allowed = bool(
            indexing_succeeded
            and document_stable_id
            and self._memory_exists(document_stable_id)
        )
        if document_stable_id and not link_allowed:
            warnings.append(
                f"memory link skipped for conversation {conversation.external_id}: memory unavailable"
            )
        messages = []
        for message in conversation.messages:
            record = self._message_record(
                message,
                conversation=conversation,
                source=source,
                raw_reference=raw_reference,
            )
            if link_allowed:
                record["memory_links"] = [
                    {
                        "memory_id": document_stable_id,
                        "relation_type": "contained_in_source_document",
                    }
                ]
            messages.append(record)
        record: dict[str, Any] = {
            "external_id": conversation.external_id,
            "title": conversation.title,
            "participants": list(conversation.participants),
            "started_at": conversation.started_at,
            "ended_at": conversation.ended_at,
            "metadata": metadata,
            "messages": messages,
        }
        self._apply_inherited_fields(
            record,
            privacy=conversation.privacy,
            projects=conversation.projects,
            agent_scope=conversation.agent_scope,
            parent_privacy=source.privacy,
            parent_projects=source.projects,
            parent_agent_scope=source.agent_scope,
        )
        return record, warnings

    def _message_record(
        self,
        message: StructuredMessage,
        *,
        conversation: StructuredConversation,
        source: StructuredSource,
        raw_reference: str,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "external_id": message.external_id,
            "role": message.role,
            "author": message.author,
            "occurred_at": message.occurred_at,
            "sequence": message.sequence,
            "content": message.content,
            "raw_reference": message.raw_reference or raw_reference,
            "metadata": dict(message.metadata),
        }
        self._apply_inherited_fields(
            record,
            privacy=message.privacy,
            projects=message.projects,
            agent_scope=message.agent_scope,
            parent_privacy=conversation.privacy or source.privacy,
            parent_projects=conversation.projects or source.projects,
            parent_agent_scope=conversation.agent_scope or source.agent_scope,
        )
        return record

    @staticmethod
    def _apply_inherited_fields(
        record: dict[str, Any],
        *,
        privacy: str | None,
        projects: tuple[str, ...],
        agent_scope: tuple[str, ...],
        parent_privacy: str,
        parent_projects: tuple[str, ...],
        parent_agent_scope: tuple[str, ...],
    ) -> None:
        if privacy is not None and privacy != parent_privacy:
            record["privacy"] = privacy
        if projects and projects != parent_projects:
            record["projects"] = list(projects)
        if agent_scope and agent_scope != parent_agent_scope:
            record["agent_scope"] = list(agent_scope)

    def _raw_provenance(
        self, raw_snapshot: Mapping[str, Any] | None
    ) -> tuple[str, dict[str, Any]]:
        if not raw_snapshot:
            return "", {}
        raw_path = Path(str(raw_snapshot.get("raw_path") or ""))
        reference = ""
        try:
            relative = raw_path.resolve().relative_to(self.raw_root.resolve())
            reference = f"raw:{relative.as_posix()}"
        except (ValueError, OSError):
            logger.warning("Raw snapshot is outside configured raw root; reference omitted")
        return reference, {
            "raw_sha256": str(raw_snapshot.get("sha256") or ""),
            "raw_kind": str(raw_snapshot.get("kind") or ""),
            "raw_size": int(raw_snapshot.get("size") or 0),
        }

    @staticmethod
    def _vault_map(vault_results: Mapping[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for action in ("created", "updated", "skipped"):
            for item in vault_results.get(action) or []:
                stable_id = str(item.get("id") or "")
                relative_path = str(item.get("relative_path") or "")
                if stable_id and relative_path and not Path(relative_path).is_absolute():
                    result[stable_id] = Path(relative_path).as_posix()
        return result

    def _memory_exists(self, memory_id: str) -> bool:
        if self.memory_database is None:
            return False
        for method_name in ("fetch_memory", "get_document", "get_memory", "get"):
            method = getattr(self.memory_database, method_name, None)
            if not callable(method):
                continue
            try:
                if method_name == "fetch_memory":
                    return bool(method(memory_id, include_chunks=False))
                return bool(method(memory_id))
            except (KeyError, LookupError):
                return False
            except TypeError:
                continue
        return False

    @staticmethod
    def _result(
        state: str,
        *,
        sources: int = 0,
        conversations: int = 0,
        messages: int = 0,
        links: int = 0,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "state": state,
            "sources": sources,
            "conversations": conversations,
            "messages": messages,
            "links": links,
            "warnings": list(warnings or []),
        }

    def _event(self, event_type: str, entity_id: str, payload: Mapping[str, Any]) -> None:
        if self.state_db is None:
            return
        try:
            self.state_db.append_event(
                event_type,
                "structured_ingestion",
                entity_id,
                dict(payload),
            )
        except Exception:
            logger.exception("Failed to append structured ingestion audit event")
