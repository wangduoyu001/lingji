from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from src.obsidian.frontmatter import atomic_write, content_hash, render_frontmatter, split_frontmatter

PROPERTY_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
PROTECTED_PROPERTIES = {
    "id",
    "schema_version",
    "content_hash",
    "created_at",
    "source_id",
    "source_path",
}
RELATION_FIELDS = {
    "project",
    "people",
    "organizations",
    "tools",
    "models",
    "sources",
    "tasks",
    "decisions",
    "related",
}


class DocumentManager:
    """Safe manual metadata operations for notes inside one vault."""

    def __init__(self, layout):
        self.layout = layout

    def resolve(self, path: Path | str, allow_private: bool = False) -> Path:
        relative = self.layout.relative(path)
        if relative.parts and relative.parts[0] == "08-Private" and not allow_private:
            raise PermissionError("Private notes require explicit owner authorization")
        return self.layout.root / relative

    def set_properties(
        self,
        path: Path | str,
        updates: dict[str, Any],
        expected_hash: str | None = None,
    ) -> dict[str, Any]:
        target = self.resolve(path)
        original = target.read_text(encoding="utf-8-sig")
        if expected_hash and content_hash(original) != expected_hash:
            raise RuntimeError("The note changed after the command was created")
        metadata, body = split_frontmatter(original)
        for key, value in updates.items():
            if not PROPERTY_KEY.match(key):
                raise ValueError(f"Invalid property name: {key}")
            if key in PROTECTED_PROPERTIES:
                raise PermissionError(f"Protected property cannot be changed manually: {key}")
            metadata[key] = value
        metadata["updated_at"] = datetime.now().isoformat(timespec="seconds")
        atomic_write(target, render_frontmatter(metadata, body))
        return metadata

    def add_tags(self, path: Path | str, tags: list[str]) -> list[str]:
        target = self.resolve(path)
        original = target.read_text(encoding="utf-8-sig")
        metadata, body = split_frontmatter(original)
        existing = metadata.get("tags") or []
        if isinstance(existing, str):
            existing = [existing]
        normalized = []
        for value in [*existing, *tags]:
            tag = self.normalize_tag(str(value))
            if tag and tag not in normalized:
                normalized.append(tag)
        if len(normalized) > 12:
            raise ValueError("A note may have at most 12 tags; use properties or links for structure")
        metadata["tags"] = normalized
        metadata["updated_at"] = datetime.now().isoformat(timespec="seconds")
        atomic_write(target, render_frontmatter(metadata, body))
        return normalized

    def link_notes(
        self,
        source_path: Path | str,
        target_path: Path | str,
        field: str = "related",
        bidirectional: bool = True,
    ) -> dict[str, str]:
        if field not in RELATION_FIELDS:
            raise ValueError(f"Unsupported relation field: {field}")
        source = self.resolve(source_path)
        target = self.resolve(target_path)
        source_link = self._wikilink(target)
        target_link = self._wikilink(source)
        self._append_link(source, field, source_link)
        if bidirectional:
            self._append_link(target, "related", target_link)
        return {"source": str(source), "target": str(target), "field": field}

    def _append_link(self, path: Path, field: str, link: str) -> None:
        original = path.read_text(encoding="utf-8-sig")
        metadata, body = split_frontmatter(original)
        values = metadata.get(field) or []
        if isinstance(values, str):
            values = [values]
        if link not in values:
            values.append(link)
        metadata[field] = values
        metadata["updated_at"] = datetime.now().isoformat(timespec="seconds")
        atomic_write(path, render_frontmatter(metadata, body))

    def _wikilink(self, path: Path) -> str:
        relative = self.layout.relative(path).as_posix()
        if relative.lower().endswith(".md"):
            relative = relative[:-3]
        return f"[[{relative}]]"

    @staticmethod
    def normalize_tag(tag: str) -> str:
        value = tag.strip().lstrip("#").replace("\\", "/")
        value = re.sub(r"\s+", "-", value)
        value = re.sub(r"[^\w\-/\u4e00-\u9fff]", "", value, flags=re.UNICODE)
        value = re.sub(r"/{2,}", "/", value).strip("/").lower()
        if not value or value.isdigit():
            return ""
        return value


