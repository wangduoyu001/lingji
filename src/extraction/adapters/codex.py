from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..base import ExtractionAdapter
from ..models import ExtractedDocument, ExtractionBatch, ExtractionRequest


class CodexWorkReportAdapter(ExtractionAdapter):
    name = "codex_work_report"
    version = "1.0.0"
    source_types = ("codex", "codex_report")

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        if source_type not in self.source_types:
            return False
        if payload:
            return True
        return bool(input_path and input_path.suffix.lower() == ".json")

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        report = self._load_report(request)
        normalized = self._normalize(report)
        task_token = self._stable_token(normalized["task_id"])
        main_id = "LJ-CODEX-" + task_token
        documents = [
            ExtractedDocument(
                stable_id=main_id,
                title=normalized["title"],
                body=self._render_report(normalized),
                source_type="codex",
                destination="work_report",
                external_id=normalized["task_id"],
                created_at=normalized["started_at"] or normalized["completed_at"],
                updated_at=normalized["completed_at"],
                metadata={
                    "project_id": normalized["project_id"],
                    "repository": normalized["repository"],
                    "branch": normalized["branch"],
                    "agent": normalized["agent"],
                    "status": normalized["status"],
                    "test_result": normalized["test_result"],
                    "commits": normalized["commits"],
                    "pull_requests": normalized["pull_requests"],
                    "related_ids": [
                        *[
                            f"LJ-ERROR-{task_token}-{index:02d}"
                            for index, _ in enumerate(normalized["errors"], 1)
                        ],
                        *[
                            f"LJ-DECISION-{task_token}-{index:02d}"
                            for index, _ in enumerate(normalized["decisions"], 1)
                        ],
                        *[
                            f"LJ-TASK-{task_token}-{index:02d}"
                            for index, _ in enumerate(normalized["remaining_tasks"], 1)
                        ],
                    ],
                    "tags": ["codex", "work-report", normalized["project_id"]],
                },
            )
        ]
        for index, error in enumerate(normalized["errors"], 1):
            documents.append(
                ExtractedDocument(
                    stable_id=f"LJ-ERROR-{task_token}-{index:02d}",
                    title=self._item_title(error, f"Codex错误 {index}"),
                    body=self._render_item(
                        "错误记录",
                        error,
                        main_id,
                        normalized["repository"],
                        normalized["branch"],
                    ),
                    source_type="codex",
                    destination="error",
                    external_id=normalized["task_id"],
                    created_at=normalized["completed_at"],
                    updated_at=normalized["completed_at"],
                    metadata={
                        "project_id": normalized["project_id"],
                        "status": "open",
                        "severity": self._item_value(error, "severity", "medium"),
                        "related_ids": [main_id],
                        "tags": ["codex", "error"],
                    },
                )
            )
        for index, decision in enumerate(normalized["decisions"], 1):
            documents.append(
                ExtractedDocument(
                    stable_id=f"LJ-DECISION-{task_token}-{index:02d}",
                    title=self._item_title(decision, f"Codex决策候选 {index}"),
                    body=self._render_item(
                        "决策候选",
                        decision,
                        main_id,
                        normalized["repository"],
                        normalized["branch"],
                    ),
                    source_type="codex",
                    destination="decision",
                    external_id=normalized["task_id"],
                    created_at=normalized["completed_at"],
                    updated_at=normalized["completed_at"],
                    metadata={
                        "project_id": normalized["project_id"],
                        "status": "needs_review",
                        "owner_confirmed": False,
                        "related_ids": [main_id],
                        "tags": ["codex", "decision-candidate"],
                    },
                )
            )
        for index, task in enumerate(normalized["remaining_tasks"], 1):
            documents.append(
                ExtractedDocument(
                    stable_id=f"LJ-TASK-{task_token}-{index:02d}",
                    title=self._item_title(task, f"后续任务 {index}"),
                    body=self._render_item(
                        "待办候选",
                        task,
                        main_id,
                        normalized["repository"],
                        normalized["branch"],
                    ),
                    source_type="codex",
                    destination="task",
                    external_id=normalized["task_id"],
                    created_at=normalized["completed_at"],
                    updated_at=normalized["completed_at"],
                    metadata={
                        "project_id": normalized["project_id"],
                        "status": "needs_review",
                        "owner_confirmed": False,
                        "related_ids": [main_id],
                        "tags": ["codex", "task-candidate"],
                    },
                )
            )
        return ExtractionBatch(
            documents=tuple(documents),
            summary={
                "task_id": normalized["task_id"],
                "project_id": normalized["project_id"],
                "reports": 1,
                "errors": len(normalized["errors"]),
                "decisions": len(normalized["decisions"]),
                "remaining_tasks": len(normalized["remaining_tasks"]),
            },
        )

    @staticmethod
    def _load_report(request: ExtractionRequest) -> dict[str, Any]:
        if request.payload:
            return dict(request.payload)
        if not request.input_path:
            raise ValueError("Codex report payload or JSON path is required")
        data = json.loads(request.input_path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("Codex work report must be a JSON object")
        return data

    def _normalize(self, report: dict[str, Any]) -> dict[str, Any]:
        summary = str(report.get("summary") or report.get("result") or "").strip()
        if not summary:
            raise ValueError("Codex work report summary is required")
        project_id = str(
            report.get("project_id") or report.get("project") or "General"
        ).strip()
        task_id = str(report.get("task_id") or report.get("id") or "").strip()
        if not task_id:
            task_id = hashlib.sha256(
                json.dumps(report, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()[:16]
        completed_at = self._iso(report.get("completed_at")) or datetime.now().isoformat(
            timespec="seconds"
        )
        started_at = self._iso(report.get("started_at"))
        title = str(report.get("title") or f"Codex工作报告：{summary[:40]}").strip()
        return {
            "task_id": task_id,
            "project_id": project_id,
            "title": title,
            "repository": str(report.get("repository") or report.get("repo") or ""),
            "branch": str(report.get("branch") or ""),
            "agent": str(report.get("agent") or report.get("agent_id") or "codex"),
            "summary": summary,
            "status": str(report.get("status") or "completed"),
            "started_at": started_at,
            "completed_at": completed_at,
            "changed_files": self._list(report.get("changed_files") or report.get("files")),
            "tests": self._list(report.get("tests")),
            "test_result": str(report.get("test_result") or report.get("tests_status") or ""),
            "commits": self._list(report.get("commits")),
            "pull_requests": self._list(report.get("pull_requests") or report.get("prs")),
            "errors": self._list(report.get("errors")),
            "decisions": self._list(report.get("decisions")),
            "remaining_tasks": self._list(
                report.get("remaining_tasks") or report.get("next_steps")
            ),
            "artifacts": self._list(report.get("artifacts")),
            "notes": str(report.get("notes") or ""),
        }

    def _render_report(self, report: dict[str, Any]) -> str:
        lines = [
            f"# {report['title']}",
            "",
            "## 结果摘要",
            "",
            report["summary"],
            "",
            "## 执行信息",
            "",
            f"- 项目：`{report['project_id']}`",
            f"- 仓库：`{report['repository'] or '-'}`",
            f"- 分支：`{report['branch'] or '-'}`",
            f"- 任务ID：`{report['task_id']}`",
            f"- Agent：`{report['agent']}`",
            f"- 状态：`{report['status']}`",
            f"- 开始：`{report['started_at'] or '-'}`",
            f"- 完成：`{report['completed_at']}`",
            "",
        ]
        self._append_section(lines, "修改文件", report["changed_files"])
        self._append_section(lines, "测试", report["tests"])
        if report["test_result"]:
            lines.extend(["### 测试结论", "", report["test_result"], ""])
        self._append_section(lines, "提交", report["commits"])
        self._append_section(lines, "Pull Requests", report["pull_requests"])
        self._append_section(lines, "错误", report["errors"])
        self._append_section(lines, "决策候选", report["decisions"])
        self._append_section(lines, "后续任务", report["remaining_tasks"])
        self._append_section(lines, "交付物", report["artifacts"])
        if report["notes"]:
            lines.extend(["## 备注", "", report["notes"], ""])
        return "\n".join(lines)

    @classmethod
    def _append_section(cls, lines: list[str], title: str, items: list[Any]) -> None:
        if not items:
            return
        lines.extend([f"## {title}", ""])
        for item in items:
            if isinstance(item, dict):
                label = cls._item_title(item, "")
                detail = "; ".join(
                    f"{key}: {value}" for key, value in item.items() if value not in (None, "", [])
                )
                lines.append(f"- **{label}**：{detail}" if label else f"- {detail}")
            else:
                lines.append(f"- {item}")
        lines.append("")

    @classmethod
    def _render_item(
        cls,
        heading: str,
        item: Any,
        report_id: str,
        repository: str,
        branch: str,
    ) -> str:
        lines = [
            f"# {cls._item_title(item, heading)}",
            "",
            f"> 来源工作报告：`{report_id}`",
            "",
            f"- 仓库：`{repository or '-'}`",
            f"- 分支：`{branch or '-'}`",
            "",
            f"## {heading}",
            "",
        ]
        if isinstance(item, dict):
            for key, value in item.items():
                if value not in (None, "", []):
                    lines.append(f"- **{key}**：{value}")
        else:
            lines.append(str(item))
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _item_title(item: Any, fallback: str) -> str:
        if isinstance(item, dict):
            for key in ("title", "name", "decision", "task", "error", "message", "summary"):
                value = item.get(key)
                if value:
                    return str(value)[:100]
        if isinstance(item, str) and item.strip():
            return item.strip()[:100]
        return fallback

    @staticmethod
    def _item_value(item: Any, key: str, default: Any = "") -> Any:
        return item.get(key, default) if isinstance(item, dict) else default

    @staticmethod
    def _list(value: Any) -> list[Any]:
        if value in (None, "", []):
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _iso(value: Any) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat(timespec="seconds")
            except (ValueError, OSError, OverflowError):
                return ""
        text = str(value)
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat(
                timespec="seconds"
            )
        except ValueError:
            return text

    @staticmethod
    def _stable_token(value: str) -> str:
        cleaned = "".join(
            char if char.isalnum() or char in "-_" else "-" for char in str(value)
        ).strip("-")
        return cleaned[:80] or "UNKNOWN"
