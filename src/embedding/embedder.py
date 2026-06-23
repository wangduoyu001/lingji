import hashlib, logging, requests
from collections import OrderedDict

logger = logging.getLogger('pemis.embedder')

class Embedder:
    def __init__(self, base_url='http://127.0.0.1:11434', model='bge-m3', cache_max=100):
        self.base_url = base_url
        self.model = model
        self._cache = OrderedDict()
        self._cache_max = cache_max

    def embed(self, text):
        h = hashlib.md5(text.encode()).hexdigest()
        if h in self._cache:
            self._cache.move_to_end(h)
            return self._cache[h]
        vec = self._call_ollama(text)
        self._cache[h] = vec
        if len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)
        return vec

    def embed_batch(self, texts):
        return [self.embed(t) for t in texts]

    def _call_ollama(self, text):
        try:
            resp = requests.post(
                f'{self.base_url}/api/embeddings',
                json={'model': self.model, 'prompt': text},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get('embedding', [])
        except Exception as e:
            logger.error(f'Ollama embedding failed: {e}')
            return []

    def clear_cache(self):
        self._cache.clear()
