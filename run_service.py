import atexit
import logging
import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from main import PEMISCore
from src.config import settings
from src.control import LocalControlService
from src.extraction import ExtractionRequestInbox, ExtractionWorker, build_extraction_pipeline
from src.health import StartupHealthChecker
from src.obsidian import LingJiSystemUI
from src.skills import SkillRegistry

LOG_DIR = settings.log_path if settings.log_path.is_absolute() else BASE_DIR / settings.log_path
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
        self.skill_registry = None
        self.request_inbox = None
        self.system_ui = None
        self.local_control = None
        self.health_report = None
        self.running = False

    def start(self):
        if self.running:
            return
        settings.storage_path.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
        logger.info("LingJi service starting, pid=%s...", os.getpid())
        try:
            if settings.startup_health_check_enabled:
                checker = StartupHealthChecker(settings)
                self.health_report = checker.run()
                for item in self.health_report["checks"]:
                    level = logging.ERROR if item["status"] == "error" else logging.WARNING if item["status"] == "warning" else logging.INFO
                    logger.log(level, "Health[%s] %s", item["name"], item["message"])
                checker.ensure_startable(self.health_report)

            self.core = PEMISCore()
            self.core.start()
            self.local_control = LocalControlService(settings, state_db=self.core.state_db)
            self.extraction_pipeline = build_extraction_pipeline(
                settings,
                on_documents_written=self._on_documents_written,
                runtime_settings=self.local_control.runtime_settings,
            )
            self.skill_registry = SkillRegistry(self.core.vault_layout, self.core.state_db)
            self.request_inbox = ExtractionRequestInbox(
                self.core.vault_layout,
                self.extraction_pipeline,
                skill_registry=self.skill_registry,
                state_db=self.core.state_db,
            )
            self.system_ui = LingJiSystemUI(
                self.core.vault_layout,
                extraction_pipeline=self.extraction_pipeline,
                skill_registry=self.skill_registry,
                request_inbox=self.request_inbox,
            )
            self.system_ui.ensure()
            for root in settings.skill_sync_paths:
                try:
                    self.skill_registry.sync_directory(root)
                except Exception:
                    logger.exception("Skill auto sync failed: %s", root)
            if settings.extraction_worker_enabled:
                self.extraction_worker = ExtractionWorker(
                    self.extraction_pipeline,
                    poll_seconds=settings.extraction_poll_seconds,
                    batch_size=settings.extraction_batch_size,
                )
                self.extraction_worker.start()
            self.running = True
            if self.health_report:
                self.core.state_db.append_event(
                    "startup_health_check",
                    "service",
                    "lingji",
                    self.health_report,
                )
            logger.info("LingJi service started successfully")
        except Exception:
            if self.extraction_worker:
                self.extraction_worker.stop()
            if self.core:
                self.core.stop()
            self._remove_pid_file()
            raise

    def _on_documents_written(self, result):
        if not self.core:
            return
        indexed = 0
        for path_text in result.get("paths") or []:
            path = Path(path_text)
            if not path.exists():
                continue
            if not self.core.vault_layout.should_index(path, include_private=False):
                continue
            if self.core.indexer.incremental_add(path):
                self.core._sync_memory_file(path)
                indexed += 1
        if indexed:
            self.core._update_control_center()
        if self.system_ui:
            self.system_ui.refresh_status()
        self.core.state_db.append_event(
            "extraction_index_synced",
            "extraction",
            str(result.get("execution_id") or ""),
            {"indexed": indexed, "paths": result.get("paths") or []},
        )

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
                if self.request_inbox:
                    result = self.request_inbox.process_pending(limit=20)
                    if result["processed"] and self.system_ui:
                        self.system_ui.refresh_status()
                time.sleep(max(settings.extraction_request_interval_minutes * 60, 5))
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
