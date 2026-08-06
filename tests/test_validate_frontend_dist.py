from pathlib import Path

import pytest

from scripts.validate_frontend_dist import (
    FrontendDistValidationError,
    validate_frontend_dist,
)


def _write_index(dist: Path, script_src: str | None) -> None:
    dist.mkdir(parents=True, exist_ok=True)
    script = "" if script_src is None else f'<script type="module" src="{script_src}"></script>'
    (dist / "index.html").write_text(
        f"<!doctype html><html><body><div id=\"root\"></div>{script}</body></html>",
        encoding="utf-8",
    )


def test_single_javascript_bundle_is_valid(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_index(dist, "/assets/index-abc.js")
    bundle = dist / "assets" / "index-abc.js"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("console.log('lingji');", encoding="utf-8")

    assert validate_frontend_dist(dist) == [bundle.resolve()]


def test_missing_dist_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(FrontendDistValidationError, match="dist directory is missing"):
        validate_frontend_dist(tmp_path / "missing")


def test_missing_index_is_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()

    with pytest.raises(FrontendDistValidationError, match="index.html is missing"):
        validate_frontend_dist(dist)


def test_index_without_javascript_entry_is_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_index(dist, None)

    with pytest.raises(FrontendDistValidationError, match="does not reference"):
        validate_frontend_dist(dist)


def test_missing_referenced_bundle_is_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_index(dist, "/assets/missing.js")

    with pytest.raises(FrontendDistValidationError, match="asset is missing"):
        validate_frontend_dist(dist)


def test_empty_referenced_bundle_is_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_index(dist, "/assets/empty.js")
    bundle = dist / "assets" / "empty.js"
    bundle.parent.mkdir(parents=True)
    bundle.touch()

    with pytest.raises(FrontendDistValidationError, match="asset is empty"):
        validate_frontend_dist(dist)


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_index(dist, "../outside.js")
    (tmp_path / "outside.js").write_text("unsafe", encoding="utf-8")

    with pytest.raises(FrontendDistValidationError, match="escapes the dist directory"):
        validate_frontend_dist(dist)


def test_remote_javascript_is_rejected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    _write_index(dist, "https://example.com/app.js")

    with pytest.raises(FrontendDistValidationError, match="Remote JavaScript asset"):
        validate_frontend_dist(dist)
