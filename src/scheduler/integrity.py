import json, logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('pemis.integrity')

class IntegrityChecker:
    def __init__(self, settings):
        self.settings = settings
        self.log_dir = Path(settings.log_dir) / 'integrity'
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def check(self, index=None):
        report = {
            'timestamp': datetime.now().isoformat(),
            'snapshot_count': 0,
            'collection_count': 0,
            'errors': [],
            'healthy': True,
        }
        if index:
            entries = index.get_all()
            report['index_entries'] = len(entries)
            hashes = [e.get('content_hash', '') for e in entries if e.get('content_hash')]
            report['with_hash'] = len(hashes)
            report['unique_hash'] = len(set(hashes))
            if len(hashes) != len(set(hashes)):
                report['errors'].append('Duplicate hashes detected')
                report['healthy'] = False
        with open(self.log_dir / 'system_integrity_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info('Integrity check: healthy=%s, entries=%d', report['healthy'], report.get('index_entries', 0))
        return report
