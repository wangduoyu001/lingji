"""Full-auto vector backfill: embed memory-layer messages into the local
Qdrant collection (embedded mode, storage/qdrant).

全自动向量化：无需任何人工点击。每次 run_once 以 message_id 为幂等键，
已存在的向量跳过；单轮有界，多轮调用直到追平。数据全部留在本机。
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Any, Protocol

COLLECTION = "lingji_automatic_memory"

# 本地（embedded）模式同一存储目录只允许一个 QdrantClient。进程内共享单例，
# 避免调度器回填线程与 API 线程各自开关客户端时撞 "already accessed" 文件锁。
_CLIENT_LOCK = threading.Lock()
# 进程级：已确认嵌入坍缩、不可修复的消息点，跳过后续向量化尝试。
_RECALL_POINT_GIVE_UP: set[str] = set()
_SHARED_CLIENT: Any = None
_SHARED_PATH: str = ""


def _vector_is_degenerate(vector: Any) -> bool:
    """零范数（全零/失败占位）向量在余弦检索里会冒充满分命中，视为退化。"""
    if not vector:
        return True
    try:
        return sum(float(x) * float(x) for x in vector) < 1e-12
    except (TypeError, ValueError):
        return True


def _shared_client(path: Path) -> Any:
    global _SHARED_CLIENT, _SHARED_PATH
    from qdrant_client import QdrantClient

    with _CLIENT_LOCK:
        if _SHARED_CLIENT is None or _SHARED_PATH != str(path):
            if _SHARED_CLIENT is not None:
                try:
                    _SHARED_CLIENT.close()
                except Exception:
                    pass
                _SHARED_CLIENT = None
            _SHARED_CLIENT = QdrantClient(path=str(path))
            _SHARED_PATH = str(path)
        return _SHARED_CLIENT


def close_shared_client() -> None:
    """测试或进程退出时释放共享客户端。"""
    global _SHARED_CLIENT, _SHARED_PATH
    with _CLIENT_LOCK:
        if _SHARED_CLIENT is not None:
            try:
                _SHARED_CLIENT.close()
            except Exception:
                pass
        _SHARED_CLIENT = None
        _SHARED_PATH = ""


class EmbeddingProviderLike(Protocol):
    def embed_many(self, texts: list[str]) -> list[list[float]]: ...

    def status(self) -> dict[str, Any]: ...


def _point_id(message_id: str) -> int:
    digest = hashlib.md5(message_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**63)


class VectorBackfill:
    """把记忆层消息向量化进本地 Qdrant（幂等、有界、全自动）。"""

    def __init__(self, settings: Any, *, provider: EmbeddingProviderLike, collection: str = COLLECTION):
        self.settings = settings
        self.provider = provider
        self.collection = collection
        self._lock = threading.Lock()

    def _qdrant_path(self) -> Path:
        return Path(str(self.settings.storage_path)).expanduser() / "qdrant"

    def _client(self):
        path = self._qdrant_path()
        path.mkdir(parents=True, exist_ok=True)
        return _shared_client(path)

    def _pending_message_rows(self, limit: int) -> list[dict[str, Any]]:
        """优先返回尚未向量化的消息（按时间正序），不受窗口截断影响。"""
        memory_db = Path(str(getattr(self.settings, "memory_db_path", "")))
        if not memory_db.exists():
            return []
        with sqlite3.connect(str(memory_db)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT m.message_id, m.conversation_id, m.role, m.content, m.occurred_at, m.content_hash
                FROM message_records m
                WHERE NOT EXISTS (
                    SELECT 1 FROM (
                        SELECT payload->>'message_id' AS mid
                        FROM (
                            SELECT json_extract(payload_json, '$.message_id') AS payload
                            FROM (
                                SELECT 1 AS payload_json, 1 AS message_id
                            )
                        )
                    ) x WHERE x.mid = m.message_id
                )
                ORDER BY m.occurred_at ASC, m.message_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        # 上面的 NOT EXISTS 无法跨 qdrant —— 改为读 qdrant 已有 id 后在内存里过滤
        return [dict(row) for row in rows]

    def _all_message_rows(self) -> list[dict[str, Any]]:
        """读取全部消息行（有界内存：只取 id/内容必要列）。"""
        memory_db = Path(str(getattr(self.settings, "memory_db_path", "")))
        if not memory_db.exists():
            return []
        with sqlite3.connect(str(memory_db)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT message_id, conversation_id, role, content, occurred_at, content_hash
                FROM message_records
                ORDER BY occurred_at ASC, message_id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def run_once(self, limit: int = 500) -> dict[str, Any]:
        with self._lock:
            return self._run_once_locked(limit)

    def _run_once_locked(self, limit: int) -> dict[str, Any]:
        from qdrant_client.models import PointIdsList, PointStruct, VectorParams

        client = self._client()
        try:
            rows = self._all_message_rows()
            if not rows:
                return {"embedded": 0, "skipped": 0, "total_vectors": self._count(client), "status": "empty"}

            existing_ids: set[str] = set()
            # 退化向量治理（WorkBuddy 2026-09-16 复检 P0-2）：零范数向量、以及不同内容
            # 嵌出同一向量的重复簇，会在召回里冒充实命中（无关查询回填 1.0 分）。
            # 重嵌无法修复提供方级坍缩：这些点直接出索引（词法层仍在），并记入
            # 进程级放弃名单，避免每轮“嵌入→删除”空转。
            remove_ids: list[str] = []
            repair_ids: set[str] = set()
            try:
                try:
                    collection_missing = not client.collection_exists(collection_name=self.collection)
                except ValueError:
                    collection_missing = True  # qdrant local 对缺失集合直接抛错
                if collection_missing:
                    points: list = []
                else:
                    # 翻页扫全量：单页 10000 截断会让尾部点永远进不了 existing_ids，
                    # 它们的消息每轮被当“未向量化”反复重嵌（2026-09-16 实测 200/轮空转）。
                    points = []
                    scroll_offset = None
                    while True:
                        page, next_offset = client.scroll(
                            collection_name=self.collection, limit=10000,
                            offset=scroll_offset, with_payload=True, with_vectors=True,
                        )
                        points.extend(page)
                        if not page or next_offset is None:
                            break
                        scroll_offset = next_offset
                signatures: dict[tuple[float, ...], list[str]] = {}
                for point in points:
                    mid = (point.payload or {}).get("message_id")
                    if not mid:
                        continue
                    # 旧版本向量 payload 缺 content 但向量健康：重嵌入补写 payload。
                    if not str((point.payload or {}).get("content", "") or ""):
                        repair_ids.add(str(mid))
                        continue
                    vector = list(getattr(point, "vector", None) or [])
                    if _vector_is_degenerate(vector):
                        remove_ids.append(str(mid))
                        continue
                    existing_ids.add(str(mid))
                    signatures.setdefault(tuple(round(float(x), 6) for x in vector), []).append(str(mid))
                for members in signatures.values():
                    # 不同内容嵌出同一向量 = 嵌入坍缩；内容相同的合法重复行不折腾。
                    distinct_contents = {str((point.payload or {}).get("content", "") or "") for point in points if str((point.payload or {}).get("message_id") or "") in set(members)}
                    if len(members) > 1 and len(distinct_contents) > 1:
                        remove_ids.extend(members)
            except Exception:
                # 扫描存量点失败（并发/锁竞争）时绝不能当作“全都没有向量化”
                # 盲目重嵌——那会把最老的一批每轮反复重写。中止本轮，稍后重试。
                return {"embedded": 0, "skipped": 0, "total_vectors": self._count(client), "status": "scan_unavailable"}
            if remove_ids:
                for mid in remove_ids:
                    existing_ids.discard(mid)
                    _RECALL_POINT_GIVE_UP.add(str(mid))
                try:
                    client.delete(collection_name=self.collection, points_selector=PointIdsList(points=list({_point_id(mid) for mid in remove_ids[:10000]})))
                except Exception:
                    pass

            # 空内容不参与向量化：既无语义可嵌，也会因 payload 恒为空而每轮重嵌。
            pending = [row for row in rows if str(row["message_id"]) not in existing_ids and str(row["message_id"]) not in _RECALL_POINT_GIVE_UP and str(row["content"] or '').strip()][:limit]
            embedded = 0
            # 整批嵌入一次调用，避免逐条 HTTP 往返；单条失败仍逐个兜底。
            vectors_by_id: dict[str, list[float]] = {}
            if pending:
                try:
                    batch_vectors = self.provider.embed_many([str(row["content"] or "") for row in pending])
                    for row, vector in zip(pending, batch_vectors):
                        if vector:
                            vectors_by_id[str(row["message_id"])] = vector
                except Exception:
                    vectors_by_id = {}
            for row in pending:
                try:
                    vector = vectors_by_id.get(str(row["message_id"]))
                    if not vector:
                        vectors = self.provider.embed_many([str(row["content"] or "")])
                        vector = vectors[0] if vectors else None
                    dim = len(vector) if vector else 0
                    if not dim or _vector_is_degenerate(vector):
                        continue  # 退化向量拒绝落库：宁缺毋滥，不留 1.0 分假命中源
                    try:
                        client.create_collection(
                            collection_name=self.collection,
                            vectors_config=VectorParams(size=dim, distance="Cosine"),
                        )
                    except Exception:
                        pass  # 集合已存在
                    client.upsert(
                        collection_name=self.collection,
                        points=[PointStruct(
                            id=_point_id(row["message_id"]),
                            vector=vector,
                            payload={
                                "message_id": row["message_id"],
                                "role": row["role"],
                                "conversation_id": row["conversation_id"],
                                "occurred_at": row["occurred_at"],
                                "content": str(row["content"] or "")[:800],
                            },
                        )],
                    )
                    embedded += 1
                except Exception:
                    continue
            return {
                "embedded": embedded,
                "skipped": len(rows) - len(pending),
                "total_vectors": self._count(client),
                "status": "ok",
            }
        finally:
            pass  # 共享客户端保持打开，供调度器/API 复用

    def _count(self, client) -> int:
        try:
            result = client.count(collection_name=self.collection, exact=True)
            return int(result.count)
        except Exception:
            return 0

    @classmethod
    def vector_count(cls, settings: Any) -> int | None:
        try:
            path = Path(str(settings.storage_path)).expanduser() / "qdrant"
            if not path.exists():
                return None
            client = _shared_client(path)
            try:
                return int(client.count(collection_name=COLLECTION, exact=True).count)
            except Exception:
                return 0
        except Exception:
            return None


    def search(self, query_embedding: list[float], limit: int = 10) -> list[dict[str, Any]]:
        """按意思搜索：返回最相近的对话/消息。"""
        path = self._qdrant_path()
        if not path.exists():
            return []
        client = _shared_client(path)
        try:
            # qdrant-client >= 1.10 移除了 search()；统一走 query_points。
            result = client.query_points(collection_name=self.collection, query=query_embedding, limit=limit)
            return [
                {
                    "score": round(hit.score, 3),
                    "content": (hit.payload or {}).get("content", ""),
                    "role": (hit.payload or {}).get("role", ""),
                    "message_id": (hit.payload or {}).get("message_id", ""),
                    "conversation_id": (hit.payload or {}).get("conversation_id", ""),
                    "occurred_at": (hit.payload or {}).get("occurred_at", ""),
                }
                for hit in result.points
            ]
        except Exception:
            return []


__all__ = ["COLLECTION", "VectorBackfill"]
