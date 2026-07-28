from __future__ import annotations

import re
from collections import Counter
from hashlib import sha1
from typing import Iterable

from .models import (
    DramaCharacter,
    DramaChunk,
    DramaEpisode,
    DramaParseResult,
    DramaScene,
    DramaSource,
)

_EPISODE_HEADER = re.compile(
    r"(?im)^\s*(?P<header>(?:第\s*[零〇一二三四五六七八九十百千两0-9]+\s*[集章]|EP(?:ISODE)?\s*\d+))\s*[：:、.\-]?\s*(?P<title>[^\n]{0,80})$"
)
_SCENE_HEADER = re.compile(
    r"(?im)^\s*(?P<header>(?:(?:第\s*)?[零〇一二三四五六七八九十百千两0-9]+\s*[场景]|(?:场景|地点)\s*[：:]\s*[^\n]+|(?:INT\.|EXT\.|内景|外景)[^\n]{0,80}))\s*$"
)
_CHARACTER_LINE = re.compile(
    r"(?m)^\s*[【\[]?(?P<name>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9·._-]{1,15})[】\]]?\s*(?:（[^）\n]{0,16}）)?\s*[：:]"
)
_STOP_NAMES = {
    "场景", "地点", "时间", "画面", "旁白", "字幕", "音效", "镜头", "内景", "外景",
    "闪回", "回忆", "转场", "众人", "所有人", "工作人员", "电话", "画外音", "OS", "VO",
}
_MAX_CHUNK_CHARS = 1800
_CHUNK_OVERLAP = 160


def parse_script(source: DramaSource) -> DramaParseResult:
    drama_id = f"drama_{source.sha256[:12]}"
    episode_ranges = _ranges(source.text, _EPISODE_HEADER)
    episodes: list[DramaEpisode] = []
    scenes: list[DramaScene] = []
    mentions: Counter[str] = Counter()
    first_episode: dict[str, int] = {}

    for ordinal, item in enumerate(episode_ranges, start=1):
        number = _episode_number(item["header"], ordinal)
        episode_text = source.text[item["start"] : item["end"]].strip()
        scene_ranges = _scene_ranges(episode_text, item["start"])
        scene_ids: list[str] = []
        for scene_ordinal, scene_range in enumerate(scene_ranges, start=1):
            scene_text = source.text[scene_range["start"] : scene_range["end"]].strip()
            names = _characters(scene_text)
            for name in names:
                mentions[name] += len(re.findall(re.escape(name), scene_text)) or 1
                first_episode.setdefault(name, number)
            scene_id = f"{drama_id}:e{number:03d}:s{scene_ordinal:03d}"
            scene_ids.append(scene_id)
            scenes.append(
                DramaScene(
                    scene_id=scene_id,
                    drama_id=drama_id,
                    episode_number=number,
                    scene_number=scene_ordinal,
                    heading=scene_range["header"],
                    text=scene_text,
                    start_offset=scene_range["start"],
                    end_offset=scene_range["end"],
                    characters=tuple(names),
                )
            )
        if not scene_ranges:
            for name in _characters(episode_text):
                mentions[name] += len(re.findall(re.escape(name), episode_text)) or 1
                first_episode.setdefault(name, number)
        episodes.append(
            DramaEpisode(
                episode_id=f"{drama_id}:e{number:03d}",
                drama_id=drama_id,
                number=number,
                title=item["title"] or item["header"] or f"第{number}集",
                text=episode_text,
                start_offset=item["start"],
                end_offset=item["end"],
                scene_ids=tuple(scene_ids),
            )
        )

    characters = tuple(
        DramaCharacter(name=name, mention_count=count, first_episode=first_episode.get(name))
        for name, count in sorted(mentions.items(), key=lambda pair: (-pair[1], pair[0]))
    )
    chunks = tuple(_build_chunks(drama_id, episodes, scenes))
    return DramaParseResult(
        drama_id=drama_id,
        title=source.title,
        source=source,
        episodes=tuple(episodes),
        scenes=tuple(scenes),
        characters=characters,
        chunks=chunks,
        metadata={
            "schema_version": 1,
            "character_count": len(characters),
            "episode_count": len(episodes),
            "scene_count": len(scenes),
            "chunk_count": len(chunks),
        },
    )


