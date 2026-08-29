from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Callable, Iterable

from watchfiles import watch

from .models import SourceRecord


class AutomaticMemoryWatcher:
    """Low-latency observation for already-authorized source roots.

    File notifications are only hints.  The callback is the existing scan
    admission boundary; reconciliation remains the correctness mechanism.
    """

    def __init__(
        self,
        *,
        source_provider: Callable[[str], SourceRecord | dict],
        on_change: Callable[[str], object],
        on_error: Callable[[str, str], object] | None = None,
        clock: Callable[[], float] | None = None,
        watch_backend: Callable[..., Iterable[set[tuple[object, str]]]] | None = None,
        stop_timeout_seconds: float = 2.0,
    ) -> None:
        self._source_provider = source_provider
        self._on_change = on_change
        self._on_error = on_error or (lambda source_id, error: None)
        self._clock = clock or time.monotonic
        self._watch_backend = watch_backend or watch
        self.stop_timeout_seconds = max(float(stop_timeout_seconds), 0.01)
        self._lock = threading.RLock()
        self._sources: dict[str, dict[str, object]] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._stops: dict[str, threading.Event] = {}
        self._generations: dict[str, int] = {}
        self._paused = False

    def start(self, source_id: str, debounce_seconds: int = 5) -> None:
        source = self._source(source_id)
        self._check_source(source)
        debounce = max(float(debounce_seconds), 0.1)
        with self._lock:
            if source_id in self._threads:
                return
            stop = threading.Event()
            generation = self._generations.get(source_id, 0) + 1
            self._generations[source_id] = generation
            self._stops[source_id] = stop
            self._sources[source_id] = {
                "root": str(Path(self._value(source, "root")).expanduser().resolve(strict=False)),
                "debounce": debounce,
                "pending_at": None,
                "pending": False,
                "generation": generation,
            }
            thread = threading.Thread(
                target=self._watch,
                args=(
                    source_id,
                    stop,
                    str(self._sources[source_id]["root"]),
                    float(self._sources[source_id]["debounce"]),
                    generation,
                ),
                daemon=True,
                name=f"lingji-memory-watch-{source_id}",
            )
            self._threads[source_id] = thread
            thread.start()

    def stop(self, *, timeout_seconds: float | None = None) -> dict[str, object]:
        with self._lock:
            stops = list(self._stops.values())
            threads = list(self._threads.values())
        for stop in stops:
            stop.set()
        for thread in threads:
            if thread is not threading.current_thread():
                thread.join(timeout=max(
                    float(timeout_seconds)
                    if timeout_seconds is not None
                    else self.stop_timeout_seconds,
                    0.01,
                ))
        surviving: list[str] = []
        with self._lock:
            for source_id, thread in tuple(self._threads.items()):
                if thread.is_alive():
                    surviving.append(thread.name)
                else:
                    self._threads.pop(source_id, None)
                    self._stops.pop(source_id, None)
                    self._sources.pop(source_id, None)
        return {"stopped": not surviving, "surviving_threads": sorted(surviving)}

    def stop_source(
        self, source_id: str, *, timeout_seconds: float | None = None
    ) -> dict[str, object]:
        """Stop one OS watcher after a source leaves the authorized set."""
        with self._lock:
            stop = self._stops.get(source_id)
            thread = self._threads.get(source_id)
        if stop is not None:
            stop.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(
                float(timeout_seconds)
                if timeout_seconds is not None
                else self.stop_timeout_seconds,
                0.01,
            ))
        surviving = bool(thread is not None and thread.is_alive())
        if not surviving:
            with self._lock:
                self._threads.pop(source_id, None)
                self._stops.pop(source_id, None)
                self._sources.pop(source_id, None)
        return {
            "stopped": not surviving,
            "surviving_threads": [thread.name] if surviving and thread else [],
        }

    def running_sources(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._threads))

    def pause(self) -> None:
        with self._lock:
            self._paused = True
            for source in self._sources.values():
                source["pending"] = False
                source["pending_at"] = None

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    def notify(self, source_id: str, changes: Iterable[tuple[object, str]]) -> None:
        """Record one backend batch after checking every path boundary."""
        with self._lock:
            if source_id not in self._sources:
                raise LookupError(f"watcher source is not running: {source_id}")
            if self._paused:
                return
            # watchfiles may yield an empty batch while a directory is quiet.
            # It is an observation heartbeat, not evidence that a source changed.
            changes = tuple(changes)
            if not changes:
                return
            source = self._source(source_id)
            if str(self._value(source, "status")) != "authorized":
                # Revocation/unsupported transitions are normal lifecycle
                # signals; discard pending hints without admitting work.
                state = self._sources[source_id]
                state["pending"] = False
                state["pending_at"] = None
                return
            self._check_source(source)
            root = Path(str(self._sources[source_id]["root"]))
            for _change, raw_path in changes:
                path = Path(raw_path).expanduser()
                resolved = path.resolve(strict=False)
                try:
                    resolved.relative_to(root)
                except ValueError as exc:
                    raise PermissionError("watch event escapes the authorized source root") from exc
                if path.is_symlink():
                    raise PermissionError("symbolic-link watch events are not allowed")
            state = self._sources[source_id]
            state["pending"] = True
            if state["pending_at"] is None:
                state["pending_at"] = self._clock()

    def flush(self, source_id: str, *, force: bool = False) -> bool:
        with self._lock:
            state = self._sources.get(source_id)
            if state is None or self._paused or not state["pending"]:
                return False
            source = self._source(source_id)
            if str(self._value(source, "status")) != "authorized":
                state["pending"] = False
                state["pending_at"] = None
                return False
            pending_at = float(state["pending_at"] or self._clock())
            if not force and self._clock() - pending_at < float(state["debounce"]):
                return False
            state["pending"] = False
            state["pending_at"] = None
        self._on_change(source_id)
        return True

    def _watch(
        self,
        source_id: str,
        stop: threading.Event,
        root: str,
        debounce_seconds: float,
        generation: int,
    ) -> None:
        debounce_ms = int(debounce_seconds * 1000)
        try:
            for changes in self._watch_backend(
                root, debounce=debounce_ms, stop_event=stop, recursive=True
            ):
                if stop.is_set():
                    break
                try:
                    self.notify(source_id, changes)
                    # watchfiles has already applied the requested debounce.
                    self.flush(source_id, force=True)
                except LookupError as exc:
                    self._on_error(source_id, str(exc)[:2000])
                    break
                except PermissionError as exc:
                    # Revocation/unsupported is an intentional stop; an
                    # authorized source failing a boundary check is auditable.
                    try:
                        current = self._source(source_id)
                        revoked = str(self._value(current, "status")) in {
                            "revoked",
                            "unsupported",
                            "expired",
                        }
                    except Exception:
                        revoked = False
                    if not revoked:
                        self._on_error(source_id, str(exc)[:2000])
                    break
                except Exception as exc:
                    # A broken source must not terminate the scheduler process;
                    # persist the truthful error through the scheduler callback.
                    self._on_error(source_id, str(exc)[:2000])
                    continue
        except Exception as exc:
            self._on_error(source_id, str(exc)[:2000])
        finally:
            with self._lock:
                current_thread = self._threads.get(source_id)
                current_state = self._sources.get(source_id)
                if (
                    current_thread is threading.current_thread()
                    and current_state is not None
                    and current_state.get("generation") == generation
                ):
                    self._threads.pop(source_id, None)
                    self._stops.pop(source_id, None)
                    self._sources.pop(source_id, None)

    def _source(self, source_id: str) -> SourceRecord | dict:
        source = self._source_provider(source_id)
        if source is None:
            raise LookupError(f"source not found: {source_id}")
        return source

    @staticmethod
    def _value(source: SourceRecord | dict, key: str) -> object:
        return source.get(key) if isinstance(source, dict) else getattr(source, key)

    def _check_source(self, source: SourceRecord | dict) -> None:
        if str(self._value(source, "status")) != "authorized":
            raise PermissionError("source is not authorized for watching")
        root = Path(str(self._value(source, "root"))).expanduser()
        if root.is_symlink() or not root.exists() or not root.is_dir():
            raise PermissionError("authorized watch root must be a real directory")
        absolute = Path(os.path.abspath(str(root)))
        if self._has_symlink_component(absolute):
            raise PermissionError("watch root contains a symbolic-link component")
        if absolute.resolve(strict=False) != absolute:
            raise PermissionError("watch root is not canonical")

    @staticmethod
    def _has_symlink_component(path: Path) -> bool:
        current = path
        while current != current.parent:
            if current.is_symlink():
                return True
            current = current.parent
        return False
