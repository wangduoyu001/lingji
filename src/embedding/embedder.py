import hashlib, logging, requests, time
from collections import OrderedDict

logger = logging.getLogger('pemis.embedder')


class Embedder:
    def __init__(self, base_url, primary_model, fallback_model, cache_max=100):
        self.base_url = base_url
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.current_model = primary_model
        self._cache = OrderedDict()
        self._cache_max = cache_max
        self._fallback_active = False
        self._switch_log = []

    def embed(self, text):
        h = hashlib.md5(text.encode()).hexdigest()
        if h in self._cache:
            self._cache.move_to_end(h)
            return self._cache[h]
        vec = self._call_ollama(text)
        if vec:
            self._cache[h] = vec
            if len(self._cache) > self._cache_max:
                self._cache.popitem(last=False)
        return vec or []

    def embed_batch(self, texts):
        return [self.embed(t) for t in texts]

    def _call_ollama(self, text):
        for attempt in range(2):
            model = self.current_model
            try:
                resp = requests.post(
                    f'{self.base_url}/api/embeddings',
                    json={'model': model, 'prompt': text},
                    timeout=15
                )
                resp.raise_for_status()
                data = resp.json()
                embedding = data.get('embedding', [])
                if embedding and self._fallback_active:
                    logger.info(f'Embedder recovered on primary: {self.primary_model}')
                    self._fallback_active = False
                    self.current_model = self.primary_model
                    self._switch_log.append({'time': time.time(), 'from': self.fallback_model, 'to': self.primary_model})
                return embedding
            except requests.RequestException as e:
                logger.warning(f'Embedding attempt {attempt + 1} failed with {model}: {e}')
                if not self._fallback_model or model == self.fallback_model:
                    continue
                logger.info(f'Falling back to {self.fallback_model}')
                self._fallback_active = True
                self.current_model = self.fallback_model
                self._switch_log.append({'time': time.time(), 'from': model, 'to': self.fallback_model, 'reason': str(e)[:100]})
        logger.error(f'All embedding models failed for: {text[:50]}...')
        return None

    def clear_cache(self):
        self._cache.clear()

    def get_status(self):
        return {
            'current_model': self.current_model,
            'primary': self.primary_model,
            'fallback': self.fallback_model,
            'fallback_active': self._fallback_active,
            'cache_size': len(self._cache),
            'switches': self._switch_log[-5:] if self._switch_log else []
        }
