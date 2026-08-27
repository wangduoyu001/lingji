"""Acceptance-only end-to-end proof for the packaged automatic-memory composition.

The fixture talks to ``run_packaged_control_api`` over its authenticated loopback
HTTP boundary.  It intentionally does not construct a scheduler, watcher, queue,
or extraction sink in-process: the subprocess is the same composition used by a
packaged sidecar.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO_ROOT / "run_packaged_control_api.py"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _process_inventory(pid: int) -> list[str]:
    try:
        output = subprocess.check_output(
            ["ps", "-axo", "pid=,ppid=,command="], text=True, timeout=2
        )
    except (OSError, subprocess.SubprocessError):
        return []
    rows = []
    for line in output.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) >= 2 and (fields[0] == str(pid) or fields[1] == str(pid)):
            rows.append(line.strip())
    return rows


def _json_request(
    port: int,
    path: str,
    *,
    token: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 8.0,
) -> tuple[int, Any]:
    body = None
    headers = {"X-LingJi-Token": token}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return int(response.status), json.loads(raw.decode("utf-8")) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            value = raw.decode("utf-8", errors="replace")
        return int(exc.code), value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sentinel(root: Path) -> dict[str, dict[str, Any]]:
    """Record all observable file-tree attributes without following symlinks."""
    result: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        is_link = path.is_symlink()
        result[relative] = {
            "kind": "symlink" if is_link else "directory" if path.is_dir() else "file",
            "sha256": _sha256(path) if path.is_file() and not is_link else None,
            "size": int(metadata.st_size),
            "mtime_ns": int(metadata.st_mtime_ns),
            "mode": int(stat.S_IMODE(metadata.st_mode)),
            "target": os.readlink(path) if is_link else None,
        }
    return result


def _fixture_history(path: Path, *, conversation: str, message: str, count: int = 1) -> None:
    conversations = []
    for index in range(count):
        conversations.append(
            {
                "conversation_id": f"{conversation}-{index}",
                "title": f"Acceptance conversation {index}",
                "messages": [
                    {
                        "message_id": f"{conversation}-message-{index}",
                        "role": "user",
                        "content": message if index == 0 else f"{message} {index}",
                        "timestamp": "2026-08-28T00:00:00Z",
                    }
                ],
            }
        )
    path.write_text(
        json.dumps(
            {"schema": "lingji.history.inbox", "schema_version": "1", "conversations": conversations},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _vault_bootstrap_allowlist() -> set[str]:
    from src.memory.vault_layout import REQUIRED_FOLDERS, TOP_LEVEL_FOLDERS
    allowed = {""}
    for relative in (*TOP_LEVEL_FOLDERS, *REQUIRED_FOLDERS):
        parts = Path(relative).parts
        allowed.update(Path(*parts[:index]).as_posix() for index in range(1, len(parts) + 1))
    return allowed


def _sentinel_diff(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    *,
    allowlist: set[str] = frozenset(),
) -> dict[str, dict[str, Any]]:
    diff = {}
    for path in sorted(set(before) | set(after)):
        if before.get(path) == after.get(path) or path in allowlist:
            continue
        diff[path] = {"before": before.get(path), "after": after.get(path)}
    return diff


def _sqlite_counts(root: Path) -> dict[str, Any]:
    db = root / "storage" / "lingji_state.db"
    if not db.exists():
        return {"sources": 0, "scans": [], "jobs": [], "events": [], "queued": 0}
    with sqlite3.connect(db) as connection:
        connection.row_factory = sqlite3.Row
        sources = int(connection.execute("SELECT COUNT(*) FROM automatic_memory_sources").fetchone()[0])
        scans = [dict(row) for row in connection.execute("SELECT * FROM automatic_memory_scans ORDER BY updated_at").fetchall()]
        jobs = [dict(row) for row in connection.execute("SELECT * FROM extraction_jobs ORDER BY created_at").fetchall()]
        events = [dict(row) for row in connection.execute("SELECT event_type, entity_type, entity_id, payload_json FROM events ORDER BY event_id").fetchall()]
    return {
        "sources": sources,
        "scans": scans,
        "jobs": jobs,
        "events": events,
        "queued": sum(row["status"] in {"queued", "retrying", "running"} for row in jobs),
    }


def _structured_counts(root: Path) -> dict[str, int]:
    db = root / "storage" / "lingji_memory.db"
    if not db.exists():
        return {"sources": 0, "conversations": 0, "messages": 0, "memories": 0}
    with sqlite3.connect(db) as connection:
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        queries = {
            "sources": "source_records",
            "conversations": "conversation_records",
            "messages": "message_records",
            "memories": "memory_documents",
        }
        return {
            key: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) if table in tables else 0
            for key, table in queries.items()
        }


def _duplicate_counts(root: Path) -> dict[str, int]:
    db = root / "storage" / "lingji_memory.db"
    if not db.exists():
        return {"source": 0, "conversation": 0, "message": 0, "memory": 0}
    with sqlite3.connect(db) as connection:
        checks = {
            "source": "SELECT COUNT(*) - COUNT(DISTINCT COALESCE(external_id, source_id)) FROM source_records",
            "conversation": "SELECT COUNT(*) - COUNT(DISTINCT COALESCE(external_id, conversation_id)) FROM conversation_records",
            "message": "SELECT COUNT(*) - COUNT(DISTINCT COALESCE(external_id, message_id)) FROM message_records",
            "memory": "SELECT COUNT(*) - COUNT(DISTINCT memory_id) FROM memory_documents",
        }
        return {key: int(connection.execute(sql).fetchone()[0]) for key, sql in checks.items()}


def _identity_sets(root: Path, source_id: str) -> dict[str, Any]:
    """Read terminal identities from the durable state/raw/read-model stores."""
    state_path = root / "storage" / "lingji_state.db"
    result: dict[str, Any] = {
        "source": set(), "scan": set(), "job": set(), "raw": set(),
        "structured": {"source": set(), "conversation": set(), "message": set(), "memory": set()},
    }
    with sqlite3.connect(state_path) as connection:
        connection.row_factory = sqlite3.Row
        result["source"] = {str(row["source_id"]) for row in connection.execute("SELECT source_id FROM automatic_memory_sources WHERE source_id = ?", (source_id,))}
        result["scan"] = {str(row["scan_id"]) for row in connection.execute("SELECT scan_id FROM automatic_memory_scans WHERE source_id = ? AND status IN ('completed','failed','cancelled')", (source_id,))}
        result["job"] = {str(row["job_id"]) for row in connection.execute("SELECT job_id FROM extraction_jobs WHERE automatic_memory_source_id = ? AND status IN ('completed','failed','cancelled')", (source_id,))}
    raw = root / "storage" / "raw"
    if raw.exists():
        result["raw"] = {_sha256(path) for path in raw.rglob("*") if path.is_file()}
    memory_path = root / "storage" / "lingji_memory.db"
    if memory_path.exists():
        with sqlite3.connect(memory_path) as connection:
            tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for key, table, columns in (
                ("source", "source_records", ("external_id", "source_id")),
                ("conversation", "conversation_records", ("external_id", "conversation_id")),
                ("message", "message_records", ("external_id", "message_id")),
                ("memory", "memory_documents", ("memory_id",)),
            ):
                if table not in tables:
                    continue
                available = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
                expression = next((column for column in columns if column in available), None)
                if expression:
                    result["structured"][key] = {str(row[0]) for row in connection.execute(f"SELECT {expression} FROM {table} WHERE {expression} IS NOT NULL")}
    return result


def _wait_until(predicate, *, timeout: float = 12.0, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    latest = None
    while time.monotonic() < deadline:
        try:
            latest = predicate()
        except (urllib.error.URLError, ConnectionError, OSError):
            latest = None
        if latest:
            return latest
        time.sleep(interval)
    return latest


class PackagedSidecar:
    def __init__(self, root: Path, *, source_dir: Path, qdrant_failure: bool = False):
        self.root = root
        self.source_dir = source_dir
        self.port = _free_port()
        self.process: subprocess.Popen[str] | None = None
        self.token = ""
        self.qdrant_failure = qdrant_failure
        self.stdout_path = self.root / "logs" / "packaged.stdout.log"
        self.stderr_path = self.root / "logs" / "packaged.stderr.log"
        self.instance_id = ""
        self.child_inventory: list[str] = []

    def start(self) -> None:
        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": str(REPO_ROOT),
                "LINGJI_GENERIC_HISTORY_DIR": str(self.source_dir),
                "LINGJI_WORKSPACE": "acceptance",
                "LINGJI_AUTOMATIC_MEMORY_DEBOUNCE_SECONDS": "1",
                "LINGJI_AUTOMATIC_MEMORY_RECONCILIATION_SECONDS": "1",
                "LINGJI_AUTOMATIC_MEMORY_INTEGRITY_SECONDS": "3600",
                "LINGJI_SCHEDULER_POLL_SECONDS": "0.05",
                "LINGJI_EXTRACTION_POLL_SECONDS": "0.05",
                "LINGJI_EXTRACTION_BATCH_SIZE": "2",
                "LINGJI_EXTRACTION_MAX_ATTEMPTS": "1",
                "LINGJI_EXTRACTION_STALE_AFTER_SECONDS": "30",
                # Settings accepts these names without a prefix; retain the
                # LINGJI-prefixed discovery/control seams above as well.
                "AUTOMATIC_MEMORY_DEBOUNCE_SECONDS": "1",
                "AUTOMATIC_MEMORY_RECONCILIATION_SECONDS": "60",
                "AUTOMATIC_MEMORY_INTEGRITY_SECONDS": "3600",
                "SCHEDULER_POLL_SECONDS": "0.05",
                "EXTRACTION_POLL_SECONDS": "0.05",
                "EXTRACTION_BATCH_SIZE": "2",
                "EXTRACTION_MAX_ATTEMPTS": "1",
                "EXTRACTION_STALE_AFTER_SECONDS": "30",
                "EMBEDDING_ENABLED": "false",
                "SEMANTIC_ENABLED": "false",
                "LINGJI_EMBEDDING_ENABLED": "false",
                "LINGJI_SEMANTIC_ENABLED": "false",
                "VAULT_DIR": str(self.root / "vault"),
            }
        )
        self.stdout_path.parent.mkdir(parents=True, exist_ok=True)
        self.instance_id = f"{self.root.name}-{time.time_ns()}"
        stdout = self.stdout_path.open("w", encoding="utf-8")
        stderr = self.stderr_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, str(ENTRYPOINT), "--data-root", str(self.root), "--workspace", "acceptance", "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=REPO_ROOT,
            env=env,
            stdout=stdout,
            stderr=stderr,
        )
        stdout.close()
        stderr.close()
        token_path = self.root / "storage" / "control_api_token"
        _wait_until(lambda: token_path.exists(), timeout=8.0)
        self.token = token_path.read_text(encoding="utf-8-sig").strip()
        assert self.token
        status = _wait_until(lambda: _json_request(self.port, "/api/runtime/ping", token=self.token)[0] == 200, timeout=12.0)
        assert status, self._output()

    def stop(self, *, crash: bool = False) -> None:
        process = self.process
        if process is None:
            return
        if process.poll() is None:
            if crash:
                process.kill()
            else:
                _json_request(self.port, "/api/runtime/pause-runtime", token=self.token, method="POST", payload={"confirmation": True}, timeout=2.0)
                try:
                    _json_request(
                        self.port,
                        "/api/automatic-memory/pause-runtime",
                        token=self.token,
                        method="POST",
                        payload={"confirmation": True},
                        timeout=2.0,
                    )
                except (urllib.error.URLError, ConnectionError, OSError):
                    pass
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self.child_inventory = _process_inventory(process.pid)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", self.port))
        self.process = None

    def _output(self) -> str:
        chunks = []
        for path in (self.stdout_path, self.stderr_path):
            if path.exists():
                chunks.append(path.read_text(encoding="utf-8", errors="replace")[-4000:])
        return "\n---\n".join(chunks)

    def get(self, path: str) -> Any:
        status, body = _json_request(self.port, path, token=self.token)
        assert status == 200, (path, status, body)
        return body

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        status, body = _json_request(self.port, path, token=self.token, method="POST", payload=payload)
        assert status == 200, (path, status, body)
        return body


@contextmanager
def _sidecar(root: Path, source_dir: Path) -> Iterator[PackagedSidecar]:
    sidecar = PackagedSidecar(root, source_dir=source_dir)
    try:
        sidecar.start()
        yield sidecar
    finally:
        sidecar.stop()


def _authorize(sidecar: PackagedSidecar, source_dir: Path, *, expires_at: datetime | None = None, grant_id: str = "acceptance-grant") -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return sidecar.post(
        "/api/automatic-memory/authorize",
        {
            "grant_id": grant_id,
            "source_kinds": ["generic_ai_history"],
            "roots": [str(source_dir)],
            "granted_at": now.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "owner_confirmed": True,
            "kind": "generic_ai_history",
            "root": str(source_dir),
        },
    )


def _scan_until_terminal(sidecar: PackagedSidecar, source_id: str, *, timeout: float = 20.0) -> dict[str, Any]:
    status, started = _json_request(sidecar.port, "/api/automatic-memory/scan", token=sidecar.token, method="POST", payload={"source_id": source_id})
    assert status == 200, (status, started)
    scan_id = str(started.get("scan_id") or "")
    assert scan_id and started.get("work_id") == f"automatic-memory:{scan_id}", (source_id, started)
    scan = _wait_until(
        lambda: next((row for row in sidecar.get("/api/automatic-memory/scans") if row.get("scan_id") == scan_id and row.get("status") in {"completed", "failed", "cancelled"}), None),
        timeout=timeout,
    )
    assert scan, sidecar.get("/api/automatic-memory/scans")
    return dict(scan) | {"report": dict(started)}


def _automatic_scan_until_terminal(
    sidecar: PackagedSidecar,
    source_id: str,
    previous_scan_ids: set[str],
    *,
    reasons: set[str],
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Wait for one production-triggered scan and bind it to its event reason."""
    def candidate() -> dict[str, Any] | None:
        scans = sidecar.get("/api/automatic-memory/scans")
        for row in scans:
            scan_id = str(row.get("scan_id") or "")
            if row.get("source_id") != source_id or scan_id in previous_scan_ids:
                continue
            if row.get("status") not in {"completed", "failed", "cancelled"}:
                continue
            for event in _sqlite_counts(sidecar.root)["events"]:
                if event["event_type"] != "automatic_memory_reconciliation" or event["entity_id"] != source_id:
                    continue
                try:
                    payload = json.loads(event["payload_json"])
                except (TypeError, json.JSONDecodeError):
                    continue
                if payload.get("reason") in reasons and payload.get("scan_id") == scan_id:
                    return dict(row) | {"trigger_reason": payload["reason"]}
        return None
    result = _wait_until(candidate, timeout=timeout)
    assert result is not None, {"source_id": source_id, "known": sorted(previous_scan_ids), "scans": sidecar.get("/api/automatic-memory/scans")}
    return result


