from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable, Literal, Mapping, Sequence

from src.storage.state_db import StateDatabase

from .models import ExecutionEvent, Failure, NextAction, Outcome, PendingAction, WorkItem

# 指纹剥离的是易变部分（路径、任务号、时间戳、哈希、裸数字），保留错误类别，
# 否则同一持久故障会因文件名/时间不同而无法聚合成一行。
_FAILURE_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bLJ-JOB-[0-9A-Za-z]+\b"),
    re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"),
    re.compile(r"(?:[A-Za-z]:)?[^\s'\"，。；;()（）]*[/\\][^\s'\"，。；;()（）]*"),
    re.compile(r"\b[0-9a-fA-F]{16,}\b"),
)

# 命中即把失败路由给主人（PendingAction actor="owner"）；顺序即优先级。
_OWNER_HINT_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("no approved extraction adapter", "no approved adapter", "adapter not approved"),
        "该来源缺少可用的提取适配器：可在来源页停用该来源，或等待新版本支持后再启用。",
    ),
    (
        ("size limit", "too large", "storage limit reached", "超限", "过大"),
        "来源文件超出大小限制：可在来源页移除或拆分过大文件，或等待版本放宽限制。",
    ),
    (
        ("unsupported", "malformed", "not valid", "invalid json", "invalid format", "无法解析", "格式错误", "配置"),
        "来源内容或配置当前无法处理：请检查该来源的格式与设置，或在来源页停用该来源。",
    ),
)

_FAILURE_EVIDENCE_LIMIT = 10

# work_items 的聚合状态：该行的失败事实已并入同来源聚合代表行，投影层不再单列。
# 保留行本身（而不是物理删除）以维持 execution_events / work_outcomes / 待办的
# 引用完整性；重试该行仍可正常复活为 retrying/completed。
MERGED_WORK_STATUS = "merged"

_AGGREGATED_TITLE_SUFFIX = "（历史失败已聚合，共 {count} 次扫描）"
_AGGREGATED_TITLE_PATTERN = re.compile(r"（历史失败已聚合，共 \d+ 次扫描）$")


