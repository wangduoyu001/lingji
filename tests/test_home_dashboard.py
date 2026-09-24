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


def test_delivery_writes_plain_path_copy_to_real_vault(tmp_path: Path):
    from src.memory.home_dashboard import DELIVERY_NAME, deliver_home_dashboard

    vault = tmp_path / "vault"
    _seed_vault(vault)
    real = tmp_path / "real-obsidian"
    real.mkdir()
    result = deliver_home_dashboard(vault, real)
    assert result is not None
    delivered = real / DELIVERY_NAME
    text = delivered.read_text(encoding="utf-8")
    assert "lingji_managed: true" in text
    assert "永久记忆（Core）：1 篇" in text
    assert "[[" not in text, "投递版链接不可点，必须纯文本路径"
    assert "`03-Knowledge/Core-Memory/General/core-a.md`" in text


def test_delivery_missing_dir_returns_none(tmp_path: Path):
    from src.memory.home_dashboard import deliver_home_dashboard

    assert deliver_home_dashboard(tmp_path / "vault", tmp_path / "nope") is None


def test_delivery_renames_aside_owner_file(tmp_path: Path):
    from src.memory.home_dashboard import DELIVERY_NAME, deliver_home_dashboard

    vault = tmp_path / "vault"
    _seed_vault(vault)
    real = tmp_path / "real-obsidian2"
    real.mkdir()
    owner_text = "# 我自己的记忆摘要"
    (real / DELIVERY_NAME).write_text(owner_text, encoding="utf-8")
    deliver_home_dashboard(vault, real)
    renamed = list(real.glob("灵机记忆首页-主人的笔记-*.md"))
    assert len(renamed) == 1 and renamed[0].read_text(encoding="utf-8") == owner_text
