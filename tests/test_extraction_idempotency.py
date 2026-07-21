from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.extraction.idempotency import (
    build_extraction_idempotency_key,
    build_input_identity,
    canonical_json_bytes,
    directory_manifest,
    extraction_key_for_request,
)
from src.extraction.queue import SQLiteExtractionQueue


def test_canonical_json_ignores_mapping_order_and_normalizes_datetime():
    first = {"b": 2, "a": {"when": datetime(2026, 7, 22, tzinfo=timezone.utc)}}
    second = {"a": {"when": datetime(2026, 7, 22, tzinfo=timezone.utc)}, "b": 2}
    assert canonical_json_bytes(first) == canonical_json_bytes(second)


def test_payload_order_does_not_change_key_but_adapter_version_does():
    common = {
        "source_type": "web",
        "adapter_name": "web_capture",
        "input_identity": {"kind": "payload"},
        "effective_options": {"network": False},
    }
    first = build_extraction_idempotency_key(
        **common,
        adapter_version="1.0",
        payload={"title": "x", "url": "https://example.test"},
    )
    reordered = build_extraction_idempotency_key(
        **common,
        adapter_version="1.0",
        payload={"url": "https://example.test", "title": "x"},
    )
    upgraded = build_extraction_idempotency_key(
        **common,
        adapter_version="2.0",
        payload={"title": "x", "url": "https://example.test"},
    )
    assert first == reordered
    assert first != upgraded


def test_same_file_content_at_different_paths_has_same_identity(tmp_path: Path):
    left = tmp_path / "left.txt"
    right = tmp_path / "nested" / "right.txt"
    right.parent.mkdir()
    left.write_text("same", encoding="utf-8")
    right.write_text("same", encoding="utf-8")

    assert build_input_identity(left) == build_input_identity(right)


def test_file_content_change_changes_key(tmp_path: Path):
    path = tmp_path / "input.txt"
    path.write_text("one", encoding="utf-8")
    first = extraction_key_for_request(
        source_type="file",
        adapter_name="text",
        adapter_version="1",
        input_path=path,
        payload={},
        effective_options={},
    )
    path.write_text("two", encoding="utf-8")
    second = extraction_key_for_request(
        source_type="file",
        adapter_name="text",
        adapter_version="1",
        input_path=path,
        payload={},
        effective_options={},
    )
    assert first != second


def test_directory_manifest_is_stable_and_content_sensitive(tmp_path: Path):
    root = tmp_path / "input"
    root.mkdir()
    (root / "b.txt").write_text("b", encoding="utf-8")
    (root / "a.txt").write_text("a", encoding="utf-8")
    first = directory_manifest(root)
    assert [item["path"] for item in first] == ["a.txt", "b.txt"]

    (root / "a.txt").write_text("changed", encoding="utf-8")
    second = directory_manifest(root)
    assert first != second


def test_missing_input_is_not_treated_as_empty(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_input_identity(tmp_path / "missing.txt")


def test_pipeline_and_queue_compatibility_signatures_share_the_same_key(tmp_path: Path):
    path = tmp_path / "input.txt"
    path.write_text("content", encoding="utf-8")
    direct = extraction_key_for_request(
        source_type="file",
        adapter_name="text",
        adapter_version="1",
        input_path=path,
        payload={"a": 1},
        effective_options={"b": 2},
    )
    queued = SQLiteExtractionQueue.build_idempotency_key(
        "file",
        path,
        {"a": 1},
        {"b": 2},
        "text",
        "1",
    )
    assert direct == queued


def test_duplicate_queue_submission_marks_existing_job(tmp_path: Path):
    queue = SQLiteExtractionQueue(tmp_path / "state.db")
    first = queue.enqueue("web", payload={"url": "https://example.test"})
    second = queue.enqueue("web", payload={"url": "https://example.test"})
    assert first["job_id"] == second["job_id"]
    assert first["existing_job"] is False
    assert second["existing_job"] is True
