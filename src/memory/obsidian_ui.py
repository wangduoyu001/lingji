from __future__ import annotations

import json
from pathlib import Path

from src.obsidian.frontmatter import atomic_write, render_frontmatter


class PermanentMemoryObsidianManager:
    """Generate owner-facing permanent-memory review views in Obsidian."""

    def __init__(self, layout):
        self.layout = layout

    def ensure(self) -> dict[str, list[str]]:
        result = {"created": [], "updated": [], "skipped": []}
        for relative, content in self._files().items():
            action = self._write(self.layout.root / relative, content)
            result[action].append(relative)
        return result

    def _write(self, path: Path, content: str) -> str:
        normalized = content.rstrip() + "\n"
        if not path.exists():
            atomic_write(path, normalized)
            return "created"
        existing = path.read_text(encoding="utf-8-sig")
        if "lingji_managed: true" not in "\n".join(existing.splitlines()[:8]):
            return "skipped"
        if existing == normalized:
            return "skipped"
        atomic_write(path, normalized)
        return "updated"

    def _files(self) -> dict[str, str]:
        base = "\n".join(
            [
                "# lingji_managed: true",
                "filters: 'memory_tier != null && file.ext == \"md\"'",
                "views:",
                "  - type: table",
                f"    name: {json.dumps('核心记忆', ensure_ascii=False)}",
                "    filters: 'memory_tier == \"core\" && status == \"active\"'",
                "    order:",
                "      - file.name",
                "      - importance",
                "      - agent_scope",
                "      - recall_weight",
                "      - valid_from",
                "      - valid_to",
                "      - file.mtime",
                "  - type: table",
                f"    name: {json.dumps('AI候选', ensure_ascii=False)}",
                "    filters: 'memory_tier == \"candidate\" && review_status == \"needs_review\"'",
                "    order:",
                "      - file.name",
                "      - proposed_by",
                "      - importance",
                "      - confidence",
                "      - project",
                "      - created_at",
                "  - type: table",
                f"    name: {json.dumps('已失效', ensure_ascii=False)}",
                "    filters: 'status == \"superseded\" || status == \"rejected\" || valid_to != null'",
                "    order:",
                "      - file.name",
                "      - status",
                "      - superseded_by",
                "      - valid_to",
                "      - updated_at",
            ]
        )
        center = """---
lingji_managed: true
memory_type: dashboard
status: active
privacy: private
---

# 永久记忆中心

> 永久记忆不是“搜到过的所有内容”。只有主人确认的少量核心事实、偏好、目标、约束和工作规则，才会固定注入各 AI 的上下文。

## 核心记忆

![[00-System/Bases/Permanent Memory.base#核心记忆]]

## 待审核候选

![[00-System/Bases/Permanent Memory.base#AI候选]]

## 已失效与被替代

![[00-System/Bases/Permanent Memory.base#已失效]]

## 操作规则

1. AI 只能在 `01-Inbox/AI-Memory` 提议候选。
2. 主人确认后，程序才能移动到 `03-Knowledge/Core-Memory`。
3. 变化中的事实必须填写 `valid_from` 和 `valid_to`。
4. 新事实替代旧事实时，保留 `superseded_by`，不直接删除历史。
5. `pin_to_context: true` 的核心记忆会优先进入 Context Pack。
6. 远程 AI 默认不能读取 `privacy: restricted`。

核心记忆应保持短、稳定、可核查。把所有聊天记录都钉进上下文，只会得到一个记得很多但思考时喘不过气的模型。
"""
        template_metadata = {
            "schema_version": 1,
            "id": "",
            "title": "",
            "memory_type": "knowledge",
            "memory_tier": "core",
            "status": "active",
            "review_status": "approved",
            "privacy": "private",
            "importance": "high",
            "confidence": "high",
            "pin_to_context": True,
            "agent_scope": ["all"],
            "recall_weight": 1.2,
            "valid_from": "",
            "valid_to": "",
            "supersedes": [],
            "superseded_by": "",
            "sources": [],
            "project": [],
            "tags": ["signal/core-memory"],
            "created_at": "",
            "updated_at": "",
            "lingji_managed": True,
        }
        template_body = """# 核心记忆标题

## 核心事实

请保持简短、明确、可验证。

## 适用范围

## 来源与依据

## 失效条件
"""
        return {
            "00-System/Bases/Permanent Memory.base": base,
            "00-System/Permanent-Memory.md": center,
            "00-System/Templates/核心记忆模板.md": render_frontmatter(
                template_metadata,
                template_body,
            ),
        }
