from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .index_coordinator import MemoryIndexCoordinator
from .memory_db import MemoryDatabase
from .semantic import SemanticProvider

_COLLECTION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,254}$")


class VectorCollectionMigrationError(RuntimeError):
    """Raised when a candidate collection cannot be proven safe to activate."""


@dataclass(frozen=True)
class VectorCollectionMigrationPlan:
    workspace: str
    source_collection: str
    target_collection: str
    source_model: str
    source_fallback_model: str
    target_model: str
    expected_chunks: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VectorCollectionMigrationResult:
    status: str
    plan: VectorCollectionMigrationPlan
    upserted: int
    coverage: dict[str, Any]
    vector_status: dict[str, Any]
    embedding_status: dict[str, Any]
    activation_settings: dict[str, str]
    rollback_settings: dict[str, str]
    manifest_path: str | None

    @property
    def validated(self) -> bool:
        return self.status == "validated"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "validated": self.validated,
            "plan": self.plan.to_dict(),
            "upserted": self.upserted,
            "coverage": dict(self.coverage),
            "vector_status": dict(self.vector_status),
            "embedding_status": dict(self.embedding_status),
            "activation_settings": dict(self.activation_settings),
            "rollback_settings": dict(self.rollback_settings),
            "manifest_path": self.manifest_path,
        }


