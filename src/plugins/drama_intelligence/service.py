from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

from src.retrieval import QdrantSemanticProvider, SemanticPoint

from .importer import SUPPORTED_EXTENSIONS, load_script
from .models import DramaChunk
from .parser import parse_script
from .repository import DramaRepository


class DramaSemanticIndex:
    """Reuses LingJi embedding/Qdrant runtime with a separate Drama collection."""

    def __init__(self, provider: QdrantSemanticProvider | None, *, reason: str | None = None):
        self.provider = provider
        self.reason = reason

    @classmethod
    def from_memory_gateway(cls, memory_gateway: Any | None) -> "DramaSemanticIndex":
        if memory_gateway is None:
            return cls(None, reason="memory_gateway_unavailable")
        base = getattr(getattr(memory_gateway, "retriever", None), "semantic_provider", None)
        workspace = getattr(memory_gateway, "workspace", None)
        if base is None or workspace is None:
            return cls(None, reason="semantic_runtime_unavailable")
        try:
            workspace_name = getattr(getattr(workspace, "name", None), "value", None) or "production"
            drama_workspace = replace(
                workspace,
                qdrant_collection=f"lingji_drama_{workspace_name}",
            )
            provider = QdrantSemanticProvider(
                drama_workspace,
                base.embedding_provider,
                client=base.client,
                distance=base.distance,
                timeout_seconds=base.timeout_seconds,
                collection_schema="drama-v1",
            )
            return cls(provider)
        except Exception as exc:
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
                    "episode_number": item.episode_number,
                    "scene_number": item.scene_number,
                    "source_ref": item.source_ref,
                    "characters": list(item.characters),
                    "tags": list(item.tags),
                },
            )
            for item in selected
        ]
        self.provider.upsert_many(points)
        return {"state": "ready", "indexed": len(points), "collection": self.provider.collection}

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


class DramaService:
    """Application service for the isolated Drama Memory domain."""

    def __init__(self, settings: Any, *, memory_gateway: Any | None = None):
        self.settings = settings
        self.root = Path(settings.storage_path).expanduser().resolve(strict=False) / "drama"
        self.raw_root = self.root / "raw"
        self.normalized_root = self.root / "normalized"
        self.knowledge_root = self.root / "knowledge"
        self.index_root = self.root / "index"
        for path in (self.raw_root, self.normalized_root, self.knowledge_root, self.index_root):
            path.mkdir(parents=True, exist_ok=True)
        self.repository = DramaRepository(self.index_root / "drama_read_model.db")
        self.semantic = DramaSemanticIndex.from_memory_gateway(memory_gateway)

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
        raw_directory = self.raw_root / parsed.drama_id
        normalized_directory = self.normalized_root / parsed.drama_id
        raw_directory.mkdir(parents=True, exist_ok=True)
        normalized_directory.mkdir(parents=True, exist_ok=True)
        raw_path = raw_directory / f"original{source.source_path.suffix.lower()}"
        normalized_path = normalized_directory / "full_text.md"
        shutil.copy2(source.source_path, raw_path)
        normalized_path.write_text(source.text, encoding="utf-8")
        (normalized_directory / "source_map.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "drama_id": parsed.drama_id,
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
        (self.knowledge_root / f"{parsed.drama_id}.json").write_text(
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
            "root": str(self.root),
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
        lexical = self.repository.search_lexical(
            clean,
            limit=max(bounded * 4, 20),
            drama_id=drama_id,
            chunk_type=chunk_type,
        )
        semantic_error = None
        try:
            semantic = self.semantic.search(
                clean,
                limit=max(bounded * 4, 20),
                drama_id=drama_id,
                chunk_type=chunk_type,
            )
        except Exception as exc:
            semantic = []
            semantic_error = f"{type(exc).__name__}: {exc}"[:500]

        catalog = self._chunk_catalog(drama_id)
        scores: dict[str, float] = {}
        evidence: dict[str, dict[str, Any]] = {}
        for rank, item in enumerate(lexical, start=1):
            chunk_id = str(item["chunk_id"])
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (60 + rank)
            evidence.setdefault(chunk_id, {})["lexical_rank"] = rank
            catalog.setdefault(chunk_id, item)
        for rank, item in enumerate(semantic, start=1):
            chunk_id = str(item.get("chunk_id") or "")
            if not chunk_id:
                continue
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (60 + rank)
            evidence.setdefault(chunk_id, {}).update(
                {"semantic_rank": rank, "semantic_score": item.get("score")}
            )

        ordered = sorted(scores, key=lambda value: (-scores[value], value))[:bounded]
        results: list[dict[str, Any]] = []
        for chunk_id in ordered:
            item = dict(catalog.get(chunk_id) or {})
            if not item:
                continue
            signals = evidence.get(chunk_id, {})
            reasons = []
            if signals.get("lexical_rank"):
                reasons.append("关键词或原文命中")
            if signals.get("semantic_rank"):
                reasons.append("语义结构相似")
            item.update(
                {
                    "score": round(scores[chunk_id], 8),
                    "signals": signals,
                    "match_reasons": reasons,
                }
            )
            results.append(item)
        return {
            "query": clean,
            "filters": {"drama_id": drama_id, "chunk_type": chunk_type},
            "count": len(results),
            "semantic_state": self.semantic.status(),
            "semantic_error": semantic_error,
            "results": results,
        }

    def _chunk_catalog(self, drama_id: str | None) -> dict[str, dict[str, Any]]:
        drama_ids = [drama_id] if drama_id else [
            str(item["drama_id"])
            for item in self.repository.list_dramas(limit=500, offset=0)["items"]
        ]
        output: dict[str, dict[str, Any]] = {}
        for current in drama_ids:
            if not current:
                continue
            try:
                drama = self.repository.get_drama(current)
            except LookupError:
                continue
            title = str(drama.get("title") or current)
            for chunk in self.repository.chunks(current):
                chunk["drama_title"] = title
                output[str(chunk["chunk_id"])] = chunk
        return output
