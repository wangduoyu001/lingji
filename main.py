import hashlib
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.api.decision_engine import DecisionEngine
from src.config import settings
from src.dashboard import update_dashboard
from src.embedding.embedder import Embedder
from src.indexer.index import PEMISIndex
from src.memory import InboxService, VaultLayout
from src.opp_generator import OppGenerator
from src.scheduler.cron import CronScheduler
from src.scheduler.distillation import DistillationEngine
from src.scheduler.integrity import IntegrityChecker
from src.security.safety import SafetyGuard
from src.user_feedback import UserFeedback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("pemis.main")


class PEMISCore:
    def __init__(self):
        logger.info("PEMIS v6 single-vault foundation initializing...")
        self.settings = settings
        self.vault_layout = VaultLayout(settings.vault_path)
        self.inbox = InboxService(self.vault_layout)
        self.indexer = PEMISIndex(
            settings.vault_path,
            settings.storage_path,
            include_private=settings.index_private,
        )
        self.embedder = Embedder(
            settings.ollama_base_url,
            settings.embed_model,
            settings.fallback_embed_model,
            settings.cache_max,
        )
        self.scheduler = CronScheduler()
        self.safety = SafetyGuard(settings)
        self.distiller = DistillationEngine(settings)
        self.integrity = IntegrityChecker(settings)
        self.feedback = UserFeedback(settings)
        self.generator = OppGenerator(settings, self.indexer)
        self.decision = DecisionEngine(
            self.indexer,
            settings.storage_path,
            settings.decision_history_days,
            vault_path=settings.vault_path,
            opp_generator=self.generator,
            user_feedback=self.feedback,
        )
        self._running = False
        self._start_time = None
        self._error_log = []

    def start(self):
        self._running = True
        self._start_time = time.time()

        if settings.vault_auto_init:
            created = self.vault_layout.ensure()
            if created:
                logger.info("Single vault layout initialized: %d folders created", len(created))

        self.indexer.build_index()
        self.decision.decide(count=6)
        self._update_control_center()

        if settings.watchdog_enabled:
            self.indexer.start_watchdog(callback=self._on_file_change)

        self.scheduler.add_job("distill", 24, "NORMAL")
        self.scheduler.add_job("integrity", 24, "MAINTENANCE")
        self.scheduler.add_job("full_check", 24, "MAINTENANCE")
        self.scheduler.add_job("read_feedback", 0.167, "NORMAL")
        self.scheduler.add_job("daily_capture", 24, "NORMAL")
        self.scheduler.start(runner_callback=self._run_job)

        self._update_control_center()
        logger.info("PEMIS v6 started. Mode: %s", self.safety.get_mode())

    def _run_cycle(self):
        """Full cycle: index -> generate opportunities -> decide -> dashboard."""
        logger.info("Running daily cycle...")
        self.indexer.build_index()
        try:
            self.generator.scan_and_generate()
        except Exception as exc:
            logger.error("Opp generation failed: %s", exc)
        self.indexer.build_index()
        self.decision.decide(count=6)
        logger.info("Daily cycle complete")

    def stop(self):
        self._running = False
        self.indexer.stop_watchdog()
        self.scheduler.stop()
        logger.info("PEMIS v6 stopped")

    def _run_job(self, name):
        try:
            mode = self.safety.get_mode()
            job_map = {
                "distill": lambda: self.distiller.run(mode),
                "integrity": lambda: self.integrity.check(self.indexer),
                "full_check": self._full_check,
                "daily_capture": self._run_daily_capture,
                "read_feedback": self._read_feedback_job,
            }
            action = job_map.get(name)
            if action:
                action()
                logger.info("Job completed: %s", name)
        except Exception as exc:
            logger.error("Job failed: %s - %s", name, exc)
            self._error_log.append(
                {"time": datetime.now().isoformat(), "job": name, "error": str(exc)[:200]}
            )

    def _auto_scan_job(self):
        """Hash-based opportunity scan over allowed single-vault folders."""
        logger.info("Auto scan: checking for new/modified files...")
        try:
            count = 0
            for markdown_file in self.settings.vault_path.rglob("*.md"):
                if not self.vault_layout.should_analyze(markdown_file):
                    continue
                try:
                    text = markdown_file.read_text(encoding="utf-8-sig")
                    current_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
                    existing = self.indexer.find_by_path(markdown_file)
                    if existing and current_hash == existing.get("content_hash", ""):
                        continue
                    analysis = self.generator.analyze_file(markdown_file)
                    if analysis:
                        self.generator.generate_card(markdown_file, analysis)
                        count += 1
                        logger.info("Auto scan generated: %s", markdown_file.name)
                except Exception as exc:
                    logger.error("Auto scan file error %s: %s", markdown_file.name, exc)
            if count:
                self.indexer.build_index()
                from src.dashboard import sync_opps_to_vault

                sync_opps_to_vault(self)
                self.decision.decide(count=6)
                self._update_control_center()
                logger.info("Auto scan complete: %d new opportunities", count)
            else:
                logger.info("Auto scan complete: no changes")
            self._capture_new_files()
            return {"generated": count}
        except Exception as exc:
            logger.error("Auto scan failed: %s", exc)
            return {"generated": 0, "error": str(exc)}

    def manual_scan(self):
        logger.info("Manual scan triggered by user...")
        return self._auto_scan_job()

    def create_inbox_item(self, source_type, title, content, metadata=None):
        """Controlled write entry used by future MCP/mobile/browser adapters."""
        result = self.inbox.create_text_item(source_type, title, content, metadata)
        self.indexer.incremental_add(result["path"])
        return result

    def _read_feedback_job(self):
        try:
            if self.feedback:
                self.feedback.read_from_control_center()
                self._last_feedback_read = datetime.now()
        except Exception as exc:
            self.safety.log_error("feedback", str(exc))

    def _capture_new_files(self):
        """Count uncaptured notes without reading restricted folders."""
        logger.info("Capture: checking for uncaptured files...")
        try:
            captured = 0
            for markdown_file in self.settings.vault_path.rglob("*.md"):
                if not self.vault_layout.should_analyze(markdown_file):
                    continue
                existing = self.indexer.find_by_path(markdown_file)
                if existing and existing.get("tags"):
                    continue
                captured += 1
            if captured:
                logger.info("Capture: %d files need tagging", captured)
            else:
                logger.debug("Capture: nothing new")
            return captured
        except Exception as exc:
            logger.error("Capture scan failed: %s", exc)
            return 0

    def _run_daily_capture(self):
        self._capture_new_files()
        self._auto_scan_job()

    def _full_check(self):
        self.indexer.build_index()
        self._update_control_center()

    def _update_control_center(self):
        try:
            update_dashboard(self)
        except ImportError:
            pass

    def _on_file_change(self, action, file_path):
        """Indexer has already applied the file mutation before this callback runs."""
        try:
            logger.info("Vault file %s: %s", action, file_path)
            self.decision.decide(count=6)
            self._update_control_center()
        except Exception as exc:
            self.safety.log_error("watchdog_cb", str(exc))

    def status(self):
        elapsed = int(time.time() - self._start_time) if self._start_time else 0
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

        decisions = self.decision.get_latest()
        embed_status = self.embedder.get_status()
        all_entries = self.indexer.get_all()

        return {
            "service": "LingJi - PEMIS v6",
            "mode": self.safety.get_mode(),
            "uptime": uptime,
            "uptime_seconds": elapsed,
            "current_model": embed_status["current_model"],
            "primary_model": settings.llm_model,
            "fallback_model": settings.fallback_llm,
            "embed_model": embed_status["current_model"],
            "fallback_embed_active": embed_status["fallback_active"],
            "cache_size": embed_status["cache_size"],
            "index_entries": len(all_entries),
            "jobs": self.scheduler.get_status(),
            "total_decisions": len(decisions.get("decisions", [])),
            "errors": len(self._error_log),
            "last_error": self._error_log[-1] if self._error_log else None,
            "feedback_read": getattr(self, "_last_feedback_read", None),
            "vault_layout": self.vault_layout.status(),
            "index_private": settings.index_private,
        }


if __name__ == "__main__":
    core = PEMISCore()
    try:
        core.start()
        logger.info("PEMIS v6 running. Ctrl+C to stop.")
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        core.stop()
        logger.info("Shutdown complete")
