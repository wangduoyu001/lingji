from __future__ import annotations

import re
from collections import Counter
from hashlib import sha1
from typing import Any, Iterable, Sequence

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
    "人物简介", "角色简介", "人物小传", "场景", "地点", "时间", "画面", "旁白", "字幕", "音效", "镜头",
    "内景", "外景", "闪回", "回忆", "转场", "众人", "所有人", "工作人员", "电话", "画外音", "OS", "VO",
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

    used_numbers: set[int] = set()
    for ordinal, item in enumerate(episode_ranges, start=1):
        number = _episode_number(item["header"], ordinal)
        while number in used_numbers:
            number += 1
        used_numbers.add(number)
        episode_raw = source.text[int(item["start"]) : int(item["end"])]
        episode_text = episode_raw.strip()
        scene_ranges = _scene_ranges(episode_raw, int(item["start"]))
        scene_ids: list[str] = []
        for scene_ordinal, scene_range in enumerate(scene_ranges, start=1):
            scene_raw = source.text[int(scene_range["start"]) : int(scene_range["end"])]
            scene_text = scene_raw.strip()
            leading = len(scene_raw) - len(scene_raw.lstrip())
            scene_start = int(scene_range["start"]) + leading
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
                    heading=str(scene_range["header"]),
                    text=scene_text,
                    start_offset=scene_start,
                    end_offset=scene_start + len(scene_text),
                    characters=tuple(names),
                )
            )
        if not scene_ranges:
            for name in _characters(episode_text):
                mentions[name] += len(re.findall(re.escape(name), episode_text)) or 1
                first_episode.setdefault(name, number)
        leading = len(episode_raw) - len(episode_raw.lstrip())
        episode_start = int(item["start"]) + leading
        episodes.append(
            DramaEpisode(
                episode_id=f"{drama_id}:e{number:03d}",
                drama_id=drama_id,
                number=number,
                title=str(item["title"] or item["header"] or f"第{number}集"),
                text=episode_text,
                start_offset=episode_start,
                end_offset=episode_start + len(episode_text),
                scene_ids=tuple(scene_ids),
            )
        )

    characters = tuple(
        DramaCharacter(name=name, mention_count=count, first_episode=first_episode.get(name))
        for name, count in sorted(mentions.items(), key=lambda pair: (-pair[1], pair[0]))
    )
    chunks = tuple(_build_chunks(drama_id, episodes, scenes, source.source_units))
    return DramaParseResult(
        drama_id=drama_id,
        title=source.title,
        source=source,
        episodes=tuple(episodes),
        scenes=tuple(scenes),
        characters=characters,
        chunks=chunks,
        metadata={
            "schema_version": 2,
            "character_count": len(characters),
            "episode_count": len(episodes),
            "scene_count": len(scenes),
            "chunk_count": len(chunks),
            "source_unit_count": len(source.source_units),
        },
    )


