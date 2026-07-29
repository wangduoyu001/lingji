from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .importer import SUPPORTED_EXTENSIONS


class DramaImportService(Protocol):
    def import_script(
        self,
        source_path: str,
        *,
        title: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]: ...


def import_directory(
    service: DramaImportService,
    directory_path: Path | str,
    *,
    recursive: bool = False,
    limit: int = 100,
    force: bool = False,
) -> dict[str, Any]:
    """Import supported scripts deterministically while isolating per-file failures."""

    directory = Path(directory_path).expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise ValueError(f"Drama import path is not a directory: {directory}")
    bounded = min(max(int(limit), 1), 500)
    iterator = directory.rglob("*") if recursive else directory.iterdir()
    candidates = sorted(
        (
            path
            for path in iterator
            if path.is_file()
            and not path.name.startswith(".")
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ),
        key=lambda path: str(path.relative_to(directory)).casefold(),
    )
    selected = candidates[:bounded]
    if not selected:
        raise ValueError(f"No supported drama scripts found in: {directory}")

    items: list[dict[str, Any]] = []
    imported = 0
    duplicates = 0
    failed = 0
    for path in selected:
        try:
            result = service.import_script(str(path), force=force)
            drama = dict(result.get("drama") or {})
            duplicate = bool(result.get("duplicate"))
            imported += 0 if duplicate else 1
            duplicates += 1 if duplicate else 0
            items.append(
                {
                    "path": str(path),
                    "relative_path": str(path.relative_to(directory)),
                    "status": "duplicate" if duplicate else "imported",
                    "drama_id": drama.get("drama_id"),
                    "title": drama.get("title"),
                    "episode_count": drama.get("episode_count"),
                    "scene_count": drama.get("scene_count"),
                    "chunk_count": drama.get("chunk_count"),
                    "semantic": result.get("semantic"),
                    "warnings": result.get("warnings") or [],
                }
            )
        except Exception as exc:
            failed += 1
            items.append(
                {
                    "path": str(path),
                    "relative_path": str(path.relative_to(directory)),
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}"[:1000],
                }
            )

    return {
        "directory": str(directory),
        "recursive": bool(recursive),
        "candidate_count": len(candidates),
        "processed_count": len(selected),
        "imported_count": imported,
        "duplicate_count": duplicates,
        "failed_count": failed,
        "truncated": len(candidates) > len(selected),
        "items": items,
    }
