from pathlib import Path

from src.obsidian.frontmatter import content_hash, render_frontmatter
from src.project_memory.integrity import CoreMemoryIntegrityService


class Layout:
    def __init__(self, root): self.root = root
    def relative(self, path): return Path(path).resolve().relative_to(self.root.resolve())


def test_integrity_healthy_modified_missing(tmp_path):
    body = "approved\n"; path = tmp_path / "03-Knowledge/Core-Memory/G/a.md"; path.parent.mkdir(parents=True)
    path.write_text(render_frontmatter({"id": "M1", "approved_hash": content_hash(body), "approved_at": "now"}, body), encoding="utf-8")
    service = CoreMemoryIntegrityService(Layout(tmp_path))
    assert service.inspect("M1")["state"] == "healthy"
    path.write_text(render_frontmatter({"id": "M1", "approved_hash": content_hash(body)}, "changed\n"), encoding="utf-8")
    assert service.inspect("M1")["state"] == "external_modified"
    path.unlink()
    assert service.inspect("M1")["state"] == "missing"
