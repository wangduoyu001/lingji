from __future__ import annotations

import inspect
import json
import math
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4

from src.extraction.queue import SQLiteExtractionQueue
from src.storage import StateDatabase
from src.storage.state_db import LeaseLostError
from src.automatic_memory.value_gate import evaluate_session_value

from .models import ScanRun
from .snapshot import ConsistentSnapshot, SnapshotResult


# ---------------------------------------------------------------------------
# raw 空间淘汰（主人约束：占用不能无限膨胀，2026-09-23）
#
# 触发时机：写入新快照前配额将超限时。规则宁可少删不删错：
# - 全局最新 5 个文件永不淘汰（进行中的采集/提取窗口）；
# - 小文件（<32MiB）24 小时内不淘汰；
# - 大快照（>=32MiB，活动库整库拷贝，如 ZCode 会话库）只保护最新 3 个，
#   其余 6 小时后可淘汰——它们是滚动副本，最新副本即当前事实；
# - 从最旧开始淘汰直到用量回到 target；每次淘汰追加记账到 raw/.evicted.log
#   （raw_id、大小、mtime），可审计、可解释。
# 淘汰对象都是"可从活跃来源重新采集"的快照副本，不是主人原始数据。
# ---------------------------------------------------------------------------

_LARGE_SNAPSHOT_BYTES = 32 * 1024 * 1024
_KEEP_RECENT = 5
_KEEP_LARGE_COPIES = 3
# 小文件保护窗 24h→6h（主人 2026-09-27 拍板：不得过度占用硬盘）。24h 窗让
# 小文件churn 独占 ~1.6GiB 保护地板，把 raw 上限压到保护地板之下；未终态
# 任务引用的快照本就由准确性保护名单单独硬保护，6h 足够覆盖重试边缘。
_SMALL_PROTECT_SECONDS = 6 * 3600
_LARGE_PROTECT_SECONDS = 6 * 3600
_EVICT_LOG_NAME = ".evicted.log"

# PERF_RESOURCE_CLOSEOUT_20260927B：入口价值预判的共享常量与审计工具。
# runner 写入与 API 读取必须走同一路径函数，避免两处路径漂移。
VALUE_GATE_AUDIT_FILENAME = "value_gate_skipped.jsonl"
VALUE_GATE_AUDIT_MAX_ENTRIES = 200
VALUE_GATE_SKIPPED_STATUS = "skipped_by_value_gate"


def value_gate_audit_path(raw_root: Path) -> Path:
    """被拦会话审计文件的唯一权威路径：``<raw_root>/../runtime/``。"""
    return Path(raw_root).parent / "runtime" / VALUE_GATE_AUDIT_FILENAME


def append_value_gate_audit(raw_root: Path, entry: dict[str, Any]) -> None:
    """Best-effort 追加审计并滚动截断；审计失败绝不阻断采集。"""
    try:
        audit_path = value_gate_audit_path(raw_root)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        lines = audit_path.read_text(encoding="utf-8").splitlines()
        if len(lines) > VALUE_GATE_AUDIT_MAX_ENTRIES:
            audit_path.write_text(
                "\n".join(lines[-VALUE_GATE_AUDIT_MAX_ENTRIES:]) + "\n", encoding="utf-8"
            )
    except Exception:
        pass


def read_value_gate_audit(
    raw_root: Path, *, limit: int = 50
) -> tuple[int, list[dict[str, Any]]]:
    """返回（被拦会话条数, 倒序最新 limit 条记录）；文件不存在返回 0 条。

    total 只数被拦会话（带 reason 的条目）；rescan_requested 之类的动作
    标记计入样本流但不冒充被拦会话数。
    """
    try:
        lines = value_gate_audit_path(raw_root).read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0, []
    entries: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            entries.append(parsed)
    total = sum(1 for entry in entries if entry.get("action") is None)
    sample = list(reversed(entries[-limit:])) if limit > 0 else []
    return total, sample


def _dir_usage(raw_root: Path) -> int:
    total = 0
    for entry in raw_root.iterdir():
        try:
            if entry.is_file():
                total += entry.stat().st_size
        except OSError:
            continue
    return total


