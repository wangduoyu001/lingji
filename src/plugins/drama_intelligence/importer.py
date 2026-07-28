from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

from .models import DramaSource

SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf", ".srt", ".vtt", ".ass"}
_SUBTITLE_TIME = re.compile(
    r"^\s*(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{3})(?:\s+.*)?$"
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

    if len(text.strip()) < 20:
        raise DramaImportError(f"Script contains too little readable text: {source_path}")
    return DramaSource(
        source_path=source_path,
        title=(title or source_path.stem).strip() or source_path.stem,
        source_format=suffix.lstrip("."),
        text=text,
        sha256=_sha256(source_path),
        source_units=tuple(units),
    )


def _load_text(path: Path) -> tuple[str, list[dict[str, object]]]:
    raw = path.read_bytes()
    decoded = None
    used_encoding = ""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            decoded = raw.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if decoded is None:
        raise DramaImportError(f"Unable to decode text script: {path}")

    normalized = _normalize_text(decoded)
    units: list[dict[str, object]] = []
    cursor = 0
    line_number = 0
    for line in normalized.splitlines(keepends=True):
        body = line.rstrip("\n")
        start = cursor
        end = start + len(body)
        cursor += len(line)
        line_number += 1
        if not body.strip():
            continue
        units.append(
            {
                "unit": "line",
                "number": line_number,
                "encoding": used_encoding,
                "locator": f"line:{line_number}",
                "normalized_start": start,
                "normalized_end": end,
                "characters": len(body),
            }
        )
    if not units and normalized:
        units.append(
            {
                "unit": "file",
                "number": 1,
                "encoding": used_encoding,
                "locator": "file:1",
                "normalized_start": 0,
                "normalized_end": len(normalized),
                "characters": len(normalized),
            }
        )
    return normalized, units


def _load_subtitle(path: Path, suffix: str) -> tuple[str, list[dict[str, object]]]:
    raw, _ = _load_text(path)
    if suffix == ".ass":
        return _load_ass(raw)
    return _load_srt_or_vtt(raw)


def _load_srt_or_vtt(raw: str) -> tuple[str, list[dict[str, object]]]:
    lines = raw.splitlines()
    units: list[dict[str, Any]] = []
    cue_number = 0
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.upper() == "WEBVTT" or line.isdigit():
            index += 1
            continue
        timing = _SUBTITLE_TIME.match(line)
        if timing is None:
            index += 1
            continue
        index += 1
        body: list[str] = []
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if _SUBTITLE_TIME.match(candidate):
                break
            body.append(_HTML_TAG.sub("", candidate).strip())
            index += 1
        text = "\n".join(item for item in body if item).strip()
        if text:
            cue_number += 1
            start = timing.group("start").replace(",", ".")
            end = timing.group("end").replace(",", ".")
            units.append(
                {
                    "unit": "cue",
                    "number": cue_number,
                    "start_time": start,
                    "end_time": end,
                    "locator": f"cue:{cue_number}@{start}-{end}",
                    "text": text,
                }
            )
        index += 1
    return _assemble_units(units, separator="\n")


def _load_ass(raw: str) -> tuple[str, list[dict[str, object]]]:
    units: list[dict[str, Any]] = []
    cue_number = 0
    for original in raw.splitlines():
        line = original.strip()
        if not line.startswith("Dialogue:"):
            continue
        fields = line.split(",", 9)
        if len(fields) < 10:
            continue
        text = _ASS_OVERRIDE.sub("", fields[-1]).replace("\\N", "\n")
        text = _HTML_TAG.sub("", text).strip()
        if not text:
            continue
        cue_number += 1
        start = fields[1].strip()
        end = fields[2].strip()
        actor = fields[4].strip()
        units.append(
            {
                "unit": "cue",
                "number": cue_number,
                "start_time": start,
                "end_time": end,
                "actor": actor or None,
                "locator": f"cue:{cue_number}@{start}-{end}",
                "text": text,
            }
        )
    return _assemble_units(units, separator="\n")


def _load_docx(path: Path) -> tuple[str, list[dict[str, object]]]:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - clean-install dependency contract
        raise DramaImportError("DOCX import requires python-docx") from exc

    document = Document(str(path))
    blocks: Iterable[object]
    iterator = getattr(document, "iter_inner_content", None)
    blocks = iterator() if callable(iterator) else list(document.paragraphs)
    units: list[dict[str, Any]] = []
    number = 0
    for block in blocks:
        rows = getattr(block, "rows", None)
        if rows is not None:
            for row in rows:
                text = " | ".join(
                    " ".join(str(cell.text or "").split())
                    for cell in getattr(row, "cells", ())
                    if str(cell.text or "").strip()
                ).strip()
                if not text:
                    continue
                number += 1
                units.append(
                    {
                        "unit": "table_row",
                        "number": number,
                        "locator": f"table_row:{number}",
                        "text": text,
                    }
                )
            continue
        text = str(getattr(block, "text", "") or "").strip()
        if not text:
            continue
        number += 1
        style = getattr(getattr(block, "style", None), "name", None)
        units.append(
            {
                "unit": "block",
                "number": number,
                "style": style,
                "locator": f"block:{number}",
                "text": text,
            }
        )
    return _assemble_units(units, separator="\n\n")


def _load_pdf(path: Path) -> tuple[str, list[dict[str, object]]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - clean-install dependency contract
        raise DramaImportError("PDF import requires pypdf") from exc

    reader = PdfReader(str(path))
    units: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = _normalize_text(_extract_pdf_page_text(page))
        units.append(
            {
                "unit": "page",
                "number": index,
                "locator": f"page:{index}",
                "text": text,
            }
        )
    combined, mapped = _assemble_units(units, separator="\n\n", keep_empty=True)
    if reader.pages and len(re.sub(r"\s+", "", combined)) < max(40, len(reader.pages) * 8):
        raise ScannedPdfRequiresOcr(
            "PDF appears to be scanned or lacks a usable text layer; OCR is required"
        )
    return combined, mapped


def _assemble_units(
    units: list[dict[str, Any]],
    *,
    separator: str,
    keep_empty: bool = False,
) -> tuple[str, list[dict[str, object]]]:
    text_parts: list[str] = []
    mapped: list[dict[str, object]] = []
    cursor = 0
    for original in units:
        body = _normalize_text(str(original.get("text") or ""))
        if not body and not keep_empty:
            continue
        if text_parts:
            text_parts.append(separator)
            cursor += len(separator)
        start = cursor
        text_parts.append(body)
        cursor += len(body)
        metadata = {key: value for key, value in original.items() if key != "text"}
        metadata.update(
            {
                "normalized_start": start,
                "normalized_end": cursor,
                "characters": len(body),
            }
        )
        mapped.append(metadata)
    return "".join(text_parts).strip(), mapped


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
