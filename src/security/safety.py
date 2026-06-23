import json, logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('pemis.safety')

class SafetyGuard:
    def __init__(self, settings):
        self.mode = getattr(settings, 'safety_mode', 'NORMAL')
        self.log_dir = Path(getattr(settings, 'log_dir', 'logs')) / 'journal'
        self.error_dir = Path(getattr(settings, 'log_dir', 'logs')) / 'errors'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        self._errors = []

    def get_mode(self):
        return self.mode

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


    def log_error(self, source, message, context=None):
        import json as _json
        from datetime import datetime as _dt
        entry = {"timestamp": _dt.now().isoformat(), "source": source, "message": str(message)[:500], "context": context or {}, "mode": self.mode}
        self._errors.append(entry)
        if len(self._errors) > 100:
            self._errors.pop(0)
        ef = self.error_dir / ("errors_" + _dt.now().strftime("%Y%m%d") + ".jsonl")
        with open(ef, "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + chr(10))
        logger.error("[%s] %s", source, message)

    def get_errors(self, limit=20):
        return self._errors[-limit:]

    def get_persistent_errors(self, days=7):
        import json as _json
        from datetime import datetime as _dt, timedelta as _td
        errors = []
        for i in range(days):
            d = _dt.now() - _td(days=i)
            ef = self.error_dir / ("errors_" + d.strftime("%Y%m%d") + ".jsonl")
            if ef.exists():
                with open(ef, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                errors.append(_json.loads(line))
                            except Exception:
                                pass
        return errors[-50:]

    def _journal(self, action, context, result):
        entry = {'timestamp': datetime.now().isoformat(), 'action': action, 'mode': self.mode, 'result': result, 'context': context or {}}
        jf = self.log_dir / ('journal_' + datetime.now().strftime('%Y%m%d') + '.jsonl')
        with open(jf, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + chr(10))
