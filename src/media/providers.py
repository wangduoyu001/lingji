from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Iterable, Mapping


class ProviderUnavailableError(RuntimeError):
    pass


class FasterWhisperProvider:
    name = "faster_whisper"

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("faster_whisper") is not None

    def transcribe(self, media_path: Path | str, options: Mapping[str, Any]) -> dict[str, Any]:
        if not self.available():
            raise ProviderUnavailableError(
                "faster-whisper 未安装；安装 requirements-media.txt 后再启用自动转写"
            )
        from faster_whisper import WhisperModel

        model_name = str(options.get("asr_model") or "small")
        device = str(options.get("asr_device") or "auto")
        compute_type = str(options.get("asr_compute_type") or "auto")
        if compute_type == "auto":
            compute_type = "default"
        model_kwargs: dict[str, Any] = {
            "device": device,
            "compute_type": compute_type,
        }
        download_root = str(options.get("asr_download_root") or "").strip()
        if download_root:
            model_kwargs["download_root"] = download_root
        model = WhisperModel(model_name, **model_kwargs)
        transcribe_kwargs: dict[str, Any] = {
            "beam_size": max(int(options.get("asr_beam_size") or 5), 1),
            "vad_filter": bool(options.get("asr_vad_filter", True)),
            "word_timestamps": bool(options.get("asr_word_timestamps", False)),
        }
        language = str(options.get("asr_language") or "").strip()
        if language:
            transcribe_kwargs["language"] = language
        segments_iter, info = model.transcribe(str(media_path), **transcribe_kwargs)
        segments = []
        text_parts = []
        for segment in segments_iter:
            text = str(getattr(segment, "text", "") or "").strip()
            if not text:
                continue
            row = {
                "start": round(float(getattr(segment, "start", 0.0)), 3),
                "end": round(float(getattr(segment, "end", 0.0)), 3),
                "text": text,
            }
            words = getattr(segment, "words", None)
            if words:
                row["words"] = [
                    {
                        "start": round(float(getattr(word, "start", 0.0) or 0.0), 3),
                        "end": round(float(getattr(word, "end", 0.0) or 0.0), 3),
                        "word": str(getattr(word, "word", "") or ""),
                        "probability": round(float(getattr(word, "probability", 0.0) or 0.0), 5),
                    }
                    for word in words
                ]
            segments.append(row)
            text_parts.append(text)
        return {
            "provider": self.name,
            "model": model_name,
            "device": device,
            "compute_type": compute_type,
            "language": str(getattr(info, "language", "") or language),
            "language_probability": float(getattr(info, "language_probability", 0.0) or 0.0),
            "duration": float(getattr(info, "duration", 0.0) or 0.0),
            "text": "\n".join(text_parts).strip(),
            "segments": segments,
        }


