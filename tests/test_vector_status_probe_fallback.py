"""vector_status 必须在 live 探测不可用时退回真实 HTTP 嵌入探活。

回归背景：embedded Qdrant 被服务进程持锁（已知架构债），_live_semantic_counts
恒失败，vector_status 长期返回启动早期快照——主人看到 embedding available=false
被显示为"向量未开启"，即使 Ollama/bge-m3 实际可用。
"""

from __future__ import annotations

import unittest


class _Snapshot:
    def vector_status(self):
        return {
            "state": "degraded",
            "ready": True,
            "vectors": 19747,
            "stale": True,
            "embedding": {
                "provider_id": "ollama",
                "configured_model": "bge-m3",
                "active_model": None,
                "available": False,
                "verified": False,
            },
        }


def _service(live_ok: bool, probe: dict):
    from src.control.service import LocalControlService

    service = LocalControlService.__new__(LocalControlService)
    service.memory_statistics = _Snapshot()
    service._ensure_memory_status_snapshot = lambda: None
    if live_ok:
        service._live_semantic_counts = lambda: {
            "as_of": "2026-09-22T00:00:00+00:00",
            "vectors": 19747,
            "state": "healthy",
            "ready": True,
            "embedding": {"active_model": "bge-m3", "dimension": 1024, "available": True},
        }
    else:
        service._live_semantic_counts = lambda: None
    service._probe_embedding_status = lambda: probe
    return service


class VectorStatusProbeFallbackTests(unittest.TestCase):
    def test_live_path_unchanged(self):
        service = _service(live_ok=True, probe={"active_model": "x", "available": True})
        payload = service.vector_status()
        self.assertEqual(payload["source"], "live")
        self.assertTrue(payload["embedding"]["available"])

    def test_qdrant_locked_falls_back_to_http_probe_available(self):
        """Qdrant 锁冲突 + 探活成功：available 必须反映真实探活结果。"""
        service = _service(
            live_ok=False,
            probe={"active_model": "bge-m3", "dimension": 1024, "available": True},
        )
        payload = service.vector_status()
        self.assertNotEqual(payload.get("source"), "live")
        self.assertTrue(payload["embedding"]["available"])
        self.assertEqual(payload["embedding"]["active_model"], "bge-m3")
        self.assertEqual(payload["embedding"]["dimension"], 1024)
        self.assertEqual(payload["vectors"], 19747, "计数保留快照值")

    def test_qdrant_locked_and_probe_down_reports_unavailable(self):
        """探活也失败：如实报 unavailable，不虚报。"""
        service = _service(live_ok=False, probe={"active_model": "bge-m3", "dimension": None, "available": False})
        payload = service.vector_status()
        self.assertFalse(payload["embedding"]["available"])


if __name__ == "__main__":
    unittest.main()
