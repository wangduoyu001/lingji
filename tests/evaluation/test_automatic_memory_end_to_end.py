from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from src.automatic_memory.evaluation import load_corpus, load_questions
from src.automatic_memory.evidence_identity import (
    EvidenceIdentityError,
    SelectedEvidence,
    build_identity_registry,
    select_context_evidence,
)
from src.automatic_memory.quality_gate import (
    AutomaticMemoryFunctionalGate,
    CORPUS_SHA256,
    QUESTIONS_SHA256,
    _promote_fixtures,
    run_quality_gate,
)
import src.automatic_memory.quality_gate as quality_gate_module
from src.retrieval.memory_db import MemoryDatabase
from src.sources.read_model import SourceReadModel
from src.storage.state_db import StateDatabase


ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "evaluation" / "fixtures" / "automatic_memory_corpus.jsonl"
QUESTIONS = ROOT / "evaluation" / "fixtures" / "automatic_memory_questions.jsonl"


def test_frozen_inputs_and_selector_are_expectation_blind():
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(CORPUS) == CORPUS_SHA256
    assert digest(QUESTIONS) == QUESTIONS_SHA256
    record = load_corpus(CORPUS)[0]
    registry = build_identity_registry(
        corpus=(record,),
        persisted_messages=[{
            "source_id": record.source_id,
            "conversation_id": record.conversation_id,
            "message_id": record.message_id,
            "content_hash": record.content_hash,
        }],
        promotion_bindings={"memory-1": record.fact_id},
        message_links=[{"message_id": record.message_id, "memory_id": "memory-1"}],
    )
    pack = {"sections": [{"kind": "retrieved_memory", "memory_id": "memory-1", "text": record.content}]}
    expected = {"expected_fact_ids": [record.fact_id], "forbidden_fact_ids": [], "expected_citation_ids": [record.citation_id]}
    baseline = select_context_evidence(pack, registry)
    expected["expected_fact_ids"] = ["forged"]
    expected["forbidden_fact_ids"] = [record.fact_id]
    expected["expected_citation_ids"] = ["forged-citation"]
    assert select_context_evidence(pack, registry) == baseline
    actual = json.loads(json.dumps(pack))
    actual["sections"][0]["memory_id"] = "unknown"
    with pytest.raises(ValueError):
        select_context_evidence(actual, registry)

    questions = load_questions(QUESTIONS, corpus=load_corpus(CORPUS))
    for question in questions:
        object.__setattr__(question, "expected_fact_ids", ("forged",))
        object.__setattr__(question, "forbidden_fact_ids", (record.fact_id,))
        object.__setattr__(question, "expected_citation_ids", ("forged-citation",))
        assert select_context_evidence(pack, registry) == baseline


def test_real_quality_gate_reports_measured_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    output = tmp_path / "quality.json"
    selector_calls = 0
    original_selector = quality_gate_module.select_context_evidence

    def counted_selector(*args, **kwargs):
        nonlocal selector_calls
        selector_calls += 1
        return original_selector(*args, **kwargs)

    monkeypatch.setattr(quality_gate_module, "select_context_evidence", counted_selector)
    report = run_quality_gate(CORPUS, QUESTIONS, output_path=output)
    assert report.answered_questions == 100
    assert report.imported_messages == report.expected_messages == len(load_corpus(CORPUS))
    assert len(load_questions(QUESTIONS, corpus=load_corpus(CORPUS))) == 100
    assert report.mcp_attempts == 100
    assert selector_calls == 100
    # The default test environment has no configured Production Vault root;
    # unavailable sentinel evidence is explicitly nullable, never numeric 0.
    assert report.production_pollution is None
    envelope = json.loads(output.read_text(encoding="utf-8"))
    assert envelope["production_pollution"] is None
    assert envelope["mcp_parity"]["status"] == "NOT_MEASURED"
    serialized = output.read_text(encoding="utf-8")
    assert "fixture_fact_id" not in serialized
    assert "fixture_citation_id" not in serialized
    assert AutomaticMemoryFunctionalGate.evaluate(report) in {"PASS", "FAIL"}


