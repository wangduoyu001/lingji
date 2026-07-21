from dataclasses import FrozenInstanceError

import pytest

from src.capture.models import CaptureEnvelope, CaptureStatus


def test_capture_envelope_is_frozen_and_supports_text_without_url():
    envelope = CaptureEnvelope(
        capture_id="cap-1",
        source_type="web",
        capture_method="clipboard",
        text="hello",
    )
    assert envelope.url == ""
    assert envelope.privacy == "private"
    assert envelope.project_ids == ()
    with pytest.raises(FrozenInstanceError):
        envelope.text = "changed"


def test_capture_status_values_are_stable():
    assert CaptureStatus.QUEUED.value == "queued"
    assert CaptureStatus.DUPLICATE.value == "duplicate"
