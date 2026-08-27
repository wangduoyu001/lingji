from pathlib import Path
import subprocess
import sys

from src.obsidian.memory_scope import ObsidianMemoryScope
from src.automatic_memory.models import SourceRecord
try:
    from src.automatic_memory.path_policy import enumerate_authorized_files
except ModuleNotFoundError:
    enumerate_authorized_files = None  # type: ignore[assignment]


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


def test_ordinary_obsidian_notes_are_not_enumerated_by_automatic_memory(tmp_path: Path):
    assert enumerate_authorized_files is not None, "Task 3 path policy module is absent"
    vault = tmp_path / "vault"
    ordinary = vault / "03-Knowledge" / "ordinary.md"
    ordinary.parent.mkdir(parents=True)
    ordinary.write_text("# ordinary\nsecret", encoding="utf-8")
    source = SourceRecord("obsidian-source", "obsidian", str(vault), "authorized", "metadata_discovery", "v1")

    assert enumerate_authorized_files(source) == ()