def _formal_qdrant_fallback(root: Path, *, required_packaged_text: str | None = None) -> dict[str, Any]:
    """Exercise HybridRetriever's production orchestration against persisted data."""
    from src.gateway.bootstrap import build_memory_gateway
    from src.retrieval.hybrid import SearchFilters
    from src.runtime.workspace import WorkspaceContext, WorkspaceName

    vault = root / "vault"
    storage = root / "storage"
    settings = SimpleNamespace(
        vault_auto_init=True, memory_chunk_max_chars=1400, memory_chunk_overlap_chars=180,
        semantic_batch_size=32, semantic_enabled=False, qdrant_distance="cosine", qdrant_timeout_seconds=1,
        qdrant_collection_schema="v1", memory_search_cache_size=0, memory_search_cache_ttl_seconds=0,
        vault_path=vault, storage_path=storage, state_db_path=storage / "lingji_state.db",
        memory_db_path=storage / "lingji_memory.db", log_path=root / "logs", runtime_settings_path=storage / "runtime_settings.json",
        workspace_name="acceptance", production_qdrant_collection="", vault_dir=str(vault), vault_layout_version="1",
        index_private=False,
    )
    workspace = WorkspaceContext(WorkspaceName.ACCEPTANCE, vault, storage / "raw", storage, settings.state_db_path, settings.memory_db_path, "memory", None, None, "lingji_memory_acceptance", settings.log_path, storage / "cache", settings.runtime_settings_path, settings.state_db_path, storage / "backups", storage / "derived", storage / "temp", storage / "reports")
    gateway = build_memory_gateway(settings, workspace=workspace)

    class FailingVectorClient:
        def search(self, query: str, limit: int, filters: dict[str, Any] | None = None):
            raise RuntimeError("injected qdrant unavailable")

    gateway.retriever.semantic_provider = FailingVectorClient()
    result = gateway.retriever.search_with_diagnostics("Lexical fallback", 5, SearchFilters())
    evidence = {"semantic": result["diagnostics"], "lexical_result_count": len(result["results"]), "lexical_texts": [item.get("text") for item in result["results"]]}
    assert result["results"], evidence
    assert result["diagnostics"]["semantic"] == "degraded"
    assert result["diagnostics"]["reason_code"] in {"semantic_query_failed", "semantic_unavailable"}
    if required_packaged_text is not None:
        assert any(required_packaged_text in str(item.get("text") or item.get("content") or "") for item in result["results"]), {
            "blocked_reason": "formal lexical index contains no record produced by packaged automatic-memory ingestion",
            "required_packaged_text": required_packaged_text,
            **evidence,
        }
    else:
        assert any("Lexical fallback" in str(item.get("text") or item.get("content") or "") for item in result["results"])
    gateway.close()
    return evidence


