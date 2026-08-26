from pathlib import Path

from src.obsidian.frontmatter import render_frontmatter
from src.obsidian.memory_scope import ObsidianMemoryScope


def _write(root: Path, relative: str, metadata: dict | None = None, body: str = "正文") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if metadata is None:
        path.write_text(body, encoding="utf-8")
    else:
        path.write_text(render_frontmatter(metadata, body), encoding="utf-8")
    return path


def test_scope_uses_only_dedicated_directories_or_explicit_true(tmp_path):
    scope = ObsidianMemoryScope(tmp_path)
    ordinary = _write(tmp_path, "03-Knowledge/old.md", {"id": "old"})
    inbox = _write(tmp_path, "_LingJi/Memory Inbox/inbox.md")
    library = _write(tmp_path, "_LingJi/Memory Library/library.md", {"title": "library"})
    enabled = _write(tmp_path, "03-Knowledge/opt-in.md", {"lingji_memory": True})

    assert scope.classify(ordinary).eligible is False
    assert scope.classify(inbox).eligible is True
    assert scope.classify(library).eligible is True
    assert scope.classify(enabled).eligible is True


def test_false_is_highest_precedence_and_invalid_inputs_fail_closed(tmp_path):
    scope = ObsidianMemoryScope(tmp_path)
    disabled = _write(tmp_path, "_LingJi/Memory Inbox/no.md", {"lingji_memory": False})
    wrong_type = _write(tmp_path, "03-Knowledge/wrong.md", {"lingji_memory": "true"})
    malformed = tmp_path / "03-Knowledge" / "broken.md"
    malformed.parent.mkdir(parents=True, exist_ok=True)
    malformed.write_text("---\nlingji_memory: [\n---\nbody", encoding="utf-8")
    outside = tmp_path.parent / "outside.md"
    outside.write_text("---\nlingji_memory: true\n---\nbody", encoding="utf-8")
    directory = tmp_path / "_LingJi" / "Memory Inbox" / "folder.md"
    directory.mkdir(parents=True)

    assert scope.classify(disabled).reason == "explicitly_disabled"
    assert scope.classify(wrong_type).reason == "invalid_frontmatter"
    assert scope.classify(malformed).reason == "invalid_frontmatter"
    assert scope.decide(outside, {"lingji_memory": True}).reason == "outside_vault"
    assert scope.classify(directory).reason == "directory"


def test_scope_rejects_symlink_escape_and_non_markdown(tmp_path):
    scope = ObsidianMemoryScope(tmp_path)
    outside = tmp_path.parent / "escape.md"
    outside.write_text("---\nlingji_memory: true\n---\nsecret", encoding="utf-8")
    link = tmp_path / "_LingJi" / "Memory Inbox" / "escape.md"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    internal = _write(tmp_path, "03-Knowledge/internal.md", {"lingji_memory": True})
    internal_link = tmp_path / "_LingJi" / "Memory Inbox" / "internal.md"
    internal_link.symlink_to(internal)
    text = _write(tmp_path, "_LingJi/Memory Inbox/file.txt", {"lingji_memory": True})

    assert scope.classify(link).reason == "symlink"
    assert scope.classify(internal_link).reason == "symlink"
    assert scope.classify(text).reason == "non_markdown"


def test_scope_rejects_symlink_before_resolving_dotdot_path(tmp_path):
    scope = ObsidianMemoryScope(tmp_path)
    target = _write(tmp_path, "03-Knowledge/inside.md", {"lingji_memory": True})
    link = tmp_path / "outside-link.md"
    link.symlink_to(target)

    decision = scope.classify(tmp_path / "nested" / ".." / "outside-link.md")
    assert decision.eligible is False
    assert decision.reason == "symlink"
