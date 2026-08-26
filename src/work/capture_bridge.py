from __future__ import annotations

from typing import Any

from .models import ExecutionEvent, Failure, NextAction, Outcome, PendingAction, WorkItem
from .store import WorkStore


class CaptureWorkBridge:
    """Turns successful capture submissions into traceable work facts."""

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
        existing = self.store.get_work_by_source_id(source_id or capture_id)
        if existing:
            return existing
        work = WorkItem(
            title=title or f"Capture {capture_id}",
            source_id=source_id or capture_id,
            owner_approved=approved,
            status="accepted" if approved else "pending",
        )
        work = self.store.create_work(work)
        self.store.append_event(
            ExecutionEvent(
                work_id=work.work_id,
                event_id=f"capture:{capture_id}:accepted",
                event_type="capture.accepted",
                detail={"capture_id": capture_id, "metadata": metadata or {}},
            )
        )
        if not approved:
            self.store.add_pending_action(PendingAction(action_id=f"owner-confirm:{capture_id}", work_id=work.work_id, description="确认是否将这条输入加入长期记忆", actor="owner"))
            self.store.save_next_action(NextAction(work_id=work.work_id, action_id=f"owner-confirm:{capture_id}", description="等待主人确认", actor="owner"))
        return work

    def complete_extraction(
        self,
        work_id: str,
        summary: str,
        *,
        evidence: dict[str, Any] | None = None,
    ) -> Outcome:
        outcome = Outcome(
            work_id=work_id,
            status="completed",
            summary=summary,
            evidence=evidence or {},
        )
        self.store.save_outcome(outcome)
        self.store.append_event(
            ExecutionEvent(
                work_id=work_id,
                event_id=f"work:{work_id}:extraction.completed",
                event_type="extraction.completed",
                detail={"summary": summary},
            )
        )
        self.store.save_next_action(NextAction(work_id=work_id, action_id=f"next:{work_id}:completed", description="系统继续维护可检索记忆", actor="system"))
        return outcome

    def record_failure(self, work_id: str, *, stage: str, reason: str, retryable: bool = False) -> Failure:
        failure = Failure(work_id=work_id, failure_id=f"failure:{work_id}:{stage}", stage=stage, reason=reason, retryable=retryable)
        self.store.save_failure(failure)
        self.store.save_outcome(Outcome(work_id=work_id, status="failed", summary=reason, evidence={"stage": stage}, created_at=failure.created_at))
        self.store.append_event(ExecutionEvent(work_id=work_id, event_id=f"work:{work_id}:failed:{stage}", event_type="work.failed", detail={"stage": stage, "reason": reason, "retryable": retryable}, created_at=failure.created_at))
        phase = "retrying" if retryable else "failed"
        self.store.save_next_action(NextAction(work_id=work_id, action_id=f"next:{work_id}:{phase}", description="重试处理" if retryable else "等待主人查看失败原因", actor="system" if retryable else "owner"))
        return failure

    def retry(self, work_id: str) -> None:
        self.store.append_event(ExecutionEvent(work_id=work_id, event_id=f"work:{work_id}:retrying", event_type="work.retrying", detail={"actor": "system"}))
        self.store.save_next_action(NextAction(work_id=work_id, action_id=f"next:{work_id}:retrying", description="重新执行失败阶段", actor="system"))
