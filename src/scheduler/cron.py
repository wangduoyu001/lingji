from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from src.storage.state_db import StateDatabase

logger = logging.getLogger("pemis.scheduler")


class CronScheduler:
    def __init__(
        self,
        state_db: StateDatabase,
        mode_provider: Callable[[], str] | None = None,
        poll_seconds: float = 60.0,
        max_workers: int = 2,
    ):
        self.state_db = state_db
        self.mode_provider = mode_provider or (lambda: "NORMAL")
        self.poll_seconds = max(float(poll_seconds), 0.05)
        self.max_workers = max(int(max_workers), 1)
        self.running = False
        self._thread: threading.Thread | None = None
        self._runner = None
        self._executor: ThreadPoolExecutor | None = None
        self._running_jobs: set[str] = set()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()

    def add_job(
        self,
        name,
        interval_hours,
        min_mode="NORMAL",
        enabled=True,
        run_on_start=False,
    ):
        self.state_db.upsert_scheduler_job(
            name=name,
            interval_hours=interval_hours,
            min_mode=min_mode,
            enabled=enabled,
            run_on_start=run_on_start,
        )

    def start(self, runner_callback=None):
        if self.running:
            return
        self._stop_event.clear()
        self.running = True
        self._runner = runner_callback
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="lingji-job",
        )
        self._thread = threading.Thread(
            target=self._loop,
            name="lingji-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("Scheduler started: %d jobs", len(self.state_db.list_scheduler_jobs()))

    def _loop(self):
        while self.running:
            try:
                current_mode = str(self.mode_provider() or "NORMAL").upper()
                for job in self.state_db.due_scheduler_jobs():
                    if not self.running:
                        break
                    name = job["name"]
                    if not self._mode_allows(current_mode, job.get("min_mode", "NORMAL")):
                        continue
                    with self._lock:
                        if name in self._running_jobs:
                            continue
                        self._running_jobs.add(name)
                    executor = self._executor
                    if executor is None:
                        with self._lock:
                            self._running_jobs.discard(name)
                        break
                    executor.submit(self._run_job, job)
                if self._stop_event.wait(self.poll_seconds):
                    break
            except Exception as exc:
                logger.exception("Scheduler loop failed: %s", exc)
                if self._stop_event.wait(self.poll_seconds):
                    break

    def _run_job(self, job):
        name = job["name"]
        self.state_db.mark_job_started(name)
        success = False
        error = None
        try:
            if self._runner:
                self._runner(name)
            success = True
        except Exception as exc:
            error = str(exc)
            logger.exception("Scheduled job failed: %s", name)
        finally:
            self.state_db.mark_job_finished(name, success=success, error=error)
            with self._lock:
                self._running_jobs.discard(name)

    @staticmethod
    def _mode_allows(current_mode: str, required_mode: str) -> bool:
        current_mode = current_mode.upper()
        required_mode = str(required_mode or "NORMAL").upper()
        if current_mode == "EMERGENCY":
            return required_mode == "EMERGENCY"
        if current_mode == "MAINTENANCE":
            return required_mode in {"NORMAL", "MAINTENANCE"}
        return required_mode == "NORMAL"

    def stop(self):
        """Stop scheduling and wait until all in-flight jobs release resources."""
        self.running = False
        self._stop_event.set()

        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=max(self.poll_seconds * 2, 1.0))
            if thread.is_alive():
                raise RuntimeError("Scheduler thread did not stop cleanly")
        self._thread = None

        executor = self._executor
        self._executor = None
        if executor:
            executor.shutdown(wait=True, cancel_futures=False)

        self._runner = None
        with self._lock:
            if self._running_jobs:
                raise RuntimeError(
                    f"Scheduler stopped with active jobs: {sorted(self._running_jobs)}"
                )

    def get_status(self):
        return self.state_db.list_scheduler_jobs()
