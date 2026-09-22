"""自动记忆晋升管线（主人 2026-09-22 拍板）。

原料是 ``distilled_knowledge``（lingji_memory.db，对话自动提炼的事实级要点）。
门槛全部确定性可审计：置信度阈值、类别白名单、通知类过滤、与既有
Core Memory 的全文+语义去重、标题冲突检测、每日上限。通过门槛的条目经
``MemoryLifecycleService`` 晋升为 Core Memory；未达标或有冲突的写入
``vault/03-Knowledge/Evolving/<主题>.md`` 迭代时间线，绝不静默丢弃。

每条决策写 ``auto_promotion_decision`` 审计事件，prev-hash 链式防篡改
（与 auto_review 决策哈希链同一形态）。既有 Core 文件只增不改；
总开关 ``auto_promote_enabled`` 默认关闭，回滚=关开关。
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from src.auto_review.evaluator import DeterministicAutoReviewEvaluator
from src.auto_review.models import AutoReviewAction, AutoReviewMode, ReviewCandidate, ReviewContext
from src.obsidian.frontmatter import atomic_write, render_frontmatter, split_frontmatter


EVENT_TYPE = "auto_promotion_decision"
POLICY_VERSION = "auto-promotion-1"

# 类别白名单：事实/项目结论类（提炼五类中的技术/决策/项目）。
# "问题"/"其他"多为通知性或无结论内容，走 Evolving 轨。
WHITELIST_CATEGORIES = {"技术", "决策", "项目"}
# 通知类标题标记：标题命中且无结论性词汇时视为通知（如"晨间简报失败"）。
NOTIFICATION_MARKERS = ("失败", "报错", "崩溃", "中断", "超时", "不可用", "无法")
CONCLUSION_MARKERS = ("完成", "修复", "解决", "已", "结论", "方案", "通过", "确定", "拍板", "修复了")

# 全文去重：规范化文本包含（短文本被长文本包含）或序列相似度达标即判重。
DUPLICATE_CONTAINMENT_MIN_CHARS = 20
# 中文摘要通常只有 10-25 字：要点级判重里摘要的最小有效长度。
DUPLICATE_SUMMARY_MIN_CHARS = 8
DUPLICATE_RATIO_THRESHOLD = 0.88
AUTO_AGENT_ID = "lingji-auto"


def _normalize_text(value: str) -> str:
    return re.sub(r"[^\w]+", "", str(value or "").lower(), flags=re.UNICODE)


def _row_payload_hash(row: Mapping[str, Any]) -> str:
    material = {
        "conversation_id": str(row.get("conversation_id") or ""),
        "revision": int(row.get("revision") or 0),
        "title": str(row.get("title") or ""),
        "summary": str(row.get("summary") or ""),
        "key_points_json": str(row.get("key_points_json") or ""),
    }
    return hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class _CoreDocument:
    path: Path
    text: str
    normalized_title: str
    normalized_text: str


class AutoMemoryPromotionPipeline:
    """确定性门槛评估 + 晋升/Evolving 双轨落地 + 哈希链审计。"""

    def __init__(
        self,
        *,
        settings: Any,
        lifecycle: Any,
        state_db: Any,
        memory_db_path: Path | str,
        semantic_similarity: Callable[[str, str], float] | None = None,
        setting_reader: Callable[[str], Any] | None = None,
        post_promotion_sync: Callable[[], Any] | None = None,
        now: Callable[[], datetime] | None = None,
    ):
        self.settings = settings
        self.lifecycle = lifecycle
        self.state_db = state_db
        self.memory_db_path = Path(memory_db_path)
        self.semantic_similarity = semantic_similarity
        self.setting_reader = setting_reader
        # 晋升落 vault 后的可重建投影同步（sync_core）；缺失时只写 vault。
        self.post_promotion_sync = post_promotion_sync
        self.now = now or datetime.now
        self.evaluator = DeterministicAutoReviewEvaluator()
        self._last_run: dict[str, Any] = {"status": "never_run"}
        # run_once 期间的事件缓存（最新在前）；避免每条决策全量扫描事件表。
        self._events_cache: list[dict[str, Any]] | None = None

    # ------------------------------------------------------------ settings
    def _setting(self, name: str, default: Any) -> Any:
        if self.setting_reader is not None:
            try:
                value = self.setting_reader(name)
                if value is not None:
                    return value
            except Exception:
                pass
        return getattr(self.settings, name, default)

    def enabled(self) -> bool:
        value = self._setting("auto_promote_enabled", False)
        return value is True or str(value).strip().lower() in {"1", "true", "yes", "on"}

    # ------------------------------------------------------------- public
    def run_once(self, limit: int | None = None) -> dict[str, Any]:
        """处理一批未决的提炼行；返回汇总。开关关闭时零写入。"""
        if not self.enabled():
            self._last_run = {"status": "disabled", "processed": 0}
            return dict(self._last_run)
        if not self.memory_db_path.exists():
            self._last_run = {"status": "memory_db_unavailable", "processed": 0}
            return dict(self._last_run)

        summary = {
            "status": "ok",
            "processed": 0,
            "promoted": 0,
            "evolving": 0,
            "duplicate": 0,
            "deferred": 0,
            "capped": False,
            "outcomes": [],
        }
        self._events_cache = None
        try:
            return self._run_batch(summary, rows=self._pending_rows(), limit=limit)
        finally:
            self._events_cache = None

    def _run_batch(self, summary: dict[str, Any], *, rows: list[dict[str, Any]], limit: int | None) -> dict[str, Any]:
        # 先剔除已决行再截断 limit：否则最早的已决行永久占满每轮名额，
        # 管线在首轮后空转（真机验收发现的回归）。
        decided = self._decided_keys()
        rows = [
            row
            for row in rows
            if (str(row["conversation_id"]), int(row["revision"] or 0)) not in decided
        ]
        if limit is not None:
            rows = rows[: max(int(limit), 0)]
        if not rows:
            self._last_run = dict(summary)
            return dict(summary)

        core_documents = self._load_core_documents()
        promoted_today = self._promoted_today()
        daily_limit = int(self._setting("auto_promote_daily_limit", 10) or 10)
        title_conflicts = self._ready_title_first_seen()

        for row in rows:
            key = (str(row["conversation_id"]), int(row["revision"] or 0))
            if key in decided:
                continue
            summary["processed"] += 1
            outcome, reasons, extra = self._decide_row(
                row, core_documents=core_documents, title_conflicts=title_conflicts
            )
            if outcome == "deferred":
                # 语义检查暂不可用：不落任何决策，下一轮重试。
                summary["deferred"] += 1
                continue
            if outcome == "promote":
                if promoted_today >= daily_limit:
                    summary["capped"] = True
                    break
                try:
                    promoted_path = self._promote_row(row)
                except Exception as exc:
                    outcome, reasons = "error", [f"promotion_failed:{exc.__class__.__name__}"]
                    promoted_path = None
                    extra = {}
                else:
                    promoted_today += 1
                    summary["promoted"] += 1
                    self._graduate_evolving(row, promoted_path)
                self._record_decision(
                    row,
                    outcome="promoted" if promoted_path is not None else outcome,
                    reasons=reasons,
                    extra={**(extra or {}), **({"promoted_path": promoted_path} if promoted_path else {})},
                )
                summary["outcomes"].append({"conversation_id": key[0], "outcome": "promoted" if promoted_path else outcome, "reasons": reasons})
                continue
            if outcome == "duplicate":
                summary["duplicate"] += 1
                self._record_decision(row, outcome="duplicate", reasons=reasons, extra=extra)
                summary["outcomes"].append({"conversation_id": key[0], "outcome": "duplicate", "reasons": reasons})
                continue
            # evolving
            try:
                evolving_path = self._append_evolving(row, reasons)
            except Exception as exc:
                self._record_decision(row, outcome="error", reasons=[f"evolving_failed:{exc.__class__.__name__}"], extra={})
                summary["outcomes"].append({"conversation_id": key[0], "outcome": "error", "reasons": ["evolving_failed"]})
                continue
            summary["evolving"] += 1
            self._record_decision(row, outcome="evolving", reasons=reasons, extra={**(extra or {}), "evolving_path": evolving_path})
            summary["outcomes"].append({"conversation_id": key[0], "outcome": "evolving", "reasons": reasons})

        if summary["promoted"] > 0 and self.post_promotion_sync is not None:
            # 新 Core 文件落 vault 后同步可重建投影（memory_documents/chunks），
            # UI 的永久记忆计数与语义检索才能看到；失败不影响晋升结果。
            try:
                summary["projection_sync"] = dict(self.post_promotion_sync() or {})
            except Exception as exc:
                summary["projection_sync"] = {"error": exc.__class__.__name__}

        self._last_run = dict(summary)
        return dict(summary)

    def stats(self) -> dict[str, Any]:
        return {
            "available": True,
            "enabled": self.enabled(),
            "last_run": dict(self._last_run),
        }

    # -------------------------------------------------------------- gates
    def _decide_row(
        self,
        row: Mapping[str, Any],
        *,
        core_documents: list[_CoreDocument],
        title_conflicts: Mapping[str, str],
    ) -> tuple[str, list[str], dict[str, Any]]:
        reasons: list[str] = []
        title = str(row["title"] or "").strip()
        summary_text = str(row["summary"] or "").strip()
        key_points = self._key_points(row)
        category = str(row.get("category") or "").strip()
        confidence = self._row_confidence(row)

        if not title or not summary_text or not key_points:
            return "evolving", ["schema_invalid"], {}
        if category not in WHITELIST_CATEGORIES:
            reasons.append("category_not_whitelisted")
        if self._is_notification_title(title):
            reasons.append("notification_like")
        confidence_min = float(self._setting("auto_promote_confidence_min", 0.90) or 0.90)
        if confidence is None:
            reasons.append("confidence_missing")
        elif confidence < confidence_min:
            reasons.append("confidence_below_threshold")

        normalized_title = _normalize_text(title)
        candidate_text = _normalize_text(f"{title} {summary_text} {' '.join(key_points)}")
        normalized_summary = _normalize_text(summary_text)
        normalized_points = [_normalize_text(point) for point in key_points]
        normalized_points = [point for point in normalized_points if point]

        duplicate_of = self._full_text_duplicate(
            candidate_text,
            core_documents,
            normalized_summary=normalized_summary,
            normalized_points=normalized_points,
        )
        if duplicate_of is not None:
            return "duplicate", ["full_text_duplicate"], {"duplicate_of": duplicate_of}

        conflict_with = self._title_conflict(normalized_title, candidate_text, core_documents)
        if conflict_with is None and title_conflicts.get(normalized_title) not in (None, str(row["conversation_id"])):
            conflict_with = "distilled_knowledge"
        if conflict_with is not None:
            return "evolving", ["title_conflict"], {"conflict_with": conflict_with}

        if self.semantic_similarity is None:
            return "deferred", ["semantic_check_unavailable"], {}
        semantic_threshold = float(self._setting("auto_promote_semantic_threshold", 0.92) or 0.92)
        try:
            semantic_best, semantic_target = self._semantic_duplicate(
                f"{title} {summary_text}", core_documents
            )
        except Exception:
            return "deferred", ["semantic_check_failed"], {}
        if semantic_best >= semantic_threshold:
            return "duplicate", ["semantic_duplicate"], {"semantic_score": round(semantic_best, 4), "duplicate_of": semantic_target}

        evaluation = self._evaluate(row, has_conflict=False)
        if evaluation["action"] != AutoReviewAction.WOULD_AUTO_APPROVE.value:
            reasons.extend(evaluation["finding_codes"])
            return "evolving", list(dict.fromkeys(reasons)) or ["evaluator_requires_owner"], evaluation
        if reasons:
            return "evolving", reasons, evaluation
        return "promote", [], evaluation

    def _evaluate(self, row: Mapping[str, Any], *, has_conflict: bool) -> dict[str, Any]:
        candidate = ReviewCandidate(
            memory_id=f"LJ-DIST-{str(row['conversation_id'])[:32].upper()}",
            title=str(row["title"] or "").strip(),
            content=self._render_content(row),
            memory_type="knowledge",
            proposed_by=AUTO_AGENT_ID,
            confidence=self._row_confidence(row),
            authority="derived",
            source_kind="distilled_knowledge",
            extractor_version=str(row.get("model") or ""),
            metadata={
                "source_type": "distilled_knowledge",
                "conversation_id": str(row["conversation_id"]),
                "revision": int(row["revision"] or 0),
                "category": str(row.get("category") or ""),
            },
        )
        context = ReviewContext(
            mode=AutoReviewMode.SHADOW,
            evidence_sufficient=int(row.get("message_count") or 0) > 0,
            has_conflict=has_conflict,
            requested_operation="create",
        )
        decision = self.evaluator.evaluate(candidate, context)
        return {
            "decision_id": decision.decision_id,
            "action": decision.action.value,
            "risk_score": decision.risk_score,
            "finding_codes": [item.code for item in decision.reasons],
        }

    # ------------------------------------------------------------- dedup
    @staticmethod
    def _full_text_duplicate(
        candidate_text: str,
        core_documents: list[_CoreDocument],
        *,
        normalized_summary: str = "",
        normalized_points: list[str] | None = None,
    ) -> str | None:
        if len(candidate_text) < DUPLICATE_CONTAINMENT_MIN_CHARS:
            return None
        points = normalized_points or []
        for document in core_documents:
            if not document.normalized_text:
                continue
            shorter, longer = sorted((candidate_text, document.normalized_text), key=len)
            if len(shorter) >= DUPLICATE_CONTAINMENT_MIN_CHARS and shorter in longer:
                return document.path.name
            if difflib.SequenceMatcher(None, candidate_text, document.normalized_text).ratio() >= DUPLICATE_RATIO_THRESHOLD:
                return document.path.name
            # 要点级判重：摘要与过半要点都被既有 Core 覆盖，即视为同事实重复
            #（标题措辞变化不构成新知识）。
            if (
                len(normalized_summary) >= DUPLICATE_SUMMARY_MIN_CHARS
                and normalized_summary in document.normalized_text
            ):
                covered = sum(1 for point in points if point and point in document.normalized_text)
                if points and covered * 2 >= len(points):
                    return document.path.name
        return None

    @staticmethod
    def _title_conflict(
        normalized_title: str,
        candidate_text: str,
        core_documents: list[_CoreDocument],
    ) -> str | None:
        if not normalized_title:
            return None
        for document in core_documents:
            if document.normalized_title != normalized_title:
                continue
            ratio = (
                difflib.SequenceMatcher(None, candidate_text, document.normalized_text).ratio()
                if document.normalized_text
                else 0.0
            )
            if ratio < DUPLICATE_RATIO_THRESHOLD:
                return document.path.name
        return None

    def _semantic_duplicate(self, text: str, core_documents: list[_CoreDocument]) -> tuple[float, str | None]:
        if not core_documents:
            return 0.0, None
        best_score = 0.0
        best_target: str | None = None
        for document in core_documents:
            score = float(self.semantic_similarity(text, document.text))  # type: ignore[misc]
            if score > best_score:
                best_score = score
                best_target = document.path.name
        return best_score, best_target

    def _ready_title_first_seen(self) -> dict[str, str]:
        """标题相同的多个 ready 行里，occurred_at 最早者拥有该标题。"""
        first_seen: dict[str, str] = {}
        if not self.memory_db_path.exists():
            return first_seen
        conn = sqlite3.connect(str(self.memory_db_path))
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT conversation_id, title, occurred_at, created_at
                FROM distilled_knowledge
                WHERE status = 'ready'
                ORDER BY COALESCE(occurred_at, created_at) ASC, conversation_id ASC
                """
            ).fetchall()
        finally:
            conn.close()
        for row in rows:
            key = _normalize_text(str(row["title"] or ""))
            if key and key not in first_seen:
                first_seen[key] = str(row["conversation_id"])
        return first_seen

    # --------------------------------------------------------- persistence
    def _pending_rows(self) -> list[dict[str, Any]]:
        conn = sqlite3.connect(str(self.memory_db_path))
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM distilled_knowledge
                WHERE status = 'ready'
                ORDER BY COALESCE(occurred_at, created_at) ASC, conversation_id ASC
                """
            ).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]

    def _promote_row(self, row: Mapping[str, Any]) -> str:
        confidence = self._row_confidence(row)
        proposed = self.lifecycle.propose_memory(
            agent_id=AUTO_AGENT_ID,
            title=str(row["title"] or "").strip(),
            content=self._render_content(row),
            metadata={
                "memory_type": "knowledge",
                "confidence": confidence if confidence is not None else "",
                "category": str(row.get("category") or ""),
                "conversation_id": str(row["conversation_id"]),
                "revision": int(row["revision"] or 0),
                "distill_model": str(row.get("model") or ""),
                "tags": ["source/distilled-knowledge"],
            },
        )
        promoted = self.lifecycle.promote_candidate(
            proposed["path"],
            owner_confirmed=True,
            target_category="General",
        )
        return str(promoted.get("relative_path") or "")

    # ----------------------------------------------------------- evolving
    def _evolving_dir(self) -> Path:
        return self.lifecycle.layout.root / "03-Knowledge" / "Evolving"

    def _evolving_path(self, row: Mapping[str, Any]) -> Path:
        topic = str(row["title"] or "").strip()
        safe = self.lifecycle.layout.sanitize_filename(topic)[:60].removesuffix(".md").strip()
        name = safe if safe else f"topic-{str(row['conversation_id'])[:12]}"
        return self._evolving_dir() / f"{name}.md"

    def _append_evolving(self, row: Mapping[str, Any], reasons: list[str]) -> str:
        target = self._evolving_path(row)
        marker = f"<!-- {row['conversation_id']}@{row['revision']} -->"
        confidence = self._row_confidence(row)
        now = self.now().isoformat(timespec="seconds")
        existing_text = target.read_text(encoding="utf-8-sig") if target.exists() else ""
        if marker in existing_text:
            return self.lifecycle.layout.relative(target).as_posix()
        points = self._key_points(row)
        entry_lines = [
            f"### {now}",
            f"- 来源：distilled_knowledge `{row['conversation_id']}`@r{row['revision']}",
            f"- 置信度：{confidence if confidence is not None else '未知'}（门槛 {self._setting('auto_promote_confidence_min', 0.90)}）",
            f"- 分类：{row.get('category') or ''}",
            f"- 未晋升原因：{', '.join(reasons) or '未达标'}",
            f"- 摘要：{str(row['summary'] or '').strip()}",
        ]
        if points:
            entry_lines.append("- 要点：")
            entry_lines.extend(f"  - {point}" for point in points)
        entry_lines.append(marker)
        entry = "\n".join(entry_lines) + "\n"

        if existing_text:
            metadata, body = split_frontmatter(existing_text)
            metadata.update(
                {
                    "status": "evolving",
                    "confidence": confidence if confidence is not None else "",
                    "updated": now,
                }
            )
            text = render_frontmatter(metadata, body.rstrip() + "\n\n" + entry)
        else:
            metadata = {
                "schema_version": 1,
                "topic": str(row["title"] or "").strip(),
                "status": "evolving",
                "confidence": confidence if confidence is not None else "",
                "updated": now,
                "tags": ["signal/evolving-memory"],
            }
            body = "\n".join(
                [
                    f"# {str(row['title'] or '').strip()}",
                    "",
                    "> 未定论或未达晋升门槛的迭代记录；达标毕业后自动晋升 Core Memory。",
                    "",
                    "## 时间线",
                    "",
                ]
            )
            text = render_frontmatter(metadata, body + entry)
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(target, text)
        return self.lifecycle.layout.relative(target).as_posix()

    def _graduate_evolving(self, row: Mapping[str, Any], promoted_path: str) -> None:
        target = self._evolving_path(row)
        if not target.exists():
            return
        marker = f"<!-- graduated:{row['conversation_id']} -->"
        existing_text = target.read_text(encoding="utf-8-sig")
        if marker in existing_text:
            return
        now = self.now().isoformat(timespec="seconds")
        metadata, body = split_frontmatter(existing_text)
        metadata.update(
            {
                "status": "graduated",
                "graduated_at": now,
                "core_path": promoted_path,
                "updated": now,
            }
        )
        entry = (
            f"### {now} 毕业\n"
            f"- 已晋升 Core Memory：{promoted_path}\n"
            f"{marker}\n"
        )
        atomic_write(target, render_frontmatter(metadata, body.rstrip() + "\n\n" + entry))

    # ------------------------------------------------------------- audit
    def _record_decision(
        self,
        row: Mapping[str, Any],
        *,
        outcome: str,
        reasons: list[str],
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        decided_at = self.now().isoformat(timespec="seconds")
        core = {
            "conversation_id": str(row["conversation_id"]),
            "revision": int(row["revision"] or 0),
            "title": str(row["title"] or ""),
            "outcome": outcome,
            "reasons": [str(item) for item in reasons],
            "policy_version": POLICY_VERSION,
            "row_hash": _row_payload_hash(row),
        }
        material = {"previous_hash": self._previous_hash(), "decided_at": decided_at, **core}
        event_hash = hashlib.sha256(
            json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        payload = {**material, "event_hash": event_hash, **dict(extra or {})}
        self.state_db.append_event(EVENT_TYPE, "memory", str(row["conversation_id"]), payload)
        if self._events_cache is not None:
            self._events_cache.insert(0, payload)

    def _events(self) -> list[dict[str, Any]]:
        if self._events_cache is not None:
            return self._events_cache
        output: list[dict[str, Any]] = []
        for event_row in self.state_db.recent_events(limit=100000):
            if str(event_row.get("event_type") or "") != EVENT_TYPE:
                continue
            payload = event_row.get("payload")
            if isinstance(payload, Mapping):
                output.append(dict(payload))
                continue
            raw = event_row.get("payload_json")
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                except (TypeError, ValueError):
                    continue
                if isinstance(parsed, dict):
                    output.append(parsed)
        self._events_cache = output
        return output

    def _previous_hash(self) -> str:
        events = self._events()
        return str(events[0].get("event_hash") or "") if events else ""

    def _decided_keys(self) -> set[tuple[str, int]]:
        return {
            (str(item.get("conversation_id") or ""), int(item.get("revision") or 0))
            for item in self._events()
            if str(item.get("outcome") or "") in {"promoted", "evolving", "duplicate", "error"}
        }

    def _promoted_today(self) -> int:
        today = self.now().strftime("%Y-%m-%d")
        return sum(
            1
            for item in self._events()
            if str(item.get("outcome") or "") == "promoted"
            and str(item.get("decided_at") or "").startswith(today)
        )

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _key_points(row: Mapping[str, Any]) -> list[str]:
        try:
            parsed = json.loads(str(row.get("key_points_json") or "[]"))
        except (TypeError, ValueError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(point).strip() for point in parsed if str(point).strip()]

    @staticmethod
    def _row_confidence(row: Mapping[str, Any]) -> float | None:
        value = row.get("confidence")
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number < 0.0:
            return 0.0
        if number > 1.0:
            return 1.0
        return number

    @staticmethod
    def _is_notification_title(title: str) -> bool:
        return any(marker in title for marker in NOTIFICATION_MARKERS) and not any(
            marker in title for marker in CONCLUSION_MARKERS
        )

    def _render_content(self, row: Mapping[str, Any]) -> str:
        points = self._key_points(row)
        lines = [
            str(row["summary"] or "").strip(),
            "",
            "## 要点",
            "",
        ]
        lines.extend(f"- {point}" for point in points)
        lines.append("")
        lines.append(
            f"- 来源：自动提炼 `{row['conversation_id']}`@r{row['revision']}（模型 {row.get('model') or '未知'}）"
        )
        return "\n".join(lines).strip()

    def _load_core_documents(self) -> list[_CoreDocument]:
        core_dir = self.lifecycle.layout.core_memory_dir
        if not core_dir.exists():
            return []
        documents: list[_CoreDocument] = []
        for path in sorted(core_dir.rglob("*.md")):
            try:
                metadata, body = split_frontmatter(path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            title = str(metadata.get("title") or path.stem)
            full_text = f"{title}\n{body}"
            documents.append(
                _CoreDocument(
                    path=path,
                    text=full_text,
                    normalized_title=_normalize_text(title),
                    normalized_text=_normalize_text(full_text),
                )
            )
        return documents


def verify_auto_promotion_chain(events: list[Mapping[str, Any]]) -> bool:
    """按时间倒序的决策事件列表逐条校验哈希链。"""
    previous = ""
    for item in reversed(events):
        material = {
            "previous_hash": str(item.get("previous_hash") or ""),
            "decided_at": str(item.get("decided_at") or ""),
            "conversation_id": str(item.get("conversation_id") or ""),
            "revision": int(item.get("revision") or 0),
            "title": str(item.get("title") or ""),
            "outcome": str(item.get("outcome") or ""),
            "reasons": [str(reason) for reason in (item.get("reasons") or [])],
            "policy_version": str(item.get("policy_version") or ""),
            "row_hash": str(item.get("row_hash") or ""),
        }
        expected = hashlib.sha256(
            json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if expected != str(item.get("event_hash") or ""):
            return False
        if material["previous_hash"] != previous:
            return False
        previous = str(item.get("event_hash") or "")
    return True


__all__ = [
    "AUTO_AGENT_ID",
    "AutoMemoryPromotionPipeline",
    "EVENT_TYPE",
    "POLICY_VERSION",
    "WHITELIST_CATEGORIES",
    "verify_auto_promotion_chain",
]
