from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any, Sequence

from src.model_center.embedding import EmbeddingProvider
from src.runtime.workspace import WorkspaceContext

from .semantic import SemanticPoint

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:  # pragma: no cover - exercised through status() without dependency
    QdrantClient = None  # type: ignore[assignment]
    models = None  # type: ignore[assignment]


_POINT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "lingji:qdrant-point")
_DISTANCE_NAMES = {"cosine", "dot", "euclid", "manhattan"}


class QdrantUnavailableError(RuntimeError):
    """Raised when Qdrant cannot be constructed or contacted."""


class VectorDimensionMismatchError(RuntimeError):
    """Raised when the active embedding dimension differs from the collection."""


class QdrantSemanticProvider:
    """Workspace-isolated Qdrant adapter for semantic candidates and diagnostics."""

    def __init__(
        self,
        workspace: WorkspaceContext,
        embedding_provider: EmbeddingProvider,
        *,
        client: Any | None = None,
        distance: str = "cosine",
        timeout_seconds: float = 10.0,
        collection_schema: str = "v1",
    ):
        workspace.validate()
        normalized_distance = str(distance or "cosine").strip().lower()
        if normalized_distance not in _DISTANCE_NAMES:
            raise ValueError(
                f"Unsupported Qdrant distance: {distance!r}. "
                f"Expected one of: {', '.join(sorted(_DISTANCE_NAMES))}"
            )
        timeout = float(timeout_seconds)
        if timeout <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        schema = str(collection_schema or "").strip()
        if not schema:
            raise ValueError("collection_schema must not be empty")

        self.workspace = workspace
        self.embedding_provider = embedding_provider
        self.collection = workspace.qdrant_collection
        self.distance = normalized_distance
        self.timeout_seconds = timeout
        self.collection_schema = schema
        self._client = client
        self._owns_client = client is None
        self._lock = threading.RLock()
        self._rebuild_required = False
        self._last_error: str | None = None

    @property
    def client(self) -> Any:
        with self._lock:
            if self._client is not None:
                return self._client
            if QdrantClient is None:
                raise QdrantUnavailableError(
                    "qdrant-client is not installed; install the main requirements before enabling semantic retrieval"
                )
            mode = self.workspace.qdrant_mode.strip().lower()
            try:
                if mode == "remote":
                    self._client = QdrantClient(
                        url=str(self.workspace.qdrant_url),
                        timeout=self.timeout_seconds,
                    )
                elif mode == "memory":
                    self._client = QdrantClient(location=":memory:")
                else:
                    path = self.workspace.qdrant_path
                    if path is None:
                        raise QdrantUnavailableError(
                            f"Embedded Qdrant path is missing for workspace {self.workspace.name.value}"
                        )
                    Path(path).mkdir(parents=True, exist_ok=True)
                    self._client = QdrantClient(path=str(path))
            except Exception as exc:
                self._last_error = self._safe_error(exc)
                raise QdrantUnavailableError(self._last_error) from exc
            return self._client

    def point_id(self, chunk_id: str) -> str:
        normalized = str(chunk_id or "").strip()
        if not normalized:
            raise ValueError("chunk_id must not be empty")
        value = (
            f"{self.workspace.name.value}:"
            f"{self.collection_schema}:"
            f"{normalized}"
        )
        return str(uuid.uuid5(_POINT_NAMESPACE, value))

    def upsert(self, point: SemanticPoint) -> str:
        return self.upsert_many([point])[0]

    def upsert_many(self, points: Sequence[SemanticPoint]) -> list[str]:
        selected = list(points)
        if not selected:
            return []
        for point in selected:
            self._validate_point(point)

        texts = [point.text for point in selected]
        vectors = self.embedding_provider.embed_many(texts)
        if len(vectors) != len(selected):
            raise RuntimeError(
                f"Embedding provider returned {len(vectors)} vectors for {len(selected)} points"
            )
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) != 1 or not dimensions or 0 in dimensions:
            raise ValueError("Embedding provider returned empty or inconsistent vector dimensions")
        dimension = next(iter(dimensions))
        self._ensure_collection(dimension)

        point_ids = [self.point_id(point.chunk_id) for point in selected]
        embedding_status = self.embedding_provider.status()
        active_model = embedding_status.get("active_model")
        structs = []
        for point_id, point, vector in zip(point_ids, selected, vectors):
            payload = self._payload(point, active_model=active_model)
            structs.append(models.PointStruct(id=point_id, vector=vector, payload=payload))

        try:
            self.client.upsert(
                collection_name=self.collection,
                points=structs,
                wait=True,
            )
            self._last_error = None
            return point_ids
        except Exception as exc:
            self._last_error = self._safe_error(exc)
            raise QdrantUnavailableError(self._last_error) from exc

    def delete(self, chunk_id: str) -> None:
        if not self._collection_exists():
            return
        point_id = self.point_id(chunk_id)
        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=models.PointIdsList(points=[point_id]),
                wait=True,
            )
            self._last_error = None
        except KeyError:
            return
        except Exception as exc:
            self._last_error = self._safe_error(exc)
            raise QdrantUnavailableError(self._last_error) from exc

    def delete_memory(self, memory_id: str) -> None:
        normalized = str(memory_id or "").strip()
        if not normalized:
            raise ValueError("memory_id must not be empty")
        if not self._collection_exists():
            return
        try:
            self.client.delete(
                collection_name=self.collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="memory_id",
                                match=models.MatchValue(value=normalized),
                            )
                        ]
                    )
                ),
                wait=True,
            )
            self._last_error = None
        except Exception as exc:
            self._last_error = self._safe_error(exc)
            raise QdrantUnavailableError(self._last_error) from exc

    def search(
        self,
        query: str,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        clean_query = " ".join(str(query or "").split())
        if not clean_query:
            return []
        limit = max(int(limit), 1)
        if not self._collection_exists():
            return []

        vector = self.embedding_provider.embed(clean_query)
        self._check_collection_dimension(len(vector))
        query_filter = self._build_filter(filters or {})
        try:
            result = self.client.query_points(
                collection_name=self.collection,
                query=vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            self._last_error = None
        except Exception as exc:
            self._last_error = self._safe_error(exc)
            raise QdrantUnavailableError(self._last_error) from exc

        output = []
        for point in result.points:
            payload = dict(point.payload or {})
            chunk_id = str(payload.get("chunk_id") or "")
            memory_id = str(payload.get("memory_id") or "")
            if not chunk_id and not memory_id:
                continue
            output.append(
                {
                    "id": str(point.id),
                    "chunk_id": chunk_id,
                    "memory_id": memory_id,
                    "score": float(point.score),
                    "payload": payload,
                }
            )
        return output

    def count(self, kind: str | None = None) -> int:
        if not self._collection_exists():
            return 0
        count_filter = None
        if kind:
            count_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="kind",
                        match=models.MatchValue(value=str(kind)),
                    )
                ]
            )
        try:
            return int(
                self.client.count(
                    collection_name=self.collection,
                    count_filter=count_filter,
                    exact=True,
                ).count
            )
        except Exception as exc:
            self._last_error = self._safe_error(exc)
            raise QdrantUnavailableError(self._last_error) from exc

    def exists(self, chunk_id: str) -> bool:
        if not self._collection_exists():
            return False
        try:
            points = self.client.retrieve(
                collection_name=self.collection,
                ids=[self.point_id(chunk_id)],
                with_payload=False,
                with_vectors=False,
            )
            return bool(points)
        except Exception as exc:
            self._last_error = self._safe_error(exc)
            raise QdrantUnavailableError(self._last_error) from exc

    def coverage(self, expected_chunk_ids: Sequence[str]) -> dict[str, Any]:
        expected = list(dict.fromkeys(str(value).strip() for value in expected_chunk_ids if str(value).strip()))
        if not expected:
            return {
                "expected": 0,
                "indexed": 0,
                "missing": 0,
                "coverage": 1.0,
                "missing_chunk_ids": [],
            }
        if not self._collection_exists():
            return {
                "expected": len(expected),
                "indexed": 0,
                "missing": len(expected),
                "coverage": 0.0,
                "missing_chunk_ids": expected,
            }

        found: set[str] = set()
        for start in range(0, len(expected), 256):
            batch = expected[start : start + 256]
            ids = [self.point_id(chunk_id) for chunk_id in batch]
            try:
                points = self.client.retrieve(
                    collection_name=self.collection,
                    ids=ids,
                    with_payload=True,
                    with_vectors=False,
                )
            except Exception as exc:
                self._last_error = self._safe_error(exc)
                raise QdrantUnavailableError(self._last_error) from exc
            for point in points:
                payload = dict(point.payload or {})
                chunk_id = str(payload.get("chunk_id") or "")
                if chunk_id:
                    found.add(chunk_id)

        missing = [chunk_id for chunk_id in expected if chunk_id not in found]
        indexed = len(expected) - len(missing)
        return {
            "expected": len(expected),
            "indexed": indexed,
            "missing": len(missing),
            "coverage": round(indexed / len(expected), 6),
            "missing_chunk_ids": missing,
        }

    def status(self) -> dict[str, Any]:
        base = {
            "workspace": self.workspace.name.value,
            "mode": self.workspace.qdrant_mode,
            "collection": self.collection,
            "distance": self.distance,
            "rebuild_required": self._rebuild_required,
            "embedding": self.embedding_provider.status(),
        }
        try:
            if not self._collection_exists():
                return {
                    **base,
                    "ready": True,
                    "collection_exists": False,
                    "vectors": 0,
                    "dimension": None,
                    "last_error": self._last_error,
                }
            info = self.client.get_collection(self.collection)
            dimension = self._vector_size(info)
            return {
                **base,
                "ready": not self._rebuild_required,
                "collection_exists": True,
                "vectors": self.count(),
                "dimension": dimension,
                "last_error": self._last_error,
            }
        except Exception as exc:
            self._last_error = self._safe_error(exc)
            return {
                **base,
                "ready": False,
                "collection_exists": False,
                "vectors": None,
                "dimension": None,
                "last_error": self._last_error,
            }

    def close(self) -> None:
        with self._lock:
            if self._client is not None and self._owns_client:
                close = getattr(self._client, "close", None)
                if callable(close):
                    close()
            self._client = None

    def _ensure_collection(self, dimension: int) -> None:
        if self._collection_exists():
            self._check_collection_dimension(dimension)
            return
        try:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=self._distance_value(),
                ),
            )
            self._rebuild_required = False
            self._last_error = None
        except Exception as exc:
            self._last_error = self._safe_error(exc)
            raise QdrantUnavailableError(self._last_error) from exc

    def _check_collection_dimension(self, dimension: int) -> None:
        info = self.client.get_collection(self.collection)
        existing = self._vector_size(info)
        if existing is not None and int(existing) != int(dimension):
            self._rebuild_required = True
            error = (
                f"Qdrant dimension mismatch for {self.collection}: "
                f"collection={existing}, embedding={dimension}"
            )
            self._last_error = error
            raise VectorDimensionMismatchError(error)

    def _collection_exists(self) -> bool:
        try:
            return bool(self.client.collection_exists(self.collection))
        except Exception as exc:
            self._last_error = self._safe_error(exc)
            raise QdrantUnavailableError(self._last_error) from exc

    def _payload(self, point: SemanticPoint, *, active_model: Any) -> dict[str, Any]:
        payload = {
            key: value
            for key, value in dict(point.payload or {}).items()
            if key not in {"text", "content", "body", "vector"}
        }
        payload.update(
            {
                "kind": str(payload.get("kind") or "memory_chunk"),
                "memory_id": point.memory_id,
                "chunk_id": point.chunk_id,
                "embedding_model": active_model,
                "workspace": self.workspace.name.value,
                "collection_schema": self.collection_schema,
            }
        )
        return payload

    def _build_filter(self, filters: dict[str, Any]) -> Any | None:
        if models is None:
            return None
        must = []
        self._add_match_any(must, "status", filters.get("statuses"))
        self._add_match_any(must, "privacy", filters.get("privacy"))
        self._add_match_any(must, "memory_type", filters.get("memory_types"))

        project = str(filters.get("project") or "").strip()
        if project:
            must.append(
                models.FieldCondition(
                    key="project",
                    match=models.MatchValue(value=project),
                )
            )
        for tag in filters.get("tags") or []:
            must.append(
                models.FieldCondition(
                    key="tags",
                    match=models.MatchValue(value=str(tag)),
                )
            )
        return models.Filter(must=must) if must else None

    @staticmethod
    def _add_match_any(target: list[Any], key: str, values: Any) -> None:
        selected = [str(value) for value in (values or []) if str(value)]
        if not selected:
            return
        target.append(
            models.FieldCondition(
                key=key,
                match=models.MatchAny(any=selected),
            )
        )

    def _distance_value(self) -> Any:
        mapping = {
            "cosine": models.Distance.COSINE,
            "dot": models.Distance.DOT,
            "euclid": models.Distance.EUCLID,
            "manhattan": models.Distance.MANHATTAN,
        }
        return mapping[self.distance]

    @staticmethod
    def _vector_size(info: Any) -> int | None:
        configured = info.config.params.vectors
        if hasattr(configured, "size"):
            return int(configured.size)
        if isinstance(configured, dict):
            for value in configured.values():
                if hasattr(value, "size"):
                    return int(value.size)
        return None

    @staticmethod
    def _validate_point(point: SemanticPoint) -> None:
        if not str(point.chunk_id or "").strip():
            raise ValueError("SemanticPoint.chunk_id must not be empty")
        if not str(point.memory_id or "").strip():
            raise ValueError("SemanticPoint.memory_id must not be empty")
        if not str(point.text or "").strip():
            raise ValueError("SemanticPoint.text must not be empty")

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        return f"{type(exc).__name__}: {exc}"[:500]