def normalize_failure_reason(reason: str) -> str:
    """Collapse one failure text into its stable category for fingerprinting."""
    text = str(reason or "")
    for pattern in _FAILURE_NOISE_PATTERNS:
        text = pattern.sub(" ", text)
    text = re.sub(r"\b\d+\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text or "unknown failure"


def failure_key_for(source_id: str, stage: str, normalized_reason: str) -> str:
    """failure_key = sha256(source_id, stage, normalized_reason)[:16]."""
    material = "\x00".join((str(source_id or ""), str(stage or ""), str(normalized_reason or "")))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def classify_failure_action(reason: str, retryable: bool) -> tuple[str, str]:
    """Return (actor, owner_hint). "system" failures must never enter 需要我."""
    if retryable:
        return "system", ""
    text = str(reason or "").lower()
    for needles, hint in _OWNER_HINT_RULES:
        if any(needle in text for needle in needles):
            return "owner", hint
    return "system", ""


def _merge_bounded(existing: Any, incoming: Iterable[str], limit: int) -> list[str]:
    merged = [str(item) for item in (existing or []) if str(item or "").strip()][:limit]
    for item in incoming:
        text = str(item or "").strip()
        if text and text not in merged:
            merged.append(text)
    return merged[:limit]


class WorkStore:
    """Durable Work Fact persistence backed by the existing StateDatabase."""

    def __init__(self, state: StateDatabase):
        self.state = state
        self._init_tables()

    def _init_tables(self) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS work_items (
                    work_id TEXT PRIMARY KEY, title TEXT NOT NULL, source_id TEXT,
                    status TEXT NOT NULL, owner_approved INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS execution_events (
                    event_id TEXT PRIMARY KEY, work_id TEXT NOT NULL, event_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS work_outcomes (
                    work_id TEXT PRIMARY KEY, status TEXT NOT NULL, summary TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '{}', created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS work_next_actions (
                    work_id TEXT PRIMARY KEY, action_id TEXT NOT NULL, description TEXT NOT NULL,
                    actor TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pending_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, work_id TEXT NOT NULL,
                    description TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0,
                    action_id TEXT, actor TEXT NOT NULL DEFAULT 'owner', created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS work_failures (
                    failure_id TEXT PRIMARY KEY, work_id TEXT NOT NULL, stage TEXT NOT NULL,
                    reason TEXT NOT NULL, retryable INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
                    failure_key TEXT, source_id TEXT, occurrence_count INTEGER NOT NULL DEFAULT 1,
                    first_seen_at TEXT, last_seen_at TEXT, detail_json TEXT NOT NULL DEFAULT '{}',
                    requires_owner INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            for table, columns in {
                "work_items": {"updated_at": "TEXT"},
                "work_outcomes": {"created_at": "TEXT"},
                "pending_actions": {"action_id": "TEXT", "actor": "TEXT NOT NULL DEFAULT 'owner'", "created_at": "TEXT"},
                "work_failures": {
                    "failure_key": "TEXT",
                    "source_id": "TEXT",
                    "occurrence_count": "INTEGER NOT NULL DEFAULT 1",
                    "first_seen_at": "TEXT",
                    "last_seen_at": "TEXT",
                    "detail_json": "TEXT NOT NULL DEFAULT '{}'",
                    "requires_owner": "INTEGER NOT NULL DEFAULT 0",
                },
            }.items():
                present = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
                for name, definition in columns.items():
                    if name not in present:
                        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
            connection.execute("UPDATE pending_actions SET action_id = 'legacy-' || id WHERE action_id IS NULL")
            connection.execute("UPDATE pending_actions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            connection.execute("UPDATE work_outcomes SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            duplicate_action_ids = connection.execute(
                "SELECT action_id FROM pending_actions GROUP BY action_id HAVING COUNT(*) > 1"
            ).fetchall()
            for duplicate in duplicate_action_ids:
                rows = connection.execute(
                    "SELECT id, resolved FROM pending_actions WHERE action_id = ? ORDER BY resolved ASC, id ASC",
                    (duplicate[0],),
                ).fetchall()
                for row in rows[1:]:
                    connection.execute("DELETE FROM pending_actions WHERE id = ?", (row[0],))
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_actions_action_id_unique ON pending_actions(action_id)"
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_work_failures_failure_key ON work_failures(failure_key)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_work_failures_source_recent ON work_failures(source_id, last_seen_at)")
            self._merge_legacy_failure_rows(connection)
            self._merge_legacy_failed_work_items(connection)
        self.reconcile_extraction_jobs()

    @staticmethod
    def _merge_legacy_failure_rows(connection: sqlite3.Connection) -> None:
        """One-time collapse of pre-aggregation rows: same source+stage+reason keeps one row.

        聚合上线前，同一持久故障被逐扫描写成大量 work_failures 行；此处把它们合并成
        聚合口径（计数=合并行数），否则历史库的失败数字永远停留在膨胀值。
        """
        stale = connection.execute(
            """
            SELECT rowid, failure_id, work_id, stage, reason, created_at
            FROM work_failures
            WHERE failure_key IS NULL OR failure_key = ''
            """
        ).fetchall()
        if not stale:
            return
        sources = {
            str(row[0] or ""): str(row[1] or "")
            for row in connection.execute("SELECT work_id, source_id FROM work_items").fetchall()
        }
        groups: dict[str, list[sqlite3.Row]] = {}
        for row in stale:
            key = failure_key_for(
                sources.get(str(row["work_id"]), ""),
                str(row["stage"]),
                normalize_failure_reason(str(row["reason"])),
            )
            groups.setdefault(key, []).append(row)
        for key, rows in groups.items():
            rows.sort(key=lambda item: (str(item["created_at"] or ""), int(item["rowid"])))
            keep = rows[-1]
            connection.execute(
                """
                UPDATE work_failures
                SET failure_key = ?, source_id = ?, occurrence_count = ?,
                    first_seen_at = ?, last_seen_at = ?
                WHERE failure_id = ?
                """,
                (key, sources.get(str(keep["work_id"]), ""), len(rows), rows[0]["created_at"], keep["created_at"], keep["failure_id"]),
            )
            for row in rows[:-1]:
                connection.execute("DELETE FROM work_failures WHERE failure_id = ?", (row["failure_id"],))

    @staticmethod
    def _merge_legacy_failed_work_items(connection: sqlite3.Connection) -> None:
        """One-time backfill: collapse historical per-scan failed work_items by source.

        work_failures 聚合上线之前，同一持久故障源每次扫描都会新写一行 failed
        work_item（生产库曾积压 1,297 行，主要是 codex_rollout 缺适配器），主人的
        工作履历因此整屏红字。此处按 source_id 从宽归组（标题不含原因指纹，无法
        更细分）：每组保留最早创建的一行为聚合代表（标题标注聚合次数，updated_at
        刷新为组内最新），其余行改为 merged 状态，投影层不再展示。completed /
        accepted / running 等其他状态的行永不参与；某来源只剩一行 failed 时自然
        跳过，这正是幂等条件——重开数据库不会重复执行。
        """
        sources = connection.execute(
            """
            SELECT source_id FROM work_items
            WHERE status = 'failed' AND source_id IS NOT NULL AND TRIM(source_id) <> ''
            GROUP BY source_id HAVING COUNT(*) > 1
            """
        ).fetchall()
        for row in sources:
            WorkStore._converge_failed_work_items(connection, str(row[0]))

    @staticmethod
    def _converge_failed_work_items(connection: sqlite3.Connection, source_id: str) -> dict[str, Any] | None:
        """Collapse one source's failed work_items into the earliest representative row.

        启动迁移与运行期新失败落账共用：运行期在 failed 迁移写入后立即收敛，保证
        持久失败源不会随扫描次数无界新增 failed 行。只朝行数减少的方向工作，绝不
        触碰 completed / accepted 等非 failed 行。返回归并说明；无可归并时返回 None。
        """
        resolved_source = str(source_id or "").strip()
        if not resolved_source:
            return None
        rows = connection.execute(
            """
            SELECT work_id, title, created_at, updated_at FROM work_items
            WHERE source_id = ? AND status = 'failed'
            ORDER BY created_at ASC, rowid ASC
            """,
            (resolved_source,),
        ).fetchall()
        if len(rows) < 2:
            return None
        keep = rows[0]
        represented = int(
            connection.execute(
                "SELECT COUNT(*) FROM work_items WHERE source_id = ? AND status IN ('failed', 'merged')",
                (resolved_source,),
            ).fetchone()[0]
        )
        base_title = _AGGREGATED_TITLE_PATTERN.sub("", str(keep["title"] or "")).strip() or "扫描失败"
        latest = max(str(row["updated_at"] or row["created_at"] or "") for row in rows)
        connection.execute(
            "UPDATE work_items SET title = ?, updated_at = ? WHERE work_id = ?",
            (base_title + _AGGREGATED_TITLE_SUFFIX.format(count=represented), latest, keep["work_id"]),
        )
        connection.execute(
            "UPDATE work_items SET status = ? WHERE source_id = ? AND status = 'failed' AND work_id <> ?",
            (MERGED_WORK_STATUS, resolved_source, keep["work_id"]),
        )
        WorkStore._append_merge_audit(
            connection,
            source_id=resolved_source,
            before_rows=len(rows),
            after_rows=1,
            merged_rows=len(rows) - 1,
            represented_scans=represented,
            representative_work_id=str(keep["work_id"]),
            created_at=latest,
        )
        return {
            "source_id": resolved_source,
            "merged_rows": len(rows) - 1,
            "represented_scans": represented,
            "representative_work_id": str(keep["work_id"]),
        }

    @staticmethod
    def _append_merge_audit(
        connection: sqlite3.Connection,
        *,
        source_id: str,
        before_rows: int,
        after_rows: int,
        merged_rows: int,
        represented_scans: int,
        representative_work_id: str,
        created_at: str,
    ) -> None:
        """归并必须留全局审计（来源、前后行数、合并行数、代表 work_id）。

        stable_event_id 含前后行数与时间戳：同一次归并天然只发生一次（归并后条件
        即消失），再次归并是新事实，应当留下新事件而不是被幂等规则吞掉。
        """
        stable_event_id = f"work-failed-items-merged:{source_id}:{before_rows}:{created_at}"
        if connection.execute("SELECT 1 FROM events WHERE stable_event_id = ? LIMIT 1", (stable_event_id,)).fetchone():
            return
        connection.execute(
            """
            INSERT INTO events(event_type, entity_type, entity_id, payload_json, created_at, stable_event_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "work.failed_items_merged",
                "work_item",
                source_id,
                json.dumps(
                    {
                        "source_id": source_id,
                        "before_failed_rows": before_rows,
                        "after_failed_rows": after_rows,
                        "merged_rows": merged_rows,
                        "represented_scans": represented_scans,
                        "representative_work_id": representative_work_id,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                created_at,
                stable_event_id,
            ),
        )

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _work(row: Any) -> WorkItem:
        return WorkItem(work_id=row[0], title=row[1], source_id=row[2], status=row[3], owner_approved=bool(row[4]), created_at=row[5], updated_at=row[6])

    def create_work(self, item: WorkItem) -> WorkItem:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("INSERT OR IGNORE INTO work_items(work_id, title, source_id, status, owner_approved, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (item.work_id, item.title, item.source_id, item.status, int(item.owner_approved), item.created_at, item.updated_at or item.created_at))
            row = connection.execute("SELECT work_id, title, source_id, status, owner_approved, created_at, updated_at FROM work_items WHERE work_id = ?", (item.work_id,)).fetchone()
        return self._work(row)

    def get_work(self, work_id: str) -> WorkItem | None:
        with self.state._connection() as connection:
            row = connection.execute("SELECT work_id, title, source_id, status, owner_approved, created_at, updated_at FROM work_items WHERE work_id = ?", (work_id,)).fetchone()
        return self._work(row) if row else None

    def get_work_by_source_id(self, source_id: str) -> WorkItem | None:
        with self.state._connection() as connection:
            # merged 行不再是该来源的活跃代表，崩溃重放定位工作时跳过它们，
            # 避免把已并入聚合的行重新翻回 failed。
            row = connection.execute(
                "SELECT work_id, title, source_id, status, owner_approved, created_at, updated_at FROM work_items WHERE source_id = ? AND status <> 'merged' ORDER BY created_at LIMIT 1",
                (source_id,),
            ).fetchone()
        return self._work(row) if row else None

    def touch_work(self, work_id: str, *, updated_at: str | None = None) -> bool:
        """Refresh an active work fact without appending an activity event."""
        timestamp = updated_at or datetime.now(timezone.utc).isoformat(timespec="microseconds")
        with self.state._lock, self.state._connection() as connection:
            cursor = connection.execute(
                "UPDATE work_items SET updated_at = ? WHERE work_id = ? AND status IN ('accepted', 'running', 'retrying')",
                (timestamp, str(work_id)),
            )
        return cursor.rowcount == 1

    def append_event(self, event: ExecutionEvent) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("INSERT OR IGNORE INTO execution_events(event_id, work_id, event_type, detail_json, created_at) VALUES (?, ?, ?, ?, ?)", (event.event_id, event.work_id, event.event_type, self._json(event.detail), event.created_at))
            connection.execute("UPDATE work_items SET updated_at = ? WHERE work_id = ?", (event.created_at, event.work_id))

    def save_outcome(self, outcome: Outcome) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("INSERT INTO work_outcomes(work_id, status, summary, evidence_json, created_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(work_id) DO UPDATE SET status=excluded.status, summary=excluded.summary, evidence_json=excluded.evidence_json, created_at=excluded.created_at", (outcome.work_id, outcome.status, outcome.summary, self._json(outcome.evidence), outcome.created_at))

    def get_outcome(self, work_id: str) -> Outcome | None:
        with self.state._connection() as connection:
            row = connection.execute("SELECT status, summary, evidence_json, created_at FROM work_outcomes WHERE work_id = ?", (work_id,)).fetchone()
        return Outcome(work_id=work_id, status=row[0], summary=row[1], evidence=json.loads(row[2] or "{}"), created_at=row[3] or "") if row else None

    def save_next_action(self, action: NextAction) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("INSERT INTO work_next_actions(work_id, action_id, description, actor, created_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(work_id) DO UPDATE SET action_id=excluded.action_id, description=excluded.description, actor=excluded.actor, created_at=excluded.created_at", (action.work_id, action.action_id, action.description, action.actor, action.created_at))

    def get_next_action(self, work_id: str) -> NextAction | None:
        with self.state._connection() as connection:
            row = connection.execute("SELECT action_id, description, actor, created_at FROM work_next_actions WHERE work_id = ?", (work_id,)).fetchone()
        return NextAction(work_id=work_id, action_id=row[0], description=row[1], actor=row[2], created_at=row[3]) if row else None

    def save_failure(self, failure: Failure) -> None:
        with self.state._lock, self.state._connection() as connection:
            self._upsert_failure_record(
                connection,
                work_id=failure.work_id,
                stage=failure.stage,
                reason=failure.reason,
                retryable=failure.retryable,
                occurred_at=failure.created_at,
            )

    def get_failure(self, work_id: str) -> Failure | None:
        with self.state._connection() as connection:
            row = connection.execute(
                """
                SELECT failure_id, stage, reason, retryable, created_at, failure_key, source_id,
                       occurrence_count, first_seen_at, last_seen_at, detail_json
                FROM work_failures WHERE work_id = ? ORDER BY created_at DESC LIMIT 1
                """,
                (work_id,),
            ).fetchone()
            if row is None:
                # 聚合后失败行挂在首次/最近一次失败的 work 上；同来源的其他失败工作
                # 通过 source_id 取回同一条聚合事实，而不是显示成"无失败明细"。
                source_row = connection.execute("SELECT source_id FROM work_items WHERE work_id = ?", (work_id,)).fetchone()
                source_id = str(source_row[0] or "").strip() if source_row else ""
                if source_id:
                    row = connection.execute(
                        """
                        SELECT failure_id, stage, reason, retryable, created_at, failure_key, source_id,
                               occurrence_count, first_seen_at, last_seen_at, detail_json
                        FROM work_failures WHERE source_id = ?
                        ORDER BY COALESCE(last_seen_at, created_at) DESC LIMIT 1
                        """,
                        (source_id,),
                    ).fetchone()
        if not row:
            return None
        try:
            detail = json.loads(row[10] or "{}")
        except json.JSONDecodeError:
            detail = {}
        return Failure(
            work_id=work_id,
            failure_id=row[0],
            stage=row[1],
            reason=row[2],
            retryable=bool(row[3]),
            created_at=row[4],
            failure_key=str(row[5] or ""),
            source_id=str(row[6] or ""),
            occurrence_count=int(row[7] or 1),
            first_seen_at=str(row[8] or ""),
            last_seen_at=str(row[9] or ""),
            detail=detail if isinstance(detail, dict) else {},
        )

    def list_failure_records(self, limit: int = 50, *, source_id: str | None = None) -> list[dict[str, Any]]:
        """Aggregated failure ledger: one row per source+stage+reason fingerprint."""
        if int(limit) < 1:
            raise ValueError("limit must be positive")
        query = """
            SELECT failure_id, work_id, stage, reason, retryable, created_at, failure_key, source_id,
                   occurrence_count, first_seen_at, last_seen_at, detail_json, requires_owner
            FROM work_failures
        """
        params: list[Any] = []
        if source_id:
            query += " WHERE source_id = ?"
            params.append(str(source_id))
        query += " ORDER BY COALESCE(last_seen_at, created_at) DESC LIMIT ?"
        params.append(int(limit))
        with self.state._connection() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            try:
                detail = json.loads(row[11] or "{}")
            except json.JSONDecodeError:
                detail = {}
            records.append({
                "failure_id": row[0],
                "work_id": row[1],
                "stage": row[2],
                "reason": row[3],
                "retryable": bool(row[4]),
                "created_at": row[5],
                "failure_key": str(row[6] or ""),
                "source_id": str(row[7] or ""),
                "occurrence_count": int(row[8] or 1),
                "first_seen_at": str(row[9] or ""),
                "last_seen_at": str(row[10] or ""),
                "requires_owner": bool(row[12]),
                "detail": detail if isinstance(detail, dict) else {},
            })
        return records

    def count_failure_records(self) -> int:
        """失败对账口径：聚合后的持久失败条数，不是逐扫描逐文件的行数。"""
        with self.state._connection() as connection:
            row = connection.execute("SELECT COUNT(*) FROM work_failures").fetchone()
        return int(row[0] or 0)

    def record_source_failure(
        self,
        work_id: str,
        *,
        stage: str,
        reason: str,
        retryable: bool = False,
        source_id: str | None = None,
        source_title: str | None = None,
        files: Sequence[str] = (),
        job_ids: Sequence[str] = (),
        raw_error: str | None = None,
        attempts: int | None = None,
        occurred_at: str | None = None,
    ) -> dict[str, Any]:
        """Aggregate one failure occurrence by source+stage+reason and route its actor.

        同一 failure_key 只递增计数并刷新有界 evidence，不新增行；owner 类失败维护
        恰好一条未完成 PendingAction（确定性 action_id，重复出现只更新）。
        """
        normalized = normalize_failure_reason(reason)
        actor, owner_hint = classify_failure_action(reason, retryable)
        timestamp = occurred_at or datetime.now(timezone.utc).isoformat(timespec="microseconds")
        incoming_files = [str(item or "").strip() for item in files if str(item or "").strip()]
        incoming_job_ids = [str(item or "").strip() for item in job_ids if str(item or "").strip()]
        with self.state._lock, self.state._connection() as connection:
            resolved_source = str(source_id or "").strip()
            resolved_title = str(source_title or "").strip()
            if not resolved_source or not resolved_title:
                work_row = connection.execute(
                    "SELECT source_id, title FROM work_items WHERE work_id = ?", (work_id,)
                ).fetchone()
                if work_row is not None:
                    resolved_source = resolved_source or str(work_row[0] or "").strip()
                    resolved_title = resolved_title or str(work_row[1] or "").strip()
            key = failure_key_for(resolved_source, stage, normalized)
            existing = connection.execute(
                "SELECT occurrence_count, detail_json FROM work_failures WHERE failure_key = ?",
                (key,),
            ).fetchone()
            detail: dict[str, Any] = {}
            if existing is not None:
                try:
                    loaded = json.loads(existing["detail_json"] or "{}")
                    detail = dict(loaded) if isinstance(loaded, dict) else {}
                except json.JSONDecodeError:
                    detail = {}
            detail["files"] = _merge_bounded(detail.get("files"), incoming_files, _FAILURE_EVIDENCE_LIMIT)
            detail["job_ids"] = _merge_bounded(detail.get("job_ids"), incoming_job_ids, _FAILURE_EVIDENCE_LIMIT)
            detail["file_count"] = max(int(detail.get("file_count") or 0), len(incoming_files), len(detail["files"]))
            detail["job_count"] = max(int(detail.get("job_count") or 0), len(incoming_job_ids), len(detail["job_ids"]))
            try:
                attempt_value = int(attempts) if attempts is not None else 0
            except (TypeError, ValueError):
                attempt_value = 0
            detail["attempts_max"] = max(int(detail.get("attempts_max") or 0), attempt_value)
            detail["raw_error"] = (str(raw_error or "").strip() or str(detail.get("raw_error") or ""))[:500]
            detail["source_title"] = resolved_title or str(detail.get("source_title") or "")
            detail["owner_hint"] = owner_hint or str(detail.get("owner_hint") or "")
            detail["last_work_id"] = str(work_id)
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO work_failures(
                        failure_id, work_id, stage, reason, retryable, created_at,
                        failure_key, source_id, occurrence_count, first_seen_at, last_seen_at,
                        detail_json, requires_owner
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                    """,
                    (
                        f"failure-agg:{key}", work_id, stage, str(reason or "")[:2000], int(retryable), timestamp,
                        key, resolved_source, timestamp, timestamp, self._json(detail), int(actor == "owner"),
                    ),
                )
                occurrences = 1
                self._append_failure_audit(
                    connection,
                    failure_key=key,
                    source_id=resolved_source,
                    stage=stage,
                    reason=reason,
                    normalized=normalized,
                    occurrences=occurrences,
                    actor=actor,
                    files=detail["files"],
                    created_at=timestamp,
                )
            else:
                occurrences = int(existing["occurrence_count"] or 1) + 1
                connection.execute(
                    """
                    UPDATE work_failures
                    SET last_seen_at = ?, occurrence_count = ?, detail_json = ?, reason = ?,
                        retryable = ?, requires_owner = ?, work_id = ?
                    WHERE failure_key = ?
                    """,
                    (timestamp, occurrences, self._json(detail), str(reason or "")[:2000], int(retryable), int(actor == "owner"), work_id, key),
                )
            if actor == "owner":
                self._upsert_owner_pending_action(
                    connection,
                    failure_key=key,
                    work_id=work_id,
                    hint=owner_hint,
                    occurrences=occurrences,
                    timestamp=timestamp,
                )
        return {
            "failure_key": key,
            "source_id": resolved_source,
            "stage": stage,
            "occurrences": occurrences,
            "actor": actor,
            "requires_owner": actor == "owner",
        }

    @staticmethod
    def _upsert_owner_pending_action(
        connection: sqlite3.Connection,
        *,
        failure_key: str,
        work_id: str,
        hint: str,
        occurrences: int,
        timestamp: str,
    ) -> None:
        action_id = f"failure-owner:{failure_key}"
        description = hint if occurrences <= 1 else f"{hint}（已累计 {occurrences} 次）"
        row = connection.execute("SELECT id, resolved FROM pending_actions WHERE action_id = ?", (action_id,)).fetchone()
        if row is None:
            connection.execute(
                "INSERT INTO pending_actions(work_id, description, resolved, action_id, actor, created_at) VALUES (?, ?, 0, ?, 'owner', ?)",
                (work_id, description, action_id, timestamp),
            )
        elif int(row["resolved"] or 0) == 0:
            # 同 key 未完成的待办只更新，不重复创建；已解决的保持解决状态。
            connection.execute(
                "UPDATE pending_actions SET work_id = ?, description = ?, created_at = ? WHERE id = ?",
                (work_id, description, timestamp, row["id"]),
            )

    @staticmethod
    def _append_failure_audit(
        connection: sqlite3.Connection,
        *,
        failure_key: str,
        source_id: str,
        stage: str,
        reason: str,
        normalized: str,
        occurrences: int,
        actor: str,
        files: list[str],
        created_at: str,
    ) -> None:
        """一次性的全局审计事件（stable_event_id 幂等）；后续重复计入聚合行本身。"""
        stable_event_id = f"work-failure-aggregated:{failure_key}"
        if connection.execute("SELECT 1 FROM events WHERE stable_event_id = ? LIMIT 1", (stable_event_id,)).fetchone():
            return
        connection.execute(
            """
            INSERT INTO events(event_type, entity_type, entity_id, payload_json, created_at, stable_event_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "work.failure_aggregated",
                "work_failure",
                source_id or None,
                json.dumps({
                    "failure_key": failure_key,
                    "stage": stage,
                    "reason": str(reason or "")[:500],
                    "normalized_reason": normalized,
                    "occurrences": occurrences,
                    "actor": actor,
                    "files": files[:_FAILURE_EVIDENCE_LIMIT],
                }, ensure_ascii=False, sort_keys=True),
                created_at,
                stable_event_id,
            ),
        )

    def _upsert_failure_record(
        self,
        connection: sqlite3.Connection,
        *,
        work_id: str,
        stage: str,
        reason: str,
        retryable: bool,
        occurred_at: str,
    ) -> None:
        """Aggregate the durable failure row by source+stage+reason (transition path)."""
        work_row = connection.execute("SELECT source_id FROM work_items WHERE work_id = ?", (work_id,)).fetchone()
        source_id = str(work_row[0] or "").strip() if work_row is not None else ""
        key = failure_key_for(source_id, stage, normalize_failure_reason(reason))
        existing = connection.execute("SELECT failure_id FROM work_failures WHERE failure_key = ?", (key,)).fetchone()
        if existing is None:
            connection.execute(
                """
                INSERT INTO work_failures(
                    failure_id, work_id, stage, reason, retryable, created_at,
                    failure_key, source_id, occurrence_count, first_seen_at, last_seen_at, detail_json, requires_owner
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, '{}', 0)
                """,
                (f"failure-agg:{key}", work_id, stage, str(reason or "")[:2000], int(retryable), occurred_at, key, source_id, occurred_at, occurred_at),
            )
        else:
            connection.execute(
                "UPDATE work_failures SET last_seen_at = ?, occurrence_count = occurrence_count + 1, work_id = ? WHERE failure_key = ?",
                (occurred_at, work_id, key),
            )

    def add_pending_action(self, action: PendingAction) -> None:
        with self.state._lock, self.state._connection() as connection:
            existing = connection.execute("SELECT id FROM pending_actions WHERE action_id = ? LIMIT 1", (action.action_id,)).fetchone()
            if existing:
                connection.execute(
                    "UPDATE pending_actions SET work_id = ?, description = ?, resolved = ?, actor = ?, created_at = ? WHERE id = ?",
                    (action.work_id, action.description, int(action.resolved), action.actor, action.created_at, existing[0]),
                )
                return
            connection.execute("INSERT INTO pending_actions(work_id, description, resolved, action_id, actor, created_at) VALUES (?, ?, ?, ?, ?, ?)", (action.work_id, action.description, int(action.resolved), action.action_id, action.actor, action.created_at))

    def resolve_pending(self, work_id: str) -> None:
        with self.state._lock, self.state._connection() as connection:
            connection.execute("UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0", (work_id,))

    def get_pending_action(self, action_id: str) -> PendingAction | None:
        """Return one pending action, including a previously resolved action."""
        with self.state._connection() as connection:
            row = connection.execute(
                "SELECT action_id, work_id, description, resolved, actor, created_at FROM pending_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        if not row:
            return None
        return PendingAction(
            action_id=row[0],
            work_id=row[1],
            description=row[2],
            resolved=bool(row[3]),
            actor=row[4] or "owner",
            created_at=row[5] or "",
        )

    def resolve_pending_action(self, action_id: str) -> PendingAction:
        """Resolve one durable action and return its resulting state.

        Repeating the same request is deliberately idempotent; an unknown ID is
        not converted into a fake success.
        """
        with self.state._lock, self.state._connection() as connection:
            row = connection.execute(
                "SELECT action_id, work_id, description, resolved, actor, created_at FROM pending_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if not row:
                raise LookupError(f"Unknown pending action: {action_id}")
            connection.execute(
                "UPDATE pending_actions SET resolved = 1 WHERE action_id = ? AND resolved = 0",
                (action_id,),
            )
            # A resolved owner action must not remain the next actor, but a
            # newer system action for the same work must survive unchanged.
            connection.execute(
                "DELETE FROM work_next_actions WHERE work_id = ? AND action_id = ? AND actor = 'owner'",
                (row[1], action_id),
            )
        return PendingAction(
            action_id=row[0],
            work_id=row[1],
            description=row[2],
            resolved=True,
            actor=row[4] or "owner",
            created_at=row[5] or "",
        )

    @staticmethod
    def _parse_transition_time(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _transition_rank(phase: str) -> int:
        return {"retrying": 1, "failed": 2, "completed": 3}[phase]

    def apply_extraction_transition(
        self,
        work_id: str,
        phase: Literal["retrying", "completed", "failed"],
        *,
        summary: str,
        evidence: Mapping[str, Any],
        stage: str = "extraction",
        retryable: bool = False,
        occurred_at: str | None = None,
        skip_failure_record: bool = False,
    ) -> None:
        """Apply one idempotent extraction lifecycle transition atomically.

        skip_failure_record：调用方已通过 record_source_failure 写入聚合失败行时，
        跳过这里的默认聚合写，避免同一失败按两条不同指纹重复入账。
        """
        if phase not in {"retrying", "completed", "failed"}:
            raise ValueError(f"Unsupported extraction transition: {phase}")
        timestamp = occurred_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        incoming_time = self._parse_transition_time(timestamp)
        with self.state._lock, self.state._connection() as connection:
            if not connection.execute("SELECT 1 FROM work_items WHERE work_id = ?", (work_id,)).fetchone():
                raise LookupError(f"Unknown work item: {work_id}")

            outcome_row = connection.execute(
                "SELECT status, summary, evidence_json, created_at FROM work_outcomes WHERE work_id = ?",
                (work_id,),
            ).fetchone()
            current_phase: str | None = str(outcome_row[0]) if outcome_row else None
            current_timestamp = str(outcome_row[3] or "") if outcome_row else ""
            if current_phase not in {"failed", "completed"}:
                current_phase = None
            if current_phase is None:
                candidates: list[tuple[datetime, int, str, str, str]] = []
                for event in connection.execute(
                    """
                    SELECT event_id, event_type, created_at
                    FROM execution_events
                    WHERE work_id = ? AND event_type IN ('work.retrying', 'work.failed', 'extraction.completed')
                    """,
                    (work_id,),
                ).fetchall():
                    event_phase = {
                        "work.retrying": "retrying",
                        "work.failed": "failed",
                        "extraction.completed": "completed",
                    }[str(event[1])]
                    event_time = self._parse_transition_time(str(event[2] or ""))
                    if event_time is not None:
                        candidates.append((event_time, self._transition_rank(event_phase), str(event[0]), event_phase, str(event[2] or "")))
                if candidates:
                    _event_time, _rank, _event_id, current_phase, current_timestamp = max(candidates)

            current_time = self._parse_transition_time(current_timestamp)
            if current_time is not None and incoming_time is None:
                return
            if current_time is not None and incoming_time is not None:
                if incoming_time < current_time:
                    return
                if incoming_time == current_time and current_phase is not None:
                    if self._transition_rank(phase) < self._transition_rank(current_phase):
                        return

            evidence_json = self._json(dict(evidence))
            if phase == "retrying":
                connection.execute("DELETE FROM work_outcomes WHERE work_id = ?", (work_id,))
                connection.execute(
                    "UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0 AND (action_id IS NULL OR action_id NOT LIKE 'failure-owner:%')",
                    (work_id,),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO execution_events(event_id, work_id, event_type, detail_json, created_at)
                    VALUES (?, ?, 'work.retrying', ?, ?)
                    """,
                    (f"work:{work_id}:retrying", work_id, self._json({"summary": summary, "evidence": dict(evidence), "actor": "system"}), timestamp),
                )
                connection.execute(
                    """
                    INSERT INTO work_next_actions(work_id, action_id, description, actor, created_at)
                    VALUES (?, ?, ?, 'system', ?)
                    ON CONFLICT(work_id) DO UPDATE SET action_id=excluded.action_id, description=excluded.description, actor=excluded.actor, created_at=excluded.created_at
                    """,
                    (work_id, f"next:{work_id}:retrying", "系统自动重试提取", timestamp),
                )
            elif phase == "completed":
                connection.execute(
                    """
                    INSERT INTO work_outcomes(work_id, status, summary, evidence_json, created_at)
                    VALUES (?, 'completed', ?, ?, ?)
                    ON CONFLICT(work_id) DO UPDATE SET status='completed', summary=excluded.summary, evidence_json=excluded.evidence_json, created_at=excluded.created_at
                    """,
                    (work_id, summary, evidence_json, timestamp),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO execution_events(event_id, work_id, event_type, detail_json, created_at)
                    VALUES (?, ?, 'extraction.completed', ?, ?)
                    """,
                    (f"work:{work_id}:extraction.completed", work_id, self._json({"summary": summary, "evidence": dict(evidence)}), timestamp),
                )
                connection.execute("UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0", (work_id,))
                # 该来源恢复可提取后，历史失败留下的 owner 待办已过时，一并关闭。
                source_row = connection.execute("SELECT source_id FROM work_items WHERE work_id = ?", (work_id,)).fetchone()
                source_id = str(source_row[0] or "").strip() if source_row is not None else ""
                if source_id:
                    connection.execute(
                        """
                        UPDATE pending_actions SET resolved = 1
                        WHERE resolved = 0 AND action_id LIKE 'failure-owner:%'
                          AND work_id IN (SELECT work_id FROM work_items WHERE source_id = ?)
                        """,
                        (source_id,),
                    )
                connection.execute(
                    """
                    INSERT INTO work_next_actions(work_id, action_id, description, actor, created_at)
                    VALUES (?, ?, ?, 'system', ?)
                    ON CONFLICT(work_id) DO UPDATE SET action_id=excluded.action_id, description=excluded.description, actor=excluded.actor, created_at=excluded.created_at
                    """,
                    (work_id, f"next:{work_id}:completed", "系统继续维护可检索记忆", timestamp),
                )
            else:
                if not skip_failure_record:
                    self._upsert_failure_record(
                        connection,
                        work_id=work_id,
                        stage=stage,
                        reason=summary,
                        retryable=retryable,
                        occurred_at=timestamp,
                    )
                connection.execute(
                    """
                    INSERT INTO work_outcomes(work_id, status, summary, evidence_json, created_at)
                    VALUES (?, 'failed', ?, ?, ?)
                    ON CONFLICT(work_id) DO UPDATE SET status='failed', summary=excluded.summary, evidence_json=excluded.evidence_json, created_at=excluded.created_at
                    """,
                    (work_id, summary, evidence_json, timestamp),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO execution_events(event_id, work_id, event_type, detail_json, created_at)
                    VALUES (?, ?, 'work.failed', ?, ?)
                    """,
                    (f"work:{work_id}:failed:{stage}", work_id, self._json({"stage": stage, "reason": summary, "retryable": retryable, "evidence": dict(evidence)}), timestamp),
                )
                if retryable:
                    connection.execute(
                        "UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0 AND (action_id IS NULL OR action_id NOT LIKE 'failure-owner:%')",
                        (work_id,),
                    )
                    action_id = f"next:{work_id}:retrying"
                    description = "重试处理"
                    actor = "system"
                else:
                    # 不可重试的失败是最终事实，不是主人的待办：自动关闭旧待办，
                    # 系统接管下一步（失败明细已在处理详情/工作记录可查）。
                    # failure-owner 待办例外：它正是这条失败路由给主人的可行动待办。
                    connection.execute(
                        "UPDATE pending_actions SET resolved = 1 WHERE work_id = ? AND resolved = 0 AND (action_id IS NULL OR action_id NOT LIKE 'failure-owner:%')",
                        (work_id,),
                    )
                    action_id = f"next:{work_id}:failed-auto"
                    description = "自动记录失败原因，已保留原始文件，不影响已导入内容"
                    actor = "system"
                connection.execute(
                    """
                    INSERT INTO work_next_actions(work_id, action_id, description, actor, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(work_id) DO UPDATE SET action_id=excluded.action_id, description=excluded.description, actor=excluded.actor, created_at=excluded.created_at
                    """,
                    (work_id, action_id, description, actor, timestamp),
                )
            item_status = {
                "retrying": "retrying",
                "completed": "completed",
                "failed": "failed",
            }[phase]
            connection.execute(
                "UPDATE work_items SET status = ?, updated_at = ? WHERE work_id = ?",
                (item_status, timestamp, work_id),
            )
            if phase == "failed":
                # 新失败落账后立即按来源收敛：同来源已有失败行时，本行转为聚合代表
                # 或并入既有代表，持久故障不再随扫描次数在工作履历里逐行累积。
                failed_source_row = connection.execute(
                    "SELECT source_id FROM work_items WHERE work_id = ?", (work_id,)
                ).fetchone()
                if failed_source_row is not None:
                    self._converge_failed_work_items(connection, str(failed_source_row[0] or ""))

    def reconcile_extraction_jobs(self) -> None:
        """Replay terminal extraction facts after a crash between queue and callback."""
        try:
            with self.state._connection() as connection:
                rows = connection.execute(
                    "SELECT job_id, status, source_type, payload_json, result_json, updated_at FROM extraction_jobs WHERE status IN ('completed', 'failed') ORDER BY updated_at ASC, job_id ASC"
                ).fetchall()
        except sqlite3.Error:
            return
        for row in rows:
            try:
                payload = json.loads(row[3] or "{}")
                if not isinstance(payload, dict):
                    continue
                capture_id = str(payload.get("capture_id") or "").strip()
                if not capture_id:
                    continue
                work = self.get_work_by_source_id(capture_id)
                if work is None:
                    continue
                if row[1] == "completed":
                    result = json.loads(row[4] or "{}")
                    if not isinstance(result, dict):
                        result = {}
                    summary = self._safe_result_summary(result)
                    self.apply_extraction_transition(work.work_id, "completed", summary=summary, evidence={"job_id": str(row[0]), "source_type": str(row[2] or "")}, occurred_at=str(row[5] or ""))
                else:
                    reason = "提取失败，灵机无法安全完成这条输入"
                    self.apply_extraction_transition(work.work_id, "failed", summary=reason, evidence={"stage": "extraction", "job_id": str(row[0]), "source_type": str(row[2] or "")}, occurred_at=str(row[5] or ""))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue

    @staticmethod
    def _safe_result_summary(result: dict[str, Any]) -> str:
        allowed = ("execution_id", "source_type", "adapter", "adapter_version", "indexed", "document_count", "memory_count")
        summary = {key: result[key] for key in allowed if key in result and isinstance(result[key], (str, int, float, bool, type(None)))}
        return json.dumps(summary, ensure_ascii=False, sort_keys=True) if summary else "Extraction completed"

    def list_pending(self, limit: int = 20, *, work_id: str | None = None) -> list[PendingAction]:
        query = "SELECT action_id, work_id, description, resolved, actor, created_at FROM pending_actions WHERE resolved = 0"
        params: list[Any] = []
        if work_id:
            query += " AND work_id = ?"
            params.append(work_id)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(max(int(limit), 1))
        with self.state._connection() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [PendingAction(action_id=r[0], work_id=r[1], description=r[2], resolved=bool(r[3]), actor=r[4] or "owner", created_at=r[5] or "") for r in rows]

    def count_work(self, *, include_merged: bool = False) -> int:
        """工作履历总数；默认不含 merged 行（其失败事实已并入同来源代表行）。"""
        query = "SELECT COUNT(*) FROM work_items"
        if not include_merged:
            query += " WHERE status <> 'merged'"
        with self.state._connection() as connection:
            row = connection.execute(query).fetchone()
        return int(row[0] if row else 0)

    def list_work(self, limit: int = 20, *, offset: int = 0, include_merged: bool = False) -> list[WorkItem]:
        if int(limit) < 1 or int(offset) < 0:
            raise ValueError("limit must be positive and offset must not be negative")
        query = "SELECT work_id, title, source_id, status, owner_approved, created_at, updated_at FROM work_items"
        if not include_merged:
            # merged 行不进入履历分页：单列展示会让主人的工作履历回到整屏红字。
            query += " WHERE status <> 'merged'"
        query += " ORDER BY COALESCE(updated_at, created_at) DESC, work_id DESC LIMIT ? OFFSET ?"
        with self.state._connection() as connection:
            rows = connection.execute(query, (int(limit), int(offset))).fetchall()
        return [self._work(r) for r in rows]

    def list_events(self, work_id: str, limit: int = 100, *, ascending: bool = False) -> list[ExecutionEvent]:
        if int(limit) < 1:
            raise ValueError("limit must be positive")
        order = "ASC" if ascending else "DESC"
        with self.state._connection() as connection:
            rows = connection.execute(
                f"SELECT event_id, event_type, detail_json, created_at FROM execution_events WHERE work_id = ? ORDER BY created_at {order}, event_id {order} LIMIT ?",
                (work_id, int(limit)),
            ).fetchall()
        return [ExecutionEvent(work_id=work_id, event_id=r[0], event_type=r[1], detail=json.loads(r[2] or "{}"), created_at=r[3]) for r in rows]
