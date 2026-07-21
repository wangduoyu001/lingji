from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .base import ExtractionAdapter
from .models import (
    ExtractionBatch,
    ExtractionRequest,
    StructuredConversation,
    StructuredMessage,
    StructuredSource,
)


class _StructuredOutputAdapter(ExtractionAdapter):
    """Decorate explicitly opted-in legacy adapters without re-parsing input."""

    def __init__(self, adapter: ExtractionAdapter):
        self._adapter = adapter
        self.name = adapter.name
        self.version = adapter.version
        self.source_types = adapter.source_types

    def can_handle(self, source_type, input_path, payload):
        return self._adapter.can_handle(source_type, input_path, payload)

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        batch = self._adapter.extract(request)
        if batch.structured_sources or not batch.documents:
            return batch
        source = self._structured_source(request, batch)
        return ExtractionBatch(
            documents=batch.documents,
            summary=batch.summary,
            warnings=batch.warnings,
            structured_sources=(source,),
        )

    def _structured_source(self, request: ExtractionRequest, batch: ExtractionBatch) -> StructuredSource:
        documents = batch.documents
        first = documents[0]
        source_type = first.source_type or request.source_type
        metadata = dict(first.metadata)
        projects = self._tuple(metadata.get("project") or metadata.get("project_id"))
        privacy = str(metadata.get("privacy") or request.options.get("privacy") or "private")
        source_external_id = str(
            request.options.get("source_external_id")
            or metadata.get("account_name")
            or metadata.get("repository")
            or metadata.get("platform")
            or f"{source_type}:default"
        )
        display_name = str(
            request.options.get("source_display_name")
            or metadata.get("account_name")
            or metadata.get("platform")
            or metadata.get("repository")
            or source_type.title()
        )
        messages = tuple(
            StructuredMessage(
                external_id=document.stable_id,
                role=self._role(document.destination),
                author=str(document.metadata.get("author") or document.metadata.get("agent") or ""),
                occurred_at=document.updated_at or document.created_at,
                sequence=index,
                content=self._safe_content(document.body, request.input_path),
                privacy=str(document.metadata.get("privacy") or privacy),
                projects=self._tuple(document.metadata.get("project") or document.metadata.get("project_id")),
                metadata={
                    "document_stable_id": document.stable_id,
                    "destination": document.destination,
                    "external_id": document.external_id,
                    "status": document.metadata.get("status", "active"),
                    "capture_method": document.metadata.get("capture_method", ""),
                    "media_kind": document.metadata.get("media_kind", ""),
                    "semantic_status": document.metadata.get("semantic_status", ""),
                },
            )
            for index, document in enumerate(documents)
        )
        conversation_external_id = str(metadata.get("task_id") or first.external_id or first.stable_id)
        conversation = StructuredConversation(
            external_id=conversation_external_id,
            title=first.title,
            messages=messages,
            started_at=first.created_at,
            ended_at=first.updated_at,
            participants=tuple(dict.fromkeys(item.author or item.role for item in messages)),
            privacy=privacy,
            projects=projects,
            metadata={
                "document_stable_id": first.stable_id,
                "adapter_name": self.name,
                "adapter_version": self.version,
                "message_count": len(messages),
            },
        )
        return StructuredSource(
            source_type=source_type,
            external_id=source_external_id,
            display_name=display_name,
            conversations=(conversation,),
            privacy=str(request.options.get("source_privacy") or "private"),
            projects=projects,
            metadata={"adapter_name": self.name, "adapter_version": self.version},
        )

    @staticmethod
    def _safe_content(content: str, input_path: Path | None) -> str:
        if not input_path:
            return content
        candidates = {str(input_path), str(input_path.expanduser())}
        try:
            candidates.add(str(input_path.resolve()))
        except OSError:
            pass
        result = content
        for value in sorted((item for item in candidates if item), key=len, reverse=True):
            result = result.replace(value, "[local file]")
            result = result.replace(value.replace("\\", "/"), "[local file]")
        return result

    @staticmethod
    def _role(destination: str) -> str:
        return {
            "work_report": "assistant",
            "error": "error",
            "decision": "decision",
            "task": "task",
            "source_archive": "content",
            "private_source": "content",
        }.get(destination, "content")

    @staticmethod
    def _tuple(value: Any) -> tuple[str, ...]:
        if value in (None, "", [], ()):
            return ()
        if isinstance(value, (list, tuple, set)):
            return tuple(str(item) for item in value if str(item))
        return (str(value),)


class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, ExtractionAdapter] = {}

    def register(self, adapter: ExtractionAdapter, structured_fallback: bool = False) -> None:
        name = str(adapter.name).strip().lower()
        if not name:
            raise ValueError("Adapter name is required")
        if name in self._adapters:
            raise ValueError(f"Adapter already registered: {name}")
        self._adapters[name] = _StructuredOutputAdapter(adapter) if structured_fallback else adapter

    def get(self, name: str) -> ExtractionAdapter:
        key = str(name).strip().lower()
        try:
            return self._adapters[key]
        except KeyError as exc:
            raise LookupError(f"Unknown extraction adapter: {name}") from exc

    def resolve(
        self,
        source_type: str,
        input_path: Path | None = None,
        payload: Mapping[str, Any] | None = None,
        preferred: str | None = None,
    ) -> ExtractionAdapter:
        payload = payload or {}
        if preferred:
            adapter = self.get(preferred)
            if not adapter.can_handle(source_type, input_path, payload):
                raise ValueError(f"Adapter {adapter.name} cannot handle source type {source_type}")
            return adapter
        for adapter in self._adapters.values():
            if adapter.can_handle(source_type, input_path, payload):
                return adapter
        raise LookupError(f"No extraction adapter for source type: {source_type}")

    def list(self) -> list[dict[str, Any]]:
        return [
            {"name": adapter.name, "version": adapter.version, "source_types": list(adapter.source_types)}
            for adapter in self._adapters.values()
        ]
