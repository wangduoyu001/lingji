import sys, os, json, logging, threading, time
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
        logger.info('Initializing PEMIS v5...')
        self.settings = settings
        self.indexer = PEMISIndex(settings.vault_dir, settings.storage_dir)
        self.embedder = Embedder(settings.ollama_base_url, settings.embedding_model, settings.cache_max)
        self.scheduler = CronScheduler(settings)
        self.safety = SafetyGuard(settings)
        self.distiller = DistillationEngine(settings)
        self.integrity = IntegrityChecker(settings)
        self.decision = DecisionEngine(self.indexer, settings.storage_dir)
        self._running = False
        self._threads = []

    def start(self):
        self._running = True
        self.indexer.build_index()
        self.decision.decide(count=3)
        self.scheduler.start()
        t = threading.Thread(target=self._scheduler_loop, daemon=True)
        t.start()
        self._threads.append(t)
        logger.info('PEMIS v5 started. Mode: %s', self.safety.get_mode())

    def stop(self):
        self._running = False
        self.scheduler.stop()
        logger.info('PEMIS v5 stopped')

    def _scheduler_loop(self):
        while self._running:
            try:
                now = datetime.now()
                for job in self.scheduler.get_due_jobs(now):
                    mode = self.safety.get_mode()
                    min_mode = job['min_mode']
                    if mode == 'SAFE' and min_mode != 'EMERGENCY':
                        continue
                    self.scheduler.mark_run(job['name'])
                    try:
                        self._execute_job(job['name'])
                        self.scheduler.mark_done(job['name'], True)
                    except Exception as e:
                        logger.error('Job %s failed: %s', job['name'], e)
                        self.scheduler.mark_done(job['name'], False)
                time.sleep(60)
            except Exception as e:
                logger.error('Scheduler loop error: %s', e)
                time.sleep(60)

    def _execute_job(self, name):
        if name == 'scan':
            self.indexer.rebuild()
        elif name == 'distill':
            self.distiller.run(self.safety.get_mode())
        elif name == 'integrity':
            self.integrity.check(self.indexer if hasattr(self, 'indexer') else None)

    def status(self):
        return {
            'service': 'LingJi - PEMIS v5',
            'mode': self.safety.get_mode(),
            'index_entries': len(self.indexer.get_all()),
            'jobs': self.scheduler.get_status(),
            'started': True
        }

core = PEMISCore()

if __name__ == '__main__':
    try:
        core.start()
        logger.info('PEMIS v5 running. Press Ctrl+C to stop.')
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        core.stop()
        logger.info('Shutdown complete')
