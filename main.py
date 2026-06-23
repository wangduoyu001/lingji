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
from src.dashboard import update_dashboard

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger('pemis.main')


class PEMISCore:
    def __init__(self):
        logger.info('PEMIS v5.2 initializing...')
        self.settings = settings
        self.indexer = PEMISIndex(settings.vault_path, settings.storage_path)
        self.embedder = Embedder(settings.ollama_base_url, settings.embed_model, settings.fallback_embed_model, settings.cache_max)
        self.scheduler = CronScheduler()
        self.safety = SafetyGuard(settings)
        self.distiller = DistillationEngine(settings)
        self.integrity = IntegrityChecker(settings)
        self.decision = DecisionEngine(
            self.indexer,
            settings.storage_path,
            settings.decision_history_days,
            vault_path=settings.vault_path
        )
        self._running = False
        self._start_time = None
        self._error_log = []

    def start(self):
        self._running = True
        self._start_time = time.time()

        # Build index
        self.indexer.build_index()

        # Run decision
        self.decision.decide(count=6)

        # Start watchdog if enabled
        if settings.watchdog_enabled:
            self.indexer.start_watchdog(callback=self._on_file_change)

        # Setup scheduler
        self.scheduler.add_job('distill', 24, 'NORMAL')
        self.scheduler.add_job('integrity', 24, 'MAINTENANCE')
        self.scheduler.add_job('full_check', 24, 'MAINTENANCE')
        self.scheduler.start(runner_callback=self._run_job)

        # Generate control center
        self._update_control_center()

        logger.info('PEMIS v5.2 started. Mode: ' + str(self.safety.get_mode()))

    def stop(self):
        self._running = False
        self.indexer.stop_watchdog()
        self.scheduler.stop()
        logger.info('PEMIS v5.2 stopped')

    def _run_job(self, name):
        try:
            mode = self.safety.get_mode()
            job_map = {
                'distill': lambda: self.distiller.run(mode),
                'integrity': lambda: self.integrity.check(self.indexer),
                'full_check': lambda: self._full_check(),
            }
            fn = job_map.get(name)
            if fn:
                fn()
                logger.info('Job completed: %s', name)
        except Exception as e:
            logger.error('Job failed: %s - %s', name, e)
            self._error_log.append({'time': datetime.now().isoformat(), 'job': name, 'error': str(e)[:200]})

    def _full_check(self):
        self.indexer.build_index()
        self.integrity.check(self.indexer)
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
            self.decision.decide(count=6)
            self._update_dashboard()
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
            'service': 'LingJi - PEMIS v5.2',
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
        logger.info('PEMIS v5.2 running. Ctrl+C to stop.')
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        core.stop()
        logger.info('Shutdown complete')