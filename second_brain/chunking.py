from __future__ import annotations


def chunk_text(content: str, max_chars: int = 1500, overlap_chars: int = 150) -> list[str]:
    paragraphs = [part.strip() for part in content.replace("\r\n", "\n").split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            step = max_chars - overlap_chars
            chunks.extend(paragraph[start:start + max_chars] for start in range(0, len(paragraph), step))
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return chunks or ([content.strip()] if content.strip() else [])
