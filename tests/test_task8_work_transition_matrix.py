from __future__ import annotations

from pathlib import Path

import pytest

from src.storage.state_db import StateDatabase
from src.work.models import WorkItem
from src.work.projector import WorkProjector
from src.work.store import WorkStore


def _store_and_work(tmp_path: Path) -> tuple[WorkStore, WorkItem]:
    store = WorkStore(StateDatabase(tmp_path / "state.db"))
    work = store.create_work(WorkItem(title="transition fixture", source_id="capture-transition"))
    return store, work


def _read_state(store: WorkStore, work_id: str) -> dict[str, object]:
    fact = WorkProjector(store).fact(work_id)
    outcome = fact["outcome"]
    next_action = fact["next_action"]
    return {
        "outcome": outcome["status"] if outcome else None,
        "failure_visible": fact["failure"] is not None,
        "next_actor": next_action["actor"] if next_action else None,
        "next_action_id": next_action["action_id"] if next_action else None,
        "pending_owner": len(fact["pending_actions"]),
        "terminal_events": len(
            [
                event
                for event in fact["events"]
                if event["event_type"] in {"extraction.completed", "work.failed"}
            ]
        ),
    }


@pytest.mark.parametrize(
    ("name", "transitions", "expected"),
    [
        (
            "new to retrying",
            [("retrying", "2026-08-26T10:00:00Z")],
            {
                "outcome": None,
                "failure_visible": False,
                "next_actor": "system",
                "next_action_id": "next:{work_id}:retrying",
                "pending_owner": 0,
                "terminal_events": 0,
            },
        ),
        (
            "new to failed",
            [("failed", "2026-08-26T10:00:00Z")],
            {
                "outcome": "failed",
                "failure_visible": True,
                "next_actor": "owner",
                "next_action_id": "next:{work_id}:failed",
                "pending_owner": 1,
                "terminal_events": 1,
            },
        ),
        (
            "failed to retrying",
            [("failed", "2026-08-26T10:00:00Z"), ("retrying", "2026-08-26T10:01:00Z")],
            {
                "outcome": None,
                "failure_visible": False,
                "next_actor": "system",
                "next_action_id": "next:{work_id}:retrying",
                "pending_owner": 0,
                "terminal_events": 1,
            },
        ),
        (
            "failed to completed without reopening",
            [("failed", "2026-08-26T10:00:00Z"), ("completed", "2026-08-26T10:01:00Z")],
            {
                "outcome": "completed",
                "failure_visible": False,
                "next_actor": "system",
                "next_action_id": "next:{work_id}:completed",
                "pending_owner": 0,
                "terminal_events": 2,
            },
        ),
        (
            "retrying to completed",
            [("retrying", "2026-08-26T10:00:00Z"), ("completed", "2026-08-26T10:01:00Z")],
            {
                "outcome": "completed",
                "failure_visible": False,
                "next_actor": "system",
                "next_action_id": "next:{work_id}:completed",
                "pending_owner": 0,
                "terminal_events": 1,
            },
        ),
        (
            "repeated failed",
            [("failed", "2026-08-26T10:00:00Z"), ("failed", "2026-08-26T10:00:00Z")],
            {
                "outcome": "failed",
                "failure_visible": True,
                "next_actor": "owner",
                "next_action_id": "next:{work_id}:failed",
                "pending_owner": 1,
                "terminal_events": 1,
            },
        ),
        (
            "repeated completed",
            [("completed", "2026-08-26T10:00:00Z"), ("completed", "2026-08-26T10:00:00Z")],
            {
                "outcome": "completed",
                "failure_visible": False,
                "next_actor": "system",
                "next_action_id": "next:{work_id}:completed",
                "pending_owner": 0,
                "terminal_events": 1,
            },
        ),
    ],
)
def test_extraction_transition_matrix(
    tmp_path: Path,
    name: str,
    transitions: list[tuple[str, str]],
    expected: dict[str, object],
) -> None:
    store, work = _store_and_work(tmp_path / name.replace(" ", "-"))
    for phase, occurred_at in transitions:
        store.apply_extraction_transition(
            work.work_id,
            phase,
            summary=f"{name}:{phase}",
            evidence={"case": name},
            occurred_at=occurred_at,
        )

    expected = dict(expected)
    expected["next_action_id"] = expected["next_action_id"].format(work_id=work.work_id)
    assert _read_state(store, work.work_id) == expected


