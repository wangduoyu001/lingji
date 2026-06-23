import json, logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('pemis.safety')

class SafetyGuard:
    def __init__(self, settings):
        self.mode = getattr(settings, 'safety_mode', 'NORMAL')
        self.log_dir = Path(getattr(settings, 'log_dir', 'logs')) / 'journal'
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def set_mode(self, mode):
        old = self.mode
        self.mode = mode
        logger.info('Safety mode: %s -> %s', old, mode)
        return old

    def _is_allowed(self, action):
        rules = {
            'NORMAL': ['search','query','context','snapshot_read','index_build','index_read'],
            'MAINTENANCE': ['search','query','context','snapshot_read','index_build','index_read','rebuild','reindex','cleanup','backup'],
            'EMERGENCY': ['recovery','snapshot_restore','rollback'],
        }
        return action in rules.get(self.mode, rules['NORMAL'])

    def check(self, action, context=None):
        ok = self._is_allowed(action)
        self._journal(action, context, 'allowed' if ok else 'denied')
        if not ok:
            logger.warning('Safety guard denied: %s in %s', action, self.mode)
        return ok

    def require_backup(self, action):
        return self.mode != 'NORMAL'

    def _journal(self, action, context, result):
        entry = {'timestamp': datetime.now().isoformat(), 'action': action, 'mode': self.mode, 'result': result, 'context': context or {}}
        jf = self.log_dir / ('journal_' + datetime.now().strftime('%Y%m%d') + '.jsonl')
        with open(jf, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + chr(10))
