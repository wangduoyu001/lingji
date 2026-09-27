"""Regression tests for PERF_RESOURCE_CLOSEOUT_20260927B (B3 mixed-collection guard).

qdrant-local persists its collection registry in ``<path>/meta.json``. The B3
archive removed the stale ``lingji_memory_acceptance`` directory but not its
registration, so every process that opened the production qdrant path recreated
an empty collection directory (2026-09-27 15:26:17 reproduction). The pool now
deregisters empty foreign ``lingji_memory_*`` collections on first open.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.retrieval import qdrant_client_pool as pool

_DIM = 4


@pytest.fixture(autouse=True)
def _isolated_pool():
    pool.close_all()
    yield
    pool.close_all()


def _seed(path: Path, name: str, *, points: int = 0) -> None:
    path.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(path))
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=_DIM, distance=Distance.COSINE),
    )
    for index in range(points):
        client.upsert(
            collection_name=name,
            points=[PointStruct(
                id=index + 1,
                vector=[0.1, 0.2, 0.3, 0.4],
                payload={"n": index},
            )],
        )
    client.close()


def _names(client: object) -> set[str]:
    response = client.get_collections()
    items = getattr(response, "collections", response)
    return {str(item.name) for item in items}


def test_stale_empty_foreign_registration_is_deregistered(tmp_path: Path) -> None:
    _seed(tmp_path, "lingji_memory_acceptance")
    client = pool.shared_embedded_client(
        tmp_path, own_collection="lingji_memory_production"
    )
    assert "lingji_memory_acceptance" not in _names(client)
    meta = json.loads((tmp_path / "meta.json").read_text(encoding="utf-8"))
    assert "lingji_memory_acceptance" not in meta["collections"]


def test_non_empty_foreign_collection_is_kept(tmp_path: Path) -> None:
    _seed(tmp_path, "lingji_memory_acceptance", points=1)
    client = pool.shared_embedded_client(
        tmp_path, own_collection="lingji_memory_production"
    )
    assert "lingji_memory_acceptance" in _names(client)


def test_own_collection_is_never_removed_even_when_empty(tmp_path: Path) -> None:
    _seed(tmp_path, "lingji_memory_production")
    client = pool.shared_embedded_client(
        tmp_path, own_collection="lingji_memory_production"
    )
    assert "lingji_memory_production" in _names(client)


def test_guard_runs_once_per_path(tmp_path: Path) -> None:
    _seed(tmp_path, "lingji_memory_acceptance")
    client = pool.shared_embedded_client(
        tmp_path, own_collection="lingji_memory_production"
    )
    assert "lingji_memory_acceptance" not in _names(client)
    # A foreign registration that appears after the guarded open is left alone:
    # the guard is a startup reconciliation, not a per-call sweep.
    client.create_collection(
        collection_name="lingji_memory_acceptance",
        vectors_config=VectorParams(size=_DIM, distance=Distance.COSINE),
    )
    same = pool.shared_embedded_client(
        tmp_path, own_collection="lingji_memory_production"
    )
    assert "lingji_memory_acceptance" in _names(same)


def test_open_without_own_collection_skips_guard(tmp_path: Path) -> None:
    _seed(tmp_path, "lingji_memory_acceptance")
    client = pool.shared_embedded_client(tmp_path)
    assert "lingji_memory_acceptance" in _names(client)