@pytest.mark.parametrize("order", [("callback", "replay"), ("replay", "callback")])
def test_callback_and_replay_converge_without_new_ids(tmp_path: Path, order: tuple[str, str]) -> None:
    store, work = _store_and_work(tmp_path / ("callback-replay-" + "-".join(order)))
    for _origin in order:
        store.apply_extraction_transition(
            work.work_id,
            "failed",
            summary="failed",
            evidence={"source": "synthetic"},
            occurred_at="2026-08-26T10:00:00Z",
        )
    events = {event.event_id for event in store.list_events(work.work_id)}
    pending = {action.action_id for action in store.list_pending(work_id=work.work_id)}
    next_action = store.get_next_action(work.work_id)
    assert events == {f"work:{work.work_id}:failed:extraction"}
    assert pending == {f"owner-failure:{work.work_id}"}
    assert next_action is not None
    assert next_action.action_id == f"next:{work.work_id}:failed"
    assert _read_state(store, work.work_id)["terminal_events"] == 1


def test_restart_then_replay_preserves_the_same_fact_ids(tmp_path: Path) -> None:
    store, work = _store_and_work(tmp_path)
    store.apply_extraction_transition(
        work.work_id,
        "failed",
        summary="failed",
        evidence={"source": "synthetic"},
        occurred_at="2026-08-26T10:00:00Z",
    )
    restarted = WorkStore(StateDatabase(tmp_path / "state.db"))
    before = _read_state(restarted, work.work_id)
    restarted.apply_extraction_transition(
        work.work_id,
        "failed",
        summary="replayed failure",
        evidence={"source": "synthetic"},
        occurred_at="2026-08-26T10:00:00Z",
    )
    assert _read_state(restarted, work.work_id) == before


def test_older_failure_cannot_regress_completed_and_malformed_time_cannot_replace_it(tmp_path: Path) -> None:
    store, work = _store_and_work(tmp_path)
    store.apply_extraction_transition(
        work.work_id,
        "completed",
        summary="completed",
        evidence={"source": "synthetic"},
        occurred_at="2026-08-26T10:00:00+00:00",
    )
    store.apply_extraction_transition(
        work.work_id,
        "failed",
        summary="older failure",
        evidence={"source": "synthetic"},
        occurred_at="2026-08-26T09:00:00Z",
    )
    store.apply_extraction_transition(
        work.work_id,
        "failed",
        summary="malformed failure",
        evidence={"source": "synthetic"},
        occurred_at="not-an-iso-instant",
    )
    assert _read_state(store, work.work_id) == {
        "outcome": "completed",
        "failure_visible": False,
        "next_actor": "system",
        "next_action_id": f"next:{work.work_id}:completed",
        "pending_owner": 0,
        "terminal_events": 1,
    }


def test_equal_timestamp_terminal_precedence_is_completed_then_failed_then_retrying(tmp_path: Path) -> None:
    store, work = _store_and_work(tmp_path)
    store.apply_extraction_transition(
        work.work_id,
        "failed",
        summary="failed",
        evidence={"source": "synthetic"},
        occurred_at="2026-08-26T10:00:00Z",
    )
    store.apply_extraction_transition(
        work.work_id,
        "completed",
        summary="completed",
        evidence={"source": "synthetic"},
        occurred_at="2026-08-26T10:00:00+00:00",
    )
    store.apply_extraction_transition(
        work.work_id,
        "retrying",
        summary="retrying",
        evidence={"source": "synthetic"},
        occurred_at="2026-08-26T10:00:00Z",
    )
    assert _read_state(store, work.work_id) == {
        "outcome": "completed",
        "failure_visible": False,
        "next_actor": "system",
        "next_action_id": f"next:{work.work_id}:completed",
        "pending_owner": 0,
        "terminal_events": 2,
    }
