from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app
from src.control.service import LocalControlService
from src.gateway.bootstrap import build_memory_gateway
from src.runtime import WorkspaceResolver


def now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def check_ollama(base_url: str, model: str, timeout: float) -> dict[str, Any]:
    result: dict[str, Any] = {
        "base_url": base_url,
        "model": model,
        "reachable": False,
        "installed": False,
        "models": [],
        "error": None,
    }
    try:
        response = requests.get(base_url.rstrip("/") + "/api/tags", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        names = [str(item.get("name") or "") for item in payload.get("models") or []]
        result["reachable"] = True
        result["models"] = names
        result["installed"] = any(
            name == model or name.split(":", 1)[0] == model.split(":", 1)[0]
            for name in names
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:500]
    return result


def write_memory(
    vault_root: Path,
    path: Path,
    memory_id: str,
    title: str,
    body: str,
) -> dict[str, Any]:
    import hashlib

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
        "tags: [acceptance/vector]\n"
        "agent_scope: [all]\n"
        "---\n"
        f"{body}\n"
    )
    path.write_text(text, encoding="utf-8")
    return {
        "id": memory_id,
        "relative_path": path.relative_to(vault_root).as_posix(),
        "title": title,
        "memory_type": "knowledge",
        "memory_tier": "archival",
        "status": "active",
        "review_status": "approved",
        "privacy": "private",
        "project": ["lingji"],
        "tags": ["acceptance/vector"],
        "agent_scope": ["all"],
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def run_acceptance(model: str, ollama_url: str, timeout: float) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "started_at": now_text(),
        "model": model,
        "ollama": check_ollama(ollama_url, model, timeout),
        "checks": [],
        "status": "failed",
    }
    if not report["ollama"]["reachable"]:
        report["checks"].append(
            {
                "name": "ollama_reachable",
                "passed": False,
                "detail": report["ollama"]["error"],
            }
        )
        report["finished_at"] = now_text()
        return report
    if not report["ollama"]["installed"]:
        report["checks"].append(
            {
                "name": "embedding_model_installed",
                "passed": False,
                "detail": f"Run: ollama pull {model}",
            }
        )
        report["finished_at"] = now_text()
        return report

    with tempfile.TemporaryDirectory(prefix="lingji-p1-05-") as temporary:
        root = Path(temporary)
        settings = Settings(
            _env_file=None,
            vault_dir=str(root / "legacy-vault"),
            storage_dir=str(root / "legacy-storage"),
            log_dir=str(root / "legacy-logs"),
            backup_dir=str(root / "legacy-backups"),
            workspace_root=str(root / "workspaces"),
            workspace_name="acceptance",
            acceptance_qdrant_mode="memory",
            acceptance_qdrant_collection="lingji_memory_p1_05_acceptance",
            semantic_enabled=True,
            embedding_enabled=True,
            embedding_provider="ollama",
            embed_model=model,
            fallback_embed_model=model,
            ollama_base_url=ollama_url,
            embedding_timeout_seconds=timeout,
            qdrant_timeout_seconds=timeout,
            vault_auto_init=False,
            index_private=False,
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
                workspace.vault_path / "03-Knowledge" / "vector-cn.md",
                "MEM-P1-05-CN",
                "中文语义检索",
                "# 中文语义\n\n灵机需要准确理解中文项目记忆与第二大脑检索。",
            ),
            write_memory(
                workspace.vault_path,
                workspace.vault_path / "03-Knowledge" / "vector-en.md",
                "MEM-P1-05-EN",
                "English semantic retrieval",
                "# English semantic\n\nLingJi should retrieve multilingual project memory reliably.",
            ),
        ]

        gateway = None
        control = None
        try:
            gateway = build_memory_gateway(
                settings,
                rebuild_if_empty=False,
                workspace=workspace,
            )
            rebuild = gateway.rebuild(entries, workspace.vault_path, force=True)
            memory_status = gateway.memory_status()
            vector_status = gateway.vector_status()
            coverage = gateway.vector_coverage()
            search = gateway.search_memory(
                "lingji-local",
                "中文项目记忆",
                limit=5,
            )

            control = LocalControlService(settings, memory_gateway=gateway)
            with TestClient(create_control_app(settings, service=control, token="acceptance")) as client:
                headers = {"X-LingJi-Token": "acceptance"}
                api_memory = client.get("/api/memory/status", headers=headers)
                api_vector = client.get("/api/vector/status", headers=headers)
                api_coverage = client.get("/api/vector/coverage", headers=headers)
                api_brain = client.get("/api/brain/status", headers=headers)

            checks = [
                (
                    "semantic_provider_active",
                    gateway.retriever.semantic_provider is not None,
                    vector_status,
                ),
                (
                    "embedding_verified",
                    bool(vector_status.get("embedding", {}).get("available")),
                    vector_status.get("embedding"),
                ),
                (
                    "vector_dimension_detected",
                    int(vector_status.get("dimension") or 0) > 0,
                    vector_status.get("dimension"),
                ),
                (
                    "coordinated_rebuild_not_degraded",
                    not bool(rebuild.get("degraded")),
                    rebuild,
                ),
                (
                    "vector_coverage_complete",
                    coverage.get("coverage") == 1.0 and coverage.get("missing") == 0,
                    coverage,
                ),
                (
                    "multilingual_search_returns_results",
                    bool(search.get("results")),
                    search,
                ),
                (
                    "control_memory_status_200",
                    api_memory.status_code == 200,
                    api_memory.json(),
                ),
                (
                    "control_vector_status_200",
                    api_vector.status_code == 200,
                    api_vector.json(),
                ),
                (
                    "control_vector_coverage_200",
                    api_coverage.status_code == 200,
                    api_coverage.json(),
                ),
                (
                    "brain_status_not_fake_zero",
                    api_brain.status_code == 200
                    and api_brain.json().get("memory_count") == memory_status.get("documents")
                    and api_brain.json().get("vector_count") == vector_status.get("vectors"),
                    api_brain.json(),
                ),
                (
                    "acceptance_workspace_isolated",
                    workspace.name.value == "acceptance"
                    and "acceptance" in workspace.qdrant_collection,
                    workspace.to_dict(),
                ),
            ]
            for name, passed, detail in checks:
                report["checks"].append(
                    {"name": name, "passed": bool(passed), "detail": detail}
                )
            report["runtime"] = {
                "memory": memory_status,
                "vector": vector_status,
                "coverage": coverage,
                "rebuild": rebuild,
                "search_result_count": len(search.get("results") or []),
            }
        except Exception as exc:
            report["checks"].append(
                {
                    "name": "acceptance_runtime",
                    "passed": False,
                    "detail": f"{type(exc).__name__}: {exc}"[:1000],
                }
            )
        finally:
            if control is not None:
                control.close()
            if gateway is not None:
                gateway.close()

    report["status"] = (
        "passed" if report["checks"] and all(item["passed"] for item in report["checks"]) else "failed"
    )
    report["finished_at"] = now_text()
    return report


