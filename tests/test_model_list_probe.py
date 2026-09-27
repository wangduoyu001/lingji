"""Regression tests for the model-list probe (2026-09-27 hang incident).

urllib 的 timeout 覆盖不了 socket.getaddrinfo：系统解析器卡死时提炼线程被
无限期挂起（实测 100+ 分钟）并拖住优雅停机。修复后走单守护探针线程 +
限时等待，至多卡死一个线程，调用方拿不到新鲜结果就退避。
"""

from __future__ import annotations

import threading
import time

import pytest

from src.automatic_memory import distillation
from src.automatic_memory.distillation import KnowledgeDistiller


@pytest.fixture(autouse=True)
def _isolated_probes():
    with distillation._PROBE_STATES_LOCK:
        distillation._PROBE_STATES.clear()
    yield
    with distillation._PROBE_STATES_LOCK:
        distillation._PROBE_STATES.clear()


def _distiller(base_url="http://127.0.0.1:9"):
    from types import SimpleNamespace

    settings = SimpleNamespace(ollama_base_url=base_url)
    return KnowledgeDistiller(settings)


def _patch_urlopen(monkeypatch, behavior) -> None:
    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", behavior)


def test_success_result_is_cached_within_freshness(tmp_path, monkeypatch) -> None:
    calls = {"n": 0}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            calls["n"] += 1
            return b'{"models": [{"name": "qwen2.5:7b", "size": 100}]}'

    def urlopen(url, timeout=None):
        return FakeResponse()

    _patch_urlopen(monkeypatch, urlopen)
    distiller = _distiller()
    first = distiller._available_models()
    second = distiller._available_models()
    assert first == [("qwen2.5:7b", 100)]
    assert second == first
    assert calls["n"] == 1, "新鲜窗口内的第二次调用必须命中缓存"


def test_resolver_wedge_returns_within_deadline_without_thread_leak(tmp_path, monkeypatch) -> None:
    release = threading.Event()

    def urlopen(url, timeout=None):
        release.wait(timeout=30)  # 模拟 getaddrinfo/连接被系统解析器卡死
        return None

    _patch_urlopen(monkeypatch, urlopen)
    monkeypatch.setattr(distillation, "_MODEL_LIST_DEADLINE_SECONDS", 0.5)
    baseline_threads = threading.active_count()
    distiller = _distiller()
    started = time.monotonic()
    for _ in range(3):
        assert distiller._available_models() == []
    elapsed = time.monotonic() - started
    assert elapsed < 5, f"三次限时探针共耗时 {elapsed:.1f}s，必须按截止时间返回"
    # 至多一个卡死的探针线程：重复调用不得每轮泄漏线程。
    assert threading.active_count() <= baseline_threads + 2
    release.set()


def test_error_response_is_cached_as_empty_then_recovered(tmp_path, monkeypatch) -> None:
    state = {"fail": True}

    def urlopen(url, timeout=None):
        if state["fail"]:
            raise ConnectionError("ollama down")
        return _fake_ok_response()

    def _fake_ok_response():
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"models": [{"name": "m1", "size": 1}]}'

        return FakeResponse()

    _patch_urlopen(monkeypatch, urlopen)
    distiller = _distiller()
    assert distiller._available_models() == []
    state["fail"] = False
    with distillation._PROBE_STATES_LOCK:
        probe = distillation._PROBE_STATES["http://127.0.0.1:9"]
    probe._fetched_at = 0.0  # 强制视为过期，触发重新探针
    assert distiller._available_models() == [("m1", 1)]