def _ranges(text: str, pattern: re.Pattern[str]) -> list[dict[str, object]]:
    matches = list(pattern.finditer(text))
    if not matches:
        return [{"start": 0, "end": len(text), "header": "", "title": ""}]
    output: list[dict[str, object]] = []
    if matches[0].start() > 0 and text[: matches[0].start()].strip():
        output.append(
            {"start": 0, "end": matches[0].start(), "header": "前言", "title": "前言"}
        )
    for index, match in enumerate(matches):
        output.append(
            {
                "start": match.start(),
                "end": matches[index + 1].start() if index + 1 < len(matches) else len(text),
                "header": match.group("header").strip(),
                "title": match.groupdict().get("title", "").strip(),
            }
        )
    return output


def _scene_ranges(episode_text: str, base_offset: int) -> list[dict[str, object]]:
    matches = list(_SCENE_HEADER.finditer(episode_text))
    if not matches:
        return []
    output: list[dict[str, object]] = []
    for index, match in enumerate(matches):
        local_start = match.start()
        local_end = matches[index + 1].start() if index + 1 < len(matches) else len(episode_text)
        output.append(
            {
                "start": base_offset + local_start,
                "end": base_offset + local_end,
                "header": match.group("header").strip(),
            }
        )
    return output


def _characters(text: str) -> list[str]:
    names: list[str] = []
    for match in _CHARACTER_LINE.finditer(text):
        name = match.group("name").strip(" ._-\t")
        if name.upper() in _STOP_NAMES or name in _STOP_NAMES or len(name) > 16:
            continue
        if name not in names:
            names.append(name)
    return names


def _build_chunks(
    drama_id: str,
    episodes: Iterable[DramaEpisode],
    scenes: Iterable[DramaScene],
) -> Iterable[DramaChunk]:
    scene_list = list(scenes)
    scenes_by_episode: dict[int, list[DramaScene]] = {}
    for scene in scene_list:
        scenes_by_episode.setdefault(scene.episode_number, []).append(scene)

    for episode in episodes:
        selected = scenes_by_episode.get(episode.number) or []
        if selected:
            for scene in selected:
                yield from _split_chunk(
                    drama_id=drama_id,
                    chunk_type="scene",
                    text=scene.text,
                    source_ref=scene.source_ref,
                    start_offset=scene.start_offset,
                    episode_number=scene.episode_number,
                    scene_number=scene.scene_number,
                    characters=scene.characters,
                )
            continue
        yield from _split_chunk(
            drama_id=drama_id,
            chunk_type="episode",
            text=episode.text,
            source_ref=episode.source_ref,
            start_offset=episode.start_offset,
            episode_number=episode.number,
            scene_number=None,
            characters=tuple(_characters(episode.text)),
        )


def _split_chunk(
    *,
    drama_id: str,
    chunk_type: str,
    text: str,
    source_ref: str,
    start_offset: int,
    episode_number: int | None,
    scene_number: int | None,
    characters: tuple[str, ...],
) -> Iterable[DramaChunk]:
    clean = text.strip()
    if not clean:
        return
    cursor = 0
    part = 1
    while cursor < len(clean):
        end = min(cursor + _MAX_CHUNK_CHARS, len(clean))
        if end < len(clean):
            newline = clean.rfind("\n", cursor + 500, end)
            if newline > cursor:
                end = newline
        body = clean[cursor:end].strip()
        if body:
            ref = source_ref if part == 1 and end == len(clean) else f"{source_ref}:p{part:02d}"
            raw_id = f"{drama_id}|{ref}|{start_offset + cursor}|{start_offset + end}"
            yield DramaChunk(
                chunk_id=f"drama_chunk_{sha1(raw_id.encode('utf-8')).hexdigest()[:20]}",
                drama_id=drama_id,
                chunk_type=chunk_type,
                text=body,
                source_ref=ref,
                start_offset=start_offset + cursor,
                end_offset=start_offset + end,
                episode_number=episode_number,
                scene_number=scene_number,
                characters=characters,
                tags=(chunk_type,),
            )
        if end >= len(clean):
            break
        cursor = max(end - _CHUNK_OVERLAP, cursor + 1)
        part += 1


def _episode_number(header: object, fallback: int) -> int:
    value = str(header or "")
    digits = re.search(r"\d+", value)
    if digits:
        return max(int(digits.group()), 1)
    chinese = re.search(r"[零〇一二三四五六七八九十百千两]+", value)
    return _chinese_number(chinese.group()) if chinese else fallback


def _chinese_number(value: str) -> int:
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000}
    total = 0
    current = 0
    for char in value:
        if char in digits:
            current = digits[char]
        elif char in units:
            total += (current or 1) * units[char]
            current = 0
    return max(total + current, 1)
