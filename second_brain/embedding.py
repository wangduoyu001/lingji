from __future__ import annotations

import logging

import requests


logger = logging.getLogger("second_brain.embedding")


class OllamaEmbedder:
    def __init__(self, base_url: str, model: str, fallback_model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_model = fallback_model
        self.active_model = model
        self._unavailable: set[str] = set()

    def embed(self, text: str) -> list[float]:
        last_error: Exception | None = None
        ordered = (self.active_model, self.model, self.fallback_model)
        for model in dict.fromkeys(ordered):
            if not model or model in self._unavailable:
                continue
            try:
                vector = self._embed_model(model, text)
                self.active_model = model
                return vector
            except (requests.RequestException, KeyError, ValueError) as exc:
                last_error = exc
                self._unavailable.add(model)
                logger.warning("Embedding failed with %s: %s", model, exc)
        raise RuntimeError(f"No embedding model available: {last_error}")

    def _embed_model(self, model: str, text: str) -> list[float]:
        response = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": model, "input": text},
            timeout=60,
        )
        if response.status_code == 404:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=60,
            )
        response.raise_for_status()
        data = response.json()
        vectors = data.get("embeddings")
        vector = vectors[0] if vectors else data.get("embedding")
        if not vector:
            raise ValueError("Ollama returned no embedding")
        return [float(value) for value in vector]

    def status(self) -> dict:
        return {
            "configured_model": self.model,
            "fallback_model": self.fallback_model,
            "active_model": self.active_model,
            "unavailable_models": sorted(self._unavailable),
        }
