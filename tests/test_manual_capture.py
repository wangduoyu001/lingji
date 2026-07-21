from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.capture.manual import (
    CAPTURE_UNSUPPORTED_TYPE,
    ManualCaptureError,
    ManualCaptureKind,
    build_manual_envelope,
    classify_manual_input,
)
from src.capture.policy import CaptureMode, CapturePolicy
from src.capture.service import CaptureService
from src.capture.models import CaptureEnvelope, CaptureStatus


class FakePipeline:
    def __init__(self):
        self.enqueued = []
        self.executed = []

    def enqueue(self, source_type, **kwargs):
        self.enqueued.append((source_type, kwargs))
        return {"job_id": "job-1"}

    def execute(self, source_type, **kwargs):
        self.executed.append((source_type, kwargs))
        return {"execution_id": "exec-1"}


def test_manual_helpers_use_formal_methods_and_queue_by_default(tmp_path):
    pipeline = FakePipeline()
    service = CaptureService(pipeline, policy=CapturePolicy.for_mode(CaptureMode.NORMAL))
    text_path = tmp_path / "note.txt"
    text_path.write_text("note", encoding="utf-8")
    media_path = tmp_path / "clip.mp4"
    media_path.write_bytes(b"media")

    assert service.submit_text("hello").status is CaptureStatus.QUEUED
    assert pipeline.enqueued[-1][1]["payload"]["capture_method"] == "manual_text"
    assert service.submit_web("https://example.com").status is CaptureStatus.QUEUED
    assert pipeline.enqueued[-1][1]["payload"]["capture_method"] == "manual_web"
    assert service.submit_file(text_path).status is CaptureStatus.QUEUED
    assert pipeline.enqueued[-1][1]["payload"]["capture_method"] == "manual_file"
    assert service.submit_media(media_path).status is CaptureStatus.QUEUED
    assert pipeline.enqueued[-1][1]["payload"]["capture_method"] == "manual_media"
    assert not pipeline.executed
    assert all(call[1]["options"]["privacy"] == "private" for call in pipeline.enqueued)


def test_chatgpt_zip_json_and_directory_classification(tmp_path):
    archive = tmp_path / "export.zip"
    archive.write_bytes(b"zip")
    export_json = tmp_path / "export.json"
    export_json.write_text(json.dumps([{"id": "c1", "mapping": {}}]), encoding="utf-8")
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    (export_dir / "conversations-1.json").write_text("[]", encoding="utf-8")

    for value in (archive, export_json, export_dir):
        result = classify_manual_input(value)
        assert result.kind is ManualCaptureKind.CHATGPT_EXPORT
        assert result.source_type == "chatgpt_export"
        assert result.capture_method == "manual_chatgpt_export"
        assert result.adapter_name == "chatgpt_export"


def test_codex_requires_explicit_mode_and_plain_json_is_web(tmp_path):
    report = tmp_path / "report.json"
    report.write_text('{"task_id":"t1"}', encoding="utf-8")
    automatic = classify_manual_input(report)
    explicit = classify_manual_input(report, selected_kind="codex")
    assert automatic.kind is ManualCaptureKind.WEB
    assert automatic.adapter_name == "web_capture"
    assert explicit.kind is ManualCaptureKind.CODEX_REPORT
    assert explicit.source_type == "codex_report"
    assert explicit.adapter_name == "codex_work_report"


def test_html_txt_url_and_raw_html_map_to_web(tmp_path):
    html_file = tmp_path / "page.html"
    html_file.write_text("<html><body>x</body></html>", encoding="utf-8")
    txt_file = tmp_path / "page.txt"
    txt_file.write_text("x", encoding="utf-8")
    for value in (html_file, txt_file, "https://example.com", "<html><body>x</body></html>"):
        result = classify_manual_input(value)
        assert result.kind in {ManualCaptureKind.WEB, ManualCaptureKind.TEXT}
        assert result.source_type == "web"
        assert result.adapter_name == "web_capture"


def test_media_extensions_use_existing_media_adapter(tmp_path):
    for filename in ("clip.mp4", "voice.wav"):
        path = tmp_path / filename
        path.write_bytes(b"media")
        result = classify_manual_input(path)
        assert result.kind is ManualCaptureKind.MEDIA
        assert result.source_type == "media"
        assert result.adapter_name == "media_local"


@pytest.mark.parametrize("filename", ["file.pdf", "file.docx", "file.xlsx", "file.pptx", "file.bin"])
def test_unsupported_files_return_stable_code(tmp_path, filename):
    path = tmp_path / filename
    path.write_bytes(b"binary")
    result = classify_manual_input(path)
    assert result.supported is False
    assert result.error_code == CAPTURE_UNSUPPORTED_TYPE
    with pytest.raises(ManualCaptureError, match=CAPTURE_UNSUPPORTED_TYPE):
        build_manual_envelope(path)


def test_adapter_conflict_is_rejected(tmp_path):
    path = tmp_path / "page.txt"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="adapter_name conflicts"):
        build_manual_envelope(path, adapter_name="media_local")

    service = CaptureService(FakePipeline())
    envelope = CaptureEnvelope(
        capture_id="cap-conflict",
        source_type="web",
        capture_method="manual_file",
        adapter_name="media_local",
        input_path=path,
        process_later=True,
    )
    with pytest.raises(ValueError, match="source_type conflicts"):
        service.submit(envelope)


def test_metadata_cannot_override_manual_contract(tmp_path):
    path = tmp_path / "page.txt"
    path.write_text("hello", encoding="utf-8")
    service = CaptureService(FakePipeline())
    envelope = build_manual_envelope(path, metadata={"adapter_name": "media_local"})
    with pytest.raises(ValueError, match="reserved capture fields"):
        service.submit(envelope)


def test_media_requests_cannot_bypass_low_power_policy(tmp_path):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"media")
    pipeline = FakePipeline()
    service = CaptureService(pipeline, policy=CapturePolicy.for_mode(CaptureMode.LOW_POWER))
    service.submit_media(
        path,
        allow_ocr=True,
        allow_transcription=True,
        extract_keyframes=True,
        extract_audio=True,
    )
    options = pipeline.enqueued[0][1]["options"]
    assert options["allow_ocr"] is False
    assert options["allow_video_transcription"] is False
    assert options["extract_keyframes"] is False
    assert options["extract_audio"] is False


def test_deferred_capabilities_are_disabled():
    capabilities = {item.name: item for item in CaptureService(FakePipeline()).capabilities()}
    for name in (
        "mobile_share",
        "browser_extension",
        "clipboard",
        "folder_watch",
        "global_keyboard_listener",
        "fullscreen_capture_listener",
    ):
        assert capabilities[name].enabled is False
    for name in ("mobile_share", "browser_extension", "clipboard", "folder_watch"):
        assert "deferred" in capabilities[name].description


def test_missing_path_error_does_not_expose_absolute_path(tmp_path):
    missing = tmp_path / "private-user" / "missing.mp4"
    service = CaptureService(FakePipeline())
    with pytest.raises(ValueError) as exc:
        service.submit_media(missing)
    assert str(exc.value) == "CAPTURE_FILE_NOT_FOUND"
    assert str(tmp_path) not in str(exc.value)


def test_long_manual_text_does_not_fail_path_probe():
    value = "manual text " * 1000
    result = classify_manual_input(value)
    assert result.kind is ManualCaptureKind.TEXT
    assert result.text == value.strip()


def test_local_control_share_capability_remains_enabled():
    capabilities = {item.name: item for item in CaptureService(FakePipeline()).capabilities()}
    assert capabilities["local_control_share"].enabled is True
