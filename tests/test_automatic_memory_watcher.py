from __future__ import annotations

from pathlib import Path
import threading
import time

from src.automatic_memory.models import SourceRecord
from src.automatic_memory.watcher import AutomaticMemoryWatcher


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value


def source(root: Path) -> SourceRecord:
    return SourceRecord("src-1", "codex", str(root), "authorized", "metadata_discovery", "v1")


def test_events_are_debounced_for_five_seconds_and_duplicate_callbacks_are_suppressed(tmp_path: Path):
    clock = Clock()
    calls: list[str] = []
    watcher = AutomaticMemoryWatcher(
        source_provider=lambda source_id: source(tmp_path),
        on_change=lambda source_id: calls.append(source_id),
        clock=clock,
    )
    watcher.start("src-1", debounce_seconds=5)
    watcher.notify("src-1", {("modified", str(tmp_path / "one.json"))})
    watcher.notify("src-1", {("modified", str(tmp_path / "one.json"))})
    watcher.flush("src-1")
    assert calls == []
    clock.value += 5
    watcher.flush("src-1")
    watcher.flush("src-1")
    assert calls == ["src-1"]
    watcher.stop()


def test_pause_revoke_and_unsupported_sources_do_not_admit_work(tmp_path: Path):
    calls: list[str] = []
    current = source(tmp_path)
    watcher = AutomaticMemoryWatcher(
        source_provider=lambda source_id: current,
        on_change=lambda source_id: calls.append(source_id),
    )
    watcher.start("src-1")
    watcher.pause()
    watcher.notify("src-1", {("modified", str(tmp_path / "x"))})
    assert watcher.flush("src-1") is False
    current = SourceRecord(current.source_id, current.kind, current.root, "revoked", current.capability, current.policy_version)
    watcher.resume()
    watcher.notify("src-1", {("modified", str(tmp_path / "y"))})
    assert watcher.flush("src-1") is False
    watcher.stop()


def test_watcher_never_accepts_a_path_outside_the_authorized_root(tmp_path: Path):
    calls: list[str] = []
    watcher = AutomaticMemoryWatcher(
        source_provider=lambda source_id: source(tmp_path),
        on_change=lambda source_id: calls.append(source_id),
    )
    watcher.start("src-1")
    try:
        watcher.notify("src-1", {("modified", str(tmp_path.parent / "escape.json"))})
    except PermissionError:
        pass
    else:
        raise AssertionError("outside-root event was accepted")
    assert calls == []
    watcher.stop()


def test_backend_creation_failure_is_reported_and_thread_exits(tmp_path: Path):
    errors: list[str] = []

    def broken_backend(*args, **kwargs):
        raise RuntimeError("backend unavailable")

    watcher = AutomaticMemoryWatcher(
        source_provider=lambda source_id: source(tmp_path),
        on_change=lambda source_id: None,
        on_error=lambda source_id, error: errors.append(error),
        watch_backend=broken_backend,
    )
    watcher.start("src-1")
    deadline = time.monotonic() + 1
    while not errors and time.monotonic() < deadline:
        time.sleep(0.01)
    assert errors == ["backend unavailable"]
    watcher.stop()


def test_stop_source_stops_backend_without_stopping_other_sources(tmp_path: Path):
    stopped: list[str] = []
    entered = threading.Event()

    def backend(root, **kwargs):
        entered.set()
        stop_event = kwargs["stop_event"]
        while not stop_event.wait(0.01):
            yield set()

    second = tmp_path / "second"
    second.mkdir()
    records = {"src-1": source(tmp_path), "src-2": source(second)}
    watcher = AutomaticMemoryWatcher(
        source_provider=lambda source_id: records[source_id],
        on_change=lambda source_id: None,
        watch_backend=backend,
    )
    watcher.start("src-1")
    watcher.start("src-2")
    assert entered.wait(1)
    watcher.stop_source("src-1")
    assert "src-1" not in watcher.running_sources()
    assert "src-2" in watcher.running_sources()
    watcher.stop()
