from __future__ import annotations

import logging
import threading
from typing import Any

from .pipeline import ExtractionPipeline

logger = logging.getLogger("lingji.extraction.worker")


class ExtractionWorker:
    """Interruptible background worker for the durable extraction queue."""

    def __init__(
        self,
        pipeline: ExtractionPipeline,
        *,
        poll_seconds: float = 5.0,
        batch_size: int = 5,
        worker_id: str | None = None,
    ):
        self.pipeline = pipeline
        self.poll_seconds = max(float(poll_seconds), 0.2)
        self.batch_size = max(int(batch_size), 1)
        self.worker_id = worker_id
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_result: dict[str, Any] | None = None
        self._stop_outcome: dict[str, Any] = {"stopped": True, "thread_alive": False}

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._stop_outcome = {"stopped": False, "thread_alive": True}
        self._thread = threading.Thread(
            target=self._loop,
            name="lingji-extraction-worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("Extraction worker started")

    def stop(self, timeout: float = 10.0) -> dict[str, Any]:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(float(timeout), 0.1))
        alive = bool(self._thread and self._thread.is_alive())
        reconcile = getattr(self.pipeline, "reconcile_transient_files", None)
        transient_cleanup = reconcile() if callable(reconcile) else {}
        self._stop_outcome = {
            "stopped": not alive,
            "thread_alive": alive,
            "outcome": "timeout" if alive else "stopped",
            "transient_cleanup": transient_cleanup,
        }
        logger.info("Extraction worker stopped")
        return dict(self._stop_outcome)

    def status(self) -> dict[str, Any]:
        inventory = getattr(self.pipeline, "transient_cleanup_inventory", {})
        return {
            "running": self.running,
            "poll_seconds": self.poll_seconds,
            "batch_size": self.batch_size,
            "thread_alive": self.running,
            "stop_outcome": dict(self._stop_outcome),
            "queue": self.pipeline.queue.stats(),
            "last_result": self._last_result or {},
            "transient_cleanup": dict(inventory) if isinstance(inventory, dict) else {},
        }

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._last_result = self.pipeline.process_pending(
                    limit=self.batch_size,
                    worker_id=self.worker_id,
                )
            except Exception:
                logger.exception("Extraction worker loop failed")
            self._stop_event.wait(self.poll_seconds)
