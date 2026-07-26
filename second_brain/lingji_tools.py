"""
LingJi (lingji) 统一工具服务层 - 封装 ObsidianCli 提供统一接口
"""
import os as _os
from pathlib import Path as _Path
# 加载 .env.second-brain 环境变量
_env_path = _Path(__file__).resolve().parents[1] / ".env.second-brain"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8-sig").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _os.environ.setdefault(_k.strip(), _v.strip().strip(chr(34)))

import json, os, sys, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from second_brain.config import ROOT  # triggers .env loading

from second_brain.obsidian_cli import ObsidianCli, ObsidianCliError
from second_brain.utils import utc_now




def tool_result(ok, data=None, error=None, tool="", duration_ms=0.0, task_id=None):
    """构建统一工具返回结构"""
    return {
        "ok": ok,
        "data": data if data is not None else {},
        "error": error,
        "meta": {
            "tool": tool,
            "duration_ms": round(duration_ms, 2),
            "timestamp": utc_now(),
            "task_id": task_id or "",
        },
    }


FRONTMATTER_TEMPLATE = """---
title: {title}
created: {created}
updated: {updated}
source: {source}
source_type: {source_type}
tags: [{tags_str}]
task_id: {task_id}
status: {status}
indexed: {indexed}
---"""


def build_frontmatter(title, source="lingji_tools", source_type="system",
                      tags=None, task_id=None, status="draft", indexed=False):
    """生成统一 Frontmatter 元数据"""
    now = utc_now()
    return {
        "title": title, "created": now, "updated": now,
        "source": source, "source_type": source_type,
        "tags": tags or [], "task_id": task_id or "",
        "status": status, "indexed": indexed,
    }


def render_frontmatter(fm):
    """将 Frontmatter 字典渲染为 YAML 字符串"""
    tl = fm.get("tags", [])
    ts = ", ".join(str(t) for t in tl) if isinstance(tl, list) else str(tl)
    return FRONTMATTER_TEMPLATE.format(
        title=fm.get("title", ""),
        created=fm.get("created", utc_now()),
        updated=fm.get("updated", utc_now()),
        source=fm.get("source", "lingji_tools"),
        source_type=fm.get("source_type", "system"),
        tags_str=ts,
        task_id=fm.get("task_id", ""),
        status=fm.get("status", "draft"),
        indexed="true" if fm.get("indexed", False) else "false",
    )


MAX_BATCH_SIZE = 20
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_TASK_LIMIT = 20
DEFAULT_TAG_LIMIT = 30

@dataclass
class LingJiToolsConfig:
    """LingJi 工具层配置，从环境变量读取"""
    dry_run: bool = False
    task_id: str = ""
    batch_limit: int = MAX_BATCH_SIZE

    @classmethod
    def from_env(cls) -> "LingJiToolsConfig":
        return cls(dry_run=os.getenv("LINGJI_TOOLS_DRY_RUN", "0") == "1")