def run_pytest() -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_memory_statistics.py",
        "tests/test_status_snapshot_wiring.py",
        "tests/test_control_api.py",
        "tests/test_embedding_provider.py",
        "tests/test_qdrant_semantic_provider.py",
        "tests/test_memory_index_coordinator.py",
        "tests/test_semantic_runtime_wiring.py",
        "-v",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-20000:],
        "stderr": completed.stderr[-10000:],
    }


def write_report(report: dict[str, Any], output_directory: Path) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = output_directory / f"P1_05_LOCAL_ACCEPTANCE_{stamp}.json"
    markdown_path = output_directory / f"P1_05_LOCAL_ACCEPTANCE_{stamp}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# P1-05 Local Acceptance",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Model: `{report.get('model')}`",
        f"- Started: `{report.get('started_at')}`",
        f"- Finished: `{report.get('finished_at')}`",
        "",
        "## Checks",
        "",
    ]
    for item in report.get("checks") or []:
        mark = "PASS" if item.get("passed") else "FAIL"
        lines.append(f"- [{mark}] {item.get('name')}")
    lines.extend(
        [
            "",
            "## Raw JSON",
            "",
            f"See `{json_path.name}`.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated LingJi P1-05 local acceptance")
    parser.add_argument("--model", default="bge-m3")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--run-pytest", action="store_true")
    parser.add_argument(
        "--output",
        default="storage/reports/p1-05-local-acceptance",
    )
    args = parser.parse_args()

    report = run_acceptance(args.model, args.ollama_url, args.timeout)
    if args.run_pytest:
        report["pytest"] = run_pytest()
        if report["pytest"]["returncode"] != 0:
            report["status"] = "failed"
    json_path, markdown_path = write_report(report, Path(args.output))
    print(
        json.dumps(
            {
                "status": report["status"],
                "json": str(json_path),
                "markdown": str(markdown_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
