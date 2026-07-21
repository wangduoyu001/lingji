from __future__ import annotations

from src.obsidian.frontmatter import content_hash


def canonical_body(text: str) -> str:
    """Normalize a Markdown body independently from frontmatter serialization."""
    return str(text or "").lstrip("\n").rstrip() + "\n"


def body_content_hash(text: str) -> str:
    """Hash the logical Markdown body, not render_frontmatter's separator newline."""
    return content_hash(canonical_body(text))
