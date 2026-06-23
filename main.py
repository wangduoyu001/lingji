import sys, os, json, logging, time, threading
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.indexer.index import PEMISIndex
from src.embedding.embedder import Embedder
from src.scheduler.cron import CronScheduler
from src.scheduler.distillation import DistillationEngine
from src.scheduler.integrity import IntegrityChecker
from src.security.safety import SafetyGuard
from src.api.decision_engine import DecisionEngine
from src.opp_generator import OppGenerator
from src.user_feedback import UserFeedback
from src.dashboard import update_dashboard

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('pemis.main')


class PEMISCore:
    def __init__(self):
        logger.info('PEMIS v6 initializing...')
        self.settings = settings
        self.indexer = PEMISIndex(settings.vault_path, settings.storage_path)
        self.embedder = Embedder(settings.ollama_base_url, settings.embed_model, settings.fallback_embed_model, settings.cache_max)
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

        # Startup: build index + decide (no qwen auto-gen)
        self.indexer.build_index()
        self.decision.decide(count=6)
        self._update_control_center()

        # Start watchdog if enabled
        if settings.watchdog_enabled:
            self.indexer.start_watchdog(callback=self._on_file_change)

        # Setup scheduler
        # daily_cycle runs once per startup; full_check handles periodic
        self.scheduler.add_job('distill', 24, 'NORMAL')
        self.scheduler.add_job('integrity', 24, 'MAINTENANCE')
        self.scheduler.add_job('full_check', 24, 'MAINTENANCE')
        self.scheduler.add_job('auto_scan', 24, 'NORMAL')
        self.scheduler.start(runner_callback=self._run_job)

        # Generate control center
        self._update_control_center()

        logger.info('PEMIS v6 started. Mode: %s', self.safety.get_mode())

    def _run_cycle(self):
        """Full cycle: index -> generate opps -> decide -> dashboard"""
        logger.info('Running daily cycle...')
        # Build index
        self.indexer.build_index()
        # Generate new opportunities (calls qwen)
        try:
            self.generator.scan_and_generate()
        except Exception as e:
            logger.error('Opp generation failed: %s', e)
        # Rebuild index with new opps
        self.indexer.build_index()
        # Run decision
        self.decision.decide(count=6)
        logger.info('Daily cycle complete')

    def stop(self):
        self._running = False
        self.indexer.stop_watchdog()
        self.scheduler.stop()
        logger.info('PEMIS v6 stopped')

    def _run_job(self, name):
        try:
            mode = self.safety.get_mode()
            job_map = {
                'distill': lambda: self.distiller.run(mode),
                'integrity': lambda: self.integrity.check(self.indexer),
                'full_check': lambda: self._full_check(),
                'auto_scan': lambda: self._auto_scan_job(),
            }
            fn = job_map.get(name)
            if fn:
                fn()
                logger.info('Job completed: %s', name)
        except Exception as e:
            logger.error('Job failed: %s - %s', name, e)
            self._error_log.append({'time': datetime.now().isoformat(), 'job': name, 'error': str(e)[:200]})

    def _auto_scan_job(self):
        """Scheduled auto-scan (called by scheduler every 24h).
        Only analyzes files whose content_hash changed since last index build."""
        logger.info('Auto scan: checking for new/modified files...')
        try:
            idx = self.indexer.get_all()
            known_hashes = {e['id']: e.get('content_hash', '') for e in idx}
            count = 0
            for mf in self.settings.vault_path.rglob('*.md'):
                if 'PEMIS' in str(mf):
                    continue
                try:
                    import hashlib
                    current_hash = hashlib.md5(mf.read_text(encoding='utf-8').encode()).hexdigest()
                    old_hash = known_hashes.get(mf.stem, '')
                    if current_hash == old_hash:
                        continue
                    # New or modified file
                    stem = mf.stem.lower()
                    already = any(stem in oppf.stem.lower() for oppf in self.generator.opp_dir.glob('*.md'))
                    analysis = self.generator.analyze_file(mf)
                    if analysis:
                        self.generator.generate_card(mf, analysis)
                        count += 1
                        logger.info('Auto scan generated: %s', mf.name)
                except Exception as e:
                    logger.error('Auto scan file error %s: %s', mf.name, e)
            if count:
                self.indexer.build_index()
                from src.dashboard import sync_opps_to_vault
                sync_opps_to_vault(self)
                self.decision.decide(count=6)
                self._update_control_center()
                logger.info('Auto scan complete: %d new opportunities', count)
            else:
                logger.info('Auto scan complete: no changes')
        except Exception as e:
            logger.error('Auto scan failed: %s', e)

    def manual_scan(self):
        """Manual scan trigger: hash-based incremental, callable from outside.
        Prepares vector store interface for future Qdrant use."""
        logger.info('Manual scan triggered by user...')
        # Delegate to the core incremental logic
        return self._auto_scan_job()

    def _full_check(self):
        self._update_control_center()

    def _update_control_center(self):
        try:
            from src.dashboard import update_dashboard
            update_dashboard(self)
        except ImportError:
            pass

    def _on_file_change(self, action, file_path):
        try:
            if action == 'deleted':
                self.indexer.incremental_remove(Path(file_path).stem)
            elif action == 'modified':
                self.indexer.incremental_update(Path(file_path))
            elif action == 'created':
                self.indexer.incremental_add(Path(file_path))
            # Re-run decision on file changes
            self.decision.decide(count=6)
            self._update_control_center()
        except Exception as e:
            self.safety.log_error('watchdog_cb', str(e))

    def _update_dashboard(self):
        try:
            update_dashboard(self)
        except Exception as e:
            self.safety.log_error('dashboard', str(e))

    def status(self):
        elapsed = int(time.time() - self._start_time) if self._start_time else 0
        h, r = divmod(elapsed, 3600)
        m, s = divmod(r, 60)
        uptime = str(h) + 'h ' + str(m) + 'm ' + str(s) + 's' if h else str(m) + 'm ' + str(s) + 's'

        decisions = self.decision.get_latest()
        embed_status = self.embedder.get_status()
        all_entries = self.indexer.get_all()

        return {
            'service': 'LingJi - PEMIS v6',
            'mode': self.safety.get_mode(),
            'uptime': uptime,
            'uptime_seconds': elapsed,
            'current_model': embed_status['current_model'],
            'primary_model': settings.llm_model,
            'fallback_model': settings.fallback_llm,
            'embed_model': embed_status['current_model'],
            'fallback_embed_active': embed_status['fallback_active'],
            'cache_size': embed_status['cache_size'],
            'index_entries': len(all_entries),
            'jobs': self.scheduler.get_status(),
            'total_decisions': len(decisions.get('decisions', [])),
            'errors': len(self._error_log),
            'last_error': self._error_log[-1] if self._error_log else None,
        }


if __name__ == '__main__':
    core = PEMISCore()
    try:
        core.start()
        logger.info('PEMIS v6 running. Ctrl+C to stop.')
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        core.stop()
        logger.info('Shutdown complete')