from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.control.obsidian_notes_api import ObsidianPathError, SafeObsidianNotesService, register_obsidian_note_routes


class Obsidian:
    def __init__(self, root): self.root = root
    def config(self): return SimpleNamespace(vault_path=str(self.root))


def test_safe_read_write_and_drift(tmp_path):
    service = SafeObsidianNotesService(Obsidian(tmp_path))
    result = service.create_manual_note(title="A", content="body", directory="03-Knowledge/Notes", project_ids=["P"])
    assert not Path(result["relative_path"]).is_absolute()
    assert service.read_note(result["relative_path"])["content"].strip() == "body"
    assert service.scan_managed_changes()["count"] == 0
    path = tmp_path / result["relative_path"]
    path.write_text(path.read_text(encoding="utf-8") + "changed", encoding="utf-8")
    assert service.scan_managed_changes()["count"] == 1


@pytest.mark.parametrize("path", ["../x.md", "C:/x.md", "/tmp/x.md", "08-Private/x.md"])
def test_forbidden_paths(tmp_path, path):
    with pytest.raises(ObsidianPathError):
        SafeObsidianNotesService(Obsidian(tmp_path)).read_note(path)


def test_note_api_401_and_404(tmp_path):
    app = FastAPI(); register_obsidian_note_routes(app, SafeObsidianNotesService(Obsidian(tmp_path)), token_validator=lambda value: value == "ok")
    client = TestClient(app)
    assert client.get("/api/obsidian/notes", params={"relative_path": "03-Knowledge/Notes/x.md"}).status_code == 401
    assert client.get("/api/obsidian/notes", headers={"X-LingJi-Token": "ok"}, params={"relative_path": "03-Knowledge/Notes/x.md"}).status_code == 404