def _run_clean_acceptance(root: Path) -> dict[str, Any]:
    source_dir = root / "generic-history"
    third_party = root / "third-party"
    vault = root / "vault"
    source_dir.mkdir(parents=True)
    third_party.mkdir(parents=True)
    vault.mkdir(parents=True)
    _fixture_history(source_dir / "history.json", conversation="initial", message="packaged acceptance fact")
    (third_party / "unmanaged.ai").write_text("must remain byte-identical\n", encoding="utf-8")
    (third_party / "metadata.json").write_text('{"owner": "fixture", "keep": true}\n', encoding="utf-8")
    (vault / "OwnerNote.md").write_text("# Owner note\nDo not rewrite this fixture.\n", encoding="utf-8")
    (vault / "GatewayFact.md").write_text("# Packaged outage fact\nLexical fallback remains truthful.\n", encoding="utf-8")
    # Capture the owner-fixture baseline before sidecar startup. Only the
    # explicit VaultLayout directory bootstrap allowlist may differ later.
    protected_before: dict[str, dict[str, dict[str, Any]]] = {
        "third_party": _tree_sentinel(third_party),
        "vault": _tree_sentinel(vault),
    }
    vault_allowlist = _vault_bootstrap_allowlist()
    timings: dict[str, float] = {}
    evidence: dict[str, Any] = {"scenarios": {}, "protected_before": protected_before}
    sidecar_receipt: dict[str, Any] = {}

    started = time.monotonic()
    with _sidecar(root, source_dir) as sidecar:
        discovered = sidecar.get("/api/automatic-memory/discovered")
        assert any(item["kind"] == "generic_ai_history" for item in discovered)
        assert _sqlite_counts(root)["sources"] == 0
        assert not list((root / "storage" / "raw").iterdir())
        evidence["scenarios"]["1_metadata_only"] = {"discovered": len(discovered), "sources": _sqlite_counts(root)["sources"]}
        timings["1_metadata_only"] = time.monotonic() - started

        source = _authorize(sidecar, source_dir)
        source_id = str(source["source_id"])
        scan = _scan_until_terminal(sidecar, source_id)
        counts = _wait_until(lambda: _sqlite_counts(root) if _sqlite_counts(root)["queued"] == 0 else None, timeout=20.0) or _sqlite_counts(root)
        structured = _structured_counts(root)
        assert scan["status"] == "completed"
        assert structured["sources"] >= 1 and structured["conversations"] >= 1 and structured["messages"] >= 1
        evidence["scenarios"]["2_authorize_startup"] = {"scan": scan, "structured": structured, "queue": counts["queued"]}
        work_id = str(scan["report"]["work_id"])
        work_fact = _wait_until(
            lambda: next(
                (item for item in sidecar.get("/api/work/history").get("items", []) if item.get("work", {}).get("work_id") == work_id and item.get("outcome", {}).get("status") in {"completed", "failed"}),
                None,
            ),
            timeout=20.0,
        )
        assert work_fact is not None and work_fact.get("outcome", {}).get("status") == "completed"
        evidence["scenarios"]["2_authorize_startup"]["work_fact"] = work_fact
        idempotency_before = _identity_sets(root, source_id)
        idempotent_scan = _scan_until_terminal(sidecar, source_id)
        idempotency_after = _identity_sets(root, source_id)
        assert idempotent_scan["status"] == "completed"
        assert int(idempotent_scan["report"].get("queued") or 0) == 0
        assert int(idempotent_scan["report"].get("reused") or 0) >= 1
        assert idempotency_before["structured"] == idempotency_after["structured"]
        assert all(value == 0 for value in _duplicate_counts(root).values())
        evidence["scenarios"]["2_idempotent_same_bytes"] = {
            "scan": idempotent_scan,
            "before": idempotency_before,
            "after": idempotency_after,
            "duplicates": _duplicate_counts(root),
        }
        timings["2_authorize_startup"] = time.monotonic() - started

        event_started = time.monotonic()
        event_before_ids = {str(row["scan_id"]) for row in sidecar.get("/api/automatic-memory/scans")}
        _fixture_history(source_dir / "history.json", conversation="event", message="event driven acceptance fact")
        event_scan = _automatic_scan_until_terminal(sidecar, source_id, event_before_ids, reasons={"event"}, timeout=30.0)
        timings["3_file_event"] = time.monotonic() - event_started
        assert timings["3_file_event"] <= 30.0
        evidence["scenarios"]["3_file_event"] = {"latency_seconds": timings["3_file_event"], "scan": event_scan}

        sidecar.post("/api/automatic-memory/pause-runtime", {"confirmation": True})
        _fixture_history(source_dir / "history.json", conversation="reconcile", message="suppressed event fact")
        paused_status = sidecar.get("/api/automatic-memory/runtime")
        assert paused_status["paused"] is True
        reconcile_before_ids = {str(row["scan_id"]) for row in sidecar.get("/api/automatic-memory/scans")}
        sidecar.post("/api/automatic-memory/resume-runtime", {"confirmation": True})
        reconciled = _automatic_scan_until_terminal(sidecar, source_id, reconcile_before_ids, reasons={"reconciliation"}, timeout=75.0)
        assert reconciled["status"] == "completed"
        evidence["scenarios"]["4_accelerated_reconciliation"] = {"paused": paused_status, "scan": reconciled}

        # The crash matrix uses the real durable scan lease/checkpoint path. A
        # separate clean root is used by the caller for each percentage.
        evidence["scenarios"]["5_crash_restart"] = {"covered_by": "_run_crash_restart_matrix"}

        expiry_dir = root / "expiry-source"
        expiry_dir.mkdir()
        expiring = _authorize(sidecar, expiry_dir, expires_at=datetime.now(timezone.utc) + timedelta(seconds=1), grant_id="expiry-grant")
        runtime_paused = sidecar.post("/api/automatic-memory/pause-runtime", {"confirmation": True})
        assert runtime_paused["paused"] is True
        runtime_resumed = sidecar.post("/api/automatic-memory/resume-runtime", {"confirmation": True})
        assert runtime_resumed["paused"] is False
        time.sleep(1.2)
        expired_sources = sidecar.get("/api/automatic-memory/sources")
        assert next(item for item in expired_sources if item["source_id"] == expiring["source_id"])["status"] == "expired"
        expired_status, expired_body = _json_request(sidecar.port, "/api/automatic-memory/scan", token=sidecar.token, method="POST", payload={"source_id": expiring["source_id"]})
        assert expired_status == 200
        assert expired_body.get("complete") is False or expired_body.get("errors")
        evidence["scenarios"]["6_lifecycle"] = {"paused": runtime_paused, "resumed": runtime_resumed, "expired": expired_body}

        # Corrupt and healthy sources are independently authorized and scanned
        # through the same scheduler/worker composition.
        bad_dir, good_dir = root / "corrupt-source", root / "healthy-source"
        bad_dir.mkdir(); good_dir.mkdir()
        (bad_dir / "broken.json").write_text("{not a supported history}", encoding="utf-8")
        _fixture_history(good_dir / "good.json", conversation="healthy", message="isolated source fact")
        bad_source = _authorize(sidecar, bad_dir, grant_id="corrupt-grant")
        good_source = _authorize(sidecar, good_dir, grant_id="healthy-grant")
        bad_scan = _scan_until_terminal(sidecar, bad_source["source_id"])
        good_scan = _scan_until_terminal(sidecar, good_source["source_id"])
        job_counts = _wait_until(lambda: _sqlite_counts(root) if _sqlite_counts(root)["queued"] == 0 else None, timeout=20.0) or _sqlite_counts(root)
        all_jobs = job_counts["jobs"]
        assert bad_scan["status"] == "completed" and good_scan["status"] == "completed"
        assert any(job["status"] == "failed" and job["automatic_memory_source_id"] == bad_source["source_id"] for job in all_jobs)
        assert any(job["status"] == "completed" and job["automatic_memory_source_id"] == good_source["source_id"] for job in all_jobs)
        evidence["scenarios"]["7_corrupt_isolation"] = {"bad_scan": bad_scan, "good_scan": good_scan, "jobs": len(all_jobs)}

        # A process restart after a source mtime jump is the sleep/wake
        # equivalent. The normal API reconciliation must remain idempotent.
        sidecar.stop()
        os.utime(source_dir / "history.json", (time.time() + 3600, time.time() + 3600))
        restart_before_ids = {str(row["scan_id"]) for row in _sqlite_counts(root)["scans"]}
        sidecar.start()
        restarted = sidecar.get("/api/automatic-memory/runtime")
        restarted_scan = _automatic_scan_until_terminal(sidecar, source_id, restart_before_ids, reasons={"reconciliation"}, timeout=30.0)
        assert restarted["running"] is True and restarted_scan["status"] == "completed"
        evidence["scenarios"]["9_sleep_wake_restart"] = {"runtime": restarted, "scan": restarted_scan, "clock_jump_seconds": 3600}
        revoked = sidecar.post("/api/automatic-memory/revoke", {"source_id": source_id})
        assert revoked["status"] == "revoked"
        evidence["scenarios"]["6_lifecycle"]["revoked"] = revoked

    protected_after = {"third_party": _tree_sentinel(third_party), "vault": _tree_sentinel(vault)}
    sidecar_receipt = {
        "port": sidecar.port,
        "stdout": str(sidecar.stdout_path.relative_to(root)),
        "stderr": str(sidecar.stderr_path.relative_to(root)),
        "child_inventory_after_exit": sidecar.child_inventory,
        "rebind_verified": True,
    }
    evidence["protected_after"] = protected_after
    evidence["sentinel_diff"] = {
        "third_party": _sentinel_diff(protected_before["third_party"], protected_after["third_party"]),
        "vault": _sentinel_diff(protected_before["vault"], protected_after["vault"], allowlist=vault_allowlist),
    }
    evidence["sentinel_allowlisted_bootstrap"] = {
        "vault": sorted(
            path for path in set(protected_after["vault"]) - set(protected_before["vault"])
            if path in vault_allowlist
        )
    }
    assert all(not diff for diff in evidence["sentinel_diff"].values())
    final_counts = _sqlite_counts(root)
    evidence["final"] = {"state": {"sources": final_counts["sources"], "queued": final_counts["queued"]}, "structured": _structured_counts(root), "duplicates": _duplicate_counts(root), "timings": timings}
    evidence["heartbeat"] = {
        "status": "NOT_MEASURED/BLOCKED",
        "scheduler_heartbeat_age": None,
        "reason": "existing runtime contract exposes no trustworthy idle scheduler heartbeat",
        "work_fact_updated_at_is_not_used_as_heartbeat": True,
    }
    evidence["cleanup_receipt"] = sidecar_receipt
    assert final_counts["queued"] == 0
    assert all(value == 0 for value in evidence["final"]["duplicates"].values())
    # Automatic-memory currently writes raw/structured read-model records but
    # intentionally does not publish a Vault/lexical memory document. Keep the
    # requirement as a hard assertion: a pre-seeded Vault fact must not satisfy
    # the packaged-ingestion Qdrant scenario.
    try:
        _formal_qdrant_fallback(root, required_packaged_text="event driven acceptance fact")
    except AssertionError as exc:
        evidence["scenarios"]["8_qdrant_outage"] = {
            "status": "BLOCKED",
            "reason": "no formal lexical record is produced by packaged automatic-memory ingestion",
            "formal_failure": str(exc),
            "structured_counts": _structured_counts(root),
        }
    else:
        evidence["scenarios"]["8_qdrant_outage"] = {"status": "PASS"}
    evidence["scenarios"]["10_sentinel"] = evidence["sentinel_diff"]
    return evidence


