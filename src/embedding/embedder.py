import hashlib
import logging
import time
from collections import OrderedDict

import requests

logger = logging.getLogger("pemis.embedder")


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
        candidates = [self.current_model]
        if self.fallback_model and self.fallback_model not in candidates:
            candidates.append(self.fallback_model)
        for attempt, model in enumerate(candidates, 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                embedding = data.get("embedding", [])
                if not embedding:
                    continue
                if model != self.current_model:
                    self._switch_log.append(
                        {
                            "time": time.time(),
                            "from": self.current_model,
                            "to": model,
                            "reason": "request_failed",
                        }
                    )
                self.current_model = model
                self._fallback_active = model == self.fallback_model and model != self.primary_model
                return embedding
            except requests.RequestException as exc:
                logger.warning("Embedding attempt %s failed with %s: %s", attempt, model, exc)
        logger.error("All embedding models failed for: %s...", text[:50])
        return None

    def clear_cache(self):
        self._cache.clear()

    def get_status(self):
        return {
            "current_model": self.current_model,
            "primary": self.primary_model,
            "fallback": self.fallback_model,
            "fallback_active": self._fallback_active,
            "cache_size": len(self._cache),
            "switches": self._switch_log[-5:] if self._switch_log else [],
        }
