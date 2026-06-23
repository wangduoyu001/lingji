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
        self.decision = DecisionEngine(self.indexer, settings.storage_path, settings.decision_history_days)
        self._running = False
        self._start_time = None
        self._error_log = []

    def start(self):
        self._running = True
        self._start_time = time.time()

        # Build index
        self.indexer.build_index()

        # Run decision
        self.decision.decide(count=3)

        # Start watchdog if enabled
        if settings.watchdog_enabled:
            self.indexer.start_watchdog()

        # Setup scheduler
        self.scheduler.add_job('distill', 24, 'NORMAL')
        self.scheduler.add_job('integrity', 24, 'MAINTENANCE')
        self.scheduler.add_job('full_check', 24, 'MAINTENANCE')
        self.scheduler.start(runner_callback=self._run_job)

        # Generate control center
        self._update_control_center()

        logger.info(f'PEMIS v5.2 started. Mode: {self.safety.get_mode()}')

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
                logger.info(f'Job completed: {name}')
        except Exception as e:
            logger.error(f'Job failed: {name} - {e}')
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

    def status(self):
        elapsed = int(time.time() - self._start_time) if self._start_time else 0
        h, r = divmod(elapsed, 3600)
        m, s = divmod(r, 60)
        uptime = f'{h}h {m}m {s}s' if h else f'{m}m {s}s'

        decisions = self.decision.get_latest()
        embed_status = self.embedder.get_status()

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
            'index_entries': len(self.indexer.get_all()),
            'cache_size': embed_status['cache_size'],
            'jobs': self.scheduler.get_status(),
            'total_decisions': len(decisions.get('decisions', [])),
            'errors': len(self._error_log),
            'last_error': self._error_log[-1] if self._error_log else None,
            'embed_switches': embed_status['switches'],
        }


core = PEMISCore()


if __name__ == '__main__':
    try:
        core.start()
        logger.info('PEMIS v5.2 running. Ctrl+C to stop.')
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        core.stop()
        logger.info('Shutdown complete')
