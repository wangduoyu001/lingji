from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STATUS_SCHEMA_VERSION = 2
_DEFAULT_STALE_SECONDS = 300.0
_MAX_MISSING_IDS = 100


class MemoryStatisticsService:
    """Build or read one truthful memory/vector status snapshot.

    A process that owns the MemoryGateway publishes live data. Other processes,
    especially the Local Control API, read the persisted snapshot instead of
    opening the same embedded Qdrant path a second time.
    """

    def __init__(
        self,
        gateway: Any | None = None,
        *,
        snapshot_path: Path | str | None = None,
        stale_after_seconds: float = _DEFAULT_STALE_SECONDS,
    ):
        self.gateway = gateway
        self.snapshot_path = Path(snapshot_path) if snapshot_path is not None else None
        self.stale_after_seconds = max(float(stale_after_seconds), 1.0)

    @staticmethod
    def snapshot_path_for(settings: Any, workspace: Any | None = None) -> Path:
        storage_path = (
            Path(workspace.storage_path)
            if workspace is not None and getattr(workspace, "storage_path", None) is not None
            else Path(settings.storage_path)
        )
        return storage_path / "memory_status.json"

    def snapshot(self, *, publish: bool = False) -> dict[str, Any]:
        if self.gateway is not None:
            payload = self._live_snapshot()
            if publish:
                self._write_snapshot(payload)
            return payload
        return self._read_snapshot()

    def publish(self) -> dict[str, Any]:
        if self.gateway is None:
            raise RuntimeError("A live MemoryGateway is required to publish statistics")
        return self.snapshot(publish=True)

    def memory_status(self) -> dict[str, Any]:
        payload = self.snapshot()
        return {
            "as_of": payload.get("as_of"),
            "source": payload.get("source"),
            "producer": dict(payload.get("producer") or {}),
            "stale": payload.get("stale", False),
            "workspace": payload.get("workspace"),
            **dict(payload.get("memory") or {}),
        }

    def vector_status(self) -> dict[str, Any]:
        payload = self.snapshot()
        return {
            "as_of": payload.get("as_of"),
            "source": payload.get("source"),
            "producer": dict(payload.get("producer") or {}),
            "stale": payload.get("stale", False),
            "workspace": payload.get("workspace"),
            "embedding": dict(payload.get("embedding") or {}),
            **dict(payload.get("vector") or {}),
        }

    def vector_coverage(self) -> dict[str, Any]:
        payload = self.snapshot()
        return {
            "as_of": payload.get("as_of"),
            "source": payload.get("source"),
            "producer": dict(payload.get("producer") or {}),
            "stale": payload.get("stale", False),
            "workspace": payload.get("workspace"),
            **dict(payload.get("coverage") or {}),
        }

    def _live_snapshot(self) -> dict[str, Any]:
        gateway = self.gateway
        database = gateway.database
        warnings = [dict(item) for item in getattr(gateway, "runtime_warnings", [])]
        workspace = getattr(gateway, "workspace", None)
        workspace_name = getattr(getattr(workspace, "name", None), "value", None)

        try:
            database_stats = dict(database.stats())
            integrity = dict(database.integrity_check())
            memory_state = "healthy" if integrity.get("healthy") else "degraded"
            database_path = Path(database_stats.get("path") or database.path)
            database_bytes = database_path.stat().st_size if database_path.is_file() else 0
            memory = {
                "state": memory_state,
                "documents": int(database_stats.get("documents") or 0),
                "chunks": int(database_stats.get("chunks") or 0),
                "core_memories": int(database_stats.get("core_memories") or 0),
                "revision": int(database_stats.get("revision") or 0),
                "database_bytes": int(database_bytes),
                "database_path": str(database_path),
                "fts_tokenizer": database_stats.get("fts_tokenizer"),
                "last_rebuild_at": database_stats.get("last_rebuild_at"),
                "integrity": integrity,
            }
        except Exception as exc:
            memory = {
                "state": "unavailable",
                "documents": None,
                "chunks": None,
                "core_memories": None,
                "revision": None,
                "database_bytes": None,
                "database_path": str(getattr(database, "path", "")),
                "integrity": {"healthy": False, "error": self._safe_error(exc)},
            }
            warnings.append(
                {
                    "code": "memory_statistics_failed",
                    "stage": "memory",
                    "message": self._safe_error(exc),
                }
            )

        semantic = getattr(getattr(gateway, "retriever", None), "semantic_provider", None)
        if semantic is None:
            degraded = any(
                item.get("code")
                in {
                    "semantic_runtime_initialization_failed",
                    "workspace_runtime_resolution_failed",
                }
                for item in warnings
            )
            vector_state = "degraded" if degraded else "disabled"
            embedding = {
                "state": vector_state,
                "available": False,
                "active_model": None,
                "dimension": None,
            }
            vector = self._normalize_vector_truth(
                {
                    "state": vector_state,
                    "ready": False,
                    "collection_exists": False,
                    "vectors": None,
                    "dimension": None,
                    "collection": getattr(workspace, "qdrant_collection", None),
                    "mode": getattr(workspace, "qdrant_mode", None),
                    "rebuild_required": False,
                    "last_error": warnings[-1].get("message") if degraded and warnings else None,
                },
                self._coverage_unavailable(
                    expected=memory.get("chunks"),
                    state=vector_state,
                ),
                embedding,
                preferred_state=vector_state,
            )
            coverage = self._coverage_unavailable(
                expected=memory.get("chunks"),
                state=vector_state,
            )
        else:
            embedding = self._embedding_status(semantic)
            raw_vector = self._vector_status(semantic)
            coverage = self._coverage_status(database, semantic, memory.get("chunks"))
            vector = self._normalize_vector_truth(raw_vector, coverage, embedding)

        states = [memory.get("state"), vector.get("state")]
        overall_state = "healthy"
        if any(state in {"unavailable", "degraded", "empty", "configuration_required"} for state in states):
            overall_state = "degraded"

        return {
            "schema_version": _STATUS_SCHEMA_VERSION,
            "as_of": self._now(),
            "source": "live",
            "producer": self._producer(),
            "stale": False,
            "state": overall_state,
            "workspace": workspace_name,
            "memory": memory,
            "embedding": embedding,
            "vector": vector,
            "coverage": coverage,
            "warnings": warnings,
        }

    def _embedding_status(self, semantic: Any) -> dict[str, Any]:
        provider = getattr(semantic, "embedding_provider", None)
        if provider is None:
            return {
                "state": "configuration_required",
                "available": False,
                "active_model": None,
                "dimension": None,
            }
        try:
            status = dict(provider.status())
            available = bool(status.get("available"))
            status["state"] = "healthy" if available else "unavailable"
            return status
        except Exception as exc:
            return {
                "state": "unavailable",
                "available": False,
                "active_model": None,
                "dimension": None,
                "last_error": self._safe_error(exc),
            }

    def _vector_status(self, semantic: Any) -> dict[str, Any]:
        try:
            status = dict(semantic.status())
            status.setdefault("collection", getattr(semantic, "collection", None))
            status.setdefault(
                "mode",
                getattr(getattr(semantic, "workspace", None), "qdrant_mode", None),
            )
            return status
        except Exception as exc:
            return {
                "ready": False,
                "collection_exists": False,
                "vectors": None,
                "dimension": None,
                "collection": getattr(semantic, "collection", None),
                "mode": getattr(
                    getattr(semantic, "workspace", None), "qdrant_mode", None
                ),
                "rebuild_required": False,
                "last_error": self._safe_error(exc),
            }

    def _coverage_status(
        self,
        database: Any,
        semantic: Any,
        expected_count: Any,
    ) -> dict[str, Any]:
        try:
            expected_ids = self._chunk_ids(database)
            result = dict(semantic.coverage(expected_ids))
            missing_ids = list(result.get("missing_chunk_ids") or [])
            result["missing_chunk_ids"] = missing_ids[:_MAX_MISSING_IDS]
            result["missing_chunk_ids_truncated"] = len(missing_ids) > _MAX_MISSING_IDS
            result["state"] = (
                "healthy" if int(result.get("missing") or 0) == 0 else "degraded"
            )
            return result
        except Exception as exc:
            result = self._coverage_unavailable(
                expected=expected_count, state="unavailable"
            )
            result["last_error"] = self._safe_error(exc)
            return result

    @staticmethod
    def _chunk_ids(database: Any) -> list[str]:
        with database._connection() as connection:
            rows = connection.execute(
                "SELECT chunk_id FROM memory_chunks ORDER BY chunk_id"
            ).fetchall()
        return [str(row["chunk_id"]) for row in rows]

    @staticmethod
    def _coverage_unavailable(expected: Any, state: str) -> dict[str, Any]:
        value = int(expected) if expected is not None else None
        return {
            "state": state,
            "expected": value,
            "indexed": None,
            "missing": None,
            "coverage": None,
            "missing_chunk_ids": [],
            "missing_chunk_ids_truncated": False,
        }

    @classmethod
    def _normalize_vector_truth(
        cls,
        raw: dict[str, Any],
        coverage: dict[str, Any],
        embedding: dict[str, Any],
        *,
        preferred_state: str | None = None,
    ) -> dict[str, Any]:
        vector = dict(raw)
        ready = bool(vector.get("ready"))
        collection_exists = bool(vector.get("collection_exists"))
        vectors_raw = vector.get("vectors")
        vectors = int(vectors_raw) if vectors_raw is not None else None
        rebuild_required = bool(vector.get("rebuild_required"))
        embedding_available = bool(embedding.get("available"))
        last_error = str(vector.get("last_error") or "")
        normalized_error = last_error.casefold()
        locked = any(
            token in normalized_error
            for token in (
                "already accessed by another instance",
                "already locked",
                "directory locked",
                "resource temporarily unavailable",
                "another lingji memory runtime owns",
            )
        )

        semantic_search_available = bool(
            ready
            and collection_exists
            and vectors is not None
            and vectors > 0
            and embedding_available
            and not rebuild_required
            and not locked
        )
        lexical_search_available = True

        if preferred_state in {"disabled", "degraded"}:
            state = preferred_state
            reason_code = (
                "semantic_runtime_initialization_failed"
                if preferred_state == "degraded"
                else "semantic_disabled"
            )
        elif locked:
            state = "unavailable"
            reason_code = "embedded_store_locked"
        elif rebuild_required:
            state = "degraded"
            reason_code = "vector_rebuild_required"
        elif not ready:
            state = "unavailable"
            reason_code = "vector_service_unavailable"
        elif not collection_exists or vectors in {None, 0}:
            state = "empty"
            reason_code = "collection_empty"
        elif not embedding_available:
            state = "degraded"
            reason_code = "embedding_unavailable"
        elif coverage.get("state") == "degraded":
            state = "degraded"
            reason_code = "vector_coverage_incomplete"
        elif coverage.get("state") == "unavailable":
            state = "unavailable"
            reason_code = "vector_coverage_unknown"
        else:
            state = "healthy"
            reason_code = "ready"

        if semantic_search_available:
            impact = "全文检索和语义检索均可用。"
            recovery_state = "not_required"
            recovery_action = ""
        elif reason_code == "collection_empty":
            impact = "全文检索可用；当前没有可供语义检索的向量。"
            recovery_state = "waiting_for_indexable_content"
            recovery_action = "导入并处理获授权资料后自动建立向量；无需手工寻找 Qdrant 目录。"
        elif reason_code == "embedded_store_locked":
            impact = "全文检索仍可用；语义检索暂不可用。"
            recovery_state = "waiting_for_single_owner"
            recovery_action = "灵机会等待旧内存进程退出并由唯一 MCP Runtime 重新接管。"
        elif reason_code == "vector_rebuild_required":
            impact = "全文检索仍可用；语义结果可能不完整。"
            recovery_state = "owner_authorization_required"
            recovery_action = "确认模型和维度后，从向量中心授权重建当前工作空间索引。"
        else:
            impact = "全文检索仍可用；语义检索当前不可用。"
            recovery_state = "diagnosis_required"
            recovery_action = "查看当前原因；灵机会自动刷新状态，但不会删除或重建生产索引。"

        vector.update(
            {
                "state": state,
                "service_ready": ready,
                "search_available": semantic_search_available,
                "semantic_search_available": semantic_search_available,
                "lexical_search_available": lexical_search_available,
                "reason_code": reason_code,
                "impact": impact,
                "recovery": {
                    "state": recovery_state,
                    "automatic_refresh": True,
                    "action": recovery_action,
                },
            }
        )
        return vector

    def _write_snapshot(self, payload: dict[str, Any]) -> None:
        if self.snapshot_path is None:
            return
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.snapshot_path.with_suffix(self.snapshot_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.snapshot_path)

    def _read_snapshot(self) -> dict[str, Any]:
        if self.snapshot_path is None or not self.snapshot_path.is_file():
            return self._unavailable_snapshot(
                "Memory runtime status snapshot is not available"
            )
        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError("status snapshot root must be an object")
            age_seconds = self._age_seconds(payload.get("as_of"))
            payload = dict(payload)
            payload["source"] = "snapshot"
            payload["producer"] = dict(payload.get("producer") or {})
            payload["stale"] = (
                age_seconds is None or age_seconds > self.stale_after_seconds
            )
            payload["age_seconds"] = age_seconds
            raw_vector = dict(payload.get("vector") or {})
            coverage = dict(payload.get("coverage") or {})
            embedding = dict(payload.get("embedding") or {})
            if "search_available" not in raw_vector:
                payload["vector"] = self._normalize_vector_truth(
                    raw_vector, coverage, embedding
                )
            if payload["stale"]:
                payload["state"] = "degraded"
                vector = dict(payload.get("vector") or {})
                vector["stale"] = True
                vector["search_available"] = False
                vector["semantic_search_available"] = False
                vector["reason_code"] = "status_snapshot_stale"
                vector["impact"] = "全文检索可用；语义检索状态过期，暂不宣称可用。"
                vector["recovery"] = {
                    "state": "waiting_for_mcp_publisher",
                    "automatic_refresh": True,
                    "action": "灵机正在等待唯一 MCP Runtime 发布新快照。",
                }
                payload["vector"] = vector
            return payload
        except Exception as exc:
            return self._unavailable_snapshot(
                f"Memory runtime status snapshot is invalid: {self._safe_error(exc)}"
            )

    def _unavailable_snapshot(self, message: str) -> dict[str, Any]:
        embedding = {
            "state": "configuration_required",
            "available": False,
            "active_model": None,
            "dimension": None,
        }
        coverage = self._coverage_unavailable(None, "configuration_required")
        vector = self._normalize_vector_truth(
            {
                "state": "configuration_required",
                "ready": False,
                "collection_exists": False,
                "vectors": None,
                "dimension": None,
                "collection": None,
                "mode": None,
                "rebuild_required": False,
                "last_error": message,
            },
            coverage,
            embedding,
        )
        vector["state"] = "configuration_required"
        vector["reason_code"] = "memory_status_snapshot_unavailable"
        return {
            "schema_version": _STATUS_SCHEMA_VERSION,
            "as_of": None,
            "source": "unavailable",
            "producer": {},
            "stale": True,
            "state": "configuration_required",
            "workspace": None,
            "memory": {
                "state": "configuration_required",
                "documents": None,
                "chunks": None,
                "core_memories": None,
                "revision": None,
                "database_bytes": None,
                "database_path": None,
            },
            "embedding": embedding,
            "vector": vector,
            "coverage": coverage,
            "warnings": [
                {
                    "code": "memory_status_snapshot_unavailable",
                    "stage": "status_reader",
                    "message": message,
                }
            ],
        }

    @staticmethod
    def _producer() -> dict[str, Any]:
        return {
            "service": str(
                os.environ.get("LINGJI_MEMORY_STATUS_PRODUCER") or "memory_gateway"
            ),
            "instance_id": str(
                os.environ.get("LINGJI_MEMORY_STATUS_INSTANCE_ID") or ""
            ),
            "pid": os.getpid(),
        }

    @staticmethod
    def _age_seconds(value: Any) -> float | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(
                (datetime.now(timezone.utc) - parsed).total_seconds(), 0.0
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _now() -> str:
        return (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        return f"{type(exc).__name__}: {exc}"[:500]
