"""UserFeedback: reads user feedback from Control Center and adjusts scoring weights."""
import json, logging, re
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.feedback')

FEEDBACK_FILE = 'storage/user_preferences.json'


class UserFeedback:
    def __init__(self, settings):
        self.settings = settings
        self.feedback_path = settings.storage_path / 'user_preferences.json'
        self._prefs = self._load()
        self._prefs.setdefault('liked', [])
        self._prefs.setdefault('disliked', [])
        self._prefs.setdefault('executed', [])
        self._prefs.setdefault('failed', [])
        self._prefs.setdefault('weight_adjustments', {})

    def _load(self):
        if self.feedback_path.exists():
            try:
                with open(self.feedback_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self):
        with open(self.feedback_path, 'w', encoding='utf-8') as f:
            json.dump(self._prefs, f, ensure_ascii=False, indent=2)

    def read_from_control_center(self):
        """Scan Control Center.md for feedback entries written by user."""
        cc = self.settings.vault_path / 'PEMIS' / 'dashboard' / 'Control Center.md'
        if not cc.exists():
            return

        text = cc.read_text(encoding='utf-8')
        changed = False

        # Parse liked/disliked/executed/failed patterns
        patterns = {
            'liked': r'喜欢的机会[：:]\s*(.+)',
            'disliked': r'不感兴趣的[：:]\s*(.+)',
            'executed': r'已执行的[：:]\s*(.+)',
            'failed': r'失败的[：:]\s*(.+)',
            'new_ideas': r'新想法[：:]\s*(.+)',
        }

        for key, pattern in patterns.items():
            m = re.search(pattern, text)
            if m:
                val = m.group(1).strip()
                if val and val not in ('', '-', '无', '暂无'):
                    if key not in self._prefs:
                        self._prefs[key] = []
                    if val not in self._prefs[key]:
                        self._prefs[key].append({'content': val, 'timestamp': datetime.now().isoformat()})
                        changed = True
                        logger.info('Feedback recorded: %s = %s', key, val[:50])

        # Parse per-opportunity feedback
        # Match blocks like: 感兴趣程度（1-5）: 4
        opp_sections = re.findall(r'### \d+\.\s*(.+?)(?=###|\Z)', text, re.DOTALL)
        for sec in opp_sections:
            lines = sec.strip().split('\n')
            title = lines[0].strip() if lines else ''
            interest = ''
            can_do = ''
            timing = ''
            for line in lines:
                if '感兴趣程度' in line:
                    interest = line.split(':')[-1].strip()
                elif '我能做吗' in line:
                    can_do = line.split(':')[-1].strip()
                elif '什么时候执行' in line:
                    timing = line.split(':')[-1].strip()

            if interest or can_do or timing:
                entry = {
                    'title': title[:60],
                    'interest': interest,
                    'can_do': can_do,
                    'timing': timing,
                    'timestamp': datetime.now().isoformat()
                }
                self._prefs.setdefault('per_opportunity', [])
                # Avoid duplicates
                existing_titles = [e.get('title', '') for e in self._prefs['per_opportunity']]
                if title[:60] not in existing_titles:
                    self._prefs['per_opportunity'].append(entry)
                    changed = True
                    logger.info('Per-opp feedback: %s interest=%s can_do=%s', title[:30], interest, can_do)

        if changed:
            self._save()

    def get_weight_adjustment(self, monetization_type):
        """Return score multiplier based on user preference."""
        adj = self._prefs.get('weight_adjustments', {})
        if monetization_type in adj:
            return adj[monetization_type]
        return 1.0

    def get_preferences(self):
        return self._prefs