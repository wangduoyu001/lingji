import json, hashlib, logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.indexer')

class PEMISIndex:
    def __init__(self, vault_dir, storage_dir):
        self.vault_dir = Path(vault_dir)
        self.storage_dir = Path(storage_dir)
        self.index_path = self.storage_dir / 'pemis_index.json'
        self._index = None

    def _parse_frontmatter(self, text):
        meta = {}
        text = text.strip()
        if not text.startswith('---'):
            return meta
        end = text.find('---', 3)
        if end == -1:
            return meta
        fm_text = text[3:end].strip()
        for line in fm_text.splitlines():
            line = line.strip()
            if ':' not in line:
                continue
            key, _, val = line.partition(':')
            key = key.strip().lower()
            val = val.strip().strip(chr(34)).strip(chr(39))
            if key in ('score', 'confidence', 'difficulty'):
                try:
                    meta[key] = float(val)
                except ValueError:
                    meta[key] = val
            elif key in ('id', 'type', 'speed', 'monetization', 'source', 'created'):
                meta[key] = val
            elif key == 'tags':
                tags = [t.strip().strip('#') for t in val.split() if t.strip()]
                meta['tags'] = tags
            elif key == 'summary':
                meta['summary'] = val
        return meta

    def _parse_md_file(self, path):
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            return None
        meta = self._parse_frontmatter(text)
        file_id = meta.get('id', path.stem)
        content_hash = hashlib.md5(text.encode()).hexdigest()
        title = path.stem
        for line in text.splitlines():
            if line.startswith('# '):
                title = line[2:].strip()
                break
        return {
            'id': file_id,
            'type': meta.get('type', 'note'),
            'score': meta.get('score', 0.0),
            'tags': meta.get('tags', []),
            'title': title,
            'summary': meta.get('summary', ''),
            'content_hash': content_hash,
            'created': meta.get('created', ''),
            'updated': datetime.now().isoformat(),
            'source': meta.get('source', 'vault'),
            'speed': meta.get('speed', ''),
            'monetization': meta.get('monetization', ''),
            'difficulty': int(meta.get('difficulty', 0)),
            'confidence': meta.get('confidence', 0.0),
        }

    def build_index(self):
        entries = {}
        md_files = list(self.vault_dir.rglob('*.md'))
        for mf in md_files:
            entry = self._parse_md_file(mf)
            if entry:
                entries[entry['id']] = entry
        self._index = {
            'meta': {
                'version': '1.0',
                'total': len(entries),
                'last_build': datetime.now().timestamp(),
                'updated_at': datetime.now().isoformat(),
            },
            'entries': entries,
        }
        self.save_index(self._index)
        logger.info(f'Index built: {len(entries)} entries from {len(md_files)} md files')
        return self._index

    def rebuild(self):
        return self.build_index()

    def get_entry(self, file_id):
        idx = self._load()
        return idx.get('entries', {}).get(file_id)

    def remove_entry(self, file_id):
        idx = self._load()
        if file_id in idx.get('entries', {}):
            del idx['entries'][file_id]
            idx['meta']['total'] = len(idx['entries'])
            idx['meta']['updated_at'] = datetime.now().isoformat()
            self.save_index(idx)
            self._index = idx
            return True
        return False

    def get_all(self):
        idx = self._load()
        return list(idx.get('entries', {}).values())

    def save_index(self, index):
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _load(self):
        if self._index is not None:
            return self._index
        if self.index_path.exists():
            self._index = json.loads(self.index_path.read_text(encoding='utf-8'))
        else:
            self._index = {'meta': {'total': 0}, 'entries': {}}
        return self._index
