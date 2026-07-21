from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from src.obsidian.frontmatter import atomic_write, content_hash, render_frontmatter, split_frontmatter


class ObsidianPathError(PermissionError):
    pass


class NoteRequest(BaseModel):
    title: str
    content: str
    directory: str = "03-Knowledge/Notes"
    project_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SafeObsidianNotesService:
    READ_ROOTS = {"01-Inbox", "02-Sources", "03-Knowledge", "04-Projects", "05-Operations"}
    WRITE_ROOTS = {"01-Inbox/Manual", "03-Knowledge/Notes", "05-Operations/Tasks"}

    def __init__(self, obsidian_service, document_manager=None, state_db=None):
        self.obsidian_service = obsidian_service
        self.document_manager = document_manager
        self.state_db = state_db

    @property
    def root(self) -> Path:
        config = self.obsidian_service.config()
        if not config.vault_path:
            raise RuntimeError("OBSIDIAN_SERVICE_UNAVAILABLE")
        root = Path(config.vault_path).expanduser().resolve()
        if not root.is_dir():
            raise RuntimeError("OBSIDIAN_SERVICE_UNAVAILABLE")
        return root

    def read_note(self, relative_path: str) -> dict[str, Any]:
        path = self._resolve(relative_path, write=False)
        if not path.is_file():
            raise FileNotFoundError(relative_path)
        raw = path.read_text(encoding="utf-8-sig")
        metadata, body = split_frontmatter(raw)
        return {"id": str(metadata.get("id") or ""), "relative_path": self._relative(path), "metadata": metadata, "content": body, "content_hash": content_hash(raw)}

    def create_manual_note(self, *, title: str, content: str, directory: str = "03-Knowledge/Notes", project_ids: list[str] | None = None, tags: list[str] | None = None) -> dict[str, Any]:
        directory_path = self._resolve(directory, write=True, directory=True)
        directory_path.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        note_id = f"LJ-NOTE-{uuid4().hex[:16].upper()}"
        safe = "".join(ch if ch.isalnum() or ch in "-_ " else "-" for ch in title).strip() or note_id
        target = directory_path / f"{safe[:100]}.md"
        if target.exists():
            target = directory_path / f"{safe[:80]}-{note_id[-8:]}.md"
        metadata = {"schema_version": 1, "id": note_id, "title": title.strip(), "memory_type": "note", "status": "active", "privacy": "private", "project_ids": list(project_ids or []), "created_at": now, "updated_at": now, "lingji_managed": True, "tags": self._tags(tags)}
        rendered = render_frontmatter(metadata, content.strip() + "\n")
        metadata["content_hash"] = content_hash(rendered)
        atomic_write(target, render_frontmatter(metadata, content.strip() + "\n"))
        result = {"id": note_id, "relative_path": self._relative(target), "content_hash": metadata["content_hash"], "created": True}
        if self.state_db:
            self.state_db.append_event("obsidian_manual_note_created", "note", note_id, result)
        return result

    def scan_managed_changes(self) -> dict[str, Any]:
        changes = []
        for root_name in self.READ_ROOTS:
            root = self.root / root_name
            for path in root.rglob("*.md") if root.exists() else ():
                raw = path.read_text(encoding="utf-8-sig")
                metadata, _ = split_frontmatter(raw)
                if metadata.get("lingji_managed") is not True:
                    continue
                current = content_hash(raw)
                stored = str(metadata.get("content_hash") or "")
                if stored and stored != current:
                    changes.append({"id": str(metadata.get("id") or ""), "relative_path": self._relative(path), "state": "external_modified", "stored_hash": stored, "current_hash": current})
        return {"items": changes, "count": len(changes)}

    def _resolve(self, value: str, *, write: bool, directory: bool = False) -> Path:
        raw = str(value or "").replace("\\", "/").strip()
        if not raw or "\x00" in raw or Path(raw).is_absolute() or (len(raw) > 1 and raw[1] == ":"):
            raise ObsidianPathError("OBSIDIAN_PATH_FORBIDDEN")
        relative = PurePosixPath(raw)
        if ".." in relative.parts or relative.parts[0] == "08-Private":
            raise ObsidianPathError("OBSIDIAN_PATH_FORBIDDEN")
        normalized = relative.as_posix().rstrip("/")
        if write:
            if normalized not in self.WRITE_ROOTS:
                raise ObsidianPathError("OBSIDIAN_WRITE_FORBIDDEN")
        elif relative.parts[0] not in self.READ_ROOTS:
            raise ObsidianPathError("OBSIDIAN_PATH_FORBIDDEN")
        target = (self.root / normalized).resolve()
        if self.root not in target.parents and target != self.root:
            raise ObsidianPathError("OBSIDIAN_PATH_FORBIDDEN")
        return target

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    @staticmethod
    def _tags(tags):
        output = ["source/owner-manual"]
        for value in tags or []:
            tag = str(value).strip().lstrip("#")
            if tag and tag not in output:
                output.append(tag)
        return output


def register_obsidian_note_routes(app, notes_service: SafeObsidianNotesService, *, token_validator: Callable[[str], bool] | None = None):
    router = APIRouter()

    def auth(token):
        if token_validator and not token_validator(token or ""):
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})

    def guard(call):
        try:
            return call()
        except ObsidianPathError as exc:
            code = str(exc)
            raise HTTPException(status_code=403, detail={"code": code}) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail={"code": "OBSIDIAN_NOTE_NOT_FOUND"}) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail={"code": "OBSIDIAN_SERVICE_UNAVAILABLE"}) from exc

    @router.get("/api/obsidian/notes")
    def read(relative_path: str, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: notes_service.read_note(relative_path))

    @router.post("/api/obsidian/notes")
    def create(request: NoteRequest, x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(lambda: notes_service.create_manual_note(**request.model_dump()))

    @router.post("/api/obsidian/scan")
    def scan(x_lingji_token: str | None = Header(default=None)):
        auth(x_lingji_token)
        return guard(notes_service.scan_managed_changes)

    app.include_router(router)
    return router
