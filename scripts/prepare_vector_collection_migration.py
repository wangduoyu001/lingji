from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from src.config import settings
from src.gateway.bootstrap import build_memory_gateway
from src.model_center import build_embedding_provider
from src.retrieval import QdrantSemanticProvider
from src.retrieval.collection_migration import VectorCollectionMigrationService


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description=(
            "Build and validate a replacement Qdrant collection without switching "
            "the active LingJi production model or collection."
        )
    )
    command.add_argument("--model", required=True, help="Target Ollama embedding model")
    command.add_argument("--collection", required=True, help="New target Qdrant collection")
    command.add_argument(
        "--execute",
        action="store_true",
        help="Create and populate the target collection; default is plan-only",
    )
    command.add_argument(
        "--confirm-exclusive-qdrant",
        action="store_true",
        help=(
            "Confirm no other LingJi process owns the embedded Qdrant directory. "
            "Required for embedded mode execution."
        ),
    )
    command.add_argument(
        "--manifest-dir",
        default="",
        help="Optional manifest directory; defaults to the workspace reports directory",
    )
    command.add_argument("--batch-size", type=int, default=64)
    command.add_argument("--timeout", type=float, default=120.0)
    return command


def main() -> int:
    args = parser().parse_args()
    gateway = None
    embedding = None
    provider = None

    try:
        gateway = build_memory_gateway(
            settings,
            rebuild_if_empty=False,
            runtime_values={"semantic_enabled": False},
        )
        workspace = gateway.workspace
        if workspace is None:
            raise RuntimeError("Production WorkspaceContext is unavailable")
        if workspace.name.value != "production":
            raise RuntimeError(
                f"This migration command requires the production workspace, got {workspace.name.value!r}"
            )

        report_dir = (
            Path(args.manifest_dir).expanduser().resolve(strict=False)
            if args.manifest_dir
            else workspace.reports_path / "vector-migrations"
        )
        service = VectorCollectionMigrationService(
            gateway.database,
            workspace_name=workspace.name.value,
            source_collection=workspace.qdrant_collection,
            source_model=settings.embed_model,
            source_fallback_model=settings.fallback_embed_model,
            state_db=gateway.state_db,
            batch_size=args.batch_size,
            manifest_dir=report_dir,
        )
        plan = service.plan(
            target_collection=args.collection,
            target_model=args.model,
        )

        if not args.execute:
            print(
                json.dumps(
                    {
                        "status": "planned",
                        "executed": False,
                        "plan": plan.to_dict(),
                        "requirements": {
                            "stop_memory_gateway_processes": workspace.qdrant_mode == "embedded",
                            "confirm_exclusive_qdrant": workspace.qdrant_mode == "embedded",
                            "changes_active_settings": False,
                            "deletes_source_collection": False,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        if workspace.qdrant_mode == "embedded" and not args.confirm_exclusive_qdrant:
            raise RuntimeError(
                "Embedded Qdrant execution requires --confirm-exclusive-qdrant after stopping "
                "other LingJi MemoryGateway/MCP processes"
            )

        target_workspace = replace(workspace, qdrant_collection=plan.target_collection)
        embedding = build_embedding_provider(
            settings,
            {
                "embedding_enabled": True,
                "embedding_provider": "ollama",
                "embed_model": plan.target_model,
                "fallback_embed_model": plan.target_model,
                "embedding_timeout_seconds": args.timeout,
            },
        )
        if embedding is None:
            raise RuntimeError("Embedding provider is disabled")
        provider = QdrantSemanticProvider(
            target_workspace,
            embedding,
            distance=settings.qdrant_distance,
            timeout_seconds=args.timeout,
            collection_schema=settings.qdrant_collection_schema,
        )
        result = service.build_candidate(
            provider,
            target_model=plan.target_model,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.validated else 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}"[:1000],
                    "active_settings_changed": False,
                    "source_collection_deleted": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    finally:
        if provider is not None:
            provider.close()
        if embedding is not None:
            close = getattr(embedding, "close", None)
            if callable(close):
                close()
        if gateway is not None:
            gateway.close()


if __name__ == "__main__":
    raise SystemExit(main())
