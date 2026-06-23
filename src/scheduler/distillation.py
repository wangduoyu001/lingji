import json, logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('pemis.distillation')

class DistillationEngine:
    def __init__(self, settings):
        self.settings = settings
        self.log_dir = Path(settings.log_dir) / 'distillation'
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run(self, mode='NORMAL'):
        if mode == 'DEGRADED':
            # minimal_only in degraded
            return self._minimal_cleanup()
        report = {
            'last_run': datetime.now().isoformat(),
            'mode': mode,
            'status': 'completed',
            'archived': 0,
            'errors': []
        }
        with open(self.log_dir / 'latest.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info('Distillation %s: %s', mode, report['status'])
        return report

    def _minimal_cleanup(self):
        report = {'last_run': datetime.now().isoformat(), 'mode': 'DEGRADED(minimal)', 'status': 'completed', 'archived': 0}
        with open(self.log_dir / 'latest.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return report
