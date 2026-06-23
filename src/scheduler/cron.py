import time, logging, threading
from datetime import datetime

logger = logging.getLogger('pemis.scheduler')


class CronScheduler:
    def __init__(self):
        self.jobs = []
        self.running = False
        self._thread = None

    def add_job(self, name, interval_hours, min_mode='NORMAL', enabled=True):
        self.jobs.append({
            'name': name,
            'interval_hours': interval_hours,
            'min_mode': min_mode,
            'enabled': enabled,
            'last_run': None,
            'status': 'pending',
        })

    def start(self, runner_callback=None):
        self.running = True
        self._runner = runner_callback
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f'Scheduler: {len(self.jobs)} jobs')

    def _loop(self):
        while self.running:
            try:
                now = datetime.now()
                for job in self.jobs:
                    if not job['enabled']:
                        continue
                    if job['last_run'] is None:
                        due = True
                    else:
                        elapsed = (now - job['last_run']).total_seconds()
                        due = elapsed >= job['interval_hours'] * 3600
                    if due:
                        job['last_run'] = now
                        job['status'] = 'running'
                        if self._runner:
                            self._runner(job['name'])
                time.sleep(60)
            except Exception as e:
                logger.error(f'Scheduler error: {e}')
                time.sleep(60)

    def stop(self):
        self.running = False

    def get_status(self):
        return [dict(j, last_run=str(j['last_run']) if j['last_run'] else None) for j in self.jobs]
