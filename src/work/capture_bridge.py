from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from .models import ExecutionEvent, Failure, NextAction, Outcome, PendingAction, WorkItem
from .store import WorkStore, normalize_failure_reason


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
        self.store.apply_extraction_transition(
            work_id,
            "completed",
            summary=summary,
            evidence=outcome.evidence,
            occurred_at=outcome.created_at,
        )
        return outcome

    def record_failure(
        self,
        work_id: str,
        *,
        stage: str,
        reason: str,
        retryable: bool = False,
        evidence: dict[str, Any] | None = None,
        file_failures: Sequence[Mapping[str, Any]] | None = None,
    ) -> Failure:
        failure = Failure(work_id=work_id, failure_id=f"failure:{work_id}:{stage}", stage=stage, reason=reason, retryable=retryable)
        transition_evidence = {"stage": stage, **(evidence or {})}
        self._record_aggregated_failures(work_id, stage=stage, reason=reason, retryable=retryable, file_failures=file_failures or ())
        self.store.apply_extraction_transition(
            work_id,
            "failed",
            summary=reason,
            evidence=transition_evidence,
            stage=stage,
            retryable=retryable,
            occurred_at=failure.created_at,
            skip_failure_record=True,
        )
        return failure

    def _record_aggregated_failures(
        self,
        work_id: str,
        *,
        stage: str,
        reason: str,
        retryable: bool,
        file_failures: Sequence[Mapping[str, Any]],
    ) -> None:
        """Group per-file errors by reason fingerprint so one persistent fault stays one row."""
        groups: dict[str, dict[str, Any]] = {}
        for item in file_failures:
            entry = item if isinstance(item, Mapping) else {}
            error = str(entry.get("error") or "").strip()
            path = str(entry.get("relative_path") or "").strip()
            job_id = str(entry.get("job_id") or "").strip()
            attempts = entry.get("attempts")
            normalized = normalize_failure_reason(error) if error else normalize_failure_reason(reason)
            group = groups.setdefault(
                normalized,
                {"reason": error or reason, "files": [], "job_ids": [], "attempts": 0},
            )
            if error and not str(group["reason"]).strip():
                group["reason"] = error
            if path and path not in group["files"]:
                group["files"].append(path)
            if job_id and job_id not in group["job_ids"]:
                group["job_ids"].append(job_id)
            try:
                group["attempts"] = max(int(group["attempts"] or 0), int(attempts or 0))
            except (TypeError, ValueError):
                pass
        if not groups:
            self.store.record_source_failure(work_id, stage=stage, reason=reason, retryable=retryable)
            return
        # 有界写入：单次调用最多落 5 条原因指纹，最大组优先，防止错误种类爆炸。
        ordered = sorted(groups.values(), key=lambda group: (-len(group["files"]), str(group["reason"])))
        for group in ordered[:5]:
            self.store.record_source_failure(
                work_id,
                stage=stage,
                reason=str(group["reason"])[:2000],
                retryable=retryable,
                files=group["files"][:10],
                job_ids=group["job_ids"][:10],
                raw_error=str(group["reason"])[:500],
                attempts=group["attempts"],
            )

    def retry(self, work_id: str) -> None:
        self.store.apply_extraction_transition(
            work_id,
            "retrying",
            summary="重新执行失败阶段",
            evidence={"actor": "system"},
            occurred_at=datetime.now().isoformat(timespec="microseconds"),
        )
