"""Regression tests for the raw-usage TTL cache (PERF_RESOURCE_ROOT_CAUSE_20260927 收尾).

raw 顶层文件数量大时，每个来源每轮核对的全量 stat 扫描构成持续 CPU 热点；
预算检查改为进程级 60s TTL 缓存，陈旧度有界，增量记账不受影响。
"""

from __future__ import annotations

from pathlib import Path

from src.automatic_memory.checkpoint import _dir_usage


def test_dir_usage_is_cached_within_ttl(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x" * 10)
    first = _dir_usage(tmp_path)
    assert first == 10
    # 缓存窗口内新增文件不改变读数（陈旧度有界）。
    (tmp_path / "b.bin").write_bytes(b"y" * 5)
    assert _dir_usage(tmp_path) == 10


def test_dir_usage_refreshes_after_ttl(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x" * 10)
    assert _dir_usage(tmp_path) == 10
    (tmp_path / "b.bin").write_bytes(b"y" * 5)
    # max_age_seconds=0 视为过期，立即重扫。
    assert _dir_usage(tmp_path, max_age_seconds=0) == 15


def test_dir_usage_caches_per_root(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    (root_a / "f").write_bytes(b"12345")
    (root_b / "f").write_bytes(b"12345678")
    assert _dir_usage(root_a) == 5
    assert _dir_usage(root_b) == 8
    # 另一个根的缓存互不污染（同一 TTL 窗口内）。
    (root_a / "g").write_bytes(b"zz")
    assert _dir_usage(root_a) == 5
    assert _dir_usage(root_b) == 8
