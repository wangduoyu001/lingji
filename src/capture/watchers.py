from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .models import CaptureCapability, CaptureEnvelope
from .policy import CapturePolicy

CaptureEventCallback = Callable[[CaptureEnvelope], None]


class CaptureWatcher(Protocol):
    def start(self, callback: CaptureEventCallback) -> None: ...
    def stop(self) -> None: ...
    def status(self) -> dict[str, object]: ...
    def capabilities(self) -> tuple[CaptureCapability, ...]: ...


@dataclass
class NoOpCaptureWatcher:
    name: str
    policy: CapturePolicy
    running: bool = False
    paused: bool = False

    def start(self, callback: CaptureEventCallback) -> None:
        del callback
        self.running = True
        self.paused = False

    def stop(self) -> None:
        self.running = False

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def status(self) -> dict[str, object]:
        return {"name": self.name, "running": self.running, "paused": self.paused}

    def capabilities(self) -> tuple[CaptureCapability, ...]:
        return (CaptureCapability(self.name, True, realtime=False),)


class ClipboardWatcher(NoOpCaptureWatcher):
    def __init__(self, policy: CapturePolicy):
        super().__init__("clipboard", policy)
        self._last_content_hash = ""


class FolderWatcher(NoOpCaptureWatcher):
    def __init__(self, policy: CapturePolicy, roots: tuple[Path, ...] = ()):
        super().__init__("folder_watch", policy)
        self.roots = tuple(Path(root) for root in roots)
        self._validate_roots()

    def _validate_roots(self) -> None:
        for root in self.roots:
            resolved = root.expanduser().resolve()
            if resolved == Path(resolved.anchor):
                raise ValueError("FolderWatcher cannot watch a filesystem root")
        if not self.policy.filesystem_event_only:
            raise ValueError("FolderWatcher requires filesystem event mode")


class BrowserShareWatcher(NoOpCaptureWatcher):
    def __init__(self, policy: CapturePolicy):
        super().__init__("browser_extension", policy)


class MobileShareWatcher(NoOpCaptureWatcher):
    def __init__(self, policy: CapturePolicy):
        super().__init__("mobile_share", policy)