def nonterminal_job_raw_ids(state_db_path: Path) -> set[str]:
    """未终态提取任务（queued/processing/failed）引用的 raw_id 集合。

    准确性红线（2026-09-24 主人约束）：淘汰绝不能删掉还没提炼完成的快照，
    否则那些内容永远进不了记忆层。failed 也保护——失败任务会自动重试，
    raw 没了重试就永远不可能成功。
    """
    protected: set[str] = set()
    try:
        import sqlite3

        conn = sqlite3.connect(f"file:{state_db_path}?mode=ro", uri=True, timeout=10)
        try:
            rows = conn.execute(
                """
                SELECT json_extract(payload_json, '$.raw_id')
                FROM extraction_jobs
                WHERE status IN ('queued', 'processing', 'failed')
                """
            ).fetchall()
        finally:
            conn.close()
        for (raw_id,) in rows:
            if raw_id:
                protected.add(str(raw_id))
    except Exception:
        # 查不到保护名单时宁可不淘汰（返回空集会让调用方维持配额报错语义）。
        return set()
    return protected


def evict_raw_for_space(
    raw_root: Path,
    target_bytes: int,
    *,
    now: float | None = None,
    keep_recent: int = _KEEP_RECENT,
    protected: set[str] | None = None,
) -> list[dict[str, Any]]:
    """把 raw 用量淘汰回 target_bytes 以下；返回淘汰记录列表。

    无淘汰空间可释放（全是受保护文件）时返回空列表，调用方维持原配额报错语义。
    `protected`：准确性保护名单（未终态任务引用的 raw_id），永不淘汰。
    """
    now = now if now is not None else time.time()
    protected = {str(item) for item in (protected or set())}
    if not raw_root.is_dir():
        return []
    entries: list[tuple[float, int, Path]] = []  # (mtime, size, path)
    for entry in raw_root.iterdir():
        if entry.name.startswith("."):
            continue
        try:
            if not entry.is_file():
                continue
            stat = entry.stat()
        except OSError:
            continue
        entries.append((stat.st_mtime, stat.st_size, entry))
    if not entries:
        return []
    entries.sort(key=lambda item: item[0])  # 最旧优先

    usage = sum(size for _m, size, _p in entries)
    if usage <= target_bytes:
        return []
    budget = usage - target_bytes

    # "最新 5 个"窗口保护只针对小文件；大快照由"最新 3 份 + 6h"单独管辖，
    # 否则大文件被全局窗口连带保护，滚动副本永不收敛。
    newest_names = {
        path.name
        for _m, _s, path in sorted(
            (item for item in entries if item[1] < _LARGE_SNAPSHOT_BYTES),
            key=lambda item: item[0],
            reverse=True,
        )[: max(keep_recent, 0)]
    }
    large_names = {
        path.name
        for _m, _s, path in sorted(
            (item for item in entries if item[1] >= _LARGE_SNAPSHOT_BYTES),
            key=lambda item: item[0],
            reverse=True,
        )[:_KEEP_LARGE_COPIES]
    }

    evicted: list[dict[str, Any]] = []
    log_path = raw_root / _EVICT_LOG_NAME
    for mtime, size, path in entries:
        if budget <= 0:
            break
        if path.name in newest_names or path.name in large_names or path.name in protected:
            continue
        age = now - mtime
        protect = _LARGE_PROTECT_SECONDS if size >= _LARGE_SNAPSHOT_BYTES else _SMALL_PROTECT_SECONDS
        if age < protect:
            continue
        try:
            path.unlink()
        except OSError:
            continue
        record = {
            "raw_id": path.name,
            "bytes": size,
            "mtime": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
        }
        evicted.append(record)
        budget -= size
        try:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return evicted


@dataclass(frozen=True)
class ResumeToken:
    scan_id: str
    cursor: str
    source_sentinel: str
    lease_id: str
    attempt: int


