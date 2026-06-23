import json, hashlib, logging, threading, time
from pathlib import Path
from datetime import datetime

logger = logging.getLogger('pemis.indexer')


class PEMISIndex:
    def __init__(self, vault_dir, storage_dir):
        self.vault_dir = Path(vault_dir)
        self.storage_dir = Path(storage_dir)
        self.opp_dir = self.storage_dir / 'opportunities'
        self.index_path = self.storage_dir / 'pemis_index.json'
        self._index = None
        self._lock = threading.Lock()
        self._watchdog_running = False
        self._callback = None
        self._dash_dir = self.vault_dir / 'PEMIS' / 'dashboard'

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
            val = val.strip().strip('"').strip("'")
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

    def _extract_summary(self, text):
        """Extract a useful summary from the body text after frontmatter"""
        # Remove frontmatter
        body = text.strip()
        if body.startswith('---'):
            end = body.find('---', 3)
            if end != -1:
                body = body[end + 3:].strip()
        # Take first meaningful paragraph (skip title lines)
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('# '):
                continue
            if line.startswith('**'):
                continue
            if line.startswith('---'):
                continue
            # Remove markdown formatting for clean summary
            clean = line.replace('**', '').replace('[', '').replace(']', '')
            if len(clean) > 20:
                return clean[:300]
        return ''

    def _is_dashboard_file(self, path):
        try:
            return self._dash_dir in path.parents
        except Exception:
            return False

    def _infer_type(self, path, meta):
        t = meta.get('type', '')
        if t and t != 'note':
            return t
        name = path.stem.lower()
        if name.startswith('opp_'):
            return 'opportunity'
        return 'note'

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
        dtype = self._infer_type(path, meta)
        # Use frontmatter summary if available, otherwise extract from body
        summary = meta.get('summary', '')
        if not summary:
            summary = self._extract_summary(text)
        return {
            'id': file_id,
            'type': dtype,
            'score': meta.get('score', 0.0),
            'tags': meta.get('tags', []),
            'title': title or path.stem,
            'summary': summary,
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
        if self.opp_dir.exists():
            for mf in self.opp_dir.glob('*.md'):
                entry = self._parse_md_file(mf)
                if entry:
                    entries[entry['id']] = entry
        idx = {
            'meta': {
                'version': '1.0',
                'total': len(entries),
                'last_build': datetime.now().timestamp(),
                'updated_at': datetime.now().isoformat()
            },
            'entries': entries,
        }
        with self._lock:
            self._index = idx
            self.save_index(idx)
        opp_count = sum(1 for e in entries.values() if e.get('type') == 'opportunity')
        logger.info('Index built: %d entries (%d opportunities) from %d vault + %d opp files',
                     len(entries), opp_count, len(md_files),
                     len(list(self.opp_dir.glob('*.md'))) if self.opp_dir.exists() else 0)
        return idx

    def incremental_add(self, file_path):
        path = Path(file_path)
        if self._is_dashboard_file(path):
            return False
        entry = self._parse_md_file(path)
        if not entry:
            return False
        with self._lock:
            idx = self._load()
            idx['entries'][entry['id']] = entry
            idx['meta']['total'] = len(idx['entries'])
            idx['meta']['updated_at'] = datetime.now().isoformat()
            self.save_index(idx)
        return True

    def incremental_update(self, file_path):
        path = Path(file_path)
        if self._is_dashboard_file(path):
            return False
        return self.incremental_add(path)

    def incremental_remove(self, file_id):
        with self._lock:
            idx = self._load()
            if file_id in idx.get('entries', {}):
                del idx['entries'][file_id]
                idx['meta']['total'] = len(idx['entries'])
                idx['meta']['updated_at'] = datetime.now().isoformat()
                self.save_index(idx)
                logger.info('Incremental remove: %s', file_id)
                return True
        return False

    def start_watchdog(self, callback=None):
        if self._watchdog_running:
            return
        self._callback = callback
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
                    if self._is_dashboard_file(mf):
                        continue
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
                logger.error('Watchdog error: %s', e)
                time.sleep(30)

    def stop_watchdog(self):
        self._watchdog_running = False
        self._callback = None

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