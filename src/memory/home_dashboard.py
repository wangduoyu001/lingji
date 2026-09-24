"""Vault 根部 Home 仪表盘（主人"Vault 没有存在感"的正面解法）。

自动晋升管线每次运行后刷新一张托管笔记 Home.md：记忆计数、最近晋升、
最近 Evolving 时间线——主人打开 Obsidian 第一眼就看见"它在生长"。

安全边界：只写 `Home.md` 这一个托管文件（frontmatter 带 lingji_managed），
主人手写的同名笔记存在时绝不覆盖（改名让位），其余文件一律不碰。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME_NAME = "Home.md"
_MANAGED_MARKER = "lingji_managed: true"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _latest_notes(directory: Path, limit: int) -> list[Path]:
    if not directory.is_dir():
        return []
    files = [p for p in directory.rglob("*.md") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def _wiki(path: Path, vault: Path) -> str:
    return f"[[{path.relative_to(vault).with_suffix('').as_posix()}]]"


def _count_markdown(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for p in directory.rglob("*.md") if p.is_file())


def build_home_markdown(vault: Path, *, wiki_links: bool = True) -> str:
    core_dir = vault / "03-Knowledge" / "Core-Memory"
    evolving_dir = vault / "03-Knowledge" / "Evolving"
    core_latest = _latest_notes(core_dir, 8)
    evolving_latest = _latest_notes(evolving_dir, 8)

    def ref(path: Path) -> str:
        if wiki_links:
            return _wiki(path, vault)
        return "`" + path.relative_to(vault).as_posix() + "`"

    lines = [
        "---",
        _MANAGED_MARKER,
        "title: 灵机 · 记忆首页",
        f"updated_at: {_now_iso()}",
        "---",
        "",
        "# 灵机 · 记忆首页",
        "",
        "> 本页由灵机自动维护（托管文件）。每次自动整理后刷新；",
        "> 手写内容请另建笔记，本文件不会被你的手写覆盖（若同名会自动让位）。",
        "",
        "## 记忆存量",
        "",
        f"- 永久记忆（Core）：{_count_markdown(core_dir)} 篇",
        f"- 迭代时间线（Evolving）：{_count_markdown(evolving_dir)} 篇",
        f"- 页面更新：{_now_iso()[:19].replace('T', ' ')} UTC",
        "",
        "## 最近晋升为永久记忆",
        "",
    ]
    if core_latest:
        for path in core_latest:
            lines.append(f"- {ref(path)}")
    else:
        lines.append("- 暂无：达标事实会自动进入")
    lines += ["", "## 最近迭代时间线（未定论，持续演化）", ""]
    if evolving_latest:
        for path in evolving_latest:
            lines.append(f"- {ref(path)}")
    else:
        lines.append("- 暂无")
    lines.append("")
    return "\n".join(lines)


def refresh_home_dashboard(vault_path: Any) -> dict[str, Any]:
    """刷新 Home.md；返回状态。主人手写同名文件时改名让位，绝不覆盖。"""
    vault = Path(str(vault_path)).expanduser()
    vault.mkdir(parents=True, exist_ok=True)
    home = vault / HOME_NAME
    if home.exists() and _MANAGED_MARKER not in home.read_text(encoding="utf-8-sig", errors="ignore")[:400]:
        occupied = home.with_name("Home.md")
        target = vault / f"Home-主人的笔记-{_now_iso()[:10]}.md"
        occupied.rename(target)
        home = vault / HOME_NAME
    content = build_home_markdown(vault)
    temporary = home.with_suffix(".md.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(home)
    return {"path": str(home), "bytes": len(content.encode("utf-8")), "managed": True}


DELIVERY_NAME = "灵机记忆首页.md"


def deliver_home_dashboard(vault_path: Any, delivery_dir: Any) -> dict[str, Any] | None:
    """把记忆首页摘要投递到主人的真实 Obsidian 库（纯文本路径，链接不可点）。

    只新增/更新 `灵机记忆首页.md` 一个托管文件；库内已有同名非托管文件时
    改名让位。这是"灵机记忆库并入真实库"之前的存在感过渡方案。
    """
    target_dir = Path(str(delivery_dir)).expanduser()
    if not target_dir.is_dir():
        return None
    target = target_dir / DELIVERY_NAME
    if target.exists() and _MANAGED_MARKER not in target.read_text(encoding="utf-8-sig", errors="ignore")[:400]:
        occupied = target.with_name(f"灵机记忆首页-主人的笔记-{_now_iso()[:10]}.md")
        target.rename(occupied)
    content = build_home_markdown(Path(str(vault_path)).expanduser(), wiki_links=False)
    temporary = target.with_suffix(".md.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(target)
    return {"path": str(target), "bytes": len(content.encode("utf-8"))}


__all__ = ["HOME_NAME", "DELIVERY_NAME", "build_home_markdown", "refresh_home_dashboard", "deliver_home_dashboard"]
