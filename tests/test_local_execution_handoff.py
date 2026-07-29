from __future__ import annotations

import pytest

from scripts.check_local_execution_handoff import HandoffError, validate_result, validate_task


TASK = {
    "task_id": "TASK-1",
    "status": "ACTIVE",
    "repository": "wangduoyu001/lingji",
    "product_pr": "60",
    "product_branch": "feature/example",
    "product_commit": "a" * 40,
    "artifact_name": "artifact",
    "artifact_id": "1",
    "report_branch": "acceptance/task-1",
    "report_path": "docs/TEST_REPORTS/TASK_1.md",
    "public_summary_path": "docs/TEST_REPORTS/evidence/TASK_1.json",
    "public_hashes_path": "docs/TEST_REPORTS/evidence/TASK_1.txt",
    "result_receipt_path": "docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md",
    "cleanup_before_required": True,
    "cleanup_after_required": True,
    "remote_verification_required": True,
    "owner_confirmation_required": True,
}


def pending_result() -> dict[str, object]:
    return {
        "task_id": "TASK-1",
        "status": "PENDING",
        "verdict": "PENDING",
        "repository": "wangduoyu001/lingji",
        "product_pr": "60",
        "product_commit": "a" * 40,
        "task_instruction_commit": "b" * 40,
        "report_branch": "acceptance/task-1",
        "report_commit": "PENDING",
        "report_path": "docs/TEST_REPORTS/TASK_1.md",
        "public_summary_path": "docs/TEST_REPORTS/evidence/TASK_1.json",
        "public_hashes_path": "docs/TEST_REPORTS/evidence/TASK_1.txt",
        "cleanup_before": "NOT_RUN",
        "cleanup_after": "NOT_RUN",
        "remote_branch_verified": False,
        "remote_commit_verified": False,
        "remote_report_verified": False,
        "remote_result_verified": False,
        "pr_comment_verified": False,
        "local_temp_root_absent": False,
        "owner_observation": "PENDING",
        "started_at": "PENDING",
        "finished_at": "PENDING",
    }


def completed_result() -> dict[str, object]:
    result = pending_result()
    result.update(
        {
            "status": "COMPLETED",
            "verdict": "PASS",
            "report_commit": "c" * 40,
            "cleanup_before": "PASS",
            "cleanup_after": "PASS",
            "remote_branch_verified": True,
            "remote_commit_verified": True,
            "remote_report_verified": True,
            "remote_result_verified": True,
            "pr_comment_verified": True,
            "local_temp_root_absent": True,
            "owner_observation": "PASS",
            "started_at": "2026-07-30T00:00:00+08:00",
            "finished_at": "2026-07-30T01:00:00+08:00",
        }
    )
    return result


def test_active_task_and_pending_result_are_valid() -> None:
    validate_task(dict(TASK))
    validate_result(dict(TASK), pending_result())


def test_completed_result_requires_all_remote_checks_and_cleanup() -> None:
    validate_result(dict(TASK), completed_result())


@pytest.mark.parametrize(
    "field",
    [
        "remote_branch_verified",
        "remote_commit_verified",
        "remote_report_verified",
        "remote_result_verified",
        "pr_comment_verified",
        "local_temp_root_absent",
    ],
)
def test_completed_result_rejects_missing_remote_or_cleanup_proof(field: str) -> None:
    result = completed_result()
    result[field] = False
    with pytest.raises(HandoffError):
        validate_result(dict(TASK), result)


def test_completed_result_rejects_unfinished_cleanup() -> None:
    result = completed_result()
    result["cleanup_after"] = "FAIL"
    with pytest.raises(HandoffError):
        validate_result(dict(TASK), result)


def test_task_and_result_identity_must_match() -> None:
    result = pending_result()
    result["product_commit"] = "d" * 40
    with pytest.raises(HandoffError):
        validate_result(dict(TASK), result)


def test_blocked_submission_requires_blocked_verdict() -> None:
    result = pending_result()
    result.update({"status": "BLOCKED_SUBMISSION", "verdict": "FAIL"})
    with pytest.raises(HandoffError):
        validate_result(dict(TASK), result)


def test_task_requires_all_hard_gates() -> None:
    task = dict(TASK)
    task["cleanup_after_required"] = False
    with pytest.raises(HandoffError):
        validate_task(task)