def _ranges(text: str, pattern: re.Pattern[str]) -> list[dict[str, object]]:
    matches = list(pattern.finditer(text))
    if not matches:
        return [{"start": 0, "end": len(text), "header": "", "title": ""}]
    output: list[dict[str, object]] = []
    for index, match in enumerate(matches):
        start = 0 if index == 0 and text[: match.start()].strip() else match.start()
        output.append(
            {
                "start": start,
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
    stop_upper = {item.upper() for item in _STOP_NAMES}
    for match in _CHARACTER_LINE.finditer(text):
        name = match.group("name").strip(" ._-\t")
        if name.upper() in stop_upper or len(name) > 16:
            continue
        if name not in names:
            names.append(name)
    return names


def _build_chunks(
    drama_id: str,
    episodes: Iterable[DramaEpisode],
    scenes: Iterable[DramaScene],
    source_units: Sequence[dict[str, Any]],
) -> Iterable[DramaChunk]:
    scenes_by_episode: dict[int, list[DramaScene]] = {}
    for scene in scenes:
        scenes_by_episode.setdefault(scene.episode_number, []).append(scene)

    for episode in episodes:
        selected = scenes_by_episode.get(episode.number) or []
        if selected:
            for scene in selected:
                yield from _split_chunk(
                    drama_id=drama_id,
                    chunk_type="scene",
                    heading=scene.heading,
                    text=scene.text,
                    source_ref=scene.source_ref,
                    start_offset=scene.start_offset,
                    episode_number=scene.episode_number,
                    scene_number=scene.scene_number,
                    characters=scene.characters,
                    source_units=source_units,
                )
            continue
        yield from _split_chunk(
            drama_id=drama_id,
            chunk_type="episode",
            heading=episode.title,
            text=episode.text,
            source_ref=episode.source_ref,
            start_offset=episode.start_offset,
            episode_number=episode.number,
            scene_number=None,
            characters=tuple(_characters(episode.text)),
            source_units=source_units,
        )


def _split_chunk(
    *,
    drama_id: str,
    chunk_type: str,
    heading: str,
    text: str,
    source_ref: str,
    start_offset: int,
    episode_number: int | None,
    scene_number: int | None,
    characters: tuple[str, ...],
    source_units: Sequence[dict[str, Any]],
) -> Iterable[DramaChunk]:
    leading = len(text) - len(text.lstrip())
    clean = text.strip()
    if not clean:
        return
    base_offset = start_offset + leading
    cursor = 0
    part = 1
    while cursor < len(clean):
        end = min(cursor + _MAX_CHUNK_CHARS, len(clean))
        if end < len(clean):
            newline = clean.rfind("\n", cursor + 500, end)
            if newline > cursor:
                end = newline
        body_window = clean[cursor:end]
        body = body_window.strip()
        body_leading = len(body_window) - len(body_window.lstrip())
        body_start = base_offset + cursor + body_leading
        body_end = body_start + len(body)
        if body:
            ref = source_ref if part == 1 and end == len(clean) else f"{source_ref}:p{part:02d}"
            raw_id = f"{drama_id}|{ref}|{body_start}|{body_end}"
            yield DramaChunk(
                chunk_id=f"drama_chunk_{sha1(raw_id.encode('utf-8')).hexdigest()[:20]}",
                drama_id=drama_id,
                chunk_type=chunk_type,
                text=body,
                source_ref=ref,
                start_offset=body_start,
                end_offset=body_end,
                episode_number=episode_number,
                scene_number=scene_number,
                heading=heading,
                characters=characters,
                tags=(chunk_type,),
                source_locator=_source_locator(source_units, body_start, body_end),
            )
        if end >= len(clean):
            break
        cursor = max(end - _CHUNK_OVERLAP, cursor + 1)
        part += 1


def _source_locator(
    source_units: Sequence[dict[str, Any]],
    start_offset: int,
    end_offset: int,
) -> dict[str, Any]:
    selected = [
        unit
        for unit in source_units
        if int(unit.get("normalized_end") or 0) > start_offset
        and int(unit.get("normalized_start") or 0) < end_offset
    ]
    if not selected:
        return {"normalized_start": start_offset, "normalized_end": end_offset}

    def compact(unit: dict[str, Any]) -> dict[str, Any]:
        return {
            key: unit.get(key)
            for key in ("unit", "number", "locator", "start_time", "end_time", "style", "actor")
            if unit.get(key) not in (None, "")
        }

    first = compact(selected[0])
    last = compact(selected[-1])
    payload: dict[str, Any] = {
        "normalized_start": start_offset,
        "normalized_end": end_offset,
        "start": first,
        "end": last,
        "unit_count": len(selected),
    }
    if first == last:
        payload["locator"] = first.get("locator")
    else:
        payload["locator"] = f"{first.get('locator', '?')}..{last.get('locator', '?')}"
    return payload


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