class ManualCommandService:
    ALLOWED_COMMANDS = {"set_properties", "add_tags", "link_note", "mark_status"}

    def __init__(self, layout, document_manager: DocumentManager, state_db=None):
        self.layout = layout
        self.documents = document_manager
        self.state_db = state_db
        self.queue_dir = layout.root / "00-System" / "Commands" / "Queue"

    def process_pending(self, limit: int = 20) -> dict[str, int]:
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        summary = {"processed": 0, "succeeded": 0, "failed": 0}
        for path in sorted(self.queue_dir.glob("*.md"))[: max(int(limit), 1)]:
            metadata, _ = split_frontmatter(path.read_text(encoding="utf-8-sig"))
            if metadata.get("memory_type") != "command" or metadata.get("status") != "queued":
                continue
            summary["processed"] += 1
            try:
                self._set_command_status(path, "running", started_at=datetime.now().isoformat(timespec="seconds"))
                result = self._execute(metadata)
                self._set_command_status(
                    path,
                    "done",
                    result=json.dumps(result, ensure_ascii=False),
                    finished_at=datetime.now().isoformat(timespec="seconds"),
                )
                summary["succeeded"] += 1
                self._event("command_completed", path.stem, result)
            except Exception as exc:
                self._set_command_status(
                    path,
                    "failed",
                    last_error=str(exc)[:1000],
                    finished_at=datetime.now().isoformat(timespec="seconds"),
                )
                summary["failed"] += 1
                self._event("command_failed", path.stem, {"error": str(exc)})
        return summary

    def _execute(self, metadata: dict[str, Any]) -> Any:
        command_type = str(metadata.get("command_type") or "")
        if command_type not in self.ALLOWED_COMMANDS:
            raise PermissionError(f"Unsupported command: {command_type}")
        target_path = str(metadata.get("target_path") or "")
        if not target_path:
            raise ValueError("target_path is required")
        if command_type == "set_properties":
            payload = json.loads(str(metadata.get("payload_json") or "{}"))
            if not isinstance(payload, dict):
                raise ValueError("payload_json must contain a JSON object")
            return self.documents.set_properties(target_path, payload)
        if command_type == "add_tags":
            tags = metadata.get("tags_to_add") or []
            if isinstance(tags, str):
                tags = [tags]
            return {"tags": self.documents.add_tags(target_path, list(tags))}
        if command_type == "mark_status":
            return self.documents.set_properties(target_path, {"status": metadata.get("new_status")})
        return self.documents.link_notes(
            target_path,
            str(metadata.get("related_path") or ""),
            field=str(metadata.get("relation_field") or "related"),
            bidirectional=bool(metadata.get("bidirectional", True)),
        )

    def _set_command_status(self, path: Path, status: str, **updates: Any) -> None:
        original = path.read_text(encoding="utf-8-sig")
        metadata, body = split_frontmatter(original)
        metadata["status"] = status
        metadata["updated_at"] = datetime.now().isoformat(timespec="seconds")
        metadata.update(updates)
        atomic_write(path, render_frontmatter(metadata, body))

    def _event(self, event_type: str, command_id: str, payload: Any) -> None:
        if self.state_db:
            self.state_db.append_event(event_type, "command", command_id, payload)

    def status(self) -> dict[str, int]:
        result = {"queued": 0, "running": 0, "done": 0, "failed": 0}
        if not self.queue_dir.exists():
            return result
        for path in self.queue_dir.glob("*.md"):
            try:
                metadata, _ = split_frontmatter(path.read_text(encoding="utf-8-sig"))
                status = str(metadata.get("status") or "")
                if status in result:
                    result[status] += 1
            except Exception:
                result["failed"] += 1
        return result


