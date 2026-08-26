from pathlib import Path
import subprocess
import sys

from src.obsidian.memory_scope import ObsidianMemoryScope


def test_automatic_memory_scope_does_not_promote_ordinary_obsidian_notes(tmp_path: Path):
    ordinary = tmp_path / "03-Knowledge" / "old.md"
    ordinary.parent.mkdir(parents=True)
    ordinary.write_text("# old\n\nordinary", encoding="utf-8")
    decision = ObsidianMemoryScope(tmp_path).classify(ordinary)
    assert decision.eligible is False
    assert decision.reason == "excluded_ordinary"


def test_memory_database_direct_import_has_no_obsidian_package_cycle():
    completed = subprocess.run(
        [sys.executable, "-c", "from src.retrieval.memory_db import MemoryDatabase; print(MemoryDatabase.__name__)"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "MemoryDatabase"
