from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..base import ExtractionAdapter
from ..models import ExtractedDocument, ExtractionBatch, ExtractionRequest
from ..models import StructuredConversation, StructuredMessage, StructuredSource
from .generic_ai_history import SchemaDetection


class CodexWorkReportAdapter(ExtractionAdapter):
    name = "codex_work_report"
    version = "1.1.0"
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
        execution_token = self._stable_token(normalized["execution_id"])
        main_id = f"LJ-CODEX-{task_token}-{execution_token}"

        errors = [
            (self._child_id("ERROR", task_token, item), item)
            for item in normalized["errors"]
        ]
        decisions = [
            (self._child_id("DECISION", task_token, item), item)
            for item in normalized["decisions"]
        ]
        remaining_tasks = [
            (self._child_id("TASK", task_token, item), item)
            for item in normalized["remaining_tasks"]
        ]
        related_ids = [item_id for item_id, _ in [*errors, *decisions, *remaining_tasks]]

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
                    "task_id": normalized["task_id"],
                    "execution_id": normalized["execution_id"],
                    "run_number": normalized["run_number"],
                    "project_id": normalized["project_id"],
                    "repository": normalized["repository"],
                    "branch": normalized["branch"],
                    "agent": normalized["agent"],
                    "status": normalized["status"],
                    "test_result": normalized["test_result"],
                    "commits": normalized["commits"],
                    "pull_requests": normalized["pull_requests"],
                    "related_ids": related_ids,
                    "tags": ["source/codex", "topic/work-report", normalized["project_id"]],
                },
            )
        ]
        for item_id, error in errors:
            documents.append(
                ExtractedDocument(
                    stable_id=item_id,
                    title=self._item_title(error, "Codex错误"),
                    body=self._render_item(
                        "错误记录", error, main_id, normalized["repository"], normalized["branch"]
                    ),
                    source_type="codex",
                    destination="error",
                    external_id=normalized["task_id"],
                    created_at=normalized["completed_at"],
                    updated_at=normalized["completed_at"],
                    metadata={
                        "task_id": normalized["task_id"],
                        "execution_id": normalized["execution_id"],
                        "project_id": normalized["project_id"],
                        "status": "open",
                        "severity": self._item_value(error, "severity", "medium"),
                        "related_ids": [main_id],
                        "tags": ["source/codex", "signal/error"],
                    },
                )
            )
        for item_id, decision in decisions:
            documents.append(
                ExtractedDocument(
                    stable_id=item_id,
                    title=self._item_title(decision, "Codex决策候选"),
                    body=self._render_item(
                        "决策候选", decision, main_id, normalized["repository"], normalized["branch"]
                    ),
                    source_type="codex",
                    destination="decision",
                    external_id=normalized["task_id"],
                    created_at=normalized["completed_at"],
                    updated_at=normalized["completed_at"],
                    metadata={
                        "task_id": normalized["task_id"],
                        "execution_id": normalized["execution_id"],
                        "project_id": normalized["project_id"],
                        "status": "needs_review",
                        "review_status": "needs_review",
                        "owner_confirmed": False,
                        "related_ids": [main_id],
                        "tags": ["source/codex", "signal/decision-candidate"],
                    },
                )
            )
        for item_id, task in remaining_tasks:
            documents.append(
                ExtractedDocument(
                    stable_id=item_id,
                    title=self._item_title(task, "后续任务"),
                    body=self._render_item(
                        "待办候选", task, main_id, normalized["repository"], normalized["branch"]
                    ),
                    source_type="codex",
                    destination="task",
                    external_id=normalized["task_id"],
                    created_at=normalized["completed_at"],
                    updated_at=normalized["completed_at"],
                    metadata={
                        "task_id": normalized["task_id"],
                        "execution_id": normalized["execution_id"],
                        "project_id": normalized["project_id"],
                        "status": "needs_review",
                        "review_status": "needs_review",
                        "owner_confirmed": False,
                        "related_ids": [main_id],
                        "tags": ["source/codex", "attention/review"],
                    },
                )
            )
        return ExtractionBatch(
            documents=tuple(documents),
            summary={
                "task_id": normalized["task_id"],
                "execution_id": normalized["execution_id"],
                "project_id": normalized["project_id"],
                "reports": 1,
                "errors": len(errors),
                "decisions": len(decisions),
                "remaining_tasks": len(remaining_tasks),
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
        project_id = str(report.get("project_id") or report.get("project") or "General").strip()
        task_id = str(report.get("task_id") or report.get("id") or "").strip()
        if not task_id:
            task_id = self._hash(report)[:16]
        completed_at = self._iso(report.get("completed_at")) or datetime.now().isoformat(
            timespec="seconds"
        )
        started_at = self._iso(report.get("started_at"))
        commits = self._list(report.get("commits"))
        execution_id = str(report.get("execution_id") or report.get("run_id") or "").strip()
        if not execution_id:
            execution_id = self._hash(
                {
                    "task_id": task_id,
                    "completed_at": completed_at,
                    "branch": report.get("branch") or "",
                    "commits": commits,
                    "summary": summary,
                }
            )[:16]
        title = str(report.get("title") or f"Codex工作报告：{summary[:40]}").strip()
        return {
            "task_id": task_id,
            "execution_id": execution_id,
            "run_number": report.get("run_number") or "",
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
            "commits": commits,
            "pull_requests": self._list(report.get("pull_requests") or report.get("prs")),
            "errors": self._list(report.get("errors")),
            "decisions": self._list(report.get("decisions")),
            "remaining_tasks": self._list(report.get("remaining_tasks") or report.get("next_steps")),
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
            f"- 执行ID：`{report['execution_id']}`",
            f"- 执行序号：`{report['run_number'] or '-'}`",
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
            return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat(timespec="seconds")
        except ValueError:
            return text

    @staticmethod
    def _stable_token(value: str) -> str:
        cleaned = "".join(
            char if char.isalnum() or char in "-_" else "-" for char in str(value)
        ).strip("-")
        return cleaned[:80] or "UNKNOWN"

    @classmethod
    def _child_id(cls, prefix: str, task_token: str, item: Any) -> str:
        token = cls._hash(item)[:12].upper()
        return f"LJ-{prefix}-{task_token}-{token}"

    @staticmethod
    def _hash(value: Any) -> str:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class CodexTranscriptAdapter(ExtractionAdapter):
    """Parser for the explicitly versioned, exported Codex transcript JSONL schema."""

    name = "codex_transcript"
    version = "1.0.0"
    source_types = ("codex_transcript", "codex_history", "codex")
    SCHEMA = "codex_transcript"
    SCHEMA_VERSION = "1"
    MAX_INPUT_BYTES = 32 * 1024 * 1024
    _ROLES = frozenset({"user", "assistant", "system", "tool"})
    _FORBIDDEN_NAMES = frozenset({"auth", "token", "config", "cookie", "cookies", "private", "credentials"})

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        del payload
        return (
            source_type in self.source_types
            and input_path is not None
            and self.detect_schema(input_path).supported
        )

    def detect_schema(self, path: Path) -> SchemaDetection:
        if not path or path.is_dir() or path.is_symlink():
            return SchemaDetection(None, None, False, "Codex transcript requires one regular JSONL file")
        if path.suffix.lower() != ".jsonl":
            return SchemaDetection(None, None, False, "Codex transcript schema requires JSONL")
        if self._forbidden_path(path):
            return SchemaDetection(None, None, False, "Codex transcript refuses credential or private storage paths")
        try:
            if path.stat().st_size > self.MAX_INPUT_BYTES:
                raise ValueError("Codex transcript exceeds size limit")
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            first = next((line for line in lines if line.strip()), "")
            header = json.loads(first)
            if not isinstance(header, dict):
                raise ValueError("Codex transcript header is not an object")
            schema = str(header.get("schema") or header.get("schema_name") or "")
            version = str(header.get("schema_version") or header.get("version") or "")
            if schema != self.SCHEMA or version != self.SCHEMA_VERSION:
                return SchemaDetection(schema or None, version or None, False, "unknown Codex transcript schema; no guessing")
            if header.get("type") not in (None, "header", "session"):
                return SchemaDetection(schema, version, False, "Codex transcript header record is invalid")
            messages = [json.loads(line) for line in lines if line.strip()][1:]
            if not messages:
                raise ValueError("Codex transcript contains no messages")
            if any(not isinstance(item, dict) or item.get("type") != "message" for item in messages):
                raise ValueError("Codex transcript contains an unknown record type")
            for item in messages:
                self._message(item)
        except (OSError, UnicodeError, StopIteration, json.JSONDecodeError, ValueError) as exc:
            return SchemaDetection(None, None, False, str(exc))
        return SchemaDetection(self.SCHEMA, self.SCHEMA_VERSION, True, "supported Codex transcript schema v1")

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        if not request.input_path:
            raise ValueError("Codex transcript path is required")
        detection = self.detect_schema(request.input_path)
        if not detection.supported:
            raise ValueError(f"unsupported Codex transcript: {detection.reason}")
        rows = [
            json.loads(line)
            for line in request.input_path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ][1:]
        grouped: dict[str, list[dict[str, str]]] = {}
        order: list[str] = []
        for row in rows:
            message = self._message(row)
            conversation_id = message["conversation_id"]
            if conversation_id not in grouped:
                grouped[conversation_id] = []
                order.append(conversation_id)
            grouped[conversation_id].append(message)
        documents: list[ExtractedDocument] = []
        conversations: list[StructuredConversation] = []
        for conversation_id in order:
            rows_for_conversation = grouped[conversation_id]
            stable = "LJ-CODEX-TRANSCRIPT-" + self._hash(conversation_id)[:24].upper()
            messages = tuple(
                StructuredMessage(
                    external_id=row["message_id"],
                    role=row["role"],
                    content=row["content"],
                    sequence=index,
                    occurred_at=row["timestamp"],
                    metadata={"conversation_id": conversation_id, "message_id": row["message_id"]},
                )
                for index, row in enumerate(rows_for_conversation)
            )
            body = "\n\n".join(
                f"## {index}. {row['role']} · {row['timestamp']}\n\n{row['content']}"
                for index, row in enumerate(rows_for_conversation, 1)
            )
            documents.append(
                ExtractedDocument(
                    stable_id=stable,
                    title=f"Codex transcript {conversation_id}",
                    body=f"# Codex transcript {conversation_id}\n\n{body}\n",
                    source_type="codex_transcript",
                    destination="source_archive",
                    external_id=conversation_id,
                    created_at=rows_for_conversation[0]["timestamp"],
                    updated_at=rows_for_conversation[-1]["timestamp"],
                    metadata={"conversation_id": conversation_id, "schema": self.SCHEMA, "schema_version": self.SCHEMA_VERSION},
                )
            )
            conversations.append(
                StructuredConversation(
                    external_id=conversation_id,
                    title=f"Codex transcript {conversation_id}",
                    messages=messages,
                    started_at=messages[0].occurred_at,
                    ended_at=messages[-1].occurred_at,
                    participants=tuple(dict.fromkeys(message.role for message in messages)),
                    metadata={"schema": self.SCHEMA, "schema_version": self.SCHEMA_VERSION},
                )
            )
        return ExtractionBatch(
            documents=tuple(documents),
            structured_sources=(
                StructuredSource(
                    source_type="codex_transcript",
                    external_id="codex-transcript-source-" + self._hash(request.input_path.read_bytes().hex())[:24].upper(),
                    display_name="Codex transcript",
                    conversations=tuple(conversations),
                    metadata={"schema": self.SCHEMA, "schema_version": self.SCHEMA_VERSION},
                ),
            ),
            summary={"conversations_found": len(documents), "documents_created": len(documents)},
        )

    @classmethod
    def _message(cls, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            raise ValueError("Codex transcript message is not an object")
        values: dict[str, str] = {}
        for field in ("conversation_id", "message_id", "role", "content", "timestamp"):
            raw = value.get(field)
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"Codex transcript {field} is required")
            values[field] = raw.strip()
        if values["role"] not in cls._ROLES:
            raise ValueError("Codex transcript role is unsupported")
        try:
            datetime.fromisoformat(values["timestamp"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Codex transcript timestamp is invalid") from exc
        return values

    @classmethod
    def _forbidden_path(cls, path: Path) -> bool:
        name = path.name.lower()
        return path.suffix.lower() in {".db", ".sqlite", ".sqlite3"} or name in cls._FORBIDDEN_NAMES or any(
            name.startswith(prefix + ".") for prefix in cls._FORBIDDEN_NAMES
        )

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
