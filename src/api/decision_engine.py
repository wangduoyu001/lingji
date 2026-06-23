import json, logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.api')

class DecisionEngine:
    def __init__(self, index, storage_dir):
        self.index = index
        self.storage_dir = Path(storage_dir)
        self.output_path = self.storage_dir / 'decision_output.json'

    def compute_decision_score(self, entry):
        score = entry.get('score', 0)
        speed_map = {'fast': 0.3, 'mid': 0.2, 'slow': 0.1}
        speed_bonus = speed_map.get(entry.get('speed', ''), 0)
        difficulty_factor = max(0, 1 - (entry.get('difficulty', 3) - 1) * 0.15)
        return round(score * 0.5 + speed_bonus * 0.3 + difficulty_factor * 0.2, 4)

    def decide(self, count=3):
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
                'summary': e.get('summary', '')[:200],
                'tags': e.get('tags', []),
            })
        result = {'timestamp': datetime.now().isoformat(), 'decisions': output}
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info('Decision engine: %d opportunities evaluated, top %d selected', len(scored), count)
        return result

    def get_latest(self):
        if self.output_path.exists():
            return json.loads(self.output_path.read_text(encoding='utf-8'))
        return {'decisions': []}
