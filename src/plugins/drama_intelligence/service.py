from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.model_center import build_embedding_provider
from src.retrieval import QdrantSemanticProvider, SemanticPoint
from src.runtime.workspace import WorkspaceResolver

from .importer import SUPPORTED_EXTENSIONS, load_script
from .models import DramaChunk
from .parser import parse_script
from .repository import DramaRepository


@dataclass(frozen=True)
class _DramaPaths:
    workspace: str
    root: Path
    raw_root: Path
    normalized_root: Path
    knowledge_root: Path
    index_root: Path


class DramaSemanticIndex:
    """Reuse LingJi embedding and Qdrant services with a separate Drama collection."""

    def __init__(
        self,
        provider: QdrantSemanticProvider | None,
        *,
        reason: str | None = None,
        closeables: Iterable[Any] = (),
    ):
        self.provider = provider
        self.reason = reason
        self._closeables = list(closeables)

    @classmethod
    def from_runtime(
        cls,
        settings: Any,
        *,
        memory_gateway: Any | None = None,
        runtime_values: Mapping[str, Any] | None = None,
    ) -> "DramaSemanticIndex":
        base = getattr(getattr(memory_gateway, "retriever", None), "semantic_provider", None)
        workspace = getattr(memory_gateway, "workspace", None)
        if base is not None and workspace is not None:
            try:
                workspace_name = getattr(getattr(workspace, "name", None), "value", None) or "production"
                provider = QdrantSemanticProvider(
                    replace(workspace, qdrant_collection=f"lingji_drama_{workspace_name}"),
                    base.embedding_provider,
                    client=base.client,
                    distance=base.distance,
                    timeout_seconds=base.timeout_seconds,
                    collection_schema="drama-v1",
                )
                return cls(provider)
            except Exception as exc:
                return cls(None, reason=f"{type(exc).__name__}: {exc}"[:500])

        embedding = None
        provider = None
        try:
            values = dict(runtime_values or {})
            embedding = build_embedding_provider(settings, values)
            if embedding is None:
                return cls(None, reason="embedding_disabled")
            workspace = workspace or WorkspaceResolver.resolve(settings)
            workspace_name = getattr(workspace.name, "value", str(workspace.name))
            provider = QdrantSemanticProvider(
                replace(workspace, qdrant_collection=f"lingji_drama_{workspace_name}"),
                embedding,
                distance=str(values.get("qdrant_distance", settings.qdrant_distance)),
                timeout_seconds=float(
                    values.get("qdrant_timeout_seconds", settings.qdrant_timeout_seconds)
                ),
                collection_schema="drama-v1",
            )
            return cls(provider, closeables=(provider, embedding))
        except Exception as exc:
            for resource in (provider, embedding):
                close = getattr(resource, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass
            return cls(None, reason=f"{type(exc).__name__}: {exc}"[:500])

    def index(self, chunks: Iterable[DramaChunk], *, title: str) -> dict[str, Any]:
        selected = list(chunks)
        if self.provider is None:
            return {"state": "disabled", "indexed": 0, "reason": self.reason}
        points = [
            SemanticPoint(
                chunk_id=item.chunk_id,
                memory_id=item.drama_id,
                text=item.text,
                payload={
                    "kind": "drama_chunk",
                    "project": item.drama_id,
                    "memory_type": item.chunk_type,
                    "drama_id": item.drama_id,
                    "drama_title": title,
                    "chunk_type": item.chunk_type,
                    "heading": item.heading,
                    "episode_number": item.episode_number,
                    "scene_number": item.scene_number,
                    "source_ref": item.source_ref,
                    "source_locator": item.source_locator,
                    "characters": list(item.characters),
                    "tags": list(item.tags),
                },
            )
            for item in selected
        ]
        self.provider.upsert_many(points)
        return {
            "state": "ready",
            "indexed": len(points),
            "collection": self.provider.collection,
        }

    def replace(self, chunks: Iterable[DramaChunk], *, drama_id: str, title: str) -> dict[str, Any]:
        if self.provider is None:
            return {"state": "disabled", "indexed": 0, "reason": self.reason}
        self.provider.delete_memory(drama_id)
        return self.index(chunks, title=title)

    def delete_drama(self, drama_id: str) -> None:
        if self.provider is not None:
            self.provider.delete_memory(drama_id)

    def search(
        self,
        query: str,
        *,
        limit: int,
        drama_id: str | None,
        chunk_type: str | None,
    ) -> list[dict[str, Any]]:
        if self.provider is None:
            return []
        filters: dict[str, Any] = {}
        if drama_id:
            filters["project"] = drama_id
        if chunk_type:
            filters["memory_types"] = [chunk_type]
        return self.provider.search(query, limit=max(limit, 1), filters=filters)

    def status(self) -> dict[str, Any]:
        if self.provider is None:
            return {"state": "disabled", "reason": self.reason, "collection": None}
        payload = self.provider.status()
        payload["state"] = "ready" if payload.get("ready") else "degraded"
        return payload

    def close(self) -> None:
        for resource in reversed(self._closeables):
            close = getattr(resource, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        self._closeables.clear()


class DramaService:
    """Application service for source-traceable Drama Memory."""

    def __init__(
        self,
        settings: Any,
        *,
        memory_gateway: Any | None = None,
        runtime_values: Mapping[str, Any] | None = None,
    ):
        self.settings = settings
        self.paths = self._resolve_paths(settings, memory_gateway)
        self.workspace = self.paths.workspace
        self.root = self.paths.root
        self.raw_root = self.paths.raw_root
        self.normalized_root = self.paths.normalized_root
        self.knowledge_root = self.paths.knowledge_root
        self.index_root = self.paths.index_root
        for path in (self.raw_root, self.normalized_root, self.knowledge_root, self.index_root):
            path.mkdir(parents=True, exist_ok=True)
        self.repository = DramaRepository(self.index_root / "drama_read_model.db")
        self.semantic = DramaSemanticIndex.from_runtime(
            settings,
            memory_gateway=memory_gateway,
            runtime_values=runtime_values,
        )

    def import_script(
        self,
        source_path: str,
        *,
        title: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        source = load_script(source_path, title=title)
        existing = self.repository.find_by_sha256(source.sha256)
        if existing and not force:
            return {
                "duplicate": True,
                "drama": existing,
                "semantic": self.semantic.status(),
                "warnings": list(source.warnings),
            }

        parsed = parse_script(source)
        drama_id = str(existing.get("drama_id")) if existing else parsed.drama_id
        raw_directory = self.raw_root / drama_id
        normalized_directory = self.normalized_root / drama_id
        knowledge_directory = self.knowledge_root / drama_id
        for path in (raw_directory, normalized_directory, knowledge_directory):
            path.mkdir(parents=True, exist_ok=True)
        raw_path = raw_directory / f"original{source.source_path.suffix.lower()}"
        normalized_path = normalized_directory / "full_text.md"
        shutil.copy2(source.source_path, raw_path)
        normalized_path.write_text(source.text, encoding="utf-8")
        (normalized_directory / "source_map.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "drama_id": drama_id,
                    "source_path": str(source.source_path),
                    "raw_path": str(raw_path),
                    "sha256": source.sha256,
                    "units": list(source.source_units),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (knowledge_directory / "drama.json").write_text(
            json.dumps(parsed.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        drama = self.repository.save(
            parsed,
            raw_path=raw_path,
            normalized_path=normalized_path,
            force=force,
        )
        semantic_error = None
        try:
            if existing and force:
                semantic = self.semantic.replace(
                    parsed.chunks,
                    drama_id=drama_id,
                    title=parsed.title,
                )
            else:
                semantic = self.semantic.index(parsed.chunks, title=parsed.title)
        except Exception as exc:
            semantic_error = f"{type(exc).__name__}: {exc}"[:500]
            semantic = {"state": "degraded", "indexed": 0, "error": semantic_error}
        return {
            "duplicate": False,
            "drama": drama,
            "semantic": semantic,
            "warnings": [*source.warnings, *([semantic_error] if semantic_error else [])],
        }

    def status(self) -> dict[str, Any]:
        return {
            "state": "ready",
            "workspace": self.workspace,
            "root": str(self.root),
            "paths": {
                "raw": str(self.raw_root),
                "normalized": str(self.normalized_root),
                "knowledge": str(self.knowledge_root),
                "index": str(self.index_root),
            },
            "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
            "structured": self.repository.status(),
            "semantic": self.semantic.status(),
        }

    def list_dramas(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return self.repository.list_dramas(limit=limit, offset=offset)

    def get_drama(self, drama_id: str) -> dict[str, Any]:
        return self.repository.get_drama(drama_id)

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        drama_id: str | None = None,
        chunk_type: str | None = None,
    ) -> dict[str, Any]:
        clean = " ".join(str(query or "").split())
        if not clean:
            raise ValueError("query must not be empty")
        bounded = min(max(int(limit), 1), 50)
        candidate_limit = max(bounded * 6, 30)
        lexical = self.repository.search_lexical(
            clean,
            limit=candidate_limit,
            drama_id=drama_id,
            chunk_type=chunk_type,
        )
        semantic_error = None
        try:
            semantic = self.semantic.search(
                clean,
                limit=candidate_limit,
                drama_id=drama_id,
                chunk_type=chunk_type,
            )
        except Exception as exc:
            semantic = []
            semantic_error = f"{type(exc).__name__}: {exc}"[:500]

        scores: dict[str, float] = {}
        evidence: dict[str, dict[str, Any]] = {}
        catalog = {str(item["chunk_id"]): dict(item) for item in lexical}
        for rank, item in enumerate(lexical, start=1):
            chunk_id = str(item["chunk_id"])
            lexical_score = float(item.get("lexical_score") or 0.0)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (60 + rank) + lexical_score * 0.002
            evidence.setdefault(chunk_id, {}).update(
                {"lexical_rank": rank, "lexical_score": lexical_score}
            )

        semantic_ids: list[str] = []
        for rank, item in enumerate(semantic, start=1):
            chunk_id = str(item.get("chunk_id") or "")
            if not chunk_id:
                continue
            semantic_ids.append(chunk_id)
            semantic_score = float(item.get("score") or 0.0)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (60 + rank) + semantic_score * 0.002
            evidence.setdefault(chunk_id, {}).update(
                {"semantic_rank": rank, "semantic_score": semantic_score}
            )
        missing_ids = [value for value in semantic_ids if value not in catalog]
        catalog.update(self.repository.chunks_by_ids(missing_ids))

        ordered = sorted(scores, key=lambda value: (-scores[value], value))[:bounded]
        drama_cache: dict[str, dict[str, Any]] = {}
        results: list[dict[str, Any]] = []
        for chunk_id in ordered:
            item = dict(catalog.get(chunk_id) or {})
            if not item:
                continue
            current_drama_id = str(item.get("drama_id") or "")
            if current_drama_id not in drama_cache:
                try:
                    drama_cache[current_drama_id] = self.repository.get_drama(current_drama_id)
                except LookupError:
                    drama_cache[current_drama_id] = {}
            drama = drama_cache[current_drama_id]
            signals = evidence.get(chunk_id, {})
            reasons = []
            if signals.get("lexical_rank"):
                reasons.append("关键词或原文命中")
            if signals.get("semantic_rank"):
                reasons.append("语义结构相似")
            item.update(
                {
                    "drama_title": drama.get("title") or current_drama_id,
                    "score": round(scores[chunk_id], 8),
                    "signals": signals,
                    "retrieval_channels": [
                        channel
                        for channel, key in (("lexical", "lexical_rank"), ("semantic", "semantic_rank"))
                        if signals.get(key)
                    ],
                    "match_reasons": reasons,
                    "citation": {
                        "drama_id": current_drama_id,
                        "title": drama.get("title"),
                        "raw_path": drama.get("raw_path"),
                        "normalized_path": drama.get("normalized_path"),
                        "source_ref": item.get("source_ref"),
                        "source_locator": item.get("source_locator") or {},
                        "start_offset": item.get("start_offset"),
                        "end_offset": item.get("end_offset"),
                    },
                }
            )
            results.append(item)

        semantic_state = self.semantic.status()
        warnings: list[dict[str, str]] = []
        if semantic_error:
            warnings.append(
                {
                    "code": "semantic_search_failed",
                    "message": semantic_error,
                }
            )
        elif semantic_state.get("state") != "ready":
            warnings.append(
                {
                    "code": "semantic_unavailable",
                    "message": str(
                        semantic_state.get("reason")
                        or semantic_state.get("last_error")
                        or "Drama semantic retrieval is unavailable; lexical results remain active"
                    ),
                }
            )
        return {
            "query": clean,
            "workspace": self.workspace,
            "revision": self.repository.revision,
            "filters": {"drama_id": drama_id, "chunk_type": chunk_type},
            "count": len(results),
            "semantic_state": semantic_state,
            "semantic_error": semantic_error,
            "warnings": warnings,
            "results": results,
        }

    def close(self) -> None:
        self.semantic.close()

    @staticmethod
    def _resolve_paths(settings: Any, memory_gateway: Any | None) -> _DramaPaths:
        workspace = getattr(memory_gateway, "workspace", None)
        if workspace is None:
            try:
                workspace = WorkspaceResolver.resolve(settings)
            except Exception:
                workspace = None
        if workspace is not None:
            name = getattr(getattr(workspace, "name", None), "value", None) or str(
                getattr(workspace, "name", "production")
            )
            raw_root = Path(workspace.raw_path).resolve(strict=False) / "drama"
            derived_root = Path(workspace.derived_path).resolve(strict=False) / "drama"
            index_root = Path(workspace.storage_path).resolve(strict=False) / "index"
            return _DramaPaths(
                workspace=name,
                root=derived_root,
                raw_root=raw_root,
                normalized_root=derived_root / "normalized",
                knowledge_root=derived_root / "knowledge",
                index_root=index_root,
            )

        name = str(getattr(settings, "workspace_name", "production") or "production")
        storage = Path(settings.storage_path).expanduser().resolve(strict=False)
        base = storage.parent if storage.name.lower() == "storage" else storage
        raw_setting = getattr(settings, f"{name}_raw_dir", None)
        raw_root = (
            Path(raw_setting).expanduser().resolve(strict=False)
            if raw_setting
            else base / "raw"
        ) / "drama"
        derived_root = base / "derived" / "drama"
        return _DramaPaths(
            workspace=name,
            root=derived_root,
            raw_root=raw_root,
            normalized_root=derived_root / "normalized",
            knowledge_root=derived_root / "knowledge",
            index_root=storage / "index",
        )
