from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .providers import (
    FasterWhisperProvider,
    PaddleOCRProvider,
    ProviderUnavailableError,
    PySceneDetectProvider,
)


class MediaSemanticService:
    """Run optional local ASR, OCR and scene detection providers.

    The service is intentionally independent from the extraction adapter. Results
    are persisted as replaceable derivatives and can be re-ingested without
    mutating the original media file.
    """

    SCHEMA_VERSION = 1

    def __init__(self, storage_path: Path | str):
        self.storage_path = Path(storage_path)
        self.derived_root = self.storage_path / "derived" / "media"

    def analyze(
        self,
        media_path: Path | str,
        options: Mapping[str, Any],
        *,
        media_hash: str | None = None,
        keyframe_directory: Path | str | None = None,
    ) -> dict[str, Any]:
        path = Path(media_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(path)
        digest = media_hash or self._sha256(path)
        target = self.derived_root / digest / "semantic"
        target.mkdir(parents=True, exist_ok=True)
        warnings: list[str] = []
        result: dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION,
            "media_sha256": digest,
            "media_path": str(path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "target_directory": str(target),
            "providers": {},
            "warnings": warnings,
        }

        if bool(options.get("auto_transcribe")) and str(options.get("asr_provider") or "off") != "off":
            try:
                transcript = FasterWhisperProvider().transcribe(path, options)
                transcript_json = target / "transcript.json"
                transcript_md = target / "transcript.md"
                transcript_json.write_text(
                    json.dumps(transcript, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                transcript_md.write_text(self._render_transcript(transcript), encoding="utf-8")
                result["providers"]["asr"] = {
                    "provider": transcript.get("provider"),
                    "text": transcript.get("text") or "",
                    "json_path": str(transcript_json),
                    "text_path": str(transcript_md),
                    "segments": len(transcript.get("segments") or []),
                    "language": transcript.get("language") or "",
                }
            except ProviderUnavailableError as exc:
                warnings.append(str(exc))
            except Exception as exc:
                warnings.append(f"自动转写失败：{exc}")

        if bool(options.get("auto_ocr")) and str(options.get("ocr_provider") or "off") != "off":
            try:
                frames = self._keyframes(keyframe_directory)
                if not frames:
                    warnings.append("自动 OCR 已启用，但没有可用关键帧；请同时启用关键帧提取")
                else:
                    ocr = PaddleOCRProvider().recognize(frames, options)
                    ocr_json = target / "ocr.json"
                    ocr_text = target / "ocr.txt"
                    ocr_json.write_text(
                        json.dumps(ocr, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    ocr_text.write_text(str(ocr.get("text") or ""), encoding="utf-8")
                    result["providers"]["ocr"] = {
                        "provider": ocr.get("provider"),
                        "text": ocr.get("text") or "",
                        "json_path": str(ocr_json),
                        "text_path": str(ocr_text),
                        "images": len(ocr.get("images") or []),
                    }
            except ProviderUnavailableError as exc:
                warnings.append(str(exc))
            except Exception as exc:
                warnings.append(f"自动 OCR 失败：{exc}")

        if bool(options.get("detect_scenes")) and str(options.get("scene_provider") or "off") != "off":
            try:
                scenes = PySceneDetectProvider().detect(path, options)
                scenes_json = target / "scenes.json"
                scenes_json.write_text(
                    json.dumps(scenes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                result["providers"]["scenes"] = {
                    "provider": scenes.get("provider"),
                    "json_path": str(scenes_json),
                    "scene_count": scenes.get("scene_count", 0),
                    "scenes": scenes.get("scenes") or [],
                }
            except ProviderUnavailableError as exc:
                warnings.append(str(exc))
            except Exception as exc:
                warnings.append(f"镜头检测失败：{exc}")

        result["semantic_status"] = "provided" if result["providers"] else "metadata_only"
        summary_path = target / "summary.json"
        summary_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        result["summary_path"] = str(summary_path)
        return result

    @staticmethod
    def _keyframes(directory: Path | str | None) -> list[Path]:
        if not directory:
            return []
        root = Path(directory)
        if not root.is_dir():
            return []
        return sorted(
            path
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )

    @staticmethod
    def _render_transcript(transcript: Mapping[str, Any]) -> str:
        lines = [
            "# 媒体转写",
            "",
            f"- Provider：{transcript.get('provider') or ''}",
            f"- 模型：{transcript.get('model') or ''}",
            f"- 语言：{transcript.get('language') or ''}",
            "",
            "## 全文",
            "",
            str(transcript.get("text") or ""),
            "",
            "## 时间码",
            "",
        ]
        for segment in transcript.get("segments") or []:
            lines.append(
                f"- [{float(segment.get('start') or 0):.3f} → {float(segment.get('end') or 0):.3f}] "
                f"{segment.get('text') or ''}"
            )
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
