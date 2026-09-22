"""懒加载嵌入 provider 的 available 不能把"从未使用"当成"不可用"显示。

回归背景：overview 的向量/嵌入状态来自语义运行时 provider 的计数器。
懒加载下启动后无人调用嵌入，available 恒为 false，UI 把向量层显示为
"向量未开启"，而向量检索实际健康（19k+ 向量在库）。
"""

from __future__ import annotations

import unittest
from pathlib import Path

from src.gateway.memory_statistics import MemoryStatisticsService


class _Provider:
    def __init__(self, embed_ok: bool):
        self.embed_ok = embed_ok
        self.request_count = 0
        self.embed_calls = 0

    def status(self):
        # 与真实 provider 同语义：available 反映"是否已有成功请求"。
        return {
            "available": self.request_count > 0,
            "active_model": "bge-m3" if self.request_count else None,
            "dimension": 1024 if self.request_count else None,
            "request_count": self.request_count,
        }

    def embed_many(self, texts):
        self.embed_calls += 1
        if not self.embed_ok:
            raise RuntimeError("ollama down")
        self.request_count += len(texts)
        return [[0.1] * 1024 for _ in texts]


class _Semantic:
    def __init__(self, provider):
        self.embedding_provider = provider


def _service(tmp_path: Path) -> MemoryStatisticsService:
    return MemoryStatisticsService(None, snapshot_path=tmp_path / "snap.json")


class EmbeddingStatusProbeTests(unittest.TestCase):
    def test_unused_provider_gets_real_probe_and_turns_healthy(self):
        provider = _Provider(embed_ok=True)
        payload = MemoryStatisticsService._embedding_status(object.__new__(MemoryStatisticsService), _Semantic(provider))
        self.assertEqual(provider.embed_calls, 1)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["state"], "healthy")
        self.assertEqual(payload["active_model"], "bge-m3")
        self.assertEqual(payload["dimension"], 1024)

    def test_probe_failure_is_cached_for_60s(self):
        service = object.__new__(MemoryStatisticsService)
        service._probe_failed_at = 0.0
        provider = _Provider(embed_ok=False)
        semantic = _Semantic(provider)
        first = MemoryStatisticsService._embedding_status(service, semantic)
        self.assertFalse(first["available"])
        self.assertEqual(first["state"], "unavailable")
        second = MemoryStatisticsService._embedding_status(service, semantic)
        self.assertEqual(provider.embed_calls, 1, "60s 内失败结果应缓存，不重复探活")

    def test_used_provider_status_is_shown_as_is(self):
        provider = _Provider(embed_ok=True)
        provider.request_count = 5
        payload = MemoryStatisticsService._embedding_status(object.__new__(MemoryStatisticsService), _Semantic(provider))
        self.assertTrue(payload["available"])
        self.assertEqual(provider.embed_calls, 0, "已有真实计数的 provider 不再探活")

    def test_missing_provider_reports_configuration_required(self):
        payload = MemoryStatisticsService._embedding_status(object.__new__(MemoryStatisticsService), _Semantic(None))
        self.assertEqual(payload["state"], "configuration_required")
        self.assertFalse(payload["available"])


if __name__ == "__main__":
    unittest.main()
