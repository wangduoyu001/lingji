"""Safe behavior coverage replacing environment-coupled Obsidian CLI cases."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from second_brain.obsidian_cli import ObsidianCli, ObsidianCliConfig, ObsidianCliError


def _config(tmp_path: Path) -> ObsidianCliConfig:
    executable = tmp_path / "Obsidian.com"
    executable.write_text("stub", encoding="utf-8")
    vault = tmp_path / "vault"
    vault.mkdir()
    return ObsidianCliConfig(
        cli_path=str(executable),
        vault_path=str(vault),
        vault_name="test-vault",
    )


def test_read_error_output_is_reported_as_missing_note(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "second_brain.obsidian_cli.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=b"Error: note not found",
            stderr=b"",
        ),
    )
    with pytest.raises(ObsidianCliError, match="笔记不存在"):
        ObsidianCli(_config(tmp_path)).read("missing.md")


def test_search_no_matches_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "second_brain.obsidian_cli.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=b"No matches found",
            stderr=b"",
        ),
    )
    assert ObsidianCli(_config(tmp_path)).search("missing") == []


def test_create_verifies_content_without_touching_real_vault(tmp_path, monkeypatch):
    responses = iter(
        (
            SimpleNamespace(returncode=0, stdout=b"created", stderr=b""),
            SimpleNamespace(returncode=0, stdout="测试内容".encode("utf-8"), stderr=b""),
        )
    )
    monkeypatch.setattr(
        "second_brain.obsidian_cli.subprocess.run",
        lambda *args, **kwargs: next(responses),
    )
    result = ObsidianCli(_config(tmp_path)).create("test.md", "测试内容")
    assert result == "created"
