from __future__ import annotations

import threading
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence

import requests


class EmbeddingProvider(Protocol):
    """Provider contract used by semantic indexes without depending on Ollama."""

    def embed(self, text: str) -> list[float]: ...

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]: ...

    def status(self) -> dict[str, Any]: ...

    def reset_failures(self) -> None: ...


class EmbeddingTransport(Protocol):
    def post_json(self, url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]: ...

    def close(self) -> None: ...


class EmbeddingEndpointNotFound(RuntimeError):
    """Raised when an Ollama version does not provide the requested endpoint."""


class RequestsEmbeddingTransport:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def post_json(self, url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        response = self.session.post(url, json=payload, timeout=timeout)
        if response.status_code == 404:
            raise EmbeddingEndpointNotFound(url)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Ollama embedding response must be an object")
        return body

    def close(self) -> None:
        self.session.close()


@dataclass(frozen=True)
class EmbeddingStatus:
    provider_id: str
    configured_model: str
    fallback_model: str | None
    active_model: str | None
    dimension: int | None
    unavailable_models: tuple[str, ...]
    request_count: int
    failure_count: int
    last_success_at: str | None
    last_failure_at: str | None
    last_error: str | None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["unavailable_models"] = list(self.unavailable_models)
        payload["available"] = self.active_model is not None and not self.last_error
        return payload


class OllamaEmbeddingProvider:
    """Ollama embedding provider with explicit primary/fallback state and recovery."""

    provider_id = "ollama"

    def __init__(
        self,
        base_url: str,
        primary_model: str,
        fallback_model: str | None = None,
        *,
        timeout_seconds: float = 60.0,
        batch_size: int = 32,
        transport: EmbeddingTransport | None = None,
    ):
        primary = str(primary_model or "").strip()
        if not primary:
            raise ValueError("primary_model must not be empty")
        fallback = str(fallback_model or "").strip() or None
        self.base_url = str(base_url or "http://127.0.0.1:11434").rstrip("/")
        self.primary_model = primary
        self.fallback_model = fallback
        self.timeout_seconds = max(float(timeout_seconds), 0.1)
        self.batch_size = max(int(batch_size), 1)
        self.transport = transport or RequestsEmbeddingTransport()
        self._lock = threading.RLock()
        self._status = EmbeddingStatus(
            provider_id=self.provider_id,
            configured_model=primary,
            fallback_model=fallback,
            active_model=primary,
            dimension=None,
            unavailable_models=(),
            request_count=0,
            failure_count=0,
            last_success_at=None,
            last_failure_at=None,
            last_error=None,
        )

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        normalized = [str(text) for text in texts]
        if not normalized:
            return []
        if any(not text.strip() for text in normalized):
            raise ValueError("embedding input must not be empty")

        output: list[list[float]] = []
        for start in range(0, len(normalized), self.batch_size):
            output.extend(self._embed_batch(normalized[start : start + self.batch_size]))
        return output

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._status.to_dict()

    def reset_failures(self) -> None:
        with self._lock:
            self._status = replace(
                self._status,
                active_model=self.primary_model,
                unavailable_models=(),
                last_error=None,
            )

    def close(self) -> None:
        close = getattr(self.transport, "close", None)
        if callable(close):
            close()

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for model in self._candidate_models():
            try:
                vectors = self._embed_model(model, texts)
                self._record_success(model, vectors)
                return vectors
            except Exception as exc:
                last_error = exc
                self._record_failure(model, exc)
        raise RuntimeError(f"No embedding model available: {self._safe_error(last_error)}") from last_error

    def _candidate_models(self) -> list[str]:
        with self._lock:
            unavailable = set(self._status.unavailable_models)
            ordered = (self._status.active_model, self.primary_model, self.fallback_model)
        return [model for model in dict.fromkeys(ordered) if model and model not in unavailable]

    def _embed_model(self, model: str, texts: list[str]) -> list[list[float]]:
        try:
            payload = self.transport.post_json(
                f"{self.base_url}/api/embed",
                {"model": model, "input": texts if len(texts) > 1 else texts[0]},
                self.timeout_seconds,
            )
            return self._parse_vectors(payload, expected=len(texts))
        except EmbeddingEndpointNotFound:
            vectors = []
            for text in texts:
                payload = self.transport.post_json(
                    f"{self.base_url}/api/embeddings",
                    {"model": model, "prompt": text},
                    self.timeout_seconds,
                )
                vectors.extend(self._parse_vectors(payload, expected=1))
            return vectors

    @staticmethod
    def _parse_vectors(payload: dict[str, Any], *, expected: int) -> list[list[float]]:
        raw = payload.get("embeddings")
        if raw is None and payload.get("embedding") is not None:
            raw = [payload["embedding"]]
        if not isinstance(raw, list) or len(raw) != expected:
            raise ValueError(f"Ollama returned {len(raw) if isinstance(raw, list) else 0} embeddings; expected {expected}")

        vectors: list[list[float]] = []
        dimension: int | None = None
        for item in raw:
            if not isinstance(item, list) or not item:
                raise ValueError("Ollama returned an empty embedding")
            vector = [float(value) for value in item]
            if dimension is None:
                dimension = len(vector)
            elif len(vector) != dimension:
                raise ValueError("Ollama returned inconsistent embedding dimensions")
            vectors.append(vector)
        return vectors

    def _record_success(self, model: str, vectors: list[list[float]]) -> None:
        with self._lock:
            unavailable = tuple(item for item in self._status.unavailable_models if item != model)
            self._status = replace(
                self._status,
                active_model=model,
                dimension=len(vectors[0]) if vectors else self._status.dimension,
                unavailable_models=unavailable,
                request_count=self._status.request_count + len(vectors),
                last_success_at=self._timestamp(),
                last_error=None,
            )

    def _record_failure(self, model: str, exc: Exception) -> None:
        with self._lock:
            unavailable = tuple(sorted(set(self._status.unavailable_models) | {model}))
            self._status = replace(
                self._status,
                active_model=None if model == self._status.active_model else self._status.active_model,
                unavailable_models=unavailable,
                failure_count=self._status.failure_count + 1,
                last_failure_at=self._timestamp(),
                last_error=self._safe_error(exc),
            )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_error(exc: Exception | None) -> str:
        if exc is None:
            return "unknown embedding error"
        return f"{type(exc).__name__}: {exc}"[:500]


def build_embedding_provider(
    settings: Any,
    runtime_values: Mapping[str, Any] | None = None,
    *,
    transport: EmbeddingTransport | None = None,
) -> EmbeddingProvider | None:
    """Build the configured provider without creating a semantic index or Qdrant client."""

    values = dict(runtime_values or {})
    enabled = _as_bool(values.get("embedding_enabled", getattr(settings, "embedding_enabled", True)))
    provider_id = str(values.get("embedding_provider", getattr(settings, "embedding_provider", "ollama"))).strip().lower()
    if not enabled or provider_id in {"", "off", "disabled", "none"}:
        return None
    if provider_id != "ollama":
        raise ValueError(f"Unsupported embedding provider: {provider_id}")

    return OllamaEmbeddingProvider(
        base_url=str(values.get("embedding_endpoint", getattr(settings, "ollama_base_url", "http://127.0.0.1:11434"))),
        primary_model=str(values.get("embedding_primary_model", getattr(settings, "embed_model", ""))),
        fallback_model=str(values.get("embedding_fallback_model", getattr(settings, "fallback_embed_model", ""))) or None,
        timeout_seconds=float(values.get("embedding_timeout_seconds", getattr(settings, "embedding_timeout_seconds", 60.0))),
        batch_size=int(values.get("embedding_batch_size", getattr(settings, "embedding_batch_size", 32))),
        transport=transport,
    )


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")