class ObsidianInteractionManager:
    """Generate core Obsidian Bases, templates and management documentation."""

    def __init__(self, layout):
        self.layout = layout

    def ensure(self) -> dict[str, list[str]]:
        result = {"created": [], "updated": [], "skipped": []}
        for relative, content in self._managed_files().items():
            path = self.layout.root / relative
            action = self._write_managed(path, content)
            result[action].append(relative)
        return result

    def _write_managed(self, path: Path, content: str) -> str:
        content = content.rstrip() + "\n"
        if not path.exists():
            atomic_write(path, content)
            return "created"
        existing = path.read_text(encoding="utf-8-sig")
        if "lingji_managed: true" not in "\n".join(existing.splitlines()[:8]):
            return "skipped"
        if existing == content:
            return "skipped"
        atomic_write(path, content)
        return "updated"

    def _managed_files(self) -> dict[str, str]:
        files = {}
        files.update(self._bases())
        files.update(self._templates())
        files.update(self._docs())
        return files

    def _bases(self) -> dict[str, str]:
        return {
            "00-System/Bases/Inbox.base": self._base(
                'file.inFolder("01-Inbox") && file.ext == "md"',
                [
                    ("待处理", 'status != "distilled" && status != "archived"', ["file.name", "status", "source_type", "project", "importance", "review_status", "file.mtime"]),
                    ("待确认", 'review_status == "needs_review"', ["file.name", "source_type", "project", "importance", "file.mtime"]),
                    ("失败", 'status == "failed"', ["file.name", "source_type", "last_error", "file.mtime"]),
                ],
            ),
            "00-System/Bases/Projects.base": self._base(
                'file.inFolder("04-Projects") && memory_type == "project"',
                [
                    ("进行中", 'status == "active" || status == "blocked"', ["file.name", "status", "phase", "progress", "priority", "next_action", "file.mtime"]),
                    ("阻塞", 'status == "blocked"', ["file.name", "blockers", "next_action", "file.mtime"]),
                    ("归档", 'status == "archived" || status == "completed"', ["file.name", "status", "updated_at"]),
                ],
            ),
            "00-System/Bases/Tasks.base": self._base(
                'file.inFolder("05-Operations/Tasks")',
                [
                    ("当前任务", 'status != "done" && status != "cancelled"', ["file.name", "status", "priority", "project", "due", "next_action", "file.mtime"]),
                    ("等待中", 'status == "waiting" || status == "blocked"', ["file.name", "status", "project", "blockers", "due"]),
                    ("已完成", 'status == "done"', ["file.name", "project", "completed_at", "updated_at"]),
                ],
            ),
            "00-System/Bases/Decisions.base": self._base(
                'file.inFolder("05-Operations/Decisions")',
                [
                    ("有效决策", 'status == "active"', ["file.name", "project", "importance", "confidence", "valid_from", "review_at", "file.mtime"]),
                    ("待复核", 'review_status == "needs_review"', ["file.name", "project", "confidence", "review_at"]),
                    ("已失效", 'status == "superseded" || status == "expired"', ["file.name", "superseded_by", "updated_at"]),
                ],
            ),
            "00-System/Bases/Knowledge.base": self._base(
                'file.inFolder("03-Knowledge")',
                [
                    ("知识总览", 'status != "archived"', ["file.name", "tags", "project", "importance", "confidence", "review_status", "file.mtime"]),
                    ("待复核", 'review_status == "needs_review"', ["file.name", "tags", "project", "confidence", "file.mtime"]),
                ],
            ),
            "00-System/Bases/Sources.base": self._base(
                'file.inFolder("02-Sources")',
                [
                    ("最近来源", 'status != "archived"', ["file.name", "source_type", "author", "published_at", "project", "review_status", "file.mtime"]),
                    ("待蒸馏", 'status == "parsed" || status == "needs_review"', ["file.name", "source_type", "project", "importance", "file.mtime"]),
                ],
            ),
            "00-System/Bases/Entities.base": self._base(
                'file.inFolder("06-Entities")',
                [("实体总览", 'status != "archived"', ["file.name", "memory_type", "aliases", "tags", "project", "file.mtime"])],
            ),
            "00-System/Bases/Commands.base": self._base(
                'file.inFolder("00-System/Commands/Queue")',
                [
                    ("待执行", 'status == "queued" || status == "running"', ["file.name", "command_type", "target_path", "status", "created_at", "last_error"]),
                    ("失败", 'status == "failed"', ["file.name", "command_type", "target_path", "last_error", "updated_at"]),
                    ("已完成", 'status == "done"', ["file.name", "command_type", "target_path", "finished_at", "result"]),
                ],
            ),
            "00-System/Bases/Memory Health.base": self._base(
                'file.ext == "md" && !file.inFolder("08-Private")',
                [
                    ("待人工确认", 'review_status == "needs_review"', ["file.name", "memory_type", "status", "source_type", "project", "file.mtime"]),
                    ("处理失败", 'status == "failed"', ["file.name", "memory_type", "last_error", "file.mtime"]),
                    ("孤立内容", 'related == null && project == null && memory_type != "dashboard"', ["file.name", "memory_type", "tags", "file.folder", "file.mtime"]),
                ],
            ),
        }

    @staticmethod
    def _base(global_filter: str, views: list[tuple[str, str, list[str]]]) -> str:
        lines = ["# lingji_managed: true", f"filters: '{global_filter}'", "views:"]
        for name, view_filter, order in views:
            lines.extend(
                [
                    "  - type: table",
                    f"    name: {json.dumps(name, ensure_ascii=False)}",
                    f"    filters: '{view_filter}'",
                    "    order:",
                ]
            )
            lines.extend(f"      - {item}" for item in order)
        return "\n".join(lines)

    def _templates(self) -> dict[str, str]:
        common = {
            "schema_version": 1,
            "id": "",
            "title": "",
            "aliases": [],
            "memory_type": "note",
            "status": "active",
            "project": [],
            "source_type": "manual",
            "privacy": "private",
            "importance": "medium",
            "confidence": "",
            "review_status": "needs_review",
            "created_at": "",
            "updated_at": "",
            "tags": [],
            "related": [],
            "people": [],
            "organizations": [],
            "tools": [],
            "models": [],
            "sources": [],
            "tasks": [],
            "decisions": [],
            "related_ids": [],
            "lingji_managed": True,
        }
        templates = {
            "通用笔记模板.md": (common, "# 标题\n\n## 一句话结论\n\n## 正文\n\n## 关联资料\n"),
            "项目模板.md": ({**common, "memory_type": "project", "phase": "planning", "progress": 0, "priority": "medium", "next_action": "", "blockers": [], "repository": ""}, "# 项目名称\n\n## 目标\n\n## 当前状态\n\n## 下一步\n\n## 关键决策\n\n## 相关资料\n"),
            "任务模板.md": ({**common, "memory_type": "task", "status": "todo", "priority": "medium", "due": "", "next_action": "", "blockers": []}, "# 任务\n\n## 完成标准\n\n## 执行记录\n\n## 结果\n"),
            "决策模板.md": ({**common, "memory_type": "decision", "status": "active", "valid_from": "", "review_at": "", "supersedes": [], "superseded_by": []}, "# 决策\n\n## 一句话结论\n\n## 决策依据\n\n## 风险\n\n## 执行结果\n"),
            "来源模板.md": ({**common, "memory_type": "source", "status": "received", "author": "", "source_url": "", "published_at": "", "content_hash": ""}, "# 来源标题\n\n## 原始内容\n\n## AI分析\n\n## 待验证\n"),
            "实体模板.md": ({**common, "memory_type": "entity", "entity_type": "person"}, "# 实体名称\n\n## 简介\n\n## 与我的关系\n\n## 相关项目\n"),
            "命令模板.md": ({**common, "memory_type": "command", "status": "queued", "command_type": "add_tags", "target_path": "", "payload_json": "{}", "tags_to_add": [], "related_path": "", "relation_field": "related", "bidirectional": True, "new_status": ""}, "# 手动管理命令\n\n> 保存后由灵机处理。删除、发布、付款和私密仓库操作不在允许范围内。\n"),
        }
        return {
            f"00-System/Templates/{name}": render_frontmatter(metadata, body)
            for name, (metadata, body) in templates.items()
        }

    def _docs(self) -> dict[str, str]:
        vault_name = quote(self.layout.root.name)
        home = f"""---
lingji_managed: true
memory_type: dashboard
status: active
privacy: private
---

# 灵机管理首页

> 一个 Vault，一套属性，一张关系网。文件夹负责生命周期，属性负责状态，链接负责关系，标签负责发现。

## 快速入口

- [[00-System/Bases/Inbox.base|收件箱管理]]
- [[00-System/Bases/Projects.base|项目管理]]
- [[00-System/Bases/Tasks.base|任务管理]]
- [[00-System/Bases/Decisions.base|决策管理]]
- [[00-System/Bases/Knowledge.base|知识管理]]
- [[00-System/Bases/Sources.base|来源管理]]
- [[00-System/Bases/Entities.base|实体管理]]
- [[00-System/Bases/Commands.base|手动命令]]
- [[00-System/Bases/Memory Health.base|记忆健康]]

## 当前待处理

![[00-System/Bases/Inbox.base#待处理]]

## 当前任务

![[00-System/Bases/Tasks.base#当前任务]]

## 项目状态

![[00-System/Bases/Projects.base#进行中]]

## 快速操作

- [打开全局搜索](obsidian://search?vault={vault_name})
- [打开今日笔记](obsidian://daily?vault={vault_name})

> 新建项目、任务、决策和命令时，优先在对应 Base 中点击“新建”，再应用 `00-System/Templates` 中的模板。
"""
        tag_dictionary = """---
lingji_managed: true
memory_type: system_rule
status: active
---

# 标签字典

标签只负责跨文件夹发现，不负责承担全部结构。每条笔记建议 3—7 个标签，最多 12 个。

## 允许的一级标签

- `domain/`：长期领域，例如 `domain/ai`、`domain/business`、`domain/directing`
- `topic/`：具体主题，例如 `topic/obsidian`、`topic/comfyui`
- `source/`：入口来源，例如 `source/chatgpt`、`source/wechat`
- `signal/`：内容信号，例如 `signal/opportunity`、`signal/risk`、`signal/error`
- `attention/`：人工关注，例如 `attention/favorite`、`attention/review`、`attention/urgent`

## 不使用标签表达

- 项目：使用 `project` 链接属性
- 状态：使用 `status` 属性
- 类型：使用 `memory_type` 属性
- 人物和工具：使用 `people`、`tools` 等链接属性
- 隐私：使用 `privacy` 属性

同一个概念禁止同时出现多种拼写。新增一级标签必须先修改本字典。
"""
        property_dictionary = """---
lingji_managed: true
memory_type: system_rule
status: active
---

# 属性字典

## 核心身份

- `id`：稳定机器 ID，移动文件时保持不变
- `title`：人类可读标题
- `aliases`：别名列表
- `memory_type`：project、task、decision、source、knowledge、entity、command 等

## 生命周期

- `status`：received、queued、processing、needs_review、active、blocked、done、superseded、archived、failed
- `review_status`：needs_review、approved、rejected
- `created_at`、`updated_at`：时间

## 关系

- `project`：所属项目链接列表
- `people`、`organizations`、`tools`、`models`：实体链接列表
- `sources`、`tasks`、`decisions`、`related`：业务关系链接列表
- `related_ids`：供程序稳定追踪的 ID 列表

## 质量与权限

- `importance`：low、medium、high、critical
- `confidence`：low、medium、high 或数值
- `privacy`：private、restricted、public

禁止随意创建同义属性，例如同时使用 `project_id`、`project-name`、`项目` 表达同一含义。
"""
        relation_rules = """---
lingji_managed: true
memory_type: system_rule
status: active
---

# 关系互联规则

## 四层关系

1. 文件夹：表示来源或生命周期位置。
2. 属性：表示可筛选、可排序的结构化状态。
3. 内部链接：表示人与项目、来源与结论、任务与决策之间的真实关系。
4. 向量相似度：只负责发现可能相关内容，不自动认定为正式关系。

## 建链规则

- 结论必须链接到 `sources`
- 任务必须链接到 `project`
- 决策必须链接到 `project`，必要时链接到 `sources`
- 工具、模型、人物统一链接到 `06-Entities`
- AI 建议的关系先写入 `related` 并标记 `review_status: needs_review`
- 主人确认后才能作为正式决策依据

不要为了让图谱更密而滥建链接。没有业务含义的双链只是线条，不是记忆。
"""
        manual_guide = """---
lingji_managed: true
memory_type: system_guide
status: active
---

# 手动管理指南

## 日常使用顺序

1. 内容先进入 `01-Inbox`。
2. 在 Inbox Base 中修改 `project`、`importance`、`review_status` 和标签。
3. 确认有价值后，移动到 `02-Sources`、`03-Knowledge` 或具体项目目录。
4. 任务、决策和实体分别使用独立模板创建。
5. 需要批量修改或建立双向关系时，新建“命令模板”并放入 `00-System/Commands/Queue`。

## 允许的命令

- `set_properties`
- `add_tags`
- `link_note`
- `mark_status`

命令不会执行删除、对外发布、付款或读取 `08-Private`。这些限制不是缺陷，是为了避免 AI 用惊人的效率替你后悔。
"""
        return {
            "00-System/Home.md": home,
            "00-System/Tag-Dictionary.md": tag_dictionary,
            "00-System/Property-Dictionary.md": property_dictionary,
            "00-System/Relationship-Rules.md": relation_rules,
            "00-System/Manual-Management-Guide.md": manual_guide,
        }
