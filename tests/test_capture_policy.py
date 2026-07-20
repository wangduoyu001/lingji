from pathlib import Path

import pytest

from src.capture.policy import CaptureMode, CapturePolicy
from src.capture.watchers import FolderWatcher


def test_default_policy_is_low_risk():
    policy = CapturePolicy()
    assert policy.mode is CaptureMode.LOW_POWER
    assert policy.queue_only is True
    assert policy.allow_realtime is False
    assert policy.allow_ocr is False
    assert policy.allow_video_transcription is False
    assert policy.global_keyboard_listener is False
    assert policy.fullscreen_capture_listener is False
    assert policy.filesystem_event_only is True


def test_low_power_does_not_allow_heavy_media():
    assert CapturePolicy().permits_heavy_media() is False
    assert CapturePolicy.for_mode(CaptureMode.DEEP_CAPTURE).permits_heavy_media() is True


def test_paused_policy_disables_vectorization():
    policy = CapturePolicy.for_mode(CaptureMode.PAUSED)
    assert policy.mode is CaptureMode.PAUSED
    assert policy.allow_vectorization is False


def test_folder_watcher_rejects_filesystem_root():
    root = Path(Path.cwd().anchor)
    with pytest.raises(ValueError):
        FolderWatcher(CapturePolicy(), roots=(root,))
