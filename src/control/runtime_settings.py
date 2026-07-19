from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Mapping


_MEDIA_TYPES = {"media", "video", "audio"}


class RuntimeSettingsStore:
    """Persist owner-editable runtime settings for the future local control UI.

    Environment variables and ``src.config.Settings`` provide safe defaults. This
    store only keeps explicit owner overrides. The desktop UI, MCP and CLI can all
    use this service instead of editing ``.env`` or implementation files directly.
    """

    SCHEMA_VERSION = 1

    def __init__(self, settings: Any, state_db: Any | None = None):
        self.settings = settings
        self.state_db = state_db
        self.path = settings.storage_path / settings.runtime_settings_file
        self._lock = threading.RLock()

    def definitions(self) -> dict[str, dict[str, Any]]:
        return {
            "media_keyframe_interval_seconds": {
                "group": "media_processing",
                "label": "关键帧间隔（秒）",
                "description": "每隔多少秒提取一张关键帧。",
                "type": "number",
                "minimum": 1.0,
                "maximum": 86400.0,
                "default": float(self.settings.media_keyframe_interval_seconds),
                "restart_required": False,
            },
            "media_max_keyframes": {
                "group": "media_processing",
                "label": "关键帧最大数量",
                "description": "单个媒体任务最多生成的关键帧数量。",
                "type": "integer",
                "minimum": 1,
                "maximum": 100000,
                "default": int(self.settings.media_max_keyframes),
                "restart_required": False,
            },
            "media_keyframe_max_dimension": {
                "group": "media_processing",
                "label": "关键帧最大边长",
                "description": "关键帧最长边像素；保持原始比例。",
                "type": "integer",
                "minimum": 64,
                "maximum": 16384,
                "default": int(self.settings.media_keyframe_max_dimension),
                "restart_required": False,
            },
            "media_ffmpeg_max_concurrency": {
                "group": "media_processing",
                "label": "FFmpeg 最大并发任务",
                "description": "同时运行的 FFmpeg 派生任务数量。",
                "type": "integer",
                "minimum": 1,
                "maximum": 32,
                "default": int(self.settings.media_ffmpeg_max_concurrency),
                "restart_required": False,
            },
            "media_ffmpeg_threads": {
                "group": "media_processing",
                "label": "FFmpeg 单任务线程数",
                "description": "传递给 FFmpeg 的 -threads 与 -filter_threads。",
                "type": "integer",
                "minimum": 1,
                "maximum": 128,
                "default": int(self.settings.media_ffmpeg_threads),
                "restart_required": False,
            },
            "media_max_input_gb": {
                "group": "media_processing",
                "label": "单文件最大体积（GB）",
                "description": "0 表示不限制；超出时任务在处理前拒绝。",
                "type": "number",
                "minimum": 0.0,
                "maximum": 102400.0,
                "default": float(self.settings.media_max_input_gb),
                "restart_required": False,
            },
            "media_max_duration_minutes": {
                "group": "media_processing",
                "label": "单文件最大时长（分钟）",
                "description": "0 表示不限制；依赖 FFprobe 获取时长。",
                "type": "number",
                "minimum": 0.0,
                "maximum": 5256000.0,
                "default": float(self.settings.media_max_duration_minutes),
                "restart_required": False,
            },
            "media_default_priority": {
                "group": "media_processing",
                "label": "媒体任务默认优先级",
                "description": "数值越小越优先；任务提交时可以临时覆盖。",
                "type": "integer",
                "minimum": 0,
                "maximum": 10000,
                "default": int(self.settings.media_default_priority),
                "restart_required": False,
            },
            "media_probe_timeout_seconds": {
                "group": "media_processing",
                "label": "FFprobe 超时（秒）",
                "description": "读取媒体元数据的最长等待时间。",
                "type": "number",
                "minimum": 1.0,
                "maximum": 3600.0,
                "default": float(self.settings.media_probe_timeout_seconds),
                "restart_required": False,
            },
            "media_ffmpeg_timeout_seconds": {
                "group": "media_processing",
                "label": "FFmpeg 超时（秒）",
                "description": "单个音轨或关键帧派生步骤的最长等待时间。",
                "type": "number",
                "minimum": 1.0,
                "maximum": 604800.0,
                "default": float(self.settings.media_ffmpeg_timeout_seconds),
                "restart_required": False,
            },
        }

    def snapshot(self) -> dict[str, Any]:
        definitions = self.definitions()
        overrides = self._load_overrides()
        values = {
            key: overrides.get(key, definition["default"])
            for key, definition in definitions.items()
        }
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
                "media_processing",
                {"actor": actor, "changes": changed},
            )
        return self.snapshot()

    def reset(self, keys: list[str] | None = None, *, actor: str = "owner") -> dict[str, Any]:
        current = self._load_overrides()
        if keys is None:
            removed = sorted(current)
            current = {}
        else:
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
                "media_processing",
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
        }

    def priority_for_source(self, source_type: str) -> int:
        if str(source_type).lower() in _MEDIA_TYPES:
            return int(self.snapshot()["values"]["media_default_priority"])
        return 100

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
            return dict(overrides) if isinstance(overrides, dict) else {}

    def _write_overrides(self, overrides: Mapping[str, Any]) -> None:
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "overrides": dict(sorted(overrides.items())),
        }
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.path)

    @staticmethod
    def _validate_value(key: str, value: Any, definition: Mapping[str, Any]) -> int | float:
        value_type = definition["type"]
        try:
            normalized: int | float
            if value_type == "integer":
                if isinstance(value, bool):
                    raise ValueError
                normalized = int(value)
                if float(value) != normalized:
                    raise ValueError
            else:
                if isinstance(value, bool):
                    raise ValueError
                normalized = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid value for {key}: {value!r}") from exc
        minimum = definition.get("minimum")
        maximum = definition.get("maximum")
        if minimum is not None and normalized < minimum:
            raise ValueError(f"{key} must be >= {minimum}")
        if maximum is not None and normalized > maximum:
            raise ValueError(f"{key} must be <= {maximum}")
        return normalized
