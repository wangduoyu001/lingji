"""Bounded chunk-level vector backfill for the formal semantic collection.

WorkBuddy 2026-09-17 复检 R1-B/R5：正式语义通道读的集合从未被灌入 chunk 向量
（旧 nomic 数据已随 768 集合废弃），导致 MCP search_memory 语义通道恒空、
coverage 恒 0。本回填按 chunk_id 幂等补齐正式集合，不建第二份数据、
不重复消息层集合（lingji_automatic_memory 继续服务对话原文召回）。
"""

from __future__ import annotations

from typing import Any

from .semantic import SemanticPoint


class ChunkVectorBackfill:
    """按 memory_chunks 幂等补齐正式语义集合；词法索引不经过本路径。"""

    def __init__(
        self,
        database: Any,
        provider: Any,
        *,
        batch_size: int = 64,
    ):
        batch = int(batch_size)
        if batch <= 0:
            raise ValueError("batch_size must be greater than zero")
        self.database = database
        self.provider = provider
        self.batch_size = batch

    def run_once(self, limit: int = 200) -> dict[str, Any]:
        limit = max(int(limit), 1)
        # PERF_RESOURCE_ROOT_CAUSE_20260927 (B2): every drain wake-up used to
        # pay three O(collection) sweeps (row fetch, coverage probe, full id
        # scroll) even when nothing drifted. Equal counts mean no missing and
        # no orphan points in almost every case, so the sweeps are skipped; a
        # compensating missing+orphan pair is rare and surfaces on the next
        # count change.
        try:
            indexed_count = int(self.provider.count())
        except Exception:
            indexed_count = -1
        expected_count = int(self.database.semantic_chunk_count())
        if indexed_count >= 0 and expected_count > 0 and indexed_count == expected_count:
            return {
                "embedded": 0,
                "remaining": 0,
                "expected": expected_count,
                "status": "fast-path",
            }

        rows = self.database.semantic_chunk_rows()
        if not rows:
            return {"embedded": 0, "remaining": 0, "expected": 0, "status": "empty"}

        expected_ids = {row["chunk_id"] for row in rows}
        coverage = self.provider.coverage(list(expected_ids))
        missing = set(coverage.get("missing_chunk_ids") or [])
        # 集合里 chunk_id 不在当前权威集合中的孤儿点：重分块后旧 id 失效，
        # 留着会在语义召回里返回已被替换的内容（数据准确性）。
        orphans = sorted(self._collection_chunk_ids() - expected_ids)
        removed = 0
        if orphans:
            for orphan_id in orphans[:limit]:
                try:
                    self.provider.delete(orphan_id)
                    removed += 1
                except Exception:
                    break
        missing -= set(orphans)
        targets = [row for row in rows if row["chunk_id"] in missing][:limit]
        if not targets:
            return {
                "embedded": 0,
                "remaining": len(missing),
                "expected": len(rows),
                "status": "ok",
            }

        embedded = 0
        failed = 0
        for start in range(0, len(targets), self.batch_size):
            batch = targets[start : start + self.batch_size]
            points = [
                SemanticPoint(
                    chunk_id=str(row["chunk_id"]),
                    memory_id=str(row["memory_id"]),
                    text=self._chunk_text(row),
                    payload={
                        "title": str(row.get("title") or ""),
                        "heading": str(row.get("heading") or ""),
                        "start_line": row.get("start_line"),
                        "end_line": row.get("end_line"),
                        "memory_type": str(row.get("memory_type") or ""),
                        "memory_tier": str(row.get("memory_tier") or ""),
                        "status": str(row.get("status") or ""),
                        "privacy": str(row.get("privacy") or "private"),
                        "importance": str(row.get("importance") or ""),
                        "project": self._loads_json(row.get("project_json"), []),
                        "tags": self._loads_json(row.get("tags_json"), []),
                        "agent_scope": self._loads_json(row.get("agent_scope_json"), []),
                    },
                )
                for row in batch
            ]
            try:
                indexed = self.provider.upsert_many(points)
                embedded += len(indexed)
            except Exception:
                # 单批失败保留下轮重试：回填按 chunk_id 幂等，不会产生重复点。
                failed += len(batch)
                break

        remaining = max(len(missing) - embedded, 0)
        return {
            "embedded": embedded,
            "remaining": remaining,
            "failed": failed,
            "removed_orphans": removed,
            "expected": len(rows),
            "status": "ok" if not failed else "degraded",
        }

    def _collection_chunk_ids(self) -> set[str]:
        try:
            return self._collection_chunk_ids_inner()
        except Exception:
            return set()

    def _collection_chunk_ids_inner(self) -> set[str]:
        ids: set[str] = set()
        scroll_offset = None
        client = getattr(self.provider, "client", None)
        if client is None:
            return ids
        collection = getattr(self.provider, "collection", "")
        while True:
            page, next_offset = client.scroll(
                collection_name=collection, limit=1000,
                offset=scroll_offset, with_payload=True, with_vectors=False,
            )
            for point in page:
                chunk_id = str((point.payload or {}).get("chunk_id") or "")
                if chunk_id:
                    ids.add(chunk_id)
            if not page or next_offset is None:
                break
            scroll_offset = next_offset
        return ids

    @staticmethod
    def _chunk_text(row: dict[str, Any]) -> str:
        heading = str(row.get("heading") or "").strip()
        text = str(row.get("text") or "").strip()
        if not text:
            text = heading
        elif heading:
            text = f"{heading}\n{text}"
        return text

    @staticmethod
    def _loads_json(value: Any, fallback: Any) -> Any:
        import json

        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value) if value else fallback
            return parsed if isinstance(parsed, list) else fallback
        except (TypeError, ValueError):
            return fallback