class PaddleOCRProvider:
    name = "paddleocr"

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("paddleocr") is not None

    def recognize(self, images: Iterable[Path | str], options: Mapping[str, Any]) -> dict[str, Any]:
        if not self.available():
            raise ProviderUnavailableError(
                "PaddleOCR 未安装；安装 requirements-media.txt 后再启用关键帧 OCR"
            )
        from paddleocr import PaddleOCR

        language = str(options.get("ocr_language") or "ch")
        try:
            engine = PaddleOCR(
                lang=language,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        except TypeError:
            engine = PaddleOCR(lang=language, use_angle_cls=True)

        rows: list[dict[str, Any]] = []
        all_text: list[str] = []
        for image in images:
            path = Path(image)
            if not path.is_file():
                continue
            result = self._run_engine(engine, path)
            lines = self._extract_lines(result)
            text = "\n".join(line["text"] for line in lines if line.get("text")).strip()
            if text:
                all_text.append(f"[{path.name}]\n{text}")
            rows.append({"image": str(path), "lines": lines, "text": text})
        return {
            "provider": self.name,
            "language": language,
            "text": "\n\n".join(all_text).strip(),
            "images": rows,
        }

    @staticmethod
    def _run_engine(engine: Any, path: Path) -> Any:
        if hasattr(engine, "predict"):
            try:
                return engine.predict(input=str(path))
            except TypeError:
                return engine.predict(str(path))
        return engine.ocr(str(path), cls=True)

    @classmethod
    def _extract_lines(cls, result: Any) -> list[dict[str, Any]]:
        lines: list[dict[str, Any]] = []
        cls._walk_result(result, lines)
        deduplicated = []
        seen = set()
        for line in lines:
            key = (line.get("text"), line.get("score"))
            if not line.get("text") or key in seen:
                continue
            seen.add(key)
            deduplicated.append(line)
        return deduplicated

    @classmethod
    def _walk_result(cls, value: Any, output: list[dict[str, Any]]) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            texts = value.get("rec_texts") or value.get("texts")
            scores = value.get("rec_scores") or value.get("scores") or []
            boxes = value.get("rec_boxes") or value.get("dt_polys") or value.get("boxes") or []
            if isinstance(texts, (list, tuple)):
                for index, text in enumerate(texts):
                    output.append(
                        {
                            "text": str(text or "").strip(),
                            "score": cls._float_at(scores, index),
                            "box": cls._value_at(boxes, index),
                        }
                    )
            for nested in value.values():
                cls._walk_result(nested, output)
            return
        if isinstance(value, (list, tuple)):
            if len(value) == 2 and isinstance(value[1], (list, tuple)) and value[1]:
                candidate = value[1]
                if isinstance(candidate[0], str):
                    output.append(
                        {
                            "text": str(candidate[0]).strip(),
                            "score": float(candidate[1]) if len(candidate) > 1 else 0.0,
                            "box": value[0],
                        }
                    )
                    return
            for nested in value:
                cls._walk_result(nested, output)
            return
        if hasattr(value, "json"):
            try:
                cls._walk_result(value.json, output)
            except Exception:
                pass
        if hasattr(value, "res"):
            try:
                cls._walk_result(value.res, output)
            except Exception:
                pass

    @staticmethod
    def _float_at(values: Any, index: int) -> float:
        try:
            return float(values[index])
        except (IndexError, KeyError, TypeError, ValueError):
            return 0.0

    @staticmethod
    def _value_at(values: Any, index: int) -> Any:
        try:
            value = values[index]
            return value.tolist() if hasattr(value, "tolist") else value
        except (IndexError, KeyError, TypeError):
            return None


class PySceneDetectProvider:
    name = "pyscenedetect"

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("scenedetect") is not None

    def detect(self, video_path: Path | str, options: Mapping[str, Any]) -> dict[str, Any]:
        if not self.available():
            raise ProviderUnavailableError(
                "PySceneDetect 未安装；安装 requirements-media.txt 后再启用镜头检测"
            )
        from scenedetect import ContentDetector, detect

        threshold = float(options.get("scene_threshold") or 27.0)
        minimum = max(int(options.get("scene_min_length_frames") or 15), 1)
        scene_list = detect(
            str(video_path),
            ContentDetector(threshold=threshold, min_scene_len=minimum),
            show_progress=bool(options.get("scene_show_progress", False)),
        )
        scenes = []
        for index, pair in enumerate(scene_list, 1):
            start, end = pair
            scenes.append(
                {
                    "index": index,
                    "start_seconds": round(float(start.get_seconds()), 3),
                    "end_seconds": round(float(end.get_seconds()), 3),
                    "duration_seconds": round(float(end.get_seconds() - start.get_seconds()), 3),
                    "start_timecode": str(start.get_timecode()),
                    "end_timecode": str(end.get_timecode()),
                }
            )
        return {
            "provider": self.name,
            "threshold": threshold,
            "minimum_scene_frames": minimum,
            "scene_count": len(scenes),
            "scenes": scenes,
        }
