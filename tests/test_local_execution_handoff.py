from __future__ import annotations

import pytest

from scripts.check_local_execution_handoff import HandoffError, validate_result, validate_task


TASK = {
    "task_id": "TASK-1",
    "status": "ACTIVE",
    "execution_mode": "DAY0_THEN_REAL_DATA_TRIAL",
    "repository": "wangduoyu001/lingji",
    "product_pr": "60",
    "product_branch": "feature/example",
    "product_commit": "a" * 40,
    "artifact_name": "artifact",
    "artifact_id": "1",
    "trial_protocol_path": "docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md",
    "report_branch": "acceptance/task-1",
    "report_path": "docs/TEST_REPORTS/TASK_1.md",
    "public_summary_path": "docs/TEST_REPORTS/evidence/TASK_1.json",
    "public_hashes_path": "docs/TEST_REPORTS/evidence/TASK_1.txt",
    "result_receipt_path": "docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md",
    "day0_required": True,
    "real_data_requires_day0_pass": True,
    "real_data_authorization_required": True,
    "minimum_quality_questions": "20",
    "minimum_owner_sample_questions": "10",
    "minimum_quality_score_percent": "90",
    "minimum_source_accuracy_percent": "95",
    "maximum_false_positive_percent": "5",
    "cleanup_before_required": True,
    "cleanup_after_required": True,
    "remote_verification_required": True,
    "owner_confirmation_required": True,
}

IDLE_TASK = {
    "task_id": "NONE",
    "status": "IDLE",
    "repository": "wangduoyu001/lingji",
    "product_pr": "88",
    "product_branch": "feature/owner-autopilot-ui-codexpp",
    "local_execution_allowed": False,
}

IDLE_RESULT = {
    "task_id": "NONE",
    "status": "IDLE",
    "verdict": "NOT_RUN",
    "repository": "wangduoyu001/lingji",
    "product_pr": "88",
}


