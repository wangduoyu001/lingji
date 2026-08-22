from __future__ import annotations

from typing import Any

from .models import ExecutionEvent, Outcome, WorkItem
from .store import WorkStore


class CaptureWorkBridge:
    """Translate capture/extraction lifecycle facts into the canonical WorkStore."""

    def __init__(self, store: WorkStore):
        self.store = store

    def create_from_capture(
        self,
        capture_id: str,
        title: str,
        *,
        source_id: str | None = None,
        approved: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> WorkItem:
        work = WorkItem(
            title=title or f"Capture {capture_id}",
            source_id=source_id or capture_id,
            owner_approved=approved,
            status="accepted",
        )
        self.store.create_work(work)
        self.store.append_event(
            ExecutionEvent(
                work_id=work.work_id,
                event_type="capture.accepted",
                detail={"capture_id": capture_id, "metadata": metadata or {}},
            )
        )
        return work

    def start_extraction(
        self,
        work_id: str,
        *,
        detail: dict[str, Any] | None = None,
    ) -> WorkItem:
        work = self.store.update_work_status(work_id, "running")
        self.store.append_event(
            ExecutionEvent(
                work_id=work_id,
                event_type="extraction.started",
                detail=detail or {},
            )
        )
        return work

    def complete_extraction(
        self,
        work_id: str,
        summary: str,
        *,
        evidence: dict[str, Any] | None = None,
    ) -> Outcome:
        self.store.append_event(
            ExecutionEvent(
                work_id=work_id,
                event_type="extraction.completed",
                detail={"summary": summary},
            )
        )
        outcome = Outcome(
            work_id=work_id,
            status="success",
            summary=summary,
            evidence=evidence or {},
        )
        self.store.save_outcome(outcome)
        return outcome

    def fail_extraction(
        self,
        work_id: str,
        summary: str,
        *,
        evidence: dict[str, Any] | None = None,
    ) -> Outcome:
        self.store.append_event(
            ExecutionEvent(
                work_id=work_id,
                event_type="extraction.failed",
                detail={"summary": summary},
            )
        )
        outcome = Outcome(
            work_id=work_id,
            status="failure",
            summary=summary,
            evidence=evidence or {},
        )
        self.store.save_outcome(outcome)
        return outcome