class LingJiTools:
    """灵机统一工具服务 - 封装 ObsidianCli + Frontmatter + 验证"""

    def __init__(self, obsidian_cli=None, config=None):
        self.obsidian = obsidian_cli or ObsidianCli()
        self.config = config or LingJiToolsConfig.from_env()
        self._log = []

    # ---------- 内部方法 ----------

    def _ok(self, data=None, tool="", task_id=None):
        return {"ok": True, "data": data if data is not None else {}, "error": None,
                "meta": {"tool": tool, "duration_ms": 0, "timestamp": utc_now(),
                         "task_id": task_id or self.config.task_id or ""}}

    def _err(self, error, tool="", task_id=None):
        return {"ok": False, "data": {}, "error": error,
                "meta": {"tool": tool, "duration_ms": 0, "timestamp": utc_now(),
                         "task_id": task_id or self.config.task_id or ""}}

    def _time(self, tool, func, *args, **kwargs):
        """计时执行并返回统一结果"""
        start = time.monotonic()
        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict) and "ok" in result:
                result["meta"]["tool"] = tool
                result["meta"]["duration_ms"] = round((time.monotonic() - start) * 1000, 2)
                result["meta"]["timestamp"] = utc_now()
                return result
            return self._ok(data=result, tool=tool)
        except ObsidianCliError as e:
            return self._err(str(e), tool=tool)
        except FileNotFoundError as e:
            return self._err(f"文件未找到: {e}", tool=tool)
        except ValueError as e:
            return self._err(str(e), tool=tool)
        except PermissionError as e:
            return self._err(f"权限错误: {e}", tool=tool)
        except Exception as e:
            return self._err(f"{type(e).__name__}: {e}", tool=tool)
        finally:
            self._log.append({
                "tool": tool, "timestamp": utc_now(), "task_id": self.config.task_id,
            })

    def _dry_run_guard(self, tool):
        """检查 dry-run 模式"""
        if self.config.dry_run:
            self._log.append({
                "tool": tool, "dry_run": True, "timestamp": utc_now(), "task_id": self.config.task_id,
            })
            return True
        return False

    def _require_obsidian(self):
        """检查 Obsidian CLI 是否可用"""
        health = self.obsidian.health()
        if not health.get("available", False):
            issues = "; ".join(health.get("issues", []))
            return self._err(f"Obsidian CLI 不可用: {issues}", tool="health_check")
        return None

    def _operate(self, tool, operation, details=""):
        """记录操作日志"""
        self._log.append({
            "tool": tool, "operation": operation, "details": details,
            "timestamp": utc_now(), "task_id": self.config.task_id, "dry_run": self.config.dry_run,
        })

    # ============================================================
    # Obsidian Vault 操作
    # ============================================================

    def search_notes(self, query, limit=DEFAULT_SEARCH_LIMIT):
        """搜索笔记"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            results = self.obsidian.search(query, limit=limit)
            self._operate("search_notes", "search", f"query={query}, limit={limit}")
            return {"notes": results, "total": len(results)}
        return self._time("search_notes", _do)

    def read_note(self, path):
        """读取笔记内容"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            content = self.obsidian.read(path)
            fm = {}
            body = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    body = parts[2].strip()
                    for line in parts[1].strip().split("\n"):
                        if ":" in line and not line.startswith("---"):
                            k, v = line.split(":", 1)
                            fm[k.strip()] = v.strip()
            self._operate("read_note", "read", f"path={path}")
            return {"content": body, "path": path, "frontmatter": fm, "raw": content}
        return self._time("read_note", _do)

    def create_note(self, path, content, metadata=None, overwrite=False):
        """创建笔记（带 Frontmatter + 写入验证）"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            if self._dry_run_guard("create_note"):
                return {"dry_run": True, "path": path}
            md = metadata or {}
            fm = build_frontmatter(
                title=Path(path).stem,
                source=md.get("source", "lingji_tools"),
                source_type=md.get("source_type", "system"),
                tags=md.get("tags"),
                task_id=md.get("task_id"),
            )
            for k in ("title", "created", "updated"):
                if k in md:
                    fm[k] = md[k]
            full = render_frontmatter(fm) + "\n\n" + content
            self.obsidian.create(path, full, overwrite=overwrite)
            v = self.obsidian.read(path)
            if not v:
                raise ObsidianCliError(f"创建后验证失败: {path}")
            self._operate("create_note", "create", f"path={path}")
            return {"path": path, "title": fm["title"], "verified": True}
        return self._time("create_note", _do)

    def append_note(self, path, content):
        """追加内容到已有笔记"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            if self._dry_run_guard("append_note"):
                return {"dry_run": True, "path": path}
            self.obsidian.append(path, content)
            v = self.obsidian.read(path)
            if not v:
                raise ObsidianCliError(f"追加后验证失败: {path}")
            self._operate("append_note", "append", f"path={path}")
            return {"path": path, "verified": True}
        return self._time("append_note", _do)

    def append_daily(self, content):
        """追加内容到今日 Daily Note"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            if self._dry_run_guard("append_daily"):
                return {"dry_run": True}
            self.obsidian.append_daily(content)
            dp = self.obsidian.get_daily_path()
            self._operate("append_daily", "append", f"daily={dp}")
            return {"daily_path": dp, "verified": True}
        return self._time("append_daily", _do)

    def list_tasks(self, status=None, limit=DEFAULT_TASK_LIMIT):
        """列出任务"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            done = {"todo": False, "done": True}.get(status) if status else None
            tasks = self.obsidian.list_tasks(done=done)
            self._operate("list_tasks", "list", f"status={status}")
            return {"tasks": tasks[:limit], "total": len(tasks)}
        return self._time("list_tasks", _do)

    def list_tags(self, limit=DEFAULT_TAG_LIMIT):
        """列出标签"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            tags = self.obsidian.list_tags()
            self._operate("list_tags", "list", f"limit={limit}")
            return {"tags": tags[:limit], "total": len(tags)}
        return self._time("list_tags", _do)

    def get_vault_info(self):
        """获取 Vault 信息"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            info = self.obsidian.get_vault_info()
            return {
                "name": info.name, "path": info.path,
                "file_count": info.file_count, "folder_count": info.folder_count,
                "size": info.size,
            }
        return self._time("get_vault_info", _do)

    # ============================================================
    # 高级知识操作
    # ============================================================

    def create_knowledge_entry(self, title, content, source="lingji_tools",
                                tags=None, task_id=None):
        """创建知识条目到 Vault"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            if self._dry_run_guard("create_knowledge_entry"):
                return {"dry_run": True, "title": title}
            now = datetime.now(timezone.utc)
            dp = now.strftime("知识库/%Y/%m")
            st = ObsidianCli.sanitize_filename(title)[:60]
            np = f"{dp}/{st}.md"
            fm = build_frontmatter(title=title, source=source, source_type="knowledge",
                                   tags=tags or [], task_id=task_id or self.config.task_id,
                                   status="published")
            full = render_frontmatter(fm) + "\n\n" + content
            self.obsidian.create(np, full, overwrite=False)
            v = self.obsidian.read(np)
            if not v:
                raise ObsidianCliError(f"知识条目创建后验证失败: {np}")
            self._operate("create_knowledge_entry", "create", f"title={title}")
            return {"path": np, "title": title, "verified": True}
        return self._time("create_knowledge_entry", _do)

    def create_ai_news_entry(self, title, summary, source_url="",
                              published_at="", tags=None):
        """创建 AI 新闻条目"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            if self._dry_run_guard("create_ai_news_entry"):
                return {"dry_run": True, "title": title}
            now = datetime.now(timezone.utc)
            dp = now.strftime("AI新闻/%Y/%m")
            st = ObsidianCli.sanitize_filename(title)[:50]
            np = f"{dp}/{st}.md"
            at = list(set((tags or []) + ["ai-news"]))
            fm = build_frontmatter(title=title, source=source_url or "ai_news",
                                   source_type="ai_news", tags=at,
                                   task_id=self.config.task_id, status="published")
            meta = ""
            if source_url:
                meta += f"\n- [来源]({source_url})"
            if published_at:
                meta += f"\n- 日期: {published_at}"
            meta += f"\n- 记录: {utc_now()}"
            full = render_frontmatter(fm) + f"\n\n## {title}\n{meta}\n\n---\n\n{summary}"
            self.obsidian.create(np, full, overwrite=False)
            v = self.obsidian.read(np)
            if not v:
                raise ObsidianCliError(f"AI 新闻创建后验证失败: {np}")
            self._operate("create_ai_news_entry", "create", f"title={title}")
            return {"path": np, "title": title, "verified": True}
        return self._time("create_ai_news_entry", _do)

    def create_opportunity_entry(self, title, summary, source="",
                                  score=0.0, tags=None):
        """创建商业机会条目"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            if self._dry_run_guard("create_opportunity_entry"):
                return {"dry_run": True, "title": title}
            sc = max(0.0, min(10.0, score))
            at = list(set((tags or []) + ["opportunity"]))
            fm = build_frontmatter(title=title, source=source or "lingji_tools",
                                   source_type="opportunity", tags=at,
                                   task_id=self.config.task_id, status="draft")
            st = ObsidianCli.sanitize_filename(title)[:50]
            np = f"PEMIS/opportunities/{st}.md"
            full = render_frontmatter(fm) + f"\n\n## {title}\n\n- 来源: {source or '未知'}\n- 评分: {sc}/10\n- 记录: {utc_now()}\n\n---\n\n{summary}"
            self.obsidian.create(np, full, overwrite=False)
            v = self.obsidian.read(np)
            if not v:
                raise ObsidianCliError(f"机会条目创建后验证失败: {np}")
            self._operate("create_opportunity_entry", "create", f"title={title}")
            return {"path": np, "title": title, "score": sc, "verified": True}
        return self._time("create_opportunity_entry", _do)

    # ============================================================
    # 索引操作
    # ============================================================

    def reindex_note(self, path, vault_root=""):
        """重索引单篇笔记（只读预览模式，全量索引需要 ObsidianConnector）"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            np = Path(path)
            if not np.is_absolute() and self.obsidian.config.vault_path:
                np = Path(self.obsidian.config.vault_path) / path
            if not np.exists():
                raise FileNotFoundError(f"笔记不存在: {np}")
            rp = str(np.relative_to(Path(self.obsidian.config.vault_path))
                    ) if self.obsidian.config.vault_path else path
            cr = self.read_note(rp)
            if not cr["ok"]:
                return cr
            self._operate("reindex_note", "preview", f"path={rp}")
            return {"path": rp, "content_length": len(cr["data"].get("raw", "")),
                    "reindex_requested": True}
        return self._time("reindex_note", _do)

    def reindex_changed_notes(self):
        """批量重索引已变更的笔记（预览模式）"""
        def _do():
            err = self._require_obsidian()
            if err:
                return err
            files = self.obsidian.list_files(ext=".md")
            self._operate("reindex_changed_notes", "preview", f"total={len(files)}")
            return {"total": len(files), "reindexed": 0, "preview": files[:10]}
        return self._time("reindex_changed_notes", _do)

    # ============================================================
    # 系统和健康检查
    # ============================================================

    def health_check(self):
        """健康检查"""
        def _do():
            h = self.obsidian.health()
            return {
                "cli_available": h.get("available", False),
                "version": h.get("version", "未知"),
                "vault_name": h.get("vault_name", ""),
                "vault_path": h.get("vault_path", ""),
                "cli_path": h.get("cli_path", ""),
                "issues": h.get("issues", []),
                "dry_run": self.config.dry_run,
                "task_id": self.config.task_id or "未设置",
                "tool_layer": "lingji_tools v0.1.0",
            }
        return self._time("health_check", _do)

    def get_system_status(self):
        """获取系统状态"""
        def _do():
            h = self.obsidian.health()
            cok = h.get("available", False)
            vi, tc, tg = {}, 0, 0
            if cok:
                try:
                    info = self.obsidian.get_vault_info()
                    vi = {"file_count": info.file_count, "folder_count": info.folder_count, "size": info.size}
                except Exception:
                    vi = {"file_count": 0}
                try:
                    tc = len(self.obsidian.list_tasks())
                except Exception:
                    tc = -1
                try:
                    tg = len(self.obsidian.list_tags())
                except Exception:
                    tg = -1
            return {
                "status": "ok" if cok else "degraded",
                "cli": {"available": cok, "version": h.get("version", "未知"), "path": h.get("cli_path", "")},
                "vault": {"name": h.get("vault_name", ""), "path": h.get("vault_path", ""), **vi},
                "tool_layer": {"version": "0.1.0", "dry_run": self.config.dry_run,
                               "task_id": self.config.task_id or "", "operations": len(self._log)},
                "counts": {"tasks": tc, "tags": tg},
                "issues": h.get("issues", []),
            }
        return self._time("get_system_status", _do)

    def get_operation_log(self, limit=50):
        """获取操作日志"""
        logs = list(self._log[-limit:])
        return self._ok(data={"logs": logs, "total": len(self._log)}, tool="get_operation_log")

