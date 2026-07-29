from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DramaSource:
    source_path: Path
    title: str
    source_format: str
    text: str
    sha256: str
    source_units: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_path"] = str(self.source_path)
        payload["source_units"] = list(self.source_units)
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass(frozen=True)
class DramaCharacter:
    name: str
    mention_count: int
    first_episode: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DramaScene:
    scene_id: str
    drama_id: str
    episode_number: int
    scene_number: int
    heading: str
    text: str
    start_offset: int
    end_offset: int
    characters: tuple[str, ...] = ()

    @property
    def source_ref(self) -> str:
        return f"{self.drama_id}:e{self.episode_number:03d}:s{self.scene_number:03d}"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["characters"] = list(self.characters)
        payload["source_ref"] = self.source_ref
        return payload


@dataclass(frozen=True)
class DramaEpisode:
    episode_id: str
    drama_id: str
    number: int
    title: str
    text: str
    start_offset: int
    end_offset: int
    scene_ids: tuple[str, ...] = ()

    @property
    def source_ref(self) -> str:
        return f"{self.drama_id}:e{self.number:03d}"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scene_ids"] = list(self.scene_ids)
        payload["source_ref"] = self.source_ref
        return payload


@dataclass(frozen=True)
class DramaChunk:
    chunk_id: str
    drama_id: str
    chunk_type: str
    text: str
    source_ref: str
    start_offset: int
    end_offset: int
    episode_number: int | None = None
    scene_number: int | None = None
    heading: str = ""
    characters: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    source_locator: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["characters"] = list(self.characters)
        payload["tags"] = list(self.tags)
        payload["source_locator"] = dict(self.source_locator)
        return payload


@dataclass(frozen=True)
class DramaParseResult:
    drama_id: str
    title: str
    source: DramaSource
    episodes: tuple[DramaEpisode, ...]
    scenes: tuple[DramaScene, ...]
    characters: tuple[DramaCharacter, ...]
    chunks: tuple[DramaChunk, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drama_id": self.drama_id,
            "title": self.title,
            "source": self.source.to_dict(),
            "episodes": [item.to_dict() for item in self.episodes],
            "scenes": [item.to_dict() for item in self.scenes],
            "characters": [item.to_dict() for item in self.characters],
            "chunks": [item.to_dict() for item in self.chunks],
            "metadata": dict(self.metadata),
        }
