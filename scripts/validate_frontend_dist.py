from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class FrontendDistValidationError(RuntimeError):
    """Raised when a built frontend distribution is incomplete or unsafe."""


class _ScriptSourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        for name, value in attrs:
            if name.lower() == "src" and value:
                self.sources.append(value)


def _resolve_local_asset(dist_root: Path, source: str) -> Path:
    parsed = urlsplit(source)
    if parsed.scheme or parsed.netloc:
        raise FrontendDistValidationError(
            f"Remote JavaScript asset is not allowed in the packaged frontend: {source}"
        )

    relative_text = unquote(parsed.path).lstrip("/")
    if not relative_text:
        raise FrontendDistValidationError("JavaScript asset path is empty")

    candidate = (dist_root / Path(relative_text)).resolve()
    try:
        candidate.relative_to(dist_root)
    except ValueError as exc:
        raise FrontendDistValidationError(
            f"JavaScript asset escapes the dist directory: {source}"
        ) from exc
    return candidate


def validate_frontend_dist(dist: Path) -> list[Path]:
    """Validate the actual Vite output without assuming a bundle count."""

    dist_root = dist.resolve()
    if not dist_root.is_dir():
        raise FrontendDistValidationError(f"Frontend dist directory is missing: {dist}")

    index = dist_root / "index.html"
    if not index.is_file():
        raise FrontendDistValidationError("Frontend index.html is missing")

    parser = _ScriptSourceParser()
    parser.feed(index.read_text(encoding="utf-8"))

    javascript_sources = [
        source
        for source in parser.sources
        if urlsplit(source).path.lower().endswith(".js")
    ]
    if not javascript_sources:
        raise FrontendDistValidationError(
            "Frontend index.html does not reference a JavaScript entry asset"
        )

    resolved_assets: list[Path] = []
    for source in javascript_sources:
        asset = _resolve_local_asset(dist_root, source)
        if not asset.is_file():
            raise FrontendDistValidationError(
                f"Referenced JavaScript asset is missing: {source}"
            )
        if asset.stat().st_size <= 0:
            raise FrontendDistValidationError(
                f"Referenced JavaScript asset is empty: {source}"
            )
        resolved_assets.append(asset)

    return resolved_assets


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a built LingJi frontend distribution."
    )
    parser.add_argument("dist", type=Path, help="Path to the Vite dist directory")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        assets = validate_frontend_dist(args.dist)
    except FrontendDistValidationError as exc:
        print(f"Frontend dist validation failed: {exc}")
        return 1

    print(
        "Frontend dist validation passed: "
        f"{len(assets)} JavaScript entr{'y' if len(assets) == 1 else 'ies'} verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
