from pathlib import Path

import pytest

from src.automatic_memory.quality_evidence import ProtectedTreeSentinel


def test_protected_sentinel_detects_nested_mutation(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "nested").mkdir()
    (root / "nested" / "x.txt").write_text("before", encoding="utf-8")
    before = ProtectedTreeSentinel.capture((root,))
    (root / "nested" / "x.txt").write_text("after", encoding="utf-8")
    changes = before.diff(ProtectedTreeSentinel.capture((root,)))
    assert any(change.path.endswith("nested/x.txt") for change in changes)


def test_protected_sentinel_rejects_symlink_escape(tmp_path: Path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir(); outside.mkdir()
    (outside / "secret").write_text("x", encoding="utf-8")
    (root / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        ProtectedTreeSentinel.capture((root,))


def test_protected_sentinel_rejects_missing_root(tmp_path: Path):
    with pytest.raises(ValueError, match="missing"):
        ProtectedTreeSentinel.capture((tmp_path / "missing",))
