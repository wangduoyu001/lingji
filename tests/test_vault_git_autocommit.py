"""Regression tests for Vault git autocommit (4.1, 2026-09-27).

数据权威 = Vault + Git：自动晋升写入权威层后必须留版本锚点。失败不阻塞
晋升（只告警），绝不 push。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.automatic_memory.runtime import _vault_git_autocommit


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "lingji@test.local")
    _git(root, "config", "user.name", "lingji-test")


def test_commit_created_when_vault_dirty(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _init_repo(vault)
    (vault / "03-Knowledge" / "Core-Memory").mkdir(parents=True)
    (vault / "03-Knowledge" / "Core-Memory" / "LJ-MEM-1.md").write_text(
        "core note", encoding="utf-8"
    )
    assert _vault_git_autocommit(vault) is True
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=vault, capture_output=True, text=True
    ).stdout
    assert "auto-promotion" in log


def test_clean_vault_is_noop(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _init_repo(vault)
    (vault / "readme.md").write_text("seed", encoding="utf-8")
    _git(vault, "add", "-A")
    _git(vault, "commit", "-qm", "seed")
    assert _vault_git_autocommit(vault) is False


def test_non_git_vault_fails_soft(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("no git here", encoding="utf-8")
    assert _vault_git_autocommit(vault) is False
