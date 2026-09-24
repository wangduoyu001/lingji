"""Vault Home 仪表盘：托管笔记刷新、主人手写让位、统计正确。"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.memory.home_dashboard import HOME_NAME, refresh_home_dashboard


def _seed_vault(vault: Path) -> None:
    core = vault / "03-Knowledge" / "Core-Memory" / "General"
    core.mkdir(parents=True, exist_ok=True)
    (core / "core-a.md").write_text(
        "---\nid: LJ-MEM-1\n---\n核心事实 A\n", encoding="utf-8"
    )
    evolving = vault / "03-Knowledge" / "Evolving" / "主题甲"
    evolving.mkdir(parents=True, exist_ok=True)
    (evolving / "主题甲-时间线.md").write_text(
        "# 主题甲\n- 2026-09-23: 观点一\n", encoding="utf-8"
    )


def test_refresh_creates_dashboard_with_counts_and_links(tmp_path: Path):
    vault = tmp_path / "vault"
    _seed_vault(vault)
    result = refresh_home_dashboard(vault)
    assert result["managed"] is True
    home = vault / HOME_NAME
    assert home.exists()
    text = home.read_text(encoding="utf-8")
    assert "lingji_managed: true" in text
    assert "永久记忆（Core）：1 篇" in text
    assert "迭代时间线（Evolving）：1 篇" in text
    assert "[[03-Knowledge/Core-Memory/General/core-a]]" in text
    assert "[[03-Knowledge/Evolving/主题甲/主题甲-时间线]]" in text


def test_refresh_is_idempotent(tmp_path: Path):
    vault = tmp_path / "vault"
    _seed_vault(vault)
    refresh_home_dashboard(vault)
    first = (vault / HOME_NAME).read_text(encoding="utf-8").splitlines()
    refresh_home_dashboard(vault)
    second = (vault / HOME_NAME).read_text(encoding="utf-8").splitlines()
    # updated_at 随时间变是设计行为；其余内容（计数/链接）必须完全稳定
    stable_first = [l for l in first if not l.startswith(("updated_at:", "- 页面更新"))]
    stable_second = [l for l in second if not l.startswith(("updated_at:", "- 页面更新"))]
    assert stable_first == stable_second


def test_owner_handwritten_home_is_renamed_aside_not_overwritten(tmp_path: Path):
    vault = tmp_path / "vault"
    _seed_vault(vault)
    owner_text = "# 我自己的首页\n手写内容，不许动。"
    (vault / HOME_NAME).write_text(owner_text, encoding="utf-8")
    refresh_home_dashboard(vault)
    assert (vault / HOME_NAME).read_text(encoding="utf-8").startswith("---"), (
        "托管版接管 Home.md"
    )
    renamed = list(vault.glob("Home-主人的笔记-*.md"))
    assert len(renamed) == 1
    assert renamed[0].read_text(encoding="utf-8") == owner_text, "主人手写原文完整让位保留"


def test_managed_home_updates_in_place(tmp_path: Path):
    vault = tmp_path / "vault"
    _seed_vault(vault)
    refresh_home_dashboard(vault)
    core = vault / "03-Knowledge" / "Core-Memory" / "General" / "core-b.md"
    core.write_text("---\nid: LJ-MEM-2\n---\n核心事实 B\n", encoding="utf-8")
    refresh_home_dashboard(vault)
    text = (vault / HOME_NAME).read_text(encoding="utf-8")
    assert "永久记忆（Core）：2 篇" in text
    renamed = list(vault.glob("Home-主人的笔记-*.md"))
    assert renamed == [], "已托管文件原地更新，不再触发让位"
