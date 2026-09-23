"""raw 快照空间淘汰：占用不能无限膨胀（2026-09-23 主人约束）。

规则：全局最新 5 个永不删；大快照（>=32MiB）只保最新 3 份、其余 6h 后可删；
小文件 24h 保护；超 target 时最旧优先淘汰并记账 .evicted.log。
"""

from __future__ import annotations

from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.automatic_memory.checkpoint import evict_raw_for_space

MB = 1024 * 1024
NOW = 1_800_000_000.0


def _make(root: Path, name: str, size_mb: int, age_seconds: float) -> Path:
    path = root / name
    path.write_bytes(b"\0" * (size_mb * MB))
    os.utime(path, (NOW - age_seconds, NOW - age_seconds))
    return path


def test_under_target_is_noop(tmp_path: Path):
    _make(tmp_path, "old-small.bin", 1, age_seconds=100 * 3600)
    evicted = evict_raw_for_space(tmp_path, target_bytes=100 * MB, now=NOW)
    assert evicted == []
    assert len(list(tmp_path.iterdir())) == 1  # 只有原文件，无淘汰日志


def test_oldest_evicted_first_newest_five_protected(tmp_path: Path):
    # 7 个小文件全部超 24h：s0 最新(100h)、s6 最旧(106h)。
    # target 只容 4MB → 淘汰最旧 2 个（s6、s5），全局最新 5 个小文件(s0..s4)受保护。
    for i in range(7):
        _make(tmp_path, f"s{i}.bin", 1, age_seconds=(100 + i) * 3600)
    evicted = evict_raw_for_space(tmp_path, target_bytes=4 * MB, now=NOW)
    names = [item["raw_id"] for item in evicted]
    assert names == ["s6.bin", "s5.bin"], "最旧优先淘汰，全局最新 5 个受保护"
    assert (tmp_path / ".evicted.log").exists(), "淘汰必须记账可审计"


def test_large_snapshots_keep_newest_three(tmp_path: Path):
    # 5 个 40MiB 大快照：big0 最新(10h)、big4 最旧(14h)，全部超过 6h
    for i in range(5):
        _make(tmp_path, f"big{i}.bin", 40, age_seconds=(10 + i) * 3600)
    evicted = evict_raw_for_space(tmp_path, target_bytes=10 * MB, now=NOW)
    names = [item["raw_id"] for item in evicted]
    assert names == ["big4.bin", "big3.bin"], "大快照只保最新 3 份，最旧优先淘汰"
    kept = {p.name for p in tmp_path.iterdir() if p.is_file()}
    for keep in ("big0.bin", "big1.bin", "big2.bin"):
        assert keep in kept


def test_recent_large_copy_beyond_three_is_still_protected_by_age(tmp_path: Path):
    # 第 4 新的大快照只有 1h（< 6h 保护期）：不能因为它超出"最新3份"就被删
    _make(tmp_path, "big-old-1.bin", 40, age_seconds=10 * 3600)
    _make(tmp_path, "big-old-2.bin", 40, age_seconds=9 * 3600)
    _make(tmp_path, "big-recent.bin", 40, age_seconds=1 * 3600)
    evicted = evict_raw_for_space(tmp_path, target_bytes=10 * MB, now=NOW)
    assert [item["raw_id"] for item in evicted if item["raw_id"] == "big-recent.bin"] == []


def test_small_files_within_24h_protected(tmp_path: Path):
    _make(tmp_path, "fresh-small.bin", 1, age_seconds=2 * 3600)
    evicted = evict_raw_for_space(tmp_path, target_bytes=0, now=NOW)
    assert evicted == [], "24h 内的小文件受保护，无可淘汰时返回空"


def test_hidden_files_ignored(tmp_path: Path):
    log = tmp_path / ".evicted.log"
    log.write_text("{}\n", encoding="utf-8")
    os.utime(log, (NOW - 100 * 3600, NOW - 100 * 3600))
    _make(tmp_path, "old.bin", 1, age_seconds=100 * 3600)
    evicted = evict_raw_for_space(tmp_path, target_bytes=0, now=NOW)
    assert evicted == []  # 单个文件即全局最新 → 受保护
    assert log.exists(), "记账文件永不成为淘汰对象"


def test_protected_raw_ids_never_evicted(tmp_path: Path):
    """准确性红线：未终态任务引用的快照永不淘汰（哪怕超期超压）。"""
    _make(tmp_path, "pending-job-raw.bin", 40, age_seconds=50 * 3600)
    evicted = evict_raw_for_space(
        tmp_path, target_bytes=10 * MB, now=NOW, protected={"pending-job-raw.bin"}
    )
    assert evicted == [], "保护名单里的文件必须存活"


def test_nonterminal_job_raw_ids_reads_state_db(tmp_path: Path):
    import sqlite3

    from src.automatic_memory.checkpoint import nonterminal_job_raw_ids

    db = tmp_path / "lingji_state.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE extraction_jobs (status TEXT, payload_json TEXT)"
    )
    for status, raw in (
        ("queued", "raw-q"),
        ("processing", "raw-p"),
        ("failed", "raw-f"),
        ("completed", "raw-done"),
        ("cancelled", "raw-cancelled"),
    ):
        conn.execute(
            "INSERT INTO extraction_jobs VALUES (?, ?)",
            (status, f'{{"raw_id": "{raw}"}}'),
        )
    conn.commit()
    conn.close()
    protected = nonterminal_job_raw_ids(db)
    assert protected == {"raw-q", "raw-p", "raw-f"}, "只有未终态任务进保护名单"


def test_nonterminal_raw_ids_missing_db_returns_empty(tmp_path: Path):
    from src.automatic_memory.checkpoint import nonterminal_job_raw_ids

    assert nonterminal_job_raw_ids(tmp_path / "nope.db") == set()
