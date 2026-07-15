from __future__ import annotations

import logging
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models


logger = logging.getLogger("second_brain.vector_store")


class VectorStore:
    def __init__(self, collection: str, path: Path | None = None, url: str = ""):
        self.collection = collection
        self.path = Path(path) if path else None
        self.url = url
        self._client: QdrantClient | None = None

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            if self.url:
                self._client = QdrantClient(url=self.url, timeout=10)
            else:
                if self.path is None:
                    raise RuntimeError("Qdrant path is required in embedded mode")
                if str(self.path) == ":memory:":
                    self._client = QdrantClient(location=":memory:")
                else:
                    self.path.mkdir(parents=True, exist_ok=True)
                    self._client = QdrantClient(path=str(self.path))
        return self._client

    def ensure_collection(self, dimension: int) -> None:
        if self.client.collection_exists(self.collection):
            info = self.client.get_collection(self.collection)
            configured = info.config.params.vectors
            existing_size = configured.size if hasattr(configured, "size") else None
            if existing_size and existing_size != dimension:
                raise RuntimeError(
                    f"Qdrant dimension changed from {existing_size} to {dimension}; run /memory/rebuild-qdrant"
                )
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
        )

    def upsert(self, item_id: str, vector: list[float], payload: dict) -> None:
        self.ensure_collection(len(vector))
        self.client.upsert(
            collection_name=self.collection,
            points=[models.PointStruct(id=item_id, vector=vector, payload=payload)],
            wait=True,
        )

    def delete(self, item_id: str) -> None:
        if not self.client.collection_exists(self.collection):
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.PointIdsList(points=[item_id]),
            wait=True,
        )

    def delete_document(self, document_id: str) -> None:
        if not self.client.collection_exists(self.collection):
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
                )
            ),
            wait=True,
        )

    def search(self, vector: list[float], limit: int = 10) -> list[dict]:
        if not self.client.collection_exists(self.collection):
            return []
        result = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        return [
            {"id": str(point.id), "score": float(point.score), "payload": point.payload or {}}
            for point in result.points
        ]

    def recreate(self, items: list[tuple[str, list[float], dict]]) -> int:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        if not items:
            return 0
        self.ensure_collection(len(items[0][1]))
        self.client.upsert(
            collection_name=self.collection,
            points=[models.PointStruct(id=item_id, vector=vector, payload=payload) for item_id, vector, payload in items],
            wait=True,
        )
        return len(items)

    def status(self) -> dict:
        mode = "remote" if self.url else "embedded"
        try:
            if not self.client.collection_exists(self.collection):
                return {"mode": mode, "collection": self.collection, "vectors": 0, "ready": True}
            info = self.client.get_collection(self.collection)
            return {
                "mode": mode,
                "collection": self.collection,
                "vectors": info.points_count or 0,
                "ready": True,
            }
        except Exception as exc:
            return {"mode": mode, "collection": self.collection, "ready": False, "error": str(exc)}

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
