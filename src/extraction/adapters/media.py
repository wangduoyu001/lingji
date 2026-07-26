from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any, Mapping

from ..base import ExtractionAdapter
from ..models import ExtractedDocument, ExtractionBatch, ExtractionRequest
from ..privacy import PrivacyClassifier


VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".ts", ".mts", ".m2ts"
}
AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"
}


class MediaExtractionAdapter(ExtractionAdapter):
    """Inspect local media and optionally create bounded audio/keyframe derivatives.

    ASR, speaker diarization, OCR and visual description are provider stages. This
    adapter accepts their output files but never pretends that metadata probing is
    equivalent to semantic video understanding.
    """

    name = "media_local"
    version = "1.1.0"
    source_types = ("media", "video", "audio")

    DEFAULT_OPTIONS: dict[str, Any] = {
        "keyframe_interval_seconds": 30.0,
        "max_keyframes": 500,
        "keyframe_max_dimension": 1280,
        "ffmpeg_max_concurrency": 1,
        "ffmpeg_threads": 2,
        "max_input_bytes": 20 * 1024**3,
        "max_duration_seconds": 360 * 60,
        "probe_timeout_seconds": 60.0,
        "ffmpeg_timeout_seconds": 1800.0,
    }
    _semaphore_lock = threading.RLock()
    _semaphores: dict[int, threading.BoundedSemaphore] = {}

    def __init__(self, storage_path: Path | str):
        self.storage_path = Path(storage_path)
        self.derived_root = self.storage_path / "derived" / "media"

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        if source_type not in self.source_types or not input_path or not input_path.is_file():
            return False
        suffix = input_path.suffix.lower()
        return suffix in VIDEO_EXTENSIONS or suffix in AUDIO_EXTENSIONS

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        if not request.input_path:
            raise ValueError("A local media path is required")
        path = request.input_path
        options = dict(self.DEFAULT_OPTIONS)
        options.update(dict(request.options or {}))
        self._validate_input_size(path, options)
        media_hash = self._sha256_file(path)
        media_kind = "audio" if path.suffix.lower() in AUDIO_EXTENSIONS else "video"
        warnings: list[str] = []
        probe = self._probe(path, options, warnings)
        self._validate_duration(probe, options)
        derivatives = self._derive(path, media_hash, media_kind, options, warnings)
        transcript = self._read_optional(
            request.payload.get("transcript") or options.get("transcript_path")
        )
        ocr_text = self._read_optional(
            request.payload.get("ocr_text") or options.get("ocr_path")
        )
        visual_notes = self._read_optional(
            request.payload.get("visual_notes") or options.get("visual_notes_path")
        )
        title = str(request.payload.get("title") or path.stem).strip()
        body = self._render(
            title,
            path,
            media_kind,
            media_hash,
            probe,
            derivatives,
            transcript,
            ocr_text,
            visual_notes,
            options,
        )
        assessment = PrivacyClassifier().assess(
            "\n".join((transcript, ocr_text, visual_notes)),
            options.get("sensitive_terms") or (),
        )
        destination = "private_source" if assessment.restricted else "source_archive"
        source_type = "audio" if media_kind == "audio" else "video"
        metadata = {
            "media_kind": media_kind,
            "media_sha256": media_hash,
            "original_path": str(path),
            "file_size": path.stat().st_size,
            "duration_seconds": self._duration(probe),
            "format_name": self._nested(probe, "format", "format_name"),
            "bit_rate": self._nested(probe, "format", "bit_rate"),
            "video_stream": self._first_stream(probe, "video"),
            "audio_stream": self._first_stream(probe, "audio"),
            "derived_audio_path": derivatives.get("audio_path", ""),
            "keyframe_directory": derivatives.get("keyframe_directory", ""),
            "keyframe_count": derivatives.get("keyframe_count", 0),
            "keyframe_max_dimension": int(options["keyframe_max_dimension"]),
            "ffmpeg_threads": int(options["ffmpeg_threads"]),
            "ffmpeg_max_concurrency": int(options["ffmpeg_max_concurrency"]),
            "semantic_status": "provided" if transcript or ocr_text or visual_notes else "metadata_only",
            "privacy": assessment.privacy,
            "sensitivity_findings": assessment.kinds(),
            "project": options.get("project_id") or options.get("project") or [],
            "tags": [f"source/{source_type}", "topic/media"],
            "status": "active" if transcript or ocr_text or visual_notes else "needs_review",
            "review_status": "needs_review" if not transcript and not ocr_text and not visual_notes else "",
        }
        return ExtractionBatch(
            documents=(
                ExtractedDocument(
                    stable_id=f"LJ-MEDIA-{media_hash[:24].upper()}",
                    title=title,
                    body=body,
                    source_type=source_type,
                    destination=destination,
                    external_id=media_hash,
                    created_at="",
                    updated_at="",
                    metadata=metadata,
                ),
            ),
            summary={
                "media_kind": media_kind,
                "duration_seconds": metadata["duration_seconds"],
                "keyframe_count": metadata["keyframe_count"],
                "semantic_status": metadata["semantic_status"],
                "restricted": assessment.restricted,
            },
            warnings=tuple(warnings),
        )

    @staticmethod
    def _validate_input_size(path: Path, options: Mapping[str, Any]) -> None:
        maximum = max(int(options.get("max_input_bytes") or 0), 0)
        size = path.stat().st_size
        if maximum and size > maximum:
            raise ValueError(
                f"媒体文件大小 {size} bytes 超过当前限制 {maximum} bytes；可在本地 UI 调整"
            )

    @classmethod
    def _validate_duration(cls, probe: Mapping[str, Any], options: Mapping[str, Any]) -> None:
        maximum = max(float(options.get("max_duration_seconds") or 0), 0.0)
        duration = cls._duration(dict(probe))
        if maximum and duration not in (None, "") and float(duration) > maximum:
            raise ValueError(
                f"媒体时长 {duration} 秒超过当前限制 {maximum} 秒；可在本地 UI 调整"
            )

    def _probe(
        self,
        path: Path,
        options: Mapping[str, Any],
        warnings: list[str],
    ) -> dict[str, Any]:
        executable = str(options.get("ffprobe_path") or "ffprobe")
        resolved = shutil.which(executable) if not Path(executable).exists() else executable
        if not resolved:
            warnings.append("ffprobe 不可用，仅保存文件级元数据")
            return {}
        command = [
            str(resolved),
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=float(options.get("probe_timeout_seconds", 60)),
            )
            data = json.loads(result.stdout or "{}")
            return data if isinstance(data, dict) else {}
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
            warnings.append(f"ffprobe 失败：{exc}")
            return {}

    def _derive(
        self,
        path: Path,
        media_hash: str,
        media_kind: str,
        options: Mapping[str, Any],
        warnings: list[str],
    ) -> dict[str, Any]:
        if not options.get("extract_audio") and not options.get("extract_keyframes"):
            return {}
        executable = str(options.get("ffmpeg_path") or "ffmpeg")
        resolved = shutil.which(executable) if not Path(executable).exists() else executable
        if not resolved:
            warnings.append("ffmpeg 不可用，未生成音轨或关键帧")
            return {}
        target = self.derived_root / media_hash
        target.mkdir(parents=True, exist_ok=True)
        result: dict[str, Any] = {}
        timeout = float(options.get("ffmpeg_timeout_seconds", 1800))
        threads = max(int(options.get("ffmpeg_threads") or 1), 1)
        concurrency = max(int(options.get("ffmpeg_max_concurrency") or 1), 1)
        if options.get("extract_audio") and media_kind == "video":
            audio_path = target / "audio.wav"
            if not audio_path.exists():
                self._run(
                    [
                        str(resolved), "-hide_banner", "-loglevel", "error", "-y",
                        "-threads", str(threads),
                        "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", str(audio_path),
                    ],
                    timeout,
                    concurrency,
                )
            result["audio_path"] = str(audio_path)
        if options.get("extract_keyframes") and media_kind == "video":
            frames_dir = target / "keyframes"
            frames_dir.mkdir(parents=True, exist_ok=True)
            interval = max(float(options.get("keyframe_interval_seconds", 30)), 1.0)
            max_frames = max(int(options.get("max_keyframes", 500)), 1)
            max_dimension = max(int(options.get("keyframe_max_dimension", 1280)), 64)
            pattern = frames_dir / "frame-%05d.jpg"
            if not any(frames_dir.glob("frame-*.jpg")):
                self._run(
                    [
                        str(resolved), "-hide_banner", "-loglevel", "error", "-y",
                        "-threads", str(threads),
                        "-filter_threads", str(threads),
                        "-i", str(path),
                        "-vf",
                        f"fps=1/{interval},scale={max_dimension}:{max_dimension}:force_original_aspect_ratio=decrease",
                        "-frames:v", str(max_frames),
                        str(pattern),
                    ],
                    timeout,
                    concurrency,
                )
            frames = sorted(frames_dir.glob("frame-*.jpg"))[:max_frames]
            result["keyframe_directory"] = str(frames_dir)
            result["keyframe_count"] = len(frames)
        return result

    @classmethod
    def _run(cls, command: list[str], timeout: float, concurrency: int) -> None:
        semaphore = cls._semaphore(concurrency)
        with semaphore:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )

    @classmethod
    def _semaphore(cls, concurrency: int) -> threading.BoundedSemaphore:
        limit = max(int(concurrency), 1)
        with cls._semaphore_lock:
            if limit not in cls._semaphores:
                cls._semaphores[limit] = threading.BoundedSemaphore(limit)
            return cls._semaphores[limit]

    @staticmethod
    def _read_optional(value: Any) -> str:
        if value in (None, ""):
            return ""
        path = Path(str(value)).expanduser()
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8-sig")
        return str(value)

    @staticmethod
    def _render(
        title: str,
        path: Path,
        media_kind: str,
        media_hash: str,
        probe: dict[str, Any],
        derivatives: dict[str, Any],
        transcript: str,
        ocr_text: str,
        visual_notes: str,
        options: Mapping[str, Any],
    ) -> str:
        lines = [
            f"# {title}", "", "## 媒体信息", "",
            f"- 类型：{media_kind}",
            f"- 原文件：`{path}`",
            f"- SHA-256：`{media_hash}`",
            f"- 时长：{MediaExtractionAdapter._duration(probe) or '-'} 秒",
            f"- 格式：{MediaExtractionAdapter._nested(probe, 'format', 'format_name') or '-'}",
            f"- 视频流：`{json.dumps(MediaExtractionAdapter._first_stream(probe, 'video'), ensure_ascii=False)}`",
            f"- 音频流：`{json.dumps(MediaExtractionAdapter._first_stream(probe, 'audio'), ensure_ascii=False)}`",
            f"- 关键帧上限：{options.get('max_keyframes')}",
            f"- 关键帧最大边长：{options.get('keyframe_max_dimension')} px",
            f"- FFmpeg 线程：{options.get('ffmpeg_threads')}",
        ]
        if derivatives:
            lines.extend(["", "## 派生文件", ""])
            for key, value in derivatives.items():
                lines.append(f"- {key}：`{value}`")
        if transcript:
            lines.extend(["", "## 转写", "", transcript])
        if ocr_text:
            lines.extend(["", "## OCR", "", ocr_text])
        if visual_notes:
            lines.extend(["", "## 视觉描述", "", visual_notes])
        if not transcript and not ocr_text and not visual_notes:
            lines.extend(
                [
                    "", "## 待处理", "",
                    "当前只完成媒体元数据提取。需要 ASR、OCR 或视觉分析后才能形成完整内容索引。",
                ]
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _duration(probe: dict[str, Any]) -> float | str:
        value = MediaExtractionAdapter._nested(probe, "format", "duration")
        try:
            return round(float(value), 3)
        except (TypeError, ValueError):
            return ""

    @staticmethod
    def _nested(data: Mapping[str, Any], first: str, second: str) -> Any:
        value = data.get(first) if isinstance(data, Mapping) else None
        return value.get(second, "") if isinstance(value, Mapping) else ""

    @staticmethod
    def _first_stream(probe: dict[str, Any], codec_type: str) -> dict[str, Any]:
        streams = probe.get("streams") if isinstance(probe, dict) else []
        if not isinstance(streams, list):
            return {}
        for stream in streams:
            if isinstance(stream, dict) and stream.get("codec_type") == codec_type:
                allowed = {
                    "codec_name", "codec_long_name", "profile", "width", "height",
                    "r_frame_rate", "avg_frame_rate", "sample_rate", "channels",
                    "channel_layout", "bit_rate", "duration",
                }
                return {key: value for key, value in stream.items() if key in allowed}
        return {}

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
