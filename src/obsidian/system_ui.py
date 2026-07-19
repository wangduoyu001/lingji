from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from src.obsidian.frontmatter import atomic_write, render_frontmatter


class LingJiSystemUI:
    """Generate owner-facing Bases, templates and status pages in Obsidian."""

    def __init__(self, layout, extraction_pipeline=None, skill_registry=None, request_inbox=None):
        self.layout = layout
        self.pipeline = extraction_pipeline
        self.skills = skill_registry
        self.requests = request_inbox

    def ensure(self) -> dict[str, list[str]]:
        result = {"created": [], "updated": [], "skipped": []}
        for relative, content in self._managed_files().items():
            action = self._write_managed(self.layout.root / relative, content)
            result[action].append(relative)
        self.refresh_status()
        return result

    def refresh_status(self) -> dict[str, str]:
        extraction_path = self.layout.root / "00-System" / "Extraction-Center.md"
        skills_path = self.layout.root / "00-System" / "Skills-Center.md"
        atomic_write(extraction_path, self._extraction_center())
        atomic_write(skills_path, self._skills_center())
        return {
            "extraction_center": str(extraction_path),
            "skills_center": str(skills_path),
        }

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
        return {
            "00-System/Bases/Extraction Sources.base": self._base(
                'file.inFolder("02-Sources") || file.inFolder("08-Private/Imports")',
                [
                    (
                        "全部采集来源",
                        'memory_type == "source"',
                        [
                            "file.name",
                            "source_type",
                            "platform",
                            "author",
                            "content_completeness",
                            "privacy",
                            "status",
                            "published_at",
                            "file.mtime",
                        ],
                    ),
                    (
                        "视频与社交平台",
                        'platform == "video_channel" || platform == "douyin" || platform == "xiaohongshu" || platform == "bilibili" || platform == "youtube"',
                        [
                            "file.name",
                            "platform",
                            "account_name",
                            "duration_seconds",
                            "content_completeness",
                            "status",
                            "file.mtime",
                        ],
                    ),
                    (
                        "需要补采",
                        'status == "needs_review" || content_completeness == "metadata_only"',
                        ["file.name", "platform", "source_url", "content_completeness", "review_status"],
                    ),
                    (
                        "敏感来源",
                        'privacy == "restricted"',
                        ["file.name", "source_type", "sensitivity_findings", "file.folder", "file.mtime"],
                    ),
                ],
            ),
            "00-System/Bases/Work Reports.base": self._base(
                'file.inFolder("05-Operations/Work-Reports")',
                [
                    (
                        "最近交付",
                        'memory_type == "work_report"',
                        [
                            "file.name",
                            "project",
                            "repository",
                            "branch",
                            "task_id",
                            "execution_id",
                            "test_result",
                            "status",
                            "file.mtime",
                        ],
                    )
                ],
            ),
            "00-System/Bases/Skills.base": self._base(
                'file.inFolder("07-Assets/Skills") && memory_type == "skill"',
                [
                    (
                        "可用 Skills",
                        'status == "active"',
                        [
                            "file.name",
                            "version",
                            "compatible_agents",
                            "capabilities",
                            "last_verified_at",
                            "review_status",
                            "file.mtime",
                        ],
                    ),
                    (
                        "待验证",
                        'review_status == "needs_review" || last_verified_at == null || version == "unknown"',
                        ["file.name", "source_path", "repository", "tests", "file.mtime"],
                    ),
                    (
                        "已停用",
                        'status == "disabled" || status == "archived"',
                        ["file.name", "status", "version", "source_path", "updated_at"],
                    ),
                ],
            ),
            "00-System/Bases/Extraction Requests.base": self._base(
                'file.inFolder("00-System/Extraction/Requests") && memory_type == "extraction_request"',
                [
                    (
                        "待处理",
                        'status == "queued" || status == "running"',
                        ["file.name", "request_type", "source_type", "input_path", "source_url", "status", "last_error"],
                    ),
                    (
                        "失败",
                        'status == "failed"',
                        ["file.name", "request_type", "last_error", "updated_at"],
                    ),
                    (
                        "已完成",
                        'status == "done"',
                        ["file.name", "request_type", "finished_at", "result_json"],
                    ),
                ],
            ),
            "00-System/Templates/ChatGPT导入请求.md": self._request_template(
                {
                    "request_type": "chatgpt_import",
                    "input_path": "D:/exports/chatgpt.zip",
                    "project": [],
                    "privacy_scan": True,
                    "force": False,
                },
                "# ChatGPT 导入请求\n\n> 修改 input_path 和项目后保存。灵机会先做 ZIP 安全检查和敏感内容分流。\n",
            ),
            "00-System/Templates/网页与视频号采集请求.md": self._request_template(
                {
                    "request_type": "web_capture",
                    "source_type": "video_channel",
                    "platform": "video_channel",
                    "source_url": "",
                    "account_name": "",
                    "published_at": "",
                    "duration_seconds": "",
                    "cover_url": "",
                    "media_url": "",
                    "project": [],
                },
                "# 网页或视频号采集请求\n\n将浏览器选中文字、视频简介、转写或 OCR 粘贴在这里。只有链接时也能保存，但会标记为需要补采。\n",
            ),
            "00-System/Templates/Skill同步请求.md": self._request_template(
                {
                    "request_type": "skill_sync",
                    "input_path": "D:/codex/skills",
                },
                "# Skill 同步请求\n\n> 扫描目录中的 SKILL.md，代码不复制进 Obsidian，只登记元数据、文档和验证状态。\n",
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

    @staticmethod
    def _request_template(extra: dict[str, Any], body: str) -> str:
        metadata = {
            "schema_version": 1,
            "id": "",
            "title": "",
            "memory_type": "extraction_request",
            "status": "queued",
            "privacy": "private",
            "created_at": "",
            "updated_at": "",
            "lingji_managed": True,
            **extra,
        }
        return render_frontmatter(metadata, body)

    def _extraction_center(self) -> str:
        now = datetime.now().isoformat(timespec="seconds")
        queue = self.pipeline.queue.stats() if self.pipeline else {}
        adapters = self.pipeline.registry.list() if self.pipeline else []
        requests = self.requests.status() if self.requests else {}
        recent = self.pipeline.queue.list(limit=15) if self.pipeline else []
        vault_name = quote(self.layout.root.name)
        lines = [
            "---",
            "lingji_managed: true",
            "memory_type: dashboard",
            "status: active",
            "privacy: private",
            f"updated_at: {now}",
            "---",
            "",
            "# 提取与采集中心",
            "",
            "> 统一管理 ChatGPT、Codex、网页、公众号、视频号、抖音、小红书及后续媒体提取。",
            "",
            "## 快速入口",
            "",
            "- [[00-System/Bases/Extraction Requests.base|采集请求队列]]",
            "- [[00-System/Bases/Extraction Sources.base|全部采集来源]]",
            "- [[00-System/Bases/Work Reports.base|Codex 工作报告]]",
            "- [[00-System/Skills-Center|Skill 管理中心]]",
            f"- [新建 ChatGPT 导入请求](obsidian://new?vault={vault_name}&file=00-System/Extraction/Requests/ChatGPT-Import)",
            f"- [新建网页或视频号采集请求](obsidian://new?vault={vault_name}&file=00-System/Extraction/Requests/Web-Capture)",
            "",
            "## 队列状态",
            "",
            f"- SQLite任务：`{json.dumps(queue, ensure_ascii=False)}`",
            f"- Obsidian请求：`{json.dumps(requests, ensure_ascii=False)}`",
            "",
            "## 已注册适配器",
            "",
        ]
        for item in adapters:
            lines.append(f"- `{item.get('name')}` `{item.get('version')}`：{', '.join(item.get('source_types') or [])}")
        lines.extend(["", "## 最近任务", ""])
        for job in recent:
            lines.append(
                f"- `{job.get('job_id')}` · {job.get('source_type')} · **{job.get('status')}** · "
                f"{job.get('progress_message') or ''} · {job.get('last_error') or ''}"
            )
        lines.extend(
            [
                "",
                "## 平台能力说明",
                "",
                "- 普通公开网页：可受控抓取或接收浏览器快照。",
                "- 公众号文章：优先保存分享链接和浏览器渲染正文。",
                "- 视频号、抖音、小红书：优先接收主动分享、浏览器快照、录屏、本地媒体、转写和 OCR；缺失正文时保留元数据并进入补采视图。",
                "- 登录态和私密内容：不得在后台偷取 Cookie，必须由主人明确授权并主动投喂。",
                "",
                "![[00-System/Bases/Extraction Requests.base#待处理]]",
                "",
            ]
        )
        return "\n".join(lines)

    def _skills_center(self) -> str:
        now = datetime.now().isoformat(timespec="seconds")
        status = self.skills.status() if self.skills else {}
        vault_name = quote(self.layout.root.name)
        return "\n".join(
            [
                "---",
                "lingji_managed: true",
                "memory_type: dashboard",
                "status: active",
                "privacy: private",
                f"updated_at: {now}",
                "---",
                "",
                "# Skill 管理中心",
                "",
                "> Obsidian 管理 Skill 的说明、状态、能力、触发条件、依赖、版本和测试证据。可执行代码仍以 Git 仓库或安装目录为权威。",
                "",
                f"- 当前状态：`{json.dumps(status, ensure_ascii=False)}`",
                "- [[00-System/Bases/Skills.base|打开 Skill 总表]]",
                f"- [新建 Skill 同步请求](obsidian://new?vault={vault_name}&file=00-System/Extraction/Requests/Skill-Sync)",
                "",
                "## 可用 Skills",
                "",
                "![[00-System/Bases/Skills.base#可用 Skills]]",
                "",
                "## 待验证",
                "",
                "![[00-System/Bases/Skills.base#待验证]]",
                "",
            ]
        )