# ============================================================
# 命令行入口
# ============================================================

def main():
    """命令行入口: python -m second_brain.lingji_tools health_check"""
    import argparse
    p = argparse.ArgumentParser(description="LingJi 工具服务命令行")
    p.add_argument("tool", help="工具名称")
    p.add_argument("--query", help="搜索关键词")
    p.add_argument("--path", help="笔记路径")
    p.add_argument("--content", help="内容")
    p.add_argument("--title", help="标题")
    p.add_argument("--status", choices=["todo", "done"], help="任务状态")
    p.add_argument("--limit", type=int, default=DEFAULT_SEARCH_LIMIT, help="数量限制")
    p.add_argument("--source", default="lingji_tools", help="来源")
    p.add_argument("--tags", nargs="*", default=[], help="标签")
    p.add_argument("--score", type=float, default=0.0, help="评分")
    p.add_argument("--overwrite", action="store_true", help="覆盖")
    p.add_argument("--dry-run", action="store_true", help="dry-run 模式")
    p.add_argument("--task-id", help="任务 ID")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    args = p.parse_args()

    cfg = LingJiToolsConfig(dry_run=args.dry_run or False, task_id=args.task_id or "")
    tools = LingJiTools(config=cfg)

    tool_map = {
        "health_check": lambda: tools.health_check(),
        "get_system_status": lambda: tools.get_system_status(),
        "get_vault_info": lambda: tools.get_vault_info(),
        "search_notes": lambda: tools.search_notes(args.query, args.limit),
        "read_note": lambda: tools.read_note(args.path),
        "list_tasks": lambda: tools.list_tasks(args.status, args.limit),
        "list_tags": lambda: tools.list_tags(args.limit),
        "get_operation_log": lambda: tools.get_operation_log(args.limit),
        "create_knowledge_entry": lambda: tools.create_knowledge_entry(
            title=args.title or args.path or "未命名", content=args.content or "",
            source=args.source, tags=list(args.tags), task_id=args.task_id),
        "create_ai_news_entry": lambda: tools.create_ai_news_entry(
            title=args.title or "AI 新闻", summary=args.content or "", tags=list(args.tags)),
        "create_opportunity_entry": lambda: tools.create_opportunity_entry(
            title=args.title or "机会", summary=args.content or "",
            source=args.source, score=args.score, tags=list(args.tags)),
        "reindex_note": lambda: tools.reindex_note(args.path),
        "reindex_changed_notes": lambda: tools.reindex_changed_notes(),
    }

    fn = tool_map.get(args.tool)
    if fn is None:
        print(f"错误: 未知工具 '{args.tool}'")
        print(f"可用: {', '.join(sorted(tool_map.keys()))}")
        sys.exit(1)

    result = fn()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["ok"]:
            print(f"[OK] {result['meta']['tool']}")
            print(json.dumps(result["data"], ensure_ascii=False, indent=2, default=str))
        else:
            print(f"[FAIL] {result['meta']['tool']}: {result['error']}")
        print(f"  time={result['meta']['duration_ms']}ms  ts={result['meta']['timestamp']}")
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
