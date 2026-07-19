import hashlib
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.api.decision_engine import DecisionEngine
from src.config import settings
from src.dashboard import update_dashboard
from src.embedding.embedder import Embedder
from src.indexer.index import PEMISIndex
from src.memory import InboxService, VaultLayout
from src.obsidian import DocumentManager, ManualCommandService, ObsidianInteractionManager
from src.opp_generator import OppGenerator
from src.scheduler.cron import CronScheduler
from src.scheduler.distillation import DistillationEngine
from src.scheduler.integrity import IntegrityChecker
from src.security.safety import SafetyGuard
from src.storage import StateDatabase
from src.user_feedback import UserFeedback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("pemis.main")

OPPORTUNITY_PROCESSOR = "opportunity_analysis"
OPPORTUNITY_PROCESSOR_VERSION = "1"


class PEMISCore:
    def __init__(self):
        logger.info("PEMIS v6 single-vault memory OS initializing...")
        self.settings = settings
        self.vault_layout = VaultLayout(settings.vault_path)
        self.state_db = StateDatabase(settings.state_db_path)
        self.safety = SafetyGuard(settings)
        self.inbox = InboxService(self.vault_layout)
        self.documents = DocumentManager(self.vault_layout)
        self.obsidian_interaction = ObsidianInteractionManager(self.vault_layout)
        self.commands = ManualCommandService(
            self.vault_layout,
            self.documents,
            state_db=self.state_db,
        )
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
        self.scheduler = CronScheduler(
            self.state_db,
            mode_provider=self.safety.get_mode,
            poll_seconds=settings.scheduler_poll_seconds,
            max_workers=settings.scheduler_workers,
        )
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
        if self._running:
            return
        self._running = True
        self._start_time = time.time()

        if settings.vault_auto_init:
            created = self.vault_layout.ensure()
            if created:
                logger.info("Single vault layout initialized: %d folders created", len(created))

        if settings.obsidian_interaction_auto_init:
            interaction_result = self.obsidian_interaction.ensure()
            logger.info(
                "Obsidian interaction initialized: %d created, %d updated, %d skipped",
                len(interaction_result["created"]),
                len(interaction_result["updated"]),
                len(interaction_result["skipped"]),
            )

        self.indexer.build_index()
        self.decision.decide(count=6)
        self._update_control_center()

        if settings.watchdog_enabled:
            self.indexer.start_watchdog(callback=self._on_file_change)

        self.scheduler.add_job("distill", 24, "NORMAL", run_on_start=False)
        self.scheduler.add_job("integrity", 24, "NORMAL", run_on_start=False)
        self.scheduler.add_job("full_check", 24, "NORMAL", run_on_start=False)
        self.scheduler.add_job("read_feedback", 0.167, "NORMAL", run_on_start=True)
        self.scheduler.add_job(
            "process_commands",
            max(settings.manual_command_interval_minutes / 60, 1 / 60),
            "NORMAL",
            run_on_start=True,
        )
        self.scheduler.add_job("daily_capture", 24, "NORMAL", run_on_start=False)
        self.scheduler.start(runner_callback=self._run_job)

        self.state_db.append_event(
            "service_started",
            "service",
            "lingji",
            {"vault": str(settings.vault_path), "index_private": settings.index_private},
        )
        self._update_control_center()
        logger.info("PEMIS v6 started. Mode: %s", self.safety.get_mode())

    def stop(self):
        if not self._running:
            return
        self._running = False
        self.indexer.stop_watchdog()
        self.scheduler.stop()
        self.state_db.append_event("service_stopped", "service", "lingji")
        logger.info("PEMIS v6 stopped")

    def _run_job(self, name):
        mode = self.safety.get_mode()
        job_map = {
            "distill": lambda: self.distiller.run(mode),
            "integrity": lambda: self.integrity.check(self.indexer),
            "full_check": self._full_check,
            "daily_capture": self._run_daily_capture,
            "read_feedback": self._read_feedback_job,
            "process_commands": self._process_commands_job,
        }
        action = job_map.get(name)
        if not action:
            raise ValueError(f"Unknown scheduled job: {name}")
        try:
            result = action()
            self.state_db.append_event(
                "job_completed",
                "scheduler_job",
                name,
                result if isinstance(result, dict) else {},
            )
            logger.info("Job completed: %s", name)
            return result
        except Exception as exc:
            logger.exception("Job failed: %s", name)
            error = {"time": datetime.now().isoformat(), "job": name, "error": str(exc)[:500]}
            self._error_log.append(error)
            self.state_db.append_event("job_failed", "scheduler_job", name, error)
            raise

    def _auto_scan_job(self):
        """Analyze changed sources using an independent processing hash."""
        logger.info("Auto scan: checking for sources requiring opportunity analysis...")
        generated = 0
        processed = 0
        failed = 0
        for markdown_file in self.settings.vault_path.rglob("*.md"):
            if not self.vault_layout.should_analyze(markdown_file):
                continue
            try:
                text = markdown_file.read_text(encoding="utf-8-sig")
                current_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
                existing = self.indexer.find_by_path(markdown_file)
                source_id = (
                    str(existing.get("id"))
                    if existing and existing.get("id")
                    else self.vault_layout.relative(markdown_file).as_posix()
                )
                if not self.state_db.needs_processing(
                    source_id,
                    OPPORTUNITY_PROCESSOR,
                    OPPORTUNITY_PROCESSOR_VERSION,
                    current_hash,
                ):
                    continue

                self.state_db.mark_processing_started(
                    source_id,
                    OPPORTUNITY_PROCESSOR,
                    OPPORTUNITY_PROCESSOR_VERSION,
                    current_hash,
                )
                analysis = self.generator.analyze_file(markdown_file)
                result = {"generated": False, "source_path": str(markdown_file)}
                if analysis:
                    result.update(self.generator.generate_card(markdown_file, analysis))
                    result["generated"] = True
                    generated += 1
                processed += 1
                self.state_db.mark_processing_finished(
                    source_id,
                    OPPORTUNITY_PROCESSOR,
                    OPPORTUNITY_PROCESSOR_VERSION,
                    current_hash,
                    success=True,
                    result=result,
                )
            except Exception as exc:
                failed += 1
                logger.exception("Auto scan file failed: %s", markdown_file)
                try:
                    self.state_db.mark_processing_finished(
                        source_id,
                        OPPORTUNITY_PROCESSOR,
                        OPPORTUNITY_PROCESSOR_VERSION,
                        current_hash,
                        success=False,
                        error=str(exc),
                    )
                except Exception:
                    pass

        if generated:
            from src.dashboard import sync_opps_to_vault

            sync_opps_to_vault(self)
            self.indexer.build_index()
            self.decision.decide(count=6)
            self._update_control_center()
        logger.info(
            "Auto scan complete: %d processed, %d generated, %d failed",
            processed,
            generated,
            failed,
        )
        return {"processed": processed, "generated": generated, "failed": failed}

    def manual_scan(self):
        logger.info("Manual scan triggered by user...")
        return self._auto_scan_job()

    def create_inbox_item(self, source_type, title, content, metadata=None):
        """Controlled write entry used by MCP, mobile and browser adapters."""
        result = self.inbox.create_text_item(source_type, title, content, metadata)
        self.indexer.incremental_add(result["path"])
        self.state_db.append_event("inbox_item_created", "source", result["id"], result)
        return result

    def process_manual_commands(self, limit=20):
        return self.commands.process_pending(limit=limit)

    def _process_commands_job(self):
        result = self.commands.process_pending(limit=50)
        if result["processed"]:
            self.indexer.build_index()
            self._update_control_center()
        return result

    def _read_feedback_job(self):
        if self.feedback:
            self.feedback.read_from_control_center()
            self._last_feedback_read = datetime.now()
        return {"feedback_read_at": self._last_feedback_read.isoformat()}

    def _capture_new_files(self):
        """Report uncaptured notes without entering restricted folders."""
        uncaptured = 0
        for markdown_file in self.settings.vault_path.rglob("*.md"):
            if not self.vault_layout.should_analyze(markdown_file):
                continue
            existing = self.indexer.find_by_path(markdown_file)
            if existing and existing.get("tags") and existing.get("project_id"):
                continue
            uncaptured += 1
        logger.info("Capture review queue: %d notes need metadata review", uncaptured)
        return {"needs_metadata_review": uncaptured}

    def _run_daily_capture(self):
        capture = self._capture_new_files()
        scan = self._auto_scan_job()
        return {**capture, **scan}

    def _full_check(self):
        self.indexer.build_index()
        integrity = self.integrity.check(self.indexer)
        interaction = self.obsidian_interaction.ensure()
        self._update_control_center()
        return {"integrity": integrity, "interaction": interaction}

    def _update_control_center(self):
        update_dashboard(self)

    def _on_file_change(self, action, file_path):
        """Indexer has already applied the file mutation before this callback runs."""
        try:
            relative = self.vault_layout.relative(file_path)
            logger.info("Vault file %s: %s", action, relative.as_posix())
            if relative.parts[:3] == ("00-System", "Commands", "Queue"):
                self._process_commands_job()
                return
            if relative.parts and relative.parts[0] == "00-System":
                return
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
            "manual_commands": self.commands.status(),
            "total_decisions": len(decisions.get("decisions", [])),
            "errors": len(self._error_log),
            "last_error": self._error_log[-1] if self._error_log else None,
            "feedback_read": getattr(self, "_last_feedback_read", None),
            "vault_layout": self.vault_layout.status(),
            "index_private": settings.index_private,
            "recent_events": self.state_db.recent_events(limit=10),
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
