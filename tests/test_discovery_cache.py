"""Regression tests for PERF_RESOURCE_ROOT_CAUSE_20260927 (A2).

The discovery endpoints behind the Desktop polling loop must serve cached
snapshots within the TTL window and re-scan only after it expires.
"""

from __future__ import annotations

import src.control.automatic_memory_api as api_module
from src.control.automatic_memory_api import cached_discovery_snapshot


def test_same_key_serves_cache_within_ttl(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "_discovery_cache", {})
    calls: list[int] = []

    def producer() -> list[int]:
        calls.append(len(calls))
        return list(calls)

    first = cached_discovery_snapshot("discovered", producer)
    second = cached_discovery_snapshot("discovered", producer)

    assert first == second == [0]
    assert len(calls) == 1


def test_expired_ttl_rescans(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "_discovery_cache", {})
    monkeypatch.setattr(api_module, "_DISCOVERY_CACHE_TTL_SECONDS", 0.0)
    calls: list[int] = []

    def producer() -> list[int]:
        calls.append(len(calls))
        return list(calls)

    cached_discovery_snapshot("discovered", producer)
    cached_discovery_snapshot("discovered", producer)

    assert len(calls) == 2


def test_keys_are_cached_independently(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "_discovery_cache", {})

    assert cached_discovery_snapshot("apps", lambda: "apps-value") == "apps-value"
    assert cached_discovery_snapshot("processes", lambda: "proc-value") == "proc-value"
    # A different key must not be served the other snapshot.
    assert cached_discovery_snapshot("apps", lambda: "apps-value-2") == "apps-value"