class CheckpointStore:
    """Persist scan recovery in the existing StateDatabase scan row."""

    def __init__(self, state_db: StateDatabase | Path | str, *, lease_ttl_seconds: float = 30.0):
        self.state_db = (
            state_db if isinstance(state_db, StateDatabase) else StateDatabase(state_db)
        )
        self.lease_ttl_seconds = max(float(lease_ttl_seconds), 0.1)

    def save(self, token: ResumeToken, *, manifest_status: str = "processed") -> None:
        self._save(token, manifest_status=manifest_status)

    def save_token_only(self, token: ResumeToken) -> None:
        self._save(token, manifest_status=None)

    def _save(self, token: ResumeToken, *, manifest_status: str | None) -> None:
        payload = json.dumps(
            {
                "scan_id": token.scan_id,
                "cursor": token.cursor,
                "source_sentinel": token.source_sentinel,
                "lease_id": token.lease_id,
                "attempt": int(token.attempt),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        self.state_db.update_automatic_memory_scan_owned(
            token.scan_id,
            token.lease_id,
            lease_ttl_seconds=self.lease_ttl_seconds,
            cursor=token.cursor or None,
            source_sentinel=token.source_sentinel,
            attempt=int(token.attempt),
            recovery_token=payload,
        )
        if token.cursor and token.source_sentinel and manifest_status is not None:
            scan = self.state_db.get_automatic_memory_scan(token.scan_id)
            if scan is not None:
                self.state_db.upsert_automatic_memory_scan_item_owned(
                    token.scan_id,
                    token.lease_id,
                    source_id=scan["source_id"],
                    relative_path=token.cursor,
                    sentinel=token.source_sentinel,
                    status=manifest_status,
                )

    def load(self, scan_id: str) -> ResumeToken | None:
        row = self.state_db.get_automatic_memory_scan(scan_id)
        if row is None:
            return None
        payload = row.get("recovery_token")
        if payload:
            try:
                decoded = json.loads(payload)
                if isinstance(decoded, dict) and decoded.get("scan_id") == scan_id:
                    return ResumeToken(
                        scan_id=scan_id,
                        cursor=str(decoded.get("cursor") or ""),
                        source_sentinel=str(decoded.get("source_sentinel") or ""),
                        lease_id=str(decoded.get("lease_id") or ""),
                        attempt=int(decoded.get("attempt") or 0),
                    )
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        if not row.get("cursor") and not row.get("source_sentinel") and not row.get("lease_id"):
            return None
        return ResumeToken(
            scan_id=scan_id,
            cursor=str(row.get("cursor") or ""),
            source_sentinel=str(row.get("source_sentinel") or ""),
            lease_id=str(row.get("lease_id") or ""),
            attempt=int(row.get("attempt") or 0),
        )


PathProvider = Callable[[Any, Any], Any]


class SnapshotJobRunner:
    """Admit authorized snapshots to the existing extraction queue."""

    def __init__(
        self,
        snapshot: ConsistentSnapshot | None = None,
        queue: SQLiteExtractionQueue | None = None,
        state_db: StateDatabase | Path | str | None = None,
        *,
        path_provider: PathProvider,
        checkpoint_store: CheckpointStore | None = None,
        snapshotter: ConsistentSnapshot | None = None,
        before_checkpoint: Callable[[int, int], None] | None = None,
        before_queue: Callable[[], None] | None = None,
        after_lease: Callable[[], None] | None = None,
        lease_ttl_seconds: float = 30.0,
        raw_max_bytes: int = 10 * 1024 ** 3,
        value_gate_enabled: bool = False,
        value_gate_min_turns: int = 2,
        value_gate_min_chars: int = 300,
        value_gate_config_provider: Callable[[], tuple[bool, int, int]] | None = None,
    ):
        if snapshot is None:
            snapshot = snapshotter
        if snapshot is None or queue is None or state_db is None:
            raise TypeError("snapshot, queue and state_db are required")
        self.snapshot = snapshot
        self.raw_max_bytes = max(int(raw_max_bytes), 1)
        self.queue = queue
        self.state_db = state_db if isinstance(state_db, StateDatabase) else StateDatabase(state_db)
        self.path_provider = path_provider
        self.lease_ttl_seconds = max(float(lease_ttl_seconds), 0.1)
        # PERF_RESOURCE_ROOT_CAUSE_20260927 (B1): off by default so existing
        # callers and tests keep today's semantics; production turns it on
        # via settings (value_gate_enabled, value_gate_min_turns/chars).
        self.value_gate_enabled = bool(value_gate_enabled)
        self.value_gate_min_turns = max(int(value_gate_min_turns), 0)
        self.value_gate_min_chars = max(int(value_gate_min_chars), 0)
        # B1 收尾：阈值可由 provider 每次判定时动态读取（RuntimeSettingsStore），
        # 主人改设置后运行中的 runner 立即生效；provider 异常时回退静态值。
        self.value_gate_config_provider = value_gate_config_provider
        self.checkpoints = checkpoint_store or CheckpointStore(
            self.state_db, lease_ttl_seconds=self.lease_ttl_seconds
        )
        self.before_checkpoint = before_checkpoint
        self.before_queue = before_queue
        self.after_lease = after_lease
        self._heartbeat_stop: threading.Event | None = None
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_error: BaseException | None = None

    def _validate_single_database(self) -> None:
        state_path = Path(self.state_db.path).expanduser()
        queue_path = Path(self.queue.path).expanduser()
        try:
            same = os.path.samefile(state_path, queue_path)
        except (FileNotFoundError, OSError):
            same = state_path.resolve(strict=False) == queue_path.resolve(strict=False)
        if not same:
            raise ValueError(
                "SnapshotJobRunner requires state database and extraction queue to use the same SQLite file"
            )

    def _start_heartbeat(self, scan_id: str, lease_id: str) -> None:
        stop = threading.Event()
        self._heartbeat_stop = stop
        self._heartbeat_error = None

        def renew() -> None:
            interval = max(min(self.lease_ttl_seconds / 3.0, 1.0), 0.05)
            while not stop.wait(interval):
                try:
                    self.state_db.renew_automatic_memory_scan_lease(
                        scan_id,
                        lease_id,
                        ttl_seconds=self.lease_ttl_seconds,
                    )
                except LeaseLostError:
                    return
                except Exception as exc:
                    self._heartbeat_error = exc
                    return

        self._heartbeat_thread = threading.Thread(
            target=renew,
            name=f"lingji-automatic-memory-heartbeat-{scan_id}",
            daemon=True,
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat(self) -> None:
        stop, thread = self._heartbeat_stop, self._heartbeat_thread
        self._heartbeat_stop = None
        self._heartbeat_thread = None
        if stop is not None:
            stop.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(self.lease_ttl_seconds, 0.2))

    def _assert_heartbeat(self) -> None:
        if self._heartbeat_error is not None:
            raise LeaseLostError(f"automatic-memory lease heartbeat failed: {self._heartbeat_error}")

    def _reconcile_snapshot_temporary_files(self, scan_id: str | None = None) -> dict[str, Any]:
        """Run snapshot cleanup and persist only a generic retryable error."""
        try:
            result = self.snapshot.reconcile_temporary_snapshots()
        except Exception:
            result = {
                "scanned": 0,
                "removed": 0,
                "preserved": 0,
                "errors": ("snapshot_reconcile_failed",),
                "clean": False,
            }
        errors = tuple(
            str(error)
            for error in (result.get("errors") or ())
            if str(error)
        ) if isinstance(result, dict) else ("snapshot_reconcile_failed",)
        if errors and scan_id:
            try:
                row = self.state_db.get_automatic_memory_scan(scan_id)
                existing = row.get("last_error") if row else None
                detail = "snapshot temporary cleanup failed: " + ",".join(
                    dict.fromkeys(errors)
                )
                if isinstance(existing, str) and existing and existing != detail:
                    detail = f"{existing[:1600]}; {detail}"
                self.state_db.update_automatic_memory_scan(
                    scan_id,
                    last_error=detail[:2000],
                    updated_at=self._updated_at(),
                )
            except Exception:
                # The receipt remains available to the caller; never turn a
                # cleanup observation into a false successful scan.
                pass
        return result if isinstance(result, dict) else {
            "scanned": 0,
            "removed": 0,
            "preserved": 0,
            "errors": ("snapshot_reconcile_failed",),
            "clean": False,
        }

    def _handle_lease_loss(self, scan_id: str, lease_id: str) -> ScanRun:
        heartbeat_error = self._heartbeat_error
        self._stop_heartbeat()
        if heartbeat_error is not None:
            try:
                self.state_db.update_automatic_memory_scan_owned(
                    scan_id,
                    lease_id,
                    lease_ttl_seconds=self.lease_ttl_seconds,
                    status="failed",
                    last_error=f"lease heartbeat failed: {heartbeat_error}"[:2000],
                    updated_at=self._updated_at(),
                )
            except LeaseLostError:
                pass
        try:
            self._release(scan_id, lease_id)
        except LeaseLostError:
            pass
        self._reconcile_snapshot_temporary_files(scan_id)
        return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

    def run(
        self,
        scan_id: str,
        crash_at: Literal["none", "30%", "70%", "after-lease"] = "none",
        *,
        force_capture: bool = False,
    ) -> ScanRun:
        if crash_at not in {"none", "30%", "70%", "after-lease"}:
            raise ValueError(f"unsupported crash_at: {crash_at}")
        self._validate_single_database()
        row = self.state_db.get_automatic_memory_scan(scan_id)
        if row is None:
            raise LookupError(f"scan not found: {scan_id}")
        if row["status"] == "cancelled":
            self._reconcile_snapshot_temporary_files(scan_id)
            return self._scan(row)
        if row["status"] == "completed" and crash_at == "none":
            self._reconcile_snapshot_temporary_files(scan_id)
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id) or row)
        source_id = str(row["source_id"])
        source = self.state_db.get_automatic_memory_source(
            source_id, now=self._updated_at()
        )
        if source is None:
            raise PermissionError("source is not authorized for scanning")
        if source.get("status") != "authorized":
            current = self.state_db.get_automatic_memory_scan(scan_id)
            if current and current["status"] == "cancelled":
                return self._scan(current)
            self.state_db.update_automatic_memory_scan(
                scan_id,
                status="failed",
                last_error="source authorization is not active",
                updated_at=self._updated_at(),
            )
            self._reconcile_snapshot_temporary_files(scan_id)
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

        paths = self._paths(row, source)
        previous = {} if force_capture else self._previous_manifest(source_id, scan_id)
        raw_used = sum(p.stat().st_size for p in self.snapshot.raw_root.iterdir()
                       if p.is_file() and not p.is_symlink())
        total = len(paths)
        token = self.checkpoints.load(scan_id)
        cursor = token.cursor if token else ""
        sentinels = {
            item["relative_path"]: item["sentinel"]
            for item in self.state_db.list_automatic_memory_scan_items(scan_id)
        }
        pending: list[Path] = []
        completed_before = 0
        for path in paths:
            relative = self._relative(source, path)
            try:
                current_sentinel = self._path_sentinel(path)
            except OSError:
                current_sentinel = ""
            if current_sentinel and self._sentinel_matches(sentinels.get(relative, ""), current_sentinel):
                completed_before += 1
            else:
                pending.append(path)
        paths = pending
        queued_count = 0
        reused_count = 0
        source_sentinel = sentinels.get(cursor, "")
        lease_id = uuid4().hex
        attempt = int(row.get("attempt") or 0) + 1
        acquired = self.state_db.acquire_automatic_memory_scan_lease(
            scan_id, lease_id, ttl_seconds=self.lease_ttl_seconds
        )
        if acquired is None:
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
        attempt = int(acquired.get("attempt") or attempt)
        self.state_db.update_automatic_memory_scan_owned(
            scan_id,
            lease_id,
            lease_ttl_seconds=self.lease_ttl_seconds,
            total=total,
            last_error=None,
            updated_at=self._updated_at(),
        )
        self._reconcile_snapshot_temporary_files(scan_id)
        self._start_heartbeat(scan_id, lease_id)
        try:
            initial = ResumeToken(scan_id, cursor, source_sentinel, lease_id, attempt)
            self.checkpoints.save_token_only(initial)
            if self.after_lease is not None:
                self.after_lease()
            if crash_at == "after-lease":
                return self._pause(scan_id, initial)
        except LeaseLostError:
            return self._handle_lease_loss(scan_id, lease_id)
        except Exception as exc:
            self._stop_heartbeat()
            try:
                self.state_db.update_automatic_memory_scan_owned(
                    scan_id,
                    lease_id,
                    lease_ttl_seconds=self.lease_ttl_seconds,
                    status="failed",
                    last_error=str(exc)[:2000],
                    updated_at=self._updated_at(),
                )
                self._release(scan_id, lease_id)
                self._reconcile_snapshot_temporary_files(scan_id)
            except LeaseLostError:
                pass
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

        crash_index = (
            math.ceil(total * 0.3)
            if crash_at == "30%"
            else math.ceil(total * 0.7)
            if crash_at == "70%"
            else None
        )
        processed = completed_before
        try:
            for path in paths:
                self._assert_heartbeat()
                relative = self._relative(source, path)
                result = self._reuse_snapshot(source_id, path, previous.get(relative))
                if result is None:
                    size = path.stat().st_size
                    if raw_used + size > self.raw_max_bytes:
                        # 先尝试淘汰过保护期的旧快照腾位（占用不能无限膨胀）；
                        # 未终态任务引用的快照在准确性保护名单里绝不淘汰；
                        # 仍不够才维持原"触顶拒绝写入"语义。
                        try:
                            target = int(self.raw_max_bytes * 0.7)
                            protected_ids = nonterminal_job_raw_ids(
                                Path(self.state_db.path)
                            )
                            evict_raw_for_space(
                                self.snapshot.raw_root, target, protected=protected_ids
                            )
                            raw_used = _dir_usage(self.snapshot.raw_root)
                        except Exception:
                            raw_used = max(raw_used, _dir_usage(self.snapshot.raw_root))
                    if raw_used + size > self.raw_max_bytes:
                        raise RuntimeError(
                            f"raw storage limit reached ({raw_used}/{self.raw_max_bytes} bytes); "
                            "existing evidence preserved; free space or raise automatic_memory_raw_max_bytes"
                        )
                    result = self.snapshot.capture(
                        source_id, path, scan_id=scan_id, lease_id=lease_id,
                        lease_guard=self._assert_heartbeat,
                    )
                    # Conservative within-scan accounting also bounds staging space.
                    raw_used += result.stat_after.size
                if not result.stable:
                    raise RuntimeError(
                        f"source changed during snapshot: {result.relative_path}"
                    )
                raw_path = self.snapshot.raw_root / result.raw_id
                # PERF_RESOURCE_ROOT_CAUSE_20260927 (B1): session value gate.
                # Short sessions without any value signal skip the entire
                # intake pipeline (queue, extraction, embedding, backfill).
                # The decision is never silent: every skip lands in a JSONL
                # audit trail, and the sentinel is still recorded so the
                # unchanged file is not re-captured every round. A source
                # rescan that changes the file invalidates the sentinel and
                # re-admits the content.
                gate_admission: dict[str, Any] | None = None
                try:
                    gate_text = raw_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    gate_text = ""
                gate_enabled, gate_min_turns, gate_min_chars = self._value_gate_config()
                gate = (
                    evaluate_session_value(
                        [gate_text] if gate_text.strip() else [],
                        min_turns=gate_min_turns,
                        min_chars=gate_min_chars,
                    )
                    if gate_enabled
                    else None
                )
                if gate is not None and not gate.approved:
                    self._record_value_gate_skip(source_id, result, gate)
                    gate_admission = {
                        "status": "skipped_by_value_gate",
                        "job_id": "",
                        "existing_job": False,
                    }
                if self.before_queue is not None:
                    self.before_queue()
                try:
                    if gate_admission is not None:
                        admission: dict[str, Any] = gate_admission
                    else:
                        admission = self.queue.enqueue_authorized_snapshot(
                        scan_id=scan_id,
                        lease_id=lease_id,
                        source_id=source_id,
                        relative_path=result.relative_path,
                        raw_id=result.raw_id,
                        sha256=result.sha256,
                        input_path=raw_path,
                        source_type=str(source.get("kind") or ""),
                    )
                    admission_status = str(admission.get("status") or "").lower()
                    existing_payload = admission.get("payload") if isinstance(admission.get("payload"), dict) else {}
                    association = "existing" if admission.get("existing_job") and str(existing_payload.get("scan_id") or "") != scan_id else "new"
                    if association == "existing" and admission_status == "completed":
                        reused_count += 1
                    elif not admission.get("existing_job"):
                        queued_count += 1
                except Exception as exc:
                    raise RuntimeError(
                        "raw committed before queue admission; orphan raw evidence "
                        f"raw_id={result.raw_id} relative_path={result.relative_path}: {exc}"
                    ) from exc
                processed += 1
                if self.before_checkpoint is not None:
                    self.before_checkpoint(processed, total)
                sentinel = self._sentinel(result)
                sentinels[result.relative_path] = sentinel
                source_sentinel = sentinel
                checkpoint = ResumeToken(
                    scan_id, result.relative_path, source_sentinel, lease_id, attempt
                )
                job_id = str(admission.get("job_id") or "")
                existing_payload = admission.get("payload") if isinstance(admission.get("payload"), dict) else {}
                association = "existing" if admission.get("existing_job") and str(existing_payload.get("scan_id") or "") != scan_id else "new"
                # B1 收尾：被拒会话从未入队，不得伪装成 "queued"；显式记录
                # skipped_by_value_gate，主人可在来源页看到并在重扫后撤销。
                if str(admission.get("status") or "") == VALUE_GATE_SKIPPED_STATUS:
                    manifest_status = VALUE_GATE_SKIPPED_STATUS
                else:
                    manifest_status = f"job:{job_id}:{association}" if job_id else "queued"
                self.checkpoints.save(checkpoint, manifest_status=manifest_status)
                cursor = result.relative_path
                source_sentinel = sentinel
                self.state_db.update_automatic_memory_scan_owned(
                    scan_id,
                    lease_id,
                    lease_ttl_seconds=self.lease_ttl_seconds,
                    progress=processed,
                    total=total,
                    updated_at=self._updated_at(),
                )
                self._assert_heartbeat()
                if crash_index is not None and processed >= crash_index:
                    return self._pause(scan_id, checkpoint)
        except LeaseLostError:
            return self._handle_lease_loss(scan_id, lease_id)
        except Exception as exc:
            checkpoint = ResumeToken(scan_id, cursor, source_sentinel, lease_id, attempt)
            try:
                self._stop_heartbeat()
                self.checkpoints.save_token_only(checkpoint)
                existing_error = (self.state_db.get_automatic_memory_scan(scan_id) or {}).get(
                    "last_error"
                )
                error_text = (
                    str(existing_error)
                    if isinstance(existing_error, str) and existing_error.startswith("raw conflict")
                    else str(exc)[:2000]
                )
                self.state_db.update_automatic_memory_scan_owned(
                    scan_id,
                    lease_id,
                    lease_ttl_seconds=self.lease_ttl_seconds,
                    status="failed",
                    total=total,
                    progress=processed,
                    last_error=error_text,
                    updated_at=self._updated_at(),
                )
                self._release(scan_id, lease_id)
                self._reconcile_snapshot_temporary_files(scan_id)
            except LeaseLostError:
                return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
        try:
            self._stop_heartbeat()
            finalized = self.state_db.finalize_automatic_memory_scan_lease(
                scan_id,
                lease_id,
                cursor=cursor if not paths else self._relative(source, paths[-1]),
                progress=total,
                total=total,
                last_error=None,
                queued_count=queued_count,
                reused_count=reused_count,
                updated_at=self._updated_at(),
            )
            self._reconcile_snapshot_temporary_files(scan_id)
        except LeaseLostError:
            self._stop_heartbeat()
            return self._scan(self.state_db.get_automatic_memory_scan(scan_id))
        final_row = self.state_db.get_automatic_memory_scan(scan_id) or finalized
        return self._scan(final_row)

    def _previous_manifest(self, source_id: str, scan_id: str) -> dict[str, Any]:
        scans = self.state_db.list_automatic_memory_scans(source_id)
        completed = [s for s in scans if s['scan_id'] != scan_id and s['status'] == 'completed']
        if not completed:
            return {}
        latest = completed[0]  # StateDatabase orders by timestamp, then insertion order.
        return {i['relative_path']: i for i in self.state_db.list_automatic_memory_scan_items(latest['scan_id'])}

    def _reuse_snapshot(self, source_id: str, path: Path, item: dict | None) -> SnapshotResult | None:
        if not item or not str(item.get('status', '')).startswith('job:'):
            return None
        # Reuse never bypasses authorization, path checks, or queue admission.
        _, relative = self.snapshot._authorized_path(source_id, path)
        before = self.snapshot._file_stat(path)
        if not self._sentinel_matches(item['sentinel'], self._path_sentinel(path)):
            return None
        try:
            job = self.queue.get(item['status'].split(':')[1])
        except (KeyError, LookupError):
            return None
        payload = job.get('payload') or {}
        digest = str(payload.get('sha256') or '')
        if (job.get('status') not in {'queued', 'running', 'completed'}
                or payload.get('source_id') != source_id
                or payload.get('relative_path') != relative
                or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)
                or payload.get('raw_id') != digest):
            return None
        raw = self.snapshot.raw_root / digest
        if raw.is_symlink() or not raw.is_file() or raw.stat().st_size != before.size:
            return None
        after = self.snapshot._file_stat(path)
        if before != after:
            return None
        return SnapshotResult(source_id, relative, digest, digest, before, after, True, 0)

    def _pause(self, scan_id: str, token: ResumeToken) -> ScanRun:
        self._stop_heartbeat()
        self.state_db.update_automatic_memory_scan_owned(
            scan_id,
            token.lease_id,
            lease_ttl_seconds=self.lease_ttl_seconds,
            status="paused",
            cursor=token.cursor or None,
            recovery_token=json.dumps(token.__dict__, sort_keys=True),
            updated_at=self._updated_at(),
        )
        self._release(scan_id, token.lease_id)
        self._reconcile_snapshot_temporary_files(scan_id)
        return self._scan(self.state_db.get_automatic_memory_scan(scan_id))

    def _release(self, scan_id: str, lease_id: str) -> None:
        self._stop_heartbeat()
        self.state_db.release_automatic_memory_scan_lease(
            scan_id, lease_id, now=self._updated_at()
        )

    def _paths(self, scan: dict[str, Any], source: dict[str, Any]) -> list[Path]:
        provider = self.path_provider
        try:
            signature = inspect.signature(provider)
            values = provider(scan, source) if len(signature.parameters) >= 2 else provider(scan)
        except (TypeError, ValueError):
            values = provider(scan, source)
        paths = [Path(value).expanduser() for value in (values or [])]
        return sorted(paths, key=lambda path: self._relative(source, path))

    @staticmethod
    def _relative(source: dict[str, Any], path: Path) -> str:
        return Path(path).expanduser().absolute().relative_to(
            Path(source["root"]).expanduser().absolute()
        ).as_posix()

    def _value_gate_config(self) -> tuple[bool, int, int]:
        """每次判定时取当前 (enabled, min_turns, min_chars)。

        provider 存在时以其为准（运行中动态生效）；provider 失败回退构造时
        的静态值，保证判定永远不会因设置读取失败而停摆。
        """
        if self.value_gate_config_provider is not None:
            try:
                enabled, min_turns, min_chars = self.value_gate_config_provider()
                return bool(enabled), max(int(min_turns), 0), max(int(min_chars), 0)
            except Exception:
                pass
        return self.value_gate_enabled, self.value_gate_min_turns, self.value_gate_min_chars

    def _record_value_gate_skip(self, source_id: str, result: Any, gate: Any) -> None:
        """Append a value-gate skip to the bounded JSONL audit trail.

        红线（B1）：绝不静默丢弃——每个被拒会话都留下可查记录（来源、原因、
        规模），主人可按来源重扫撤销；审计失败绝不阻断采集。
        """
        append_value_gate_audit(
            self.snapshot.raw_root,
            {
                "skipped_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                "source_id": source_id,
                "raw_id": result.raw_id,
                "relative_path": result.relative_path,
                "reason": gate.reason,
                "message_count": gate.message_count,
                "total_chars": gate.total_chars,
            },
        )

    @staticmethod
    def _sentinel(result: Any) -> str:
        stat = result.stat_after
        return f"{stat.size}:{stat.mtime_ns}:{int(stat.inode or 0)}:{int(getattr(stat, 'mode', 0) or 0)}"

    @staticmethod
    def _path_sentinel(path: Path) -> str:
        stat = path.lstat()
        if not path.is_file() or path.is_symlink():
            return ""
        sentinel = f"{stat.st_size}:{stat.st_mtime_ns}:{int(getattr(stat, 'st_ino', 0) or 0)}:{int(stat.st_mode)}"
        # SQLite WAL：主库文件在 checkpoint 前不反映最新提交；WAL 的体积/时间
        # 变化必须进入哨兵，否则 WAL 模式数据库源（如 ZCode 会话库）永远
        # 被当作未变化而跳过采集。
        try:
            wal_stat = path.with_name(path.name + "-wal").lstat()
            if wal_stat.st_size:
                sentinel += f":wal{wal_stat.st_size}:{wal_stat.st_mtime_ns}"
        except OSError:
            pass
        return sentinel

    @staticmethod
    def _sentinel_matches(stored: str, current: str) -> bool:
        """Compare sentinels across the pre-mode checkpoint format.

        New sentinels carry ``size:mtime_ns:inode:mode``; checkpoints written
        before the mode segment only have three segments, so they compare on
        their common prefix and an unchanged file stays completed instead of
        being re-admitted once after an upgrade. Any other shape (empty,
        truncated, malformed) is treated as changed, which is the safe
        direction: it re-admits rather than silently skipping.
        """
        if not stored or not current:
            return False
        stored_segments = stored.split(":")
        current_segments = current.split(":")
        if len(stored_segments) == 3:
            stored_segments = stored_segments[:3]
            current_segments = current_segments[:3]
        return stored_segments == current_segments


    @staticmethod
    def _updated_at() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @staticmethod
    def _scan(row: dict[str, Any]) -> ScanRun:
        return ScanRun(
            scan_id=row["scan_id"],
            source_id=row["source_id"],
            status=row["status"],
            cursor=row.get("cursor"),
            progress=int(row.get("progress") or 0),
            total=int(row["total"]) if row.get("total") is not None else None,
            last_error=row.get("last_error"),
            recovery_token=row.get("recovery_token"),
            source_sentinel=row.get("source_sentinel"),
            lease_id=row.get("lease_id"),
            attempt=int(row.get("attempt") or 0),
            queued=(
                int(row["queued_count"])
                if row.get("queued_count") is not None
                else None
            ),
            reused=(
                int(row["reused_count"])
                if row.get("reused_count") is not None
                else None
            ),
            counts_present=tuple(
                key
                for key, value in (
                    ("queued", row.get("queued_count")),
                    ("reused", row.get("reused_count")),
                )
                if value is not None
            ),
            updated_at=row.get("updated_at"),
        )


__all__ = [
    "CheckpointStore",
    "ResumeToken",
    "SnapshotJobRunner",
    "VALUE_GATE_SKIPPED_STATUS",
    "append_value_gate_audit",
    "read_value_gate_audit",
    "value_gate_audit_path",
]
