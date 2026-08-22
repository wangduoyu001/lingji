from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .models import ExecutionEvent, NextAction, Outcome, WorkItem
from .store import WorkStore


class CaptureWorkBridge:
    """Translate capture/extraction lifecycle facts into the canonical WorkStore."""

    def __init__(self, store: WorkStore):
        self.store = store

    @staticmethod
    def work_id_for_identity(identity: str) -> str:
        normalized = str(identity or "").strip()
        if not normalized:
            raise ValueError("capture identity is required")
        return str(uuid5(NAMESPACE_URL, f"lingji:capture:{normalized}"))

    def ensure_from_capture(
        self,
        capture_id: str,
        title: str,
        *,
        identity: str,
        source_id: str | None = None,
        approved: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[WorkItem, bool]:
        work_id = self.work_id_for_identity(identity)
        existing = self.store.get_work(work_id)
        if existing is not None:
            return existing, False
        work = WorkItem(
            work_id=work_id,
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
                detail={
                    "capture_id": capture_id,
                    "capture_identity": identity,
                    "metadata": metadata or {},
                },
            )
        )
        self.store.save_next_action(
            NextAction(
                work_id=work.work_id,
                actor="system",
                description="等待提取任务进入处理队列",
            )
        )
        return work, True

    def create_from_capture(
        self,
        capture_id: str,
        title: str,
        *,
        source_id: str | None = None,
        approved: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> WorkItem:
        """Backward-compatible helper for callers without a durable identity."""
        work, _ = self.ensure_from_capture(
            capture_id,
            title,
            identity=capture_id,
            source_id=source_id,
            approved=approved,
            metadata=metadata,
        )
        return work

    def record_duplicate(
        self,
        work_id: str,
        *,
        capture_id: str,
        job_id: str | None = None,
    ) -> None:
        self.store.append_event(
            ExecutionEvent(
                work_id=work_id,
                event_type="capture.duplicate",
                detail={"capture_id": capture_id, "job_id": job_id},
            )
        )

    def queue_extraction(
        self,
        work_id: str,
        *,
        job_id: str,
        detail: dict[str, Any] | None = None,
    ) -> WorkItem:
        work = self.store.update_work_status(work_id, "accepted")
        self.store.append_event(
            ExecutionEvent(
                work_id=work_id,
                event_type="extraction.queued",
                detail={"job_id": job_id, **(detail or {})},
            )
        )
        self.store.save_next_action(
            NextAction(
                work_id=work_id,
                actor="system",
                description="等待灵机提取 Worker 处理",
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
        self.store.save_next_action(
            NextAction(
                work_id=work_id,
                actor="system",
                description="灵机正在处理提取任务",
            )
        )
        return work

    def retry_extraction(
        self,
        work_id: str,
        *,
        detail: dict[str, Any] | None = None,
    ) -> WorkItem:
        work = self.store.update_work_status(work_id, "accepted")
        self.store.append_event(
            ExecutionEvent(
                work_id=work_id,
                event_type="extraction.retrying",
                detail=detail or {},
            )
        )
        self.store.save_next_action(
            NextAction(
                work_id=work_id,
                actor="system",
                description="灵机会自动重试提取任务",
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
                detail={"summary": summary, **({"job_id": evidence.get("job_id")} if evidence and evidence.get("job_id") else {})},
            )
        )
        outcome = Outcome(
            work_id=work_id,
            status="success",
            summary=summary,
            evidence=evidence or {},
        )
        self.store.save_outcome(outcome)
        self.store.save_next_action(
            NextAction(
                work_id=work_id,
                actor="none",
                description="Capture 提取已完成",
            )
        )
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
                detail={"summary": summary, **({"job_id": evidence.get("job_id")} if evidence and evidence.get("job_id") else {})},
            )
        )
        outcome = Outcome(
            work_id=work_id,
            status="failure",
            summary=summary,
            evidence=evidence or {},
        )
        self.store.save_outcome(outcome)
        self.store.save_next_action(
            NextAction(
                work_id=work_id,
                actor="none",
                description="提取失败已记录；无需伪造主人待办",
            )
        )
        return outcome

    def cancel_extraction(
        self,
        work_id: str,
        *,
        job_id: str | None = None,
        summary: str = "Capture 提取已取消",
    ) -> Outcome:
        self.store.append_event(
            ExecutionEvent(
                work_id=work_id,
                event_type="extraction.cancelled",
                detail={"job_id": job_id} if job_id else {},
            )
        )
        outcome = Outcome(
            work_id=work_id,
            status="skipped",
            summary=summary,
            evidence={"job_id": job_id} if job_id else {},
        )
        self.store.save_outcome(outcome)
        self.store.save_next_action(
            NextAction(work_id=work_id, actor="none", description="任务已取消"),
        )
        return outcome
