from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CaptureMode(str, Enum):
    LOW_POWER = "low_power"
    NORMAL = "normal"
    DEEP_CAPTURE = "deep_capture"
    PAUSED = "paused"


@dataclass(frozen=True)
class CapturePolicy:
    mode: CaptureMode = CaptureMode.LOW_POWER
    allow_realtime: bool = False
    queue_only: bool = True
    allow_ocr: bool = False
    allow_video_transcription: bool = False
    allow_vectorization: bool = True
    idle_only: bool = True
    ac_power_only: bool = False
    cpu_budget_percent: int = 20
    allow_gpu: bool = False
    batch_size: int = 10
    debounce_seconds: float = 2.0
    duplicate_window_seconds: int = 86400
    max_file_bytes: int = 2 * 1024 * 1024 * 1024
    global_keyboard_listener: bool = False
    fullscreen_capture_listener: bool = False
    software_install_listener: bool = False
    filesystem_event_only: bool = True

    @classmethod
    def for_mode(cls, mode: CaptureMode) -> "CapturePolicy":
        if mode is CaptureMode.PAUSED:
            return cls(mode=mode, allow_vectorization=False)
        if mode is CaptureMode.NORMAL:
            return cls(
                mode=mode,
                allow_realtime=True,
                queue_only=False,
                idle_only=False,
                cpu_budget_percent=45,
                batch_size=25,
                allow_gpu=True,
            )
        if mode is CaptureMode.DEEP_CAPTURE:
            return cls(
                mode=mode,
                allow_realtime=False,
                queue_only=True,
                allow_ocr=True,
                allow_video_transcription=True,
                idle_only=True,
                ac_power_only=True,
                cpu_budget_percent=70,
                allow_gpu=True,
                batch_size=5,
            )
        return cls()

    def permits_heavy_media(self) -> bool:
        return self.allow_ocr or self.allow_video_transcription