class VectorCollectionMigrationService:
    """Build and validate a replacement semantic collection without activating it.

    The service reads canonical chunks from ``lingji_memory.db`` through
    ``MemoryIndexCoordinator``. It never mutates the source collection, never
    edits runtime settings and never deletes either collection.
    """

    def __init__(
        self,
        database: MemoryDatabase,
        *,
        workspace_name: str,
        source_collection: str,
        source_model: str,
        source_fallback_model: str | None = None,
        state_db: Any | None = None,
        batch_size: int = 64,
        manifest_dir: Path | str | None = None,
    ):
        selected_batch_size = int(batch_size)
        if selected_batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
        selected_workspace = str(workspace_name or "").strip()
        if not selected_workspace:
            raise ValueError("workspace_name must not be empty")
        self.database = database
        self.workspace_name = selected_workspace
        self.source_collection = self._validate_collection(source_collection, "source_collection")
        self.source_model = self._validate_model(source_model, "source_model")
        self.source_fallback_model = self._validate_model(
            source_fallback_model or source_model,
            "source_fallback_model",
        )
        self.state_db = state_db
        self.batch_size = selected_batch_size
        self.manifest_dir = Path(manifest_dir) if manifest_dir is not None else None
        self._catalog = MemoryIndexCoordinator(database)

    def plan(self, *, target_collection: str, target_model: str) -> VectorCollectionMigrationPlan:
        collection = self._validate_collection(target_collection, "target_collection")
        model = self._validate_model(target_model, "target_model")
        if collection == self.source_collection:
            raise VectorCollectionMigrationError(
                "target_collection must differ from the active source collection"
            )
        expected_chunks = len(self._catalog.semantic_chunk_ids())
        if expected_chunks <= 0:
            raise VectorCollectionMigrationError(
                "Cannot validate a replacement collection because the canonical memory index has no chunks"
            )
        return VectorCollectionMigrationPlan(
            workspace=self.workspace_name,
            source_collection=self.source_collection,
            target_collection=collection,
            source_model=self.source_model,
            source_fallback_model=self.source_fallback_model,
            target_model=model,
            expected_chunks=expected_chunks,
            created_at=self._now(),
        )

    def build_candidate(
        self,
        target_provider: SemanticProvider,
        *,
        target_model: str,
        manifest_path: Path | str | None = None,
    ) -> VectorCollectionMigrationResult:
        target_collection = str(getattr(target_provider, "collection", "") or "").strip()
        provider_workspace = getattr(getattr(target_provider, "workspace", None), "name", None)
        provider_workspace_name = getattr(provider_workspace, "value", provider_workspace)
        if provider_workspace_name and str(provider_workspace_name) != self.workspace_name:
            raise VectorCollectionMigrationError(
                f"Target provider workspace {provider_workspace_name!r} does not match migration workspace {self.workspace_name!r}"
            )
        plan = self.plan(
            target_collection=target_collection,
            target_model=target_model,
        )
        points = self._catalog.semantic_points()
        expected_ids = [point.chunk_id for point in points]
        upserted = 0

        try:
            for start in range(0, len(points), self.batch_size):
                batch = points[start : start + self.batch_size]
                indexed_ids = target_provider.upsert_many(batch)
                if len(indexed_ids) != len(batch):
                    raise VectorCollectionMigrationError(
                        f"Target provider indexed {len(indexed_ids)} of {len(batch)} points"
                    )
                upserted += len(batch)

            coverage = dict(target_provider.coverage(expected_ids))
            vector_status = dict(target_provider.status())
            embedding_provider = getattr(target_provider, "embedding_provider", None)
            embedding_status = (
                dict(embedding_provider.status())
                if embedding_provider is not None and callable(getattr(embedding_provider, "status", None))
                else {}
            )
            self._validate_candidate(
                plan,
                upserted=upserted,
                coverage=coverage,
                vector_status=vector_status,
                embedding_status=embedding_status,
            )
            result = self._result(
                plan,
                status="validated",
                upserted=upserted,
                coverage=coverage,
                vector_status=vector_status,
                embedding_status=embedding_status,
                manifest_path=None,
            )
            written_path = self._write_manifest(result.to_dict(), manifest_path)
            result = replace(
                result,
                manifest_path=str(written_path) if written_path else None,
            )
            self._record_event("vector_collection_candidate_validated", result.to_dict())
            return result
        except Exception as exc:
            failed_payload = {
                "status": "failed",
                "validated": False,
                "plan": plan.to_dict(),
                "upserted": upserted,
                "error": self._safe_error(exc),
                "activation_settings": {},
                "rollback_settings": self._rollback_settings(plan),
            }
            written_path = self._write_manifest(failed_payload, manifest_path)
            failed_payload["manifest_path"] = str(written_path) if written_path else None
            self._record_event("vector_collection_candidate_failed", failed_payload)
            if isinstance(exc, VectorCollectionMigrationError):
                raise
            raise VectorCollectionMigrationError(self._safe_error(exc)) from exc

    def _validate_candidate(
        self,
        plan: VectorCollectionMigrationPlan,
        *,
        upserted: int,
        coverage: dict[str, Any],
        vector_status: dict[str, Any],
        embedding_status: dict[str, Any],
    ) -> None:
        expected = plan.expected_chunks
        indexed = int(coverage.get("indexed") or 0)
        missing = int(coverage.get("missing") or 0)
        coverage_value = coverage.get("coverage")
        vectors = vector_status.get("vectors")
        dimension = vector_status.get("dimension")
        active_model = str(embedding_status.get("active_model") or "").strip()

        failures: list[str] = []
        if upserted != expected:
            failures.append(f"upserted={upserted}, expected={expected}")
        if indexed != expected or missing != 0 or coverage_value != 1.0:
            failures.append(
                f"coverage indexed={indexed}, missing={missing}, coverage={coverage_value!r}"
            )
        if not vector_status.get("collection_exists"):
            failures.append("target collection does not exist")
        if not vector_status.get("ready"):
            failures.append("target collection is not ready")
        if vector_status.get("rebuild_required"):
            failures.append("target provider still reports rebuild_required")
        if vectors is None or int(vectors) != expected:
            failures.append(f"target vectors={vectors!r}, expected exactly {expected}")
        if dimension is None or int(dimension) <= 0:
            failures.append(f"invalid target dimension: {dimension!r}")
        if not embedding_status.get("available"):
            failures.append("target embedding provider is not verified available")
        if not self._same_model(active_model, plan.target_model):
            failures.append(
                f"active embedding model {active_model!r} does not match target {plan.target_model!r}"
            )
        provider_collection = str(vector_status.get("collection") or "")
        if provider_collection and provider_collection != plan.target_collection:
            failures.append(
                f"provider status collection {provider_collection!r} does not match target"
            )
        status_workspace = str(vector_status.get("workspace") or "")
        if status_workspace and status_workspace != plan.workspace:
            failures.append(
                f"provider status workspace {status_workspace!r} does not match {plan.workspace!r}"
            )
        if failures:
            raise VectorCollectionMigrationError("; ".join(failures))

    def _result(
        self,
        plan: VectorCollectionMigrationPlan,
        *,
        status: str,
        upserted: int,
        coverage: dict[str, Any],
        vector_status: dict[str, Any],
        embedding_status: dict[str, Any],
        manifest_path: str | None,
    ) -> VectorCollectionMigrationResult:
        return VectorCollectionMigrationResult(
            status=status,
            plan=plan,
            upserted=upserted,
            coverage=coverage,
            vector_status=vector_status,
            embedding_status=embedding_status,
            activation_settings={
                "embed_model": plan.target_model,
                "fallback_embed_model": plan.target_model,
                "production_qdrant_collection": plan.target_collection,
            },
            rollback_settings=self._rollback_settings(plan),
            manifest_path=manifest_path,
        )

    @staticmethod
    def _rollback_settings(plan: VectorCollectionMigrationPlan) -> dict[str, str]:
        return {
            "embed_model": plan.source_model,
            "fallback_embed_model": plan.source_fallback_model,
            "production_qdrant_collection": plan.source_collection,
        }

    def _write_manifest(
        self,
        payload: dict[str, Any],
        explicit_path: Path | str | None,
    ) -> Path | None:
        path = Path(explicit_path) if explicit_path is not None else self._default_manifest_path(payload)
        if path is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
        return path

    def _default_manifest_path(self, payload: dict[str, Any]) -> Path | None:
        if self.manifest_dir is None:
            return None
        target = str((payload.get("plan") or {}).get("target_collection") or "candidate")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return self.manifest_dir / f"VECTOR_COLLECTION_MIGRATION_{target}_{stamp}.json"

    def _record_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.state_db is None:
            return
        try:
            self.state_db.append_event(
                event_type,
                "vector_collection_migration",
                str((payload.get("plan") or {}).get("target_collection") or "candidate"),
                payload,
            )
        except Exception:
            return

    @staticmethod
    def _validate_collection(value: Any, field: str) -> str:
        normalized = str(value or "").strip()
        if not _COLLECTION_PATTERN.fullmatch(normalized):
            raise ValueError(
                f"{field} must be 3-255 characters using letters, numbers, dot, underscore or hyphen"
            )
        return normalized

    @staticmethod
    def _validate_model(value: Any, field: str) -> str:
        normalized = str(value or "").strip()
        if not normalized or len(normalized) > 255:
            raise ValueError(f"{field} must be a non-empty model name")
        return normalized

    @staticmethod
    def _same_model(left: str, right: str) -> bool:
        left_value = str(left or "").strip().lower()
        right_value = str(right or "").strip().lower()
        return bool(left_value and right_value) and (
            left_value == right_value
            or left_value.split(":", 1)[0] == right_value.split(":", 1)[0]
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        return f"{type(exc).__name__}: {exc}"[:1000]
