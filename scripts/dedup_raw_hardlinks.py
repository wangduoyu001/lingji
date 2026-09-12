#!/usr/bin/env python3
"""底稿去重维护工具：把 raw/ 里与来源文件完全相同的副本替换为硬链接。

用法：python3 scripts/dedup_raw_hardlinks.py <data_root>/acceptance/storage <来源目录> [<来源目录> ...]

- 仅当 sha256 完全一致且同盘时替换；来源已变化的时点证据原样保留。
- 幂等：已是硬链接的文件 sha 一致会再次跳过/重建为同一链接。
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path


def sha(p: Path, buf: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(buf):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    raw = Path(sys.argv[1]) / "raw"
    sources = [Path(arg) for arg in sys.argv[2:]]
    index: dict[str, Path] = {}
    for root in sources:
        for p in root.rglob("*"):
            if p.is_file():
                try:
                    index[sha(p)] = p
                except OSError:
                    pass
    reclaimed = linked = kept = 0
    for raw_file in sorted(raw.rglob("*")):
        if not raw_file.is_file():
            continue
        digest = raw_file.name if len(raw_file.name) == 64 else sha(raw_file)
        try:
            if sha(raw_file) != digest:
                kept += 1
                continue
        except OSError:
            kept += 1
            continue
        source = index.get(digest)
        if source is None or not source.exists():
            kept += 1
            continue
        tmp_link = raw_file.with_suffix(".hardlink")
        try:
            os.remove(tmp_link)
        except OSError:
            pass
        try:
            os.link(source, tmp_link)
            os.replace(tmp_link, raw_file)
            reclaimed += raw_file.stat().st_size
            linked += 1
        except OSError:
            if tmp_link.exists():
                os.remove(tmp_link)
            kept += 1
    print(f"硬链接替换 {linked} 个，回收 {reclaimed / 1024 / 1024:.0f} MB，保留时点副本 {kept} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