def pending_result() -> dict[str, object]:
    return {
        "task_id": "TASK-1",
        "status": "PENDING",
        "verdict": "PENDING",
        "execution_mode": "DAY0_THEN_REAL_DATA_TRIAL",
        "repository": "wangduoyu001/lingji",
        "product_pr": "60",
        "product_commit": "a" * 40,
        "task_instruction_commit": "PENDING",
        "trial_protocol_path": "docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md",
        "report_branch": "acceptance/task-1",
        "report_commit": "PENDING",
        "report_path": "docs/TEST_REPORTS/TASK_1.md",
        "public_summary_path": "docs/TEST_REPORTS/evidence/TASK_1.json",
        "public_hashes_path": "docs/TEST_REPORTS/evidence/TASK_1.txt",
        "day0_result": "NOT_RUN",
        "stage1_result": "NOT_RUN",
        "stage2_result": "NOT_RUN",
        "real_data_authorized": False,
        "quality_questions_total": "0",
        "owner_sample_questions": "0",
        "quality_score_percent": "NOT_RUN",
        "source_accuracy_percent": "NOT_RUN",
        "false_positive_percent": "NOT_RUN",
        "codex_mcp_success_percent": "NOT_RUN",
        "duplicate_formal_content_count": "NOT_RUN",
        "production_pollution_count": "NOT_RUN",
        "owner_config_preserved": "PENDING",
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


def completed_pass_result() -> dict[str, object]:
    result = pending_result()
    result.update(
        {
            "status": "COMPLETED",
            "verdict": "PASS",
            "task_instruction_commit": "b" * 40,
            "report_commit": "c" * 40,
            "day0_result": "PASS",
            "stage1_result": "PASS",
            "stage2_result": "PASS",
            "real_data_authorized": True,
            "quality_questions_total": "20",
            "owner_sample_questions": "10",
            "quality_score_percent": "90",
            "source_accuracy_percent": "95",
            "false_positive_percent": "5",
            "codex_mcp_success_percent": "95",
            "duplicate_formal_content_count": "0",
            "production_pollution_count": "0",
            "owner_config_preserved": "PASS",
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


def test_idle_task_and_result_are_valid_without_artifact_identity() -> None:
    validate_task(dict(IDLE_TASK))
    validate_result(dict(IDLE_TASK), dict(IDLE_RESULT))


def test_idle_task_cannot_allow_local_execution() -> None:
    task = dict(IDLE_TASK)
    task["local_execution_allowed"] = True
    with pytest.raises(HandoffError):
        validate_task(task)


@pytest.mark.parametrize(
    ("field", "value"),
    [("task_id", "STALE-TASK"), ("status", "ACTIVE")],
)
def test_idle_task_identity_cannot_be_runnable(field: str, value: object) -> None:
    task = dict(IDLE_TASK)
    task[field] = value
    with pytest.raises(HandoffError):
        validate_task(task)


@pytest.mark.parametrize(
    ("field", "value"),
    [("status", "RUNNING"), ("verdict", "PASS")],
)
def test_idle_result_cannot_claim_execution_or_pass(field: str, value: object) -> None:
    result = dict(IDLE_RESULT)
    result[field] = value
    with pytest.raises(HandoffError):
        validate_result(dict(IDLE_TASK), result)


def test_active_trial_task_and_pending_result_are_valid() -> None:
    validate_task(dict(TASK))
    validate_result(dict(TASK), pending_result())


def test_active_task_still_requires_artifact_and_acceptance_fields() -> None:
    task = dict(TASK)
    task.pop("artifact_id")
    with pytest.raises(HandoffError):
        validate_task(task)


def test_completed_trial_pass_requires_all_thresholds_and_hard_gates() -> None:
    validate_result(dict(TASK), completed_pass_result())


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
    result = completed_pass_result()
    result[field] = False
    with pytest.raises(HandoffError):
        validate_result(dict(TASK), result)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quality_questions_total", "19"),
        ("owner_sample_questions", "9"),
        ("quality_score_percent", "89.9"),
        ("source_accuracy_percent", "94.9"),
        ("false_positive_percent", "5.1"),
        ("codex_mcp_success_percent", "94.9"),
        ("duplicate_formal_content_count", "1"),
        ("production_pollution_count", "1"),
        ("owner_config_preserved", "FAIL"),
    ],
)
def test_trial_pass_rejects_quality_or_safety_threshold_failure(field: str, value: str) -> None:
    result = completed_pass_result()
    result[field] = value
    with pytest.raises(HandoffError):
        validate_result(dict(TASK), result)


def test_real_data_cannot_start_before_day0_passes() -> None:
    result = pending_result()
    result.update(
        {
            "status": "RUNNING",
            "day0_result": "FAIL",
            "stage1_result": "PASS",
            "real_data_authorized": True,
        }
    )
    with pytest.raises(HandoffError):
        validate_result(dict(TASK), result)


def test_fail_report_may_stop_after_day0_without_real_data() -> None:
    result = pending_result()
    result.update(
        {
            "status": "COMPLETED",
            "verdict": "FAIL",
            "task_instruction_commit": "b" * 40,
            "report_commit": "c" * 40,
            "day0_result": "FAIL",
            "cleanup_before": "PASS",
            "cleanup_after": "PASS",
            "remote_branch_verified": True,
            "remote_commit_verified": True,
            "remote_report_verified": True,
            "remote_result_verified": True,
            "pr_comment_verified": True,
            "local_temp_root_absent": True,
            "owner_observation": "FAIL",
            "started_at": "2026-07-30T00:00:00+08:00",
            "finished_at": "2026-07-30T01:00:00+08:00",
        }
    )
    validate_result(dict(TASK), result)


def test_task_and_result_identity_must_match() -> None:
    result = pending_result()
    result["product_commit"] = "d" * 40
    with pytest.raises(HandoffError):
        validate_result(dict(TASK), result)


def test_blocked_submission_requires_blocked_verdict() -> None:
    result = pending_result()
    result.update(
        {
            "status": "BLOCKED_SUBMISSION",
            "verdict": "FAIL",
            "task_instruction_commit": "b" * 40,
        }
    )
    with pytest.raises(HandoffError):
        validate_result(dict(TASK), result)


def test_task_requires_all_hard_gates() -> None:
    task = dict(TASK)
    task["cleanup_after_required"] = False
    with pytest.raises(HandoffError):
        validate_task(task)


def test_trial_task_rejects_weakened_quality_thresholds() -> None:
    task = dict(TASK)
    task["minimum_quality_score_percent"] = "80"
    with pytest.raises(HandoffError):
        validate_task(task)
