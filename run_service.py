import atexit
import logging
import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.extraction import ExtractionWorker, build_extraction_pipeline
from main import PEMISCore

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PID_FILE = settings.storage_path / "lingji.pid"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "lingji_service.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("lingji.service")


class LingJiService:
    def __init__(self):
        self.core = None
        self.extraction_pipeline = None
        self.extraction_worker = None
        self.running = False

    def start(self):
        if self.running:
            return
        settings.storage_path.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
        logger.info("LingJi service starting, pid=%s...", os.getpid())
        try:
            self.core = PEMISCore()
            self.core.start()
            if settings.extraction_worker_enabled:
                self.extraction_pipeline = build_extraction_pipeline(settings)
                self.extraction_worker = ExtractionWorker(
                    self.extraction_pipeline,
                    poll_seconds=settings.extraction_poll_seconds,
                    batch_size=settings.extraction_batch_size,
                )
                self.extraction_worker.start()
            self.running = True
            logger.info("LingJi service started successfully")
        except Exception:
            if self.extraction_worker:
                self.extraction_worker.stop()
            if self.core:
                self.core.stop()
            self._remove_pid_file()
            raise

    def stop(self):
        logger.info("LingJi service stopping...")
        if self.extraction_worker:
            self.extraction_worker.stop()
        if self.core:
            self.core.stop()
        self.running = False
        self._remove_pid_file()
        logger.info("LingJi service stopped")

    def run_forever(self):
        self.start()
        try:
            while self.running:
                time.sleep(10)
        except KeyboardInterrupt:
            self.stop()

    @staticmethod
    def _remove_pid_file():
        try:
            PID_FILE.unlink(missing_ok=True)
        except OSError:
            logger.warning("Unable to remove PID file: %s", PID_FILE)


if __name__ == "__main__":
    service = LingJiService()
    atexit.register(service._remove_pid_file)
    service.run_forever()
