import json, logging, time
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger('pemis.decision')


class DecisionEngine:
    def __init__(self, index, storage_dir, history_days=90, vault_path=None, opp_generator=None, user_feedback=None):
        self.profile = None
        self.index = index
        self.storage_dir = Path(storage_dir)
        self.output_path = self.storage_dir / 'decision_output.json'
        self.history_dir = self.storage_dir / 'decision_history'
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_days = history_days
        self.vault_path = vault_path
        self.generator = opp_generator
        self.feedback = user_feedback

    def _load_profile(self):
        if self.vault_path:
            try:
                from src.user_profile import load_profile
                self.profile = load_profile(self.vault_path)
                if self.profile:
                    logger.info('User profile loaded: %d keys', len(self.profile))
            except Exception as e:
                logger.warning('Failed to load profile: %s', e)

    def compute_decision_score(self, entry):
        score = entry.get('score', 0)
        speed_map = {'fast': 0.3, 'mid': 0.2, 'slow': 0.1}
        speed_bonus = speed_map.get(entry.get('speed', ''), 0)
        difficulty_factor = max(0, 1 - (entry.get('difficulty', 3) - 1) * 0.15)
        cap_match = 0.5
        if self.profile is None and self.vault_path:
            self._load_profile()
        if self.profile:
            diff = entry.get('difficulty', 3)
            if diff <= 2:
                cap_match = 0.85
            elif diff <= 3:
                cap_match = 0.65
            else:
                cap_match = 0.35

        # User feedback adjustment
        feedback_adj = 1.0
        if self.feedback:
            mon_type = entry.get('monetization', '')
            feedback_adj = self.feedback.get_weight_adjustment(mon_type)

        return round((score * 0.35 + speed_bonus * 0.25 + difficulty_factor * 0.15 + cap_match * 0.25) * feedback_adj, 4)

    def decide(self, count=6):
        self._load_profile()

        # Read user feedback from Control Center
        if self.feedback:
            self.feedback.read_from_control_center()

        # Note: opportunity generation is triggered separately, not on every decide()

        entries = self.index.get_all()
        scored = []
        for e in entries:
            if e.get('type') != 'opportunity':
                continue
            ds = self.compute_decision_score(e)
            scored.append((ds, e))
        scored.sort(key=lambda x: -x[0])
        top = scored[:count]

        output = []
        for ds, e in top:
            output.append({
                'id': e['id'],
                'title': e['title'][:80],
                'decision_score': ds,
                'score': e.get('score', 0),
                'speed': e.get('speed', ''),
                'monetization': e.get('monetization', ''),
                'summary': e.get('summary', '')[:300],
                'tags': e.get('tags', []),
                'difficulty': e.get('difficulty', 0),
                'recommendation': self._build_recommendation(ds, e),
            })

        now = datetime.now()
        result = {
            'timestamp': now.isoformat(),
            'ts': now.timestamp(),
            'total_evaluated': len(scored),
            'decisions': output,
        }

        # Save latest
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Save history (one file per day)
        fname = 'decisions_' + now.strftime('%Y%m%d') + '.json'
        with open(self.history_dir / fname, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # Cleanup old history
        self._cleanup_old()

        logger.info('Decision: %d evaluated, top %d saved', len(scored), count)
        return result

    def _build_recommendation(self, ds, entry):
        speed = entry.get('speed', 'mid')
        mon = entry.get('monetization', '')
        diff = entry.get('difficulty', 3)
        summary = entry.get('summary', '')[:150]
        if summary:
            return summary
        if speed == 'fast' and diff <= 2:
            return 'Quick win: low difficulty + fast execution. Start immediately.'
        if ds > 0.6 and speed == 'fast':
            return 'High confidence fast opportunity. Prioritize this week.'
        if ds > 0.6:
            return 'Strong opportunity. Plan execution within 2 weeks.'
        if mon in ('saas', 'tool'):
            return 'Long-term asset potential. Build for recurring income.'
        return 'Evaluate resources before committing. Medium priority.'

    def get_latest(self):
        if self.output_path.exists():
            with open(self.output_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'decisions': []}

    def get_history(self, days=7):
        results = []
        now = datetime.now()
        for i in range(days):
            d = now - timedelta(days=i)
            fname = 'decisions_' + d.strftime('%Y%m%d') + '.json'
            f = self.history_dir / fname
            if f.exists():
                with open(f, 'r', encoding='utf-8') as fh:
                    results.append(json.load(fh))
        return results

    def _cleanup_old(self):
        cutoff = datetime.now() - timedelta(days=self.history_days)
        for f in self.history_dir.glob('decisions_*.json'):
            try:
                parts = f.stem.replace('decisions_', '')
                fd = datetime.strptime(parts, '%Y%m%d')
                if fd < cutoff:
                    f.unlink()
                    logger.info('Removed old decision history: %s', f.name)
            except Exception:
                pass