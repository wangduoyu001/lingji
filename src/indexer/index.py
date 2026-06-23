import json, hashlib, logging, threading, time
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.indexer')


class PEMISIndex:
    def __init__(self, vault_dir, storage_dir):
        self.vault_dir = Path(vault_dir)
        self.storage_dir = Path(storage_dir)
        self.index_path = self.storage_dir / 'pemis_index.json'
        self._index = None
        self._lock = threading.Lock()
        self._watchdog_running = False

    def _parse_frontmatter(self, text):
        meta = {}
        text = text.strip()
        if not text.startswith('---'):
            return meta
        end = text.find('---', 3)
        if end == -1:
            return meta
        for line in text[3:end].strip().splitlines():
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
            elif key in ('id', 'type', 'speed', 'monetization', 'source', 'created', 'category'):
                meta[key] = val
            elif key == 'tags':
                meta['tags'] = [t.strip().strip('#') for t in val.split() if t.strip()]
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
            'title': title or path.stem,
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

    def _get_file_id(self, path):
        text = ''
        try:
            text = path.read_text(encoding='utf-8')
        except Exception:
            return path.stem
        meta = self._parse_frontmatter(text)
        return meta.get('id', path.stem)

    def build_index(self):
        entries = {}
        md_files = list(self.vault_dir.rglob('*.md'))
        for mf in md_files:
            entry = self._parse_md_file(mf)
            if entry:
                entries[entry['id']] = entry
        idx = {
            'meta': {'version': '1.0', 'total': len(entries), 'last_build': datetime.now().timestamp(),
                     'updated_at': datetime.now().isoformat()},
            'entries': entries,
        }
        with self._lock:
            self._index = idx
            self.save_index(idx)
        logger.info(f'Index built: {len(entries)} entries from {len(md_files)} md files')
        return idx

    def incremental_add(self, file_path):
        entry = self._parse_md_file(file_path)
        if not entry:
            return False
        with self._lock:
            idx = self._load()
            idx['entries'][entry['id']] = entry
            idx['meta']['total'] = len(idx['entries'])
            idx['meta']['updated_at'] = datetime.now().isoformat()
            self.save_index(idx)
        logger.info(f'Incremental add: {entry["id"]} ({file_path.name})')
        return True

    def incremental_update(self, file_path):
        return self.incremental_add(file_path)

    def incremental_remove(self, file_id):
        with self._lock:
            idx = self._load()
            if file_id in idx.get('entries', {}):
                del idx['entries'][file_id]
                idx['meta']['total'] = len(idx['entries'])
                idx['meta']['updated_at'] = datetime.now().isoformat()
                self.save_index(idx)
                logger.info(f'Incremental remove: {file_id}')
                return True
        return False

    def start_watchdog(self):
        if self._watchdog_running:
            return
        self._watchdog_running = True
        t = threading.Thread(target=self._watchdog_loop, daemon=True)
        t.start()
        logger.info('Watchdog started')

    def _watchdog_loop(self):
        known = {}
        while self._watchdog_running:
            try:
                current = {}
                for mf in self.vault_dir.rglob('*.md'):
                    current[str(mf)] = (mf.stat().st_mtime, mf.stat().st_size)
                for path_str, (mtime, size) in current.items():
                    if path_str not in known:
                        self.incremental_add(Path(path_str))
                    else:
                        old_mtime, old_size = known[path_str]
                        if mtime != old_mtime or size != old_size:
                            self.incremental_update(Path(path_str))
                for path_str in list(known.keys()):
                    if path_str not in current:
                        file_id = Path(path_str).stem
                        self.incremental_remove(file_id)
                known = current
                time.sleep(10)
            except Exception as e:
                logger.error(f'Watchdog error: {e}')
                time.sleep(30)

    def stop_watchdog(self):
        self._watchdog_running = False

    def get_entry(self, file_id):
        idx = self._load()
        return idx.get('entries', {}).get(file_id)

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
            with open(self.index_path, 'r', encoding='utf-8') as f:
                self._index = json.load(f)
        else:
            self._index = {'meta': {'total': 0}, 'entries': {}}
        return self._index
