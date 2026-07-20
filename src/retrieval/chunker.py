from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Iterable

from src.obsidian.frontmatter import FrontmatterError, split_frontmatter

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class MarkdownChunk:
    chunk_id: str
    memory_id: str
    ordinal: int
    heading: str
    text: str
    start_line: int
    end_line: int
    char_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class MarkdownChunker:
    """Split Markdown into stable, heading-aware chunks with line provenance."""

    def __init__(self, max_chars: int = 1400, overlap_chars: int = 180):
        self.max_chars = max(int(max_chars), 300)
        self.overlap_chars = min(max(int(overlap_chars), 0), self.max_chars // 3)

    def chunk(self, memory_id: str, text: str) -> list[MarkdownChunk]:
        try:
            _, body = split_frontmatter(text)
        except FrontmatterError:
            body = text.lstrip("\ufeff")
        lines = body.splitlines()
        sections = list(self._sections(lines))
        chunks: list[MarkdownChunk] = []
        ordinal = 0
        for heading, start_line, section_lines in sections:
            for chunk_text, local_start, local_end in self._split_section(section_lines):
                cleaned = chunk_text.strip()
                if not cleaned:
                    continue
                line_start = start_line + local_start
                line_end = start_line + local_end
                digest = hashlib.sha256(
                    f"{memory_id}|{heading}|{ordinal}|{cleaned}".encode("utf-8")
                ).hexdigest()[:20]
                chunks.append(
                    MarkdownChunk(
                        chunk_id=f"LJ-CHUNK-{digest.upper()}",
                        memory_id=memory_id,
                        ordinal=ordinal,
                        heading=heading,
                        text=cleaned,
                        start_line=line_start,
                        end_line=line_end,
                        char_count=len(cleaned),
                    )
                )
                ordinal += 1
        return chunks

    @staticmethod
    def _sections(lines: list[str]) -> Iterable[tuple[str, int, list[str]]]:
        heading_stack: list[str] = []
        current_heading = "正文"
        current_start = 1
        current_lines: list[str] = []

        for index, line in enumerate(lines, 1):
            match = HEADING_PATTERN.match(line)
            if match:
                if current_lines:
                    yield current_heading, current_start, current_lines
                level = len(match.group(1))
                title = match.group(2).strip()
                heading_stack = heading_stack[: level - 1]
                heading_stack.append(title)
                current_heading = " / ".join(heading_stack)
                current_start = index
                current_lines = [line]
            else:
                if not current_lines:
                    current_start = index
                current_lines.append(line)
        if current_lines:
            yield current_heading, current_start, current_lines

    def _split_section(self, lines: list[str]) -> Iterable[tuple[str, int, int]]:
        if not lines:
            return
        paragraphs: list[tuple[str, int, int]] = []
        buffer: list[str] = []
        paragraph_start = 0

        for index, line in enumerate(lines):
            if not line.strip() and buffer:
                paragraphs.append(("\n".join(buffer).strip(), paragraph_start, index - 1))
                buffer = []
                continue
            if not buffer and line.strip():
                paragraph_start = index
            if line.strip() or buffer:
                buffer.append(line)
        if buffer:
            paragraphs.append(("\n".join(buffer).strip(), paragraph_start, len(lines) - 1))

        current: list[str] = []
        current_start = 0
        current_end = 0
        for paragraph, start, end in paragraphs:
            if len(paragraph) > self.max_chars:
                if current:
                    yield "\n\n".join(current), current_start, current_end
                    current = []
                yield from self._split_long_text(paragraph, start, end)
                continue
            proposed = "\n\n".join([*current, paragraph]) if current else paragraph
            if current and len(proposed) > self.max_chars:
                combined = "\n\n".join(current)
                yield combined, current_start, current_end
                overlap = combined[-self.overlap_chars :].strip() if self.overlap_chars else ""
                current = [overlap, paragraph] if overlap else [paragraph]
                current_start = start
            else:
                if not current:
                    current_start = start
                current.append(paragraph)
            current_end = end
        if current:
            yield "\n\n".join(current), current_start, current_end

    def _split_long_text(self, text: str, start: int, end: int) -> Iterable[tuple[str, int, int]]:
        cursor = 0
        step = self.max_chars - self.overlap_chars
        while cursor < len(text):
            stop = min(cursor + self.max_chars, len(text))
            if stop < len(text):
                boundary = max(text.rfind("。", cursor, stop), text.rfind("\n", cursor, stop))
                if boundary > cursor + self.max_chars // 2:
                    stop = boundary + 1
            piece = text[cursor:stop].strip()
            if piece:
                yield piece, start, end
            if stop >= len(text):
                break
            cursor = max(stop - self.overlap_chars, cursor + step)
