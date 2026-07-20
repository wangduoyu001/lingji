from __future__ import annotations

import unittest

from src.model_center.embedding import (
    EmbeddingEndpointNotFound,
    OllamaEmbeddingProvider,
)


class FakeTransport:
    def __init__(self, handlers):
        self.handlers = handlers
        self.calls = []
        self.closed = False

    def post_json(self, url, payload, timeout):
        self.calls.append((url, payload, timeout))
        key = (url.rsplit("/", 1)[-1], payload["model"])
        handler = self.handlers[key]
        if isinstance(handler, Exception):
            raise handler
        if callable(handler):
            return handler(payload)
        return handler

    def close(self):
        self.closed = True


class EmbeddingProviderTests(unittest.TestCase):
    def test_primary_model_success_records_dimension(self):
        transport = FakeTransport({("embed", "primary"): {"embeddings": [[1, 2, 3]]}})
        provider = OllamaEmbeddingProvider("http://ollama", "primary", "fallback", transport=transport)

        self.assertEqual(provider.embed("hello"), [1.0, 2.0, 3.0])
        status = provider.status()
        self.assertEqual(status["active_model"], "primary")
        self.assertEqual(status["dimension"], 3)
        self.assertEqual(status["request_count"], 1)
        self.assertTrue(status["available"])

    def test_primary_failure_uses_fallback(self):
        transport = FakeTransport(
            {
                ("embed", "primary"): RuntimeError("primary unavailable"),
                ("embed", "fallback"): {"embeddings": [[0.5, 0.25]]},
            }
        )
        provider = OllamaEmbeddingProvider("http://ollama", "primary", "fallback", transport=transport)

        self.assertEqual(provider.embed("hello"), [0.5, 0.25])
        status = provider.status()
        self.assertEqual(status["active_model"], "fallback")
        self.assertEqual(status["unavailable_models"], ["primary"])
        self.assertEqual(status["failure_count"], 1)
        self.assertIsNone(status["last_error"])

    def test_reset_failures_retries_primary(self):
        attempts = {"primary": 0}

        def primary(payload):
            attempts["primary"] += 1
            if attempts["primary"] == 1:
                raise RuntimeError("temporary")
            return {"embeddings": [[9, 8]]}

        transport = FakeTransport(
            {
                ("embed", "primary"): primary,
                ("embed", "fallback"): {"embeddings": [[1, 1]]},
            }
        )
        provider = OllamaEmbeddingProvider("http://ollama", "primary", "fallback", transport=transport)

        self.assertEqual(provider.embed("first"), [1.0, 1.0])
        provider.reset_failures()
        self.assertEqual(provider.embed("second"), [9.0, 8.0])
        self.assertEqual(provider.status()["active_model"], "primary")

    def test_embed_many_respects_batch_size(self):
        def handler(payload):
            values = payload["input"] if isinstance(payload["input"], list) else [payload["input"]]
            return {"embeddings": [[float(len(value))] for value in values]}

        transport = FakeTransport({("embed", "primary"): handler})
        provider = OllamaEmbeddingProvider(
            "http://ollama", "primary", batch_size=2, transport=transport
        )

        self.assertEqual(provider.embed_many(["a", "bb", "ccc"]), [[1.0], [2.0], [3.0]])
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(provider.status()["request_count"], 3)

    def test_legacy_embeddings_endpoint_is_supported(self):
        transport = FakeTransport(
            {
                ("embed", "primary"): EmbeddingEndpointNotFound("missing"),
                ("embeddings", "primary"): lambda payload: {
                    "embedding": [float(len(payload["prompt"]))]
                },
            }
        )
        provider = OllamaEmbeddingProvider("http://ollama", "primary", transport=transport)

        self.assertEqual(provider.embed_many(["a", "abcd"]), [[1.0], [4.0]])
        self.assertEqual([call[0].rsplit("/", 1)[-1] for call in transport.calls], ["embed", "embeddings", "embeddings"])

    def test_all_models_fail_with_explicit_error(self):
        transport = FakeTransport(
            {
                ("embed", "primary"): RuntimeError("primary down"),
                ("embed", "fallback"): RuntimeError("fallback down"),
            }
        )
        provider = OllamaEmbeddingProvider("http://ollama", "primary", "fallback", transport=transport)

        with self.assertRaisesRegex(RuntimeError, "No embedding model available"):
            provider.embed("hello")
        status = provider.status()
        self.assertEqual(status["active_model"], None)
        self.assertEqual(status["unavailable_models"], ["fallback", "primary"])
        self.assertEqual(status["failure_count"], 2)
        self.assertFalse(status["available"])

    def test_invalid_or_empty_input_is_rejected(self):
        provider = OllamaEmbeddingProvider(
            "http://ollama",
            "primary",
            transport=FakeTransport({("embed", "primary"): {"embeddings": []}}),
        )
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            provider.embed(" ")
        with self.assertRaisesRegex(RuntimeError, "No embedding model available"):
            provider.embed("hello")

    def test_close_releases_transport(self):
        transport = FakeTransport({("embed", "primary"): {"embeddings": [[1.0]]}})
        provider = OllamaEmbeddingProvider("http://ollama", "primary", transport=transport)
        provider.close()
        self.assertTrue(transport.closed)


if __name__ == "__main__":
    unittest.main()
