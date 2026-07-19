from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from src.embedding.embedder import Embedder


class EmbedderFallbackTests(unittest.TestCase):
    def test_fallback_model_is_used_without_attribute_error(self):
        success = Mock()
        success.raise_for_status.return_value = None
        success.json.return_value = {"embedding": [0.1, 0.2]}
        with patch(
            "src.embedding.embedder.requests.post",
            side_effect=[requests.ConnectionError("primary offline"), success],
        ) as post:
            embedder = Embedder("http://127.0.0.1:11434", "primary", "fallback")
            vector = embedder.embed("hello")
        self.assertEqual(vector, [0.1, 0.2])
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[1].kwargs["json"]["model"], "fallback")
        self.assertTrue(embedder.get_status()["fallback_active"])

    def test_same_primary_and_fallback_only_attempt_once(self):
        with patch(
            "src.embedding.embedder.requests.post",
            side_effect=requests.ConnectionError("offline"),
        ) as post:
            embedder = Embedder("http://127.0.0.1:11434", "same", "same")
            self.assertEqual(embedder.embed("hello"), [])
        self.assertEqual(post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
