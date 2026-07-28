from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from .models import DramaSource

SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf", ".srt", ".vtt", ".ass"}
_SUBTITLE_TIME = re.compile(
    r"^\s*(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{3}\s*-->\s*(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{3}.*$"
)
_ASS_OVERRIDE = re.compile(r"\{[^}]*\}")
_HTML_TAG = re.compile(r"<[^>]+>")


class DramaImportError(ValueError):
    """Raised when a script cannot be imported safely."""


class ScannedPdfRequiresOcr(DramaImportError):
    """Raised when a PDF has pages but no usable text layer."""


def load_script(path: Path | str, *, title: str | None = None) -> DramaSource:
    source_path = Path(path).expanduser().resolve(strict=True)
    if not source_path.is_file():
        raise DramaImportError(f"Script path is not a file: {source_path}")
    suffix = source_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise DramaImportError(f"Unsupported script format {suffix!r}; expected one of {supported}")

    if suffix in {".txt", ".md"}:
        text, units = _load_text(source_path)
    elif suffix in {".srt", ".vtt", ".ass"}:
        text, units = _load_subtitle(source_path, suffix)
    elif suffix == ".docx":
        text, units = _load_docx(source_path)
    else:
        text, units = _load_pdf(source_path)

    normalized = _normalize_text(text)
    if len(normalized.strip()) < 20:
        raise DramaImportError(f"Script contains too little readable text: {source_path}")
    return DramaSource(
        source_path=source_path,
        title=(title or source_path.stem).strip() or source_path.stem,
        source_format=suffix.lstrip("."),
        text=normalized,
        sha256=_sha256(source_path),
        source_units=tuple(units),
    )


def _load_text(path: Path) -> tuple[str, list[dict[str, object]]]:
    raw = path.read_bytes()
    text = None
    used_encoding = ""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise DramaImportError(f"Unable to decode text script: {path}")
    return text, [{"unit": "file", "number": 1, "encoding": used_encoding}]


def _load_subtitle(path: Path, suffix: str) -> tuple[str, list[dict[str, object]]]:
    raw, _ = _load_text(path)
    lines: list[str] = []
    units: list[dict[str, object]] = []
    cue_number = 0
    for original in raw.splitlines():
        line = original.strip()
        if not line or line.isdigit() or _SUBTITLE_TIME.match(line) or line.upper() == "WEBVTT":
            continue
        if suffix == ".ass":
            if line.startswith(("[", ";", "Format:")):
                continue
            if line.startswith("Dialogue:"):
                fields = line.split(",", 9)
                line = fields[-1] if fields else line
            elif line.startswith(("Style:", "Comment:")):
                continue
            line = _ASS_OVERRIDE.sub("", line).replace("\\N", "\n")
        line = _HTML_TAG.sub("", line).strip()
        if not line:
            continue
        cue_number += 1
        units.append({"unit": "cue", "number": cue_number, "text": line})
        lines.append(line)
    return "\n".join(lines), units


def _load_docx(path: Path) -> tuple[str, list[dict[str, object]]]:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - exercised by clean-install validation
        raise DramaImportError("DOCX import requires python-docx") from exc

    document = Document(str(path))
    blocks: Iterable[object]
    iterator = getattr(document, "iter_inner_content", None)
    blocks = iterator() if callable(iterator) else list(document.paragraphs)
    lines: list[str] = []
    units: list[dict[str, object]] = []
    number = 0
    for block in blocks:
        if hasattr(block, "text"):
            text = str(getattr(block, "text") or "").strip()
            if not text:
                continue
            number += 1
            style = getattr(getattr(block, "style", None), "name", None)
            units.append({"unit": "block", "number": number, "style": style, "text": text})
            lines.append(text)
            continue
        rows = getattr(block, "rows", ())
        for row in rows:
            text = " | ".join(
                " ".join(str(cell.text or "").split())
                for cell in getattr(row, "cells", ())
                if str(cell.text or "").strip()
            ).strip()
            if text:
                number += 1
                units.append({"unit": "table_row", "number": number, "text": text})
                lines.append(text)
    return "\n".join(lines), units


def _load_pdf(path: Path) -> tuple[str, list[dict[str, object]]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - exercised by clean-install validation
        raise DramaImportError("PDF import requires pypdf") from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    units: list[dict[str, object]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = _extract_pdf_page_text(page)
        cleaned = _normalize_text(text)
        pages.append(cleaned)
        units.append({"unit": "page", "number": index, "characters": len(cleaned)})
    combined = "\n\n".join(pages)
    if reader.pages and len(re.sub(r"\s+", "", combined)) < max(40, len(reader.pages) * 8):
        raise ScannedPdfRequiresOcr(
            "PDF appears to be scanned or lacks a usable text layer; OCR is required"
        )
    return combined, units


def _extract_pdf_page_text(page: object) -> str:
    extractor = getattr(page, "extract_text", None)
    if not callable(extractor):
        return ""
    try:
        return str(extractor(extraction_mode="layout") or "")
    except TypeError:
        try:
            return str(extractor() or "")
        except (KeyError, AttributeError):
            return ""
    except (KeyError, AttributeError):
        return ""


def _normalize_text(text: str) -> str:
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [line.rstrip() for line in value.split("\n")]
    output: list[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank and output:
                output.append("")
            blank = True
            continue
        output.append(line)
        blank = False
    return "\n".join(output).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