def _run_crash_restart_matrix(root: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for percentage in ("30%", "70%"):
        run_root = root / percentage.replace("%", "pct")
        source_dir = run_root / "generic-history"
        source_dir.mkdir(parents=True)
        for index in range(20):
            _fixture_history(source_dir / f"history-{index:03d}.json", conversation=f"crash-{percentage}-{index}", message="crash recovery fact")
        sidecar = PackagedSidecar(run_root, source_dir=source_dir)
        sidecar.start()
        try:
            source = _authorize(sidecar, source_dir, grant_id=f"acceptance-crash-{percentage}")
            request_process = subprocess.Popen(
                [sys.executable, "-c", ""],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            request_process.kill()
            request_process.wait()
            # Start the real scan through HTTP in this process. The scan is
            # synchronous, so killing the packaged owner while progress is
            # durable is the process-crash boundary being tested.
            import threading
            request_result: list[Any] = []
            def request_scan():
                try:
                    request_result.append(_json_request(sidecar.port, "/api/automatic-memory/scan", token=sidecar.token, method="POST", payload={"source_id": source["source_id"]}))
                except (urllib.error.URLError, ConnectionError, OSError):
                    return
            thread = threading.Thread(target=request_scan, daemon=True)
            thread.start()
            progress = _wait_until(lambda: next((row for row in sidecar.get("/api/automatic-memory/scans") if row.get("source_id") == source["source_id"] and row.get("status") == "running" and int(row.get("total") or 0) > 0 and int(row.get("progress") or 0) >= max(1, int(int(row.get("total") or 1) * (0.3 if percentage == "30%" else 0.7)))), None), timeout=12.0)
            assert progress is not None, sidecar.get("/api/automatic-memory/scans")
            crash_barrier = dict(progress)
            assert crash_barrier["scan_id"] and crash_barrier["total"]
            assert crash_barrier.get("lease_owner_pid") and crash_barrier.get("lease_expires_at")
            assert crash_barrier.get("scheduler_lease_owner") and crash_barrier.get("scheduler_lease_expires_at")
            terminal_before = _identity_sets(run_root, source["source_id"])
            sidecar.stop(crash=True)
            sidecar = PackagedSidecar(run_root, source_dir=source_dir)
            sidecar.start()
            # SnapshotJobRunner's durable lease is intentionally conservative;
            # wait only until the persisted lease expiry, then explicitly
            # trigger the normal API reconciliation after process restart.
            lease_row = _wait_until(lambda: next((row for row in sidecar.get("/api/automatic-memory/scans") if row.get("scan_id") == progress.get("scan_id")), None), timeout=5.0)
            if lease_row and lease_row.get("lease_expires_at"):
                expiry = datetime.fromisoformat(str(lease_row["lease_expires_at"]).replace("Z", "+00:00"))
                time.sleep(max(0.0, (expiry - datetime.now(timezone.utc)).total_seconds()) + 0.1)
            recovery_status, recovery = _json_request(sidecar.port, "/api/automatic-memory/scan", token=sidecar.token, method="POST", payload={"source_id": source["source_id"]}, timeout=5.0)
            assert recovery_status == 200 and recovery.get("scan_id") == crash_barrier["scan_id"]
            terminal = _wait_until(lambda: next((row for row in sidecar.get("/api/automatic-memory/scans") if row.get("scan_id") == crash_barrier["scan_id"] and row.get("status") in {"completed", "failed", "cancelled"}), None), timeout=30.0)
            assert terminal is not None, sidecar.get("/api/automatic-memory/scans")
            thread.join(timeout=5)
            counts = _wait_until(lambda: _sqlite_counts(run_root) if _sqlite_counts(run_root)["queued"] == 0 else None, timeout=30.0) or _sqlite_counts(run_root)
            assert counts["queued"] == 0
            terminal_after = _identity_sets(run_root, source["source_id"])
            results[percentage] = {
                "crash_barrier": crash_barrier,
                "terminal": terminal,
                "terminal_before": terminal_before,
                "terminal_after": terminal_after,
                "jobs": len(counts["jobs"]),
                "structured": _structured_counts(run_root),
            }
        finally:
            sidecar.stop()
    assert results["30%"]["jobs"] == results["70%"]["jobs"]
    for key in ("source", "scan", "job", "raw"):
        assert len(results["30%"]["terminal_after"][key]) == len(results["70%"]["terminal_after"][key])
    for key in ("source", "conversation", "message", "memory"):
        assert len(results["30%"]["terminal_after"]["structured"][key]) == len(results["70%"]["terminal_after"]["structured"][key])
    return results


def test_automatic_memory_packaged_flow_runs_twice_from_clean_acceptance_roots(tmp_path: Path):
    """Run all measured composition scenarios twice; any skipped scenario fails."""
    all_runs: list[dict[str, Any]] = []
    for run_number in (1, 2):
        root = tmp_path / f"acceptance-run-{run_number}"
        evidence = _run_clean_acceptance(root)
        evidence["run_identity"] = run_number
        evidence["crash_restart"] = _run_crash_restart_matrix(tmp_path / f"crash-run-{run_number}")
        all_runs.append(evidence)
    scenario_names = {
        "1_metadata_only", "2_authorize_startup", "3_file_event",
        "4_accelerated_reconciliation", "5_crash_restart", "6_lifecycle",
        "7_corrupt_isolation", "8_qdrant_outage", "9_sleep_wake_restart", "10_sentinel",
    }
    assert scenario_names <= set(all_runs[0]["scenarios"])
    assert all(run["final"]["state"]["queued"] == 0 for run in all_runs)
    assert all(run["scenarios"]["8_qdrant_outage"]["status"] == "PASS" for run in all_runs)


def test_qdrant_outage_uses_formal_retrieval_orchestration_with_lexical_fallback(tmp_path: Path):
    """Inject a product semantic-client failure and retain lexical results."""
    (tmp_path / "vault").mkdir()
    (tmp_path / "storage").mkdir()
    (tmp_path / "vault" / "fact.md").write_text(
        "# Packaged outage fact\nLexical fallback remains truthful.\n", encoding="utf-8"
    )
    evidence = _formal_qdrant_fallback(tmp_path)
    assert evidence["lexical_result_count"] > 0
