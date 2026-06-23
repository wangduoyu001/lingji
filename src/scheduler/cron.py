import asyncio, logging, json
from datetime import datetime, timedelta

logger = logging.getLogger('pemis.scheduler')

class CronScheduler:
    def __init__(self, settings=None):
        self.jobs = []
        self.running = False
        if settings:
            self._load_from_env(settings)

    def _load_from_env(self, settings):
        for i in range(1, 10):
            key = f'cron_job_{i}'
            val = getattr(settings, key, None) or ''
            if not val.strip():
                continue
            parts = [p.strip() for p in val.split(',')]
            name = parts[0] if len(parts) > 0 else ''
            interval = float(parts[1]) if len(parts) > 1 else 24
            min_mode = parts[2] if len(parts) > 2 else 'NORMAL'
            if name:
                self.add_job(name, interval, min_mode)
        if not self.jobs:
            self.add_job('scan', 6, 'NORMAL')
            self.add_job('distill', 24, 'NORMAL')
            self.add_job('integrity', 24, 'MAINTENANCE')

    def add_job(self, name, interval_hours, min_mode='NORMAL'):
        self.jobs.append({
            'name': name,
            'interval_hours': interval_hours,
            'min_mode': min_mode,
            'last_run': None,
            'status': 'pending',
        })

    def start(self):
        self.running = True
        logger.info(f'CronScheduler started with {len(self.jobs)} jobs')

    def stop(self):
        self.running = False

    def get_due_jobs(self, current_time=None):
        if current_time is None:
            current_time = datetime.now()
        due = []
        for job in self.jobs:
            if job['last_run'] is None:
                due.append(job)
            else:
                elapsed = (current_time - job['last_run']).total_seconds()
                if elapsed >= job['interval_hours'] * 3600:
                    due.append(job)
        return due

    def mark_run(self, job_name):
        for job in self.jobs:
            if job['name'] == job_name:
                job['last_run'] = datetime.now()
                job['status'] = 'running'
                break

    def mark_done(self, job_name, success=True):
        for job in self.jobs:
            if job['name'] == job_name:
                job['status'] = 'completed' if success else 'failed'
                break

    def get_status(self):
        return [dict(j, last_run=str(j['last_run']) if j['last_run'] else None) for j in self.jobs]
