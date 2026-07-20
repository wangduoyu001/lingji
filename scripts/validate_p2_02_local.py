from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.config import Settings
from src.model_center import build_embedding_provider
from src.retrieval import (
    MemoryDatabase,
    MemoryIndexCoordinator,
    QdrantSemanticProvider,
    VectorCollectionMigrationService,
)
from src.runtime import WorkspaceResolver


def write_memory(
    vault: Path,
    relative_path: str,
    memory_id: str,
    title: str,
    body: str,
) -> dict[str, Any]:
    path = vault / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        "---\n"
        f"id: {memory_id}\n"
        f"title: {title}\n"
        "memory_type: knowledge\n"
        "memory_tier: archival\n"
        "status: active\n"
        "review_status: approved\n"
        "privacy: private\n"
        "project: [lingji]\n"
        "tags: [acceptance/vector-migration]\n"
        "agent_scope: [all]\n"
        "---\n"
        f"{body}\n"
    )
    path.write_text(text, encoding="utf-8")
    return {
        "id": memory_id,
        "relative_path": relative_path,
        "title": title,
        "memory_type": "knowledge",
        "memory_tier": "archival",
        "status": "active",
        "review_status": "approved",
        "privacy": "private",
        "project": ["lingji"],
        "tags": ["acceptance/vector-migration"],
        "agent_scope": ["all"],
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def run(model: str, ollama_url: str, timeout: float) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="lingji-p2-02-") as temporary:
        root = Path(temporary)
        settings = Settings(
            _env_file=None,
            workspace_root=str(root / "workspaces"),
            workspace_name="acceptance",
            acceptance_qdrant_mode="memory",
            acceptance_qdrant_collection="lingji_memory_acceptance_source",
            vault_auto_init=False,
            semantic_enabled=True,
            embedding_enabled=True,
            embedding_provider="ollama",
            embed_model=model,
            fallback_embed_model=model,
            ollama_base_url=ollama_url,
            embedding_timeout_seconds=timeout,
            qdrant_timeout_seconds=timeout,
            startup_min_free_gb=0,
        )
        workspace = WorkspaceResolver.resolve(
            settings,
            "acceptance",
            environ={},
            project_root=root,
        )
        workspace.vault_path.mkdir(parents=True, exist_ok=True)
        workspace.storage_path.mkdir(parents=True, exist_ok=True)

        entries = [
            write_memory(
                workspace.vault_path,
                "03-Knowledge/migration-cn.md",
                "MEM-P2-02-CN",
                "中文迁移验证",
                "# 中文迁移验证\n\n灵机需要安全构建新的向量集合。",
            ),
            write_memory(
                workspace.vault_path,
                "03-Knowledge/migration-en.md",
                "MEM-P2-02-EN",
                "English migration validation",
                "# Migration validation\n\nLingJi builds a replacement vector collection safely.",
            ),
        ]
        database = MemoryDatabase(workspace.memory_db_path)
        MemoryIndexCoordinator(database).sync(
            entries,
            workspace.vault_path,
            force=True,
        )

        embedding = build_embedding_provider(
            settings,
            {
                "embedding_enabled": True,
                "embedding_provider": "ollama",
                "embedding_primary_model": model,
                "embedding_fallback_model": model,
                "embedding_timeout_seconds": timeout,
            },
        )
        if embedding is None:
            raise RuntimeError("Embedding provider is disabled")

        target_workspace = replace(
            workspace,
            qdrant_collection="lingji_memory_acceptance_bge_m3_candidate",
        )
        provider = QdrantSemanticProvider(
            target_workspace,
            embedding,
            timeout_seconds=timeout,
        )
        manifest_dir = workspace.reports_path / "vector-migrations"
        service = VectorCollectionMigrationService(
            database,
            workspace_name="acceptance",
            source_collection=workspace.qdrant_collection,
            source_model="nomic-embed-text",
            source_fallback_model="nomic-embed-text",
            batch_size=1,
            manifest_dir=manifest_dir,
        )

        try:
            result = service.build_candidate(provider, target_model=model)
            payload = result.to_dict()
            payload["checks"] = {
                "validated": result.validated,
                "coverage_complete": result.coverage.get("coverage") == 1.0,
                "no_missing": result.coverage.get("missing") == 0,
                "exact_vectors": result.vector_status.get("vectors")
                == result.plan.expected_chunks,
                "dimension_detected": int(result.vector_status.get("dimension") or 0) > 0,
                "active_model": result.embedding_status.get("active_model"),
                "manifest_exists": bool(
                    result.manifest_path and Path(result.manifest_path).is_file()
                ),
                "source_unchanged": result.plan.source_collection
                == "lingji_memory_acceptance_source",
            }
            if not all(
                value
                for key, value in payload["checks"].items()
                if key != "active_model"
            ):
                raise RuntimeError(f"P2-02 acceptance failed: {payload['checks']}")
            return payload
        finally:
            provider.close()
            close = getattr(embedding, "close", None)
            if callable(close):
                close()


def main() -> int:
    command = argparse.ArgumentParser(
        description="Run isolated real bge-m3/Qdrant validation for P2-02"
    )
    command.add_argument("--model", default="bge-m3")
    command.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    command.add_argument("--timeout", type=float, default=120.0)
    args = command.parse_args()

    try:
        result = run(args.model, args.ollama_url, args.timeout)
        print(json.dumps({"status": "passed", **result}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}"[:1000],
                    "production_data_modified": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