@pytest.mark.parametrize(
    "selected",
    [
        SelectedEvidence(("UNKNOWN-FACT",), (), ()),
        SelectedEvidence(("fact-preference-001",), ("UNKNOWN-CITATION",), ()),
    ],
)
def test_quality_runner_rejects_unknown_selected_membership(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected: SelectedEvidence):
    monkeypatch.setattr(quality_gate_module, "select_context_evidence", lambda *_args, **_kwargs: selected)
    with pytest.raises(EvidenceIdentityError):
        run_quality_gate(CORPUS, QUESTIONS, output_path=tmp_path / "unknown.json")
    assert not (tmp_path / "unknown.json").exists()


def test_real_import_promotion_storage_snapshot_has_no_evaluation_labels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    held_roots: list[Path] = []
    real_rmtree = quality_gate_module.shutil.rmtree

    def hold_quality_root(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.name.startswith("lingji-acceptance-quality-"):
            held_roots.append(candidate)
            return
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(quality_gate_module.shutil, "rmtree", hold_quality_root)
    try:
        run_quality_gate(CORPUS, QUESTIONS, output_path=tmp_path / "storage-snapshot.json")
        assert len(held_roots) == 1
        root = held_roots[0]
        read_model = SourceReadModel(root / "storage" / "index" / "lingji_memory.db")
        memory_db = MemoryDatabase(root / "storage" / "index" / "lingji_memory.db")
        messages = []
        offset = 0
        while True:
            page = read_model.list_messages(owner=True, limit=200, offset=offset)
            messages.extend(page["items"])
            if not page.get("next_offset"):
                break
            offset = int(page["next_offset"])
        documents = memory_db.list_documents(include_chunks=True)
        state_db = StateDatabase(root / "storage" / "state" / "lingji_state.db")
        corpus = load_corpus(CORPUS)
        labels = {item.fact_id for item in corpus} | {item.citation_id for item in corpus}
        for row in messages:
            metadata = row.get("metadata") or {}
            serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            assert not any(key.startswith("fixture_") for key in metadata)
            assert not labels.intersection(serialized.split('"'))
        for row in documents:
            relationships = row.get("relationships") or {}
            serialized = json.dumps(relationships, ensure_ascii=False, sort_keys=True)
            assert not any(key.startswith("fixture_") for key in relationships)
            assert not labels.intersection(serialized.split('"'))
        for event in state_db.recent_events(limit=100000):
            payload = json.loads(str(event.get("payload_json") or "{}"))
            metadata = payload.get("metadata") or {}
            serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            assert not any(key.startswith("fixture_") for key in metadata)
            assert not labels.intersection(serialized.split('"'))
    finally:
        for root in held_roots:
            real_rmtree(root, ignore_errors=True)


def _sqlite_snapshot(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Read every user table and persisted column from a temporary SQLite store."""
    connection = sqlite3.connect(path)
    try:
        tables = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        ]
        snapshot: dict[str, list[dict[str, Any]]] = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            columns = [str(row[1]) for row in connection.execute(f"PRAGMA table_info({quoted})").fetchall()]
            rows = connection.execute(f"SELECT * FROM {quoted}").fetchall()
            snapshot[table] = [dict(zip(columns, row)) for row in rows]
        return snapshot
    finally:
        connection.close()


_EVALUATOR_MARKERS = (
    "fixture_",
    "expected_fact_ids",
    "forbidden_fact_ids",
    "expected_citation_ids",
)
_PHYSICAL_BODY_LOCATIONS = frozenset(
    {
        ("source_read_model", "message_records", "content"),
        ("memory_database", "message_records", "content"),
        ("source_read_model", "memory_chunks", "text"),
        ("source_read_model", "memory_fts", "text"),
        ("memory_database", "memory_chunks", "text"),
        ("memory_database", "memory_fts", "text"),
        ("source_read_model", "memory_fts_content", "c4"),
        ("memory_database", "memory_fts_content", "c4"),
    }
)
_STRUCTURED_EVENT_BODY_LOCATION = ("state_database", "events", "payload_json")


def _walk_raw_and_decoded(value: Any):
    """Yield raw values and recursively decoded JSON values without key deletion."""
    yield value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_raw_and_decoded(key)
            yield from _walk_raw_and_decoded(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_raw_and_decoded(child)
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return
        if parsed != value:
            yield from _walk_raw_and_decoded(parsed)


def _has_marker(value: Any, marker: str) -> bool:
    return any(marker in item for item in _walk_raw_and_decoded(value) if isinstance(item, str))


def _walk_marker_values(value: Any, location: tuple[str, str, str], path: tuple[str, ...] = ()):
    """Yield marker-bearing structural values while retaining body fields."""
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            yield key_text
            # A promotion event's top-level candidate ``content`` is a known
            # body value inside an otherwise structured JSON column.  Only
            # that scalar is exempt; nested content/text objects remain fully
            # inspected below.
            if (
                location == _STRUCTURED_EVENT_BODY_LOCATION
                and path == ()
                and key_text == "content"
                and isinstance(child, str)
                and not _contains_structured_json(child)
            ):
                continue
            yield from _walk_marker_values(child, location, path + (key_text,))
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_marker_values(child, location, path + (str(index),))
        return
    if isinstance(value, str):
        if location in _PHYSICAL_BODY_LOCATIONS and not path and not _contains_structured_json(value):
            return
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            yield value
            return
        if parsed != value:
            yield from _walk_marker_values(parsed, location, path)
        return
    yield value


def _has_structural_marker(value: Any, location: tuple[str, str, str], marker: str) -> bool:
    return any(marker in item for item in _walk_marker_values(value, location) if isinstance(item, str))


def _contains_structured_json(value: Any) -> bool:
    if isinstance(value, (dict, list)):
        return True
    if not isinstance(value, str):
        return False
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(parsed, (dict, list))


def _assert_clean_storage_value(
    store: str, table: str, column: str, value: Any, labels: set[str]
) -> None:
    for label in labels:
        if _has_marker(value, label):
            raise AssertionError((store, table, column, "frozen label", label, value))
    location = (store, table, column)
    if location in _PHYSICAL_BODY_LOCATIONS and not _contains_structured_json(value):
        return
    location = (store, table, column)
    for marker in _EVALUATOR_MARKERS:
        if _has_structural_marker(value, location, marker):
            raise AssertionError((store, table, column, "evaluator marker", marker, value))


def test_opaque_batch_identity_collision_fails_before_any_persistence(
    tmp_path: Path,
):
    first, second = load_corpus(CORPUS)[:2]
    duplicate = replace(
        second,
        fact_id="fact-collision-distinct",
        citation_id="citation-collision-distinct",
        source_id=first.source_id,
        conversation_id=first.conversation_id,
        message_id=first.message_id,
        content_hash=first.content_hash,
    )
    corpus = (first, duplicate)
    memory_db = MemoryDatabase(tmp_path / "storage" / "index" / "memory.db")
    read_model = SourceReadModel(memory_db)
    state_db = StateDatabase(tmp_path / "storage" / "state" / "state.db")
    message_map = {
        first.fact_id: {"message_id": "message-primary-1"},
        duplicate.fact_id: {"message_id": "message-primary-2"},
    }
    with pytest.raises(ValueError, match="opaque memory ID collision"):
        _promote_fixtures(corpus, message_map, memory_db, read_model, state_db)
    assert memory_db.list_documents() == []
    assert state_db.recent_events(limit=100) == []


@pytest.mark.parametrize("field", ["content", "text"])
def test_scanner_rejects_nested_evaluator_metadata_under_body_named_keys(field: str):
    value = {"structured_content": {field: {"expected_fact_ids": ["hidden"]}}}
    with pytest.raises(AssertionError):
        _assert_clean_storage_value(
            "state_database", "events", "payload_json", value, {"fact-preference-001"}
        )


@pytest.mark.parametrize(
    ("escaped_label", "label"),
    [
        (r"\u0066act\u002dpreference\u002d001", "fact-preference-001"),
        (r"\u0063itation\u002dpreference\u002d001", "citation-preference-001"),
    ],
)
def test_scanner_rejects_unicode_escaped_frozen_labels(escaped_label: str, label: str):
    value = '{"nested":"' + escaped_label + '"}'
    with pytest.raises(AssertionError):
        _assert_clean_storage_value("state_database", "events", "payload_json", value, {label})


@pytest.mark.parametrize(
    "location",
    sorted(_PHYSICAL_BODY_LOCATIONS),
)
def test_scanner_allows_marker_words_only_in_known_plain_body_columns(location):
    _assert_clean_storage_value(*location, "用户正文提到 forbidden_fact_ids 这个字段名。", {"fact-preference-001"})


def test_scanner_rejects_marker_in_metadata_json_and_labels_in_body():
    with pytest.raises(AssertionError):
        _assert_clean_storage_value(
            "state_database", "events", "payload_json",
            json.dumps({"metadata": {"content": {"expected_fact_ids": []}}}),
            {"fact-preference-001"},
        )
    with pytest.raises(AssertionError):
        _assert_clean_storage_value(
            "source_read_model", "message_records", "content", "用户正文 fact-preference-001", {"fact-preference-001"}
        )


def test_real_promotion_uses_opaque_memory_ids_and_scans_all_temporary_sqlite_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    held_roots: list[Path] = []
    registry_box: dict[str, Any] = {}
    real_rmtree = quality_gate_module.shutil.rmtree
    real_registry_builder = quality_gate_module.build_identity_registry

    def hold_quality_root(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.name.startswith("lingji-acceptance-quality-"):
            held_roots.append(candidate)
            return
        return real_rmtree(path, *args, **kwargs)

    def capture_registry(*args, **kwargs):
        registry = real_registry_builder(*args, **kwargs)
        registry_box["registry"] = registry
        return registry

    monkeypatch.setattr(quality_gate_module.shutil, "rmtree", hold_quality_root)
    monkeypatch.setattr(quality_gate_module, "build_identity_registry", capture_registry)
    try:
        run_quality_gate(CORPUS, QUESTIONS, output_path=tmp_path / "opaque-storage-snapshot.json")
        assert len(held_roots) == 1
        root = held_roots[0]
        corpus = load_corpus(CORPUS)
        labels = {item.fact_id for item in corpus} | {item.citation_id for item in corpus}
        # SourceReadModel and MemoryDatabase are two real readers over the same
        # temporary SQLite file; StateDatabase is the third real store.
        stores = {
            "source_read_model": root / "storage" / "index" / "lingji_memory.db",
            "memory_database": root / "storage" / "index" / "lingji_memory.db",
            "state_database": root / "storage" / "state" / "lingji_state.db",
        }
        snapshots = {name: _sqlite_snapshot(path) for name, path in stores.items()}
        for store_name, snapshot in snapshots.items():
            for table, rows in snapshot.items():
                for row in rows:
                    for column, value in row.items():
                        _assert_clean_storage_value(store_name, table, column, value, labels)

        memory_snapshot = snapshots["memory_database"]
        documents = memory_snapshot.get("memory_documents", [])
        links = memory_snapshot.get("message_memory_links", [])
        assert documents, "real promotion must create non-empty memory documents"
        assert links, "real promotion must create non-empty message-memory links"
        derived_documents = [row for row in documents if str(row.get("memory_tier")) == "derived"]
        assert derived_documents, "real promotion must create non-empty derived memory documents"
        persisted_memory_ids = {str(row["memory_id"]) for row in derived_documents}
        assert persisted_memory_ids
        assert not persisted_memory_ids.intersection(labels)
        assert all(str(row.get("memory_id")) in persisted_memory_ids for row in links)

        state_events = snapshots["state_database"].get("events", [])
        promotion_events = [
            row for row in state_events
            if str(row.get("event_type")) == "memory_promotion_decision"
            and '"status": "active"' in str(row.get("payload_json") or "")
        ]
        assert promotion_events, "real promotion must emit an active decision event"

        registry = registry_box.get("registry")
        assert registry is not None
        bridge = dict(registry.memory_to_fact)
        assert bridge, "real promotion must expose a non-empty in-memory identity bridge"
        assert set(bridge.values()) == {item.fact_id for item in corpus}
        assert set(persisted_memory_ids).issubset(bridge)
        assert not set(bridge).intersection(labels)
    finally:
        for root in held_roots:
            real_rmtree(root, ignore_errors=True)
