"""底稿保留零膨胀：同盘硬链接优先，跨盘/失败回退复制。"""

from __future__ import annotations

import os
from pathlib import Path

from src.extraction.sink import VaultExtractionSink


def _sink(tmp_path: Path) -> VaultExtractionSink:
    from src.memory import VaultLayout

    layout = VaultLayout(tmp_path / "vault")
    return VaultExtractionSink(layout, tmp_path / "storage")


def test_same_volume_preserve_uses_hardlink(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = source_dir / "rollout-2026-09-12.jsonl"
    source.write_text("abc" * 1000, encoding="utf-8")
    sink = _sink(tmp_path)
    manifest = sink.preserve_raw(source, "codex_rollout")
    raw_file = Path(manifest["raw_path"])
    assert raw_file.exists()
    assert os.stat(source).st_ino == os.stat(raw_file).st_ino, "同盘应建立硬链接"
    assert os.stat(source).st_nlink >= 2
    # 来源删除后，底稿仍然保全数据（证据职责）
    source.unlink()
    assert raw_file.read_text(encoding="utf-8") == "abc" * 1000


def test_preserve_is_deduplicated_by_content(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    a = source_dir / "a.jsonl"
    a.write_text("same-content", encoding="utf-8")
    sink = _sink(tmp_path)
    first = sink.preserve_raw(a, "codex_rollout")
    b = source_dir / "b.jsonl"
    b.write_text("same-content", encoding="utf-8")
    second = sink.preserve_raw(b, "codex_rollout")
    assert os.stat(Path(first["raw_path"])).st_ino == os.stat(Path(second["raw_path"])).st_ino, "同内容不同文件名共享同一物理底稿"
    assert os.stat(Path(first["raw_path"])).st_nlink >= 3, "多个来源名共享同一物理底稿"


def test_hardlink_failure_falls_back_to_copy(tmp_path: Path, monkeypatch):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = source_dir / "f.jsonl"
    source.write_text("data", encoding="utf-8")
    sink = _sink(tmp_path)

    import os as os_module

    def broken_link(src, dst):
        raise OSError("cross-device link")

    monkeypatch.setattr(os_module, "link", broken_link)
    manifest = sink.preserve_raw(source, "codex_rollout")
    raw_file = Path(manifest["raw_path"])
    assert raw_file.read_text(encoding="utf-8") == "data"
    assert os.stat(raw_file).st_ino != os.stat(source).st_ino, "回退为独立副本"
