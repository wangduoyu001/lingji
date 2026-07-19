from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Mapping


_MEDIA_TYPES = {"media", "video", "audio"}


class RuntimeSettingsStore:
    """Persist owner-editable settings shared by UI, CLI and service layers."""

    SCHEMA_VERSION = 2

    def __init__(self, settings: Any, state_db: Any | None = None):
        self.settings = settings
        self.state_db = state_db
        self.path = settings.storage_path / settings.runtime_settings_file
        self._lock = threading.RLock()

    def definitions(self) -> dict[str, dict[str, Any]]:
        return {
            # Media extraction limits.
            "media_keyframe_interval_seconds": self._number(
                "media_processing", "关键帧间隔（秒）", "每隔多少秒提取一张关键帧。", 30.0, 1.0, 86400.0
            ),
            "media_max_keyframes": self._integer(
                "media_processing", "关键帧最大数量", "单个媒体任务最多生成的关键帧数量。", 500, 1, 100000
            ),
            "media_keyframe_max_dimension": self._integer(
                "media_processing", "关键帧最大边长", "关键帧最长边像素；保持原始比例。", 1280, 64, 16384
            ),
            "media_ffmpeg_max_concurrency": self._integer(
                "media_processing", "FFmpeg 最大并发任务", "同时运行的 FFmpeg 派生任务数量。", 1, 1, 32
            ),
            "media_ffmpeg_threads": self._integer(
                "media_processing", "FFmpeg 单任务线程数", "传递给 FFmpeg 的 -threads 与 -filter_threads。", 2, 1, 128
            ),
            "media_max_input_gb": self._number(
                "media_processing", "单文件最大体积（GB）", "0 表示不限制；超出时任务在处理前拒绝。", 20.0, 0.0, 102400.0
            ),
            "media_max_duration_minutes": self._number(
                "media_processing", "单文件最大时长（分钟）", "0 表示不限制；依赖 FFprobe 获取时长。", 360.0, 0.0, 5256000.0
            ),
            "media_default_priority": self._integer(
                "media_processing", "媒体任务默认优先级", "数值越小越优先；单任务可以覆盖。", 100, 0, 10000
            ),
            "media_probe_timeout_seconds": self._number(
                "media_processing", "FFprobe 超时（秒）", "读取媒体元数据的最长等待时间。", 60.0, 1.0, 3600.0
            ),
            "media_ffmpeg_timeout_seconds": self._number(
                "media_processing", "FFmpeg 超时（秒）", "单个派生步骤的最长等待时间。", 1800.0, 1.0, 604800.0
            ),
            # Optional local semantic providers. Disabled unless the owner enables them.
            "media_auto_transcribe": self._boolean(
                "media_ai", "自动转写", "媒体任务自动调用本地 ASR Provider。", False
            ),
            "media_asr_provider": self._choice(
                "media_ai", "ASR Provider", "默认使用免费本地 faster-whisper；off 表示关闭。", "off", ["off", "faster_whisper"]
            ),
            "media_asr_model": self._string(
                "media_ai", "ASR 模型", "faster-whisper 模型名或本地模型目录。", "small", 240
            ),
            "media_asr_device": self._choice(
                "media_ai", "ASR 设备", "auto 自动选择，亦可固定 CPU 或 CUDA。", "auto", ["auto", "cpu", "cuda"]
            ),
            "media_asr_compute_type": self._choice(
                "media_ai", "ASR 精度", "auto 自动选择；GPU 通常使用 float16，CPU 可使用 int8。", "auto", ["auto", "float16", "float32", "int8", "int8_float16"]
            ),
            "media_asr_language": self._string(
                "media_ai", "ASR 语言", "留空自动识别；中文可填 zh。", "", 32
            ),
            "media_auto_ocr": self._boolean(
                "media_ai", "自动关键帧 OCR", "对生成的关键帧调用本地 OCR Provider。", False
            ),
            "media_ocr_provider": self._choice(
                "media_ai", "OCR Provider", "默认使用免费本地 PaddleOCR；off 表示关闭。", "off", ["off", "paddleocr"]
            ),
            "media_ocr_language": self._string(
                "media_ai", "OCR 语言", "PaddleOCR 语言代码，例如 ch、en。", "ch", 32
            ),
            "media_detect_scenes": self._boolean(
                "media_ai", "自动镜头切分", "使用 PySceneDetect 检测镜头边界。", False
            ),
            "media_scene_provider": self._choice(
                "media_ai", "镜头检测 Provider", "免费开源 PySceneDetect；off 表示关闭。", "off", ["off", "pyscenedetect"]
            ),
            "media_scene_threshold": self._number(
                "media_ai", "镜头检测阈值", "数值越低越敏感；默认 27。", 27.0, 1.0, 100.0
            ),
            # Storage lifecycle. Raw and Vault remain protected in implementation.
            "storage_max_gb": self._number(
                "storage", "灵机最大占用（GB）", "用于预警和仪表盘，不会直接删除原始资料。", 500.0, 1.0, 1048576.0
            ),
            "storage_min_free_gb": self._number(
                "storage", "磁盘最小剩余空间（GB）", "低于该值时进入预警。", 20.0, 0.0, 1048576.0
            ),
            "storage_auto_cleanup_enabled": self._boolean(
                "storage", "自动清理", "仅处理可重建/可过期类别，并先生成可审计计划。", False
            ),
            "storage_cold_enabled": self._boolean(
                "storage", "启用冷存储", "允许将指定类别迁移到用户选择的冷存储目录。", False
            ),
            "storage_cold_path": self._string(
                "storage", "冷存储目录", "必须由主人在本地 UI 选择。", "", 1024
            ),
            "storage_derived_retention_days": self._integer(
                "storage", "派生媒体保留天数", "0 表示不按时间清理。", 30, 0, 36500
            ),
            "storage_versions_retention_days": self._integer(
                "storage", "历史版本保留天数", "0 表示不按时间处理。", 90, 0, 36500
            ),
            "storage_logs_retention_days": self._integer(
                "storage", "日志保留天数", "0 表示不按时间清理。", 30, 0, 36500
            ),
            "storage_temp_retention_days": self._integer(
                "storage", "临时文件保留天数", "0 表示不按时间清理。", 7, 0, 36500
            ),
            "storage_cache_retention_days": self._integer(
                "storage", "缓存保留天数", "0 表示不按时间清理。", 30, 0, 36500
            ),
            "storage_derived_max_gb": self._number(
                "storage", "派生媒体最大容量（GB）", "0 表示不按容量处理。", 100.0, 0.0, 1048576.0
            ),
            "storage_versions_max_gb": self._number(
                "storage", "历史版本最大容量（GB）", "0 表示不按容量处理。", 50.0, 0.0, 1048576.0
            ),
            "storage_logs_max_gb": self._number(
                "storage", "日志最大容量（GB）", "0 表示不按容量处理。", 10.0, 0.0, 1048576.0
            ),
            "storage_archive_versions": self._boolean(
                "storage", "历史版本迁移冷存储", "启用冷存储时优先迁移，而不是进入恢复区。", True
            ),
            "storage_archive_logs": self._boolean(
                "storage", "日志迁移冷存储", "启用冷存储时可迁移旧日志。", False
            ),
            # Backup defaults.
            "backup_default_profile": self._choice(
                "backup", "默认备份范围", "metadata 不含 Raw/Derived；full 包含全部。", "metadata", ["metadata", "full"]
            ),
        }

    def snapshot(self) -> dict[str, Any]:
        definitions = self.definitions()
        overrides = self._load_overrides()
        values = {key: overrides.get(key, definition["default"]) for key, definition in definitions.items()}
        return {
            "schema_version": self.SCHEMA_VERSION,
            "path": str(self.path),
            "values": values,
            "overrides": overrides,
            "definitions": definitions,
        }

    def update(self, values: Mapping[str, Any], *, actor: str = "owner") -> dict[str, Any]:
        definitions = self.definitions()
        current = self._load_overrides()
        changed: dict[str, Any] = {}
        for key, value in values.items():
            if key not in definitions:
                raise KeyError(f"Unknown runtime setting: {key}")
            normalized = self._validate_value(key, value, definitions[key])
            default = definitions[key]["default"]
            if normalized == default:
                current.pop(key, None)
            else:
                current[key] = normalized
            changed[key] = normalized
        self._write_overrides(current)
        if self.state_db and changed:
            self.state_db.append_event(
                "runtime_settings_updated",
                "settings",
                "runtime",
                {"actor": actor, "changes": changed},
            )
        return self.snapshot()

    def reset(self, keys: list[str] | None = None, *, actor: str = "owner") -> dict[str, Any]:
        current = self._load_overrides()
        if keys is None:
            removed = sorted(current)
            current = {}
        else:
            unknown = [key for key in keys if key not in self.definitions()]
            if unknown:
                raise KeyError(f"Unknown runtime setting: {unknown[0]}")
            removed = []
            for key in keys:
                if key in current:
                    removed.append(key)
                    current.pop(key, None)
        self._write_overrides(current)
        if self.state_db and removed:
            self.state_db.append_event(
                "runtime_settings_reset",
                "settings",
                "runtime",
                {"actor": actor, "keys": removed},
            )
        return self.snapshot()

    def options_for_source(self, source_type: str) -> dict[str, Any]:
        if str(source_type).lower() not in _MEDIA_TYPES:
            return {}
        values = self.snapshot()["values"]
        return {
            "keyframe_interval_seconds": values["media_keyframe_interval_seconds"],
            "max_keyframes": values["media_max_keyframes"],
            "keyframe_max_dimension": values["media_keyframe_max_dimension"],
            "ffmpeg_max_concurrency": values["media_ffmpeg_max_concurrency"],
            "ffmpeg_threads": values["media_ffmpeg_threads"],
            "max_input_bytes": int(float(values["media_max_input_gb"]) * 1024**3),
            "max_duration_seconds": float(values["media_max_duration_minutes"]) * 60.0,
            "probe_timeout_seconds": values["media_probe_timeout_seconds"],
            "ffmpeg_timeout_seconds": values["media_ffmpeg_timeout_seconds"],
            "auto_transcribe": values["media_auto_transcribe"],
            "asr_provider": values["media_asr_provider"],
            "asr_model": values["media_asr_model"],
            "asr_device": values["media_asr_device"],
            "asr_compute_type": values["media_asr_compute_type"],
            "asr_language": values["media_asr_language"],
            "auto_ocr": values["media_auto_ocr"],
            "ocr_provider": values["media_ocr_provider"],
            "ocr_language": values["media_ocr_language"],
            "detect_scenes": values["media_detect_scenes"],
            "scene_provider": values["media_scene_provider"],
            "scene_threshold": values["media_scene_threshold"],
        }

    def priority_for_source(self, source_type: str) -> int:
        if str(source_type).lower() in _MEDIA_TYPES:
            return int(self.snapshot()["values"]["media_default_priority"])
        return 100

    def storage_policy(self) -> dict[str, Any]:
        values = self.snapshot()["values"]
        archive_categories = []
        if values["storage_archive_versions"]:
            archive_categories.append("versions")
        if values["storage_archive_logs"]:
            archive_categories.append("logs")
        return {
            "retention_days": {
                "derived": values["storage_derived_retention_days"],
                "versions": values["storage_versions_retention_days"],
                "logs": values["storage_logs_retention_days"],
                "temp": values["storage_temp_retention_days"],
                "cache": values["storage_cache_retention_days"],
            },
            "max_category_gb": {
                "derived": values["storage_derived_max_gb"],
                "versions": values["storage_versions_max_gb"],
                "logs": values["storage_logs_max_gb"],
            },
            "cold_storage_enabled": values["storage_cold_enabled"],
            "cold_storage_path": values["storage_cold_path"],
            "archive_categories": archive_categories,
            "auto_cleanup_enabled": values["storage_auto_cleanup_enabled"],
            "max_storage_gb": values["storage_max_gb"],
            "min_free_gb": values["storage_min_free_gb"],
        }

    def _load_overrides(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return {}
            try:
                data = json.loads(self.path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Unable to read runtime settings: {exc}") from exc
            if not isinstance(data, dict):
                raise RuntimeError("Runtime settings file must contain an object")
            overrides = data.get("overrides", data)
            if not isinstance(overrides, dict):
                return {}
            definitions = self.definitions()
            return {
                key: self._validate_value(key, value, definitions[key])
                for key, value in overrides.items()
                if key in definitions
            }

    def _write_overrides(self, overrides: Mapping[str, Any]) -> None:
        payload = {"schema_version": self.SCHEMA_VERSION, "overrides": dict(sorted(overrides.items()))}
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.path)

    @staticmethod
    def _validate_value(key: str, value: Any, definition: Mapping[str, Any]) -> Any:
        value_type = definition["type"]
        try:
            if value_type == "boolean":
                if isinstance(value, bool):
                    normalized: Any = value
                elif str(value).strip().lower() in {"1", "true", "yes", "on"}:
                    normalized = True
                elif str(value).strip().lower() in {"0", "false", "no", "off"}:
                    normalized = False
                else:
                    raise ValueError
            elif value_type == "integer":
                if isinstance(value, bool):
                    raise ValueError
                normalized = int(value)
                if float(value) != normalized:
                    raise ValueError
            elif value_type == "number":
                if isinstance(value, bool):
                    raise ValueError
                normalized = float(value)
            elif value_type in {"string", "choice"}:
                normalized = str(value).strip()
                if len(normalized) > int(definition.get("max_length") or 4096):
                    raise ValueError
            else:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid value for {key}: {value!r}") from exc
        minimum = definition.get("minimum")
        maximum = definition.get("maximum")
        if minimum is not None and normalized < minimum:
            raise ValueError(f"{key} must be >= {minimum}")
        if maximum is not None and normalized > maximum:
            raise ValueError(f"{key} must be <= {maximum}")
        choices = definition.get("choices")
        if choices and normalized not in choices:
            raise ValueError(f"{key} must be one of: {', '.join(str(item) for item in choices)}")
        return normalized

    @staticmethod
    def _base(group: str, label: str, description: str, kind: str, default: Any) -> dict[str, Any]:
        return {
            "group": group,
            "label": label,
            "description": description,
            "type": kind,
            "default": default,
            "restart_required": False,
        }

    @classmethod
    def _integer(cls, group: str, label: str, description: str, default: int, minimum: int, maximum: int) -> dict[str, Any]:
        return {**cls._base(group, label, description, "integer", default), "minimum": minimum, "maximum": maximum}

    @classmethod
    def _number(cls, group: str, label: str, description: str, default: float, minimum: float, maximum: float) -> dict[str, Any]:
        return {**cls._base(group, label, description, "number", default), "minimum": minimum, "maximum": maximum}

    @classmethod
    def _boolean(cls, group: str, label: str, description: str, default: bool) -> dict[str, Any]:
        return cls._base(group, label, description, "boolean", default)

    @classmethod
    def _string(cls, group: str, label: str, description: str, default: str, max_length: int) -> dict[str, Any]:
        return {**cls._base(group, label, description, "string", default), "max_length": max_length}

    @classmethod
    def _choice(cls, group: str, label: str, description: str, default: str, choices: list[str]) -> dict[str, Any]:
        return {**cls._base(group, label, description, "choice", default), "choices": choices, "max_length": 128}
