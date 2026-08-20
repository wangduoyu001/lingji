#!/usr/bin/env python3
"""Validate the repository-authoritative local execution handoff documents."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = ROOT / "docs" / "ACCEPTANCE" / "LOCAL_EXECUTION_TASK.md"
RESULT_PATH = ROOT / "docs" / "ACCEPTANCE" / "LOCAL_EXECUTION_RESULT.md"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
ISO_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
TRIAL_MODE = "DAY0_THEN_REAL_DATA_TRIAL"
STAGE_RESULTS = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}


class HandoffError(ValueError):
    """Raised when the local execution handoff is invalid."""


def _parse_scalar(raw: str) -> str | bool:
    value = raw.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def parse_yaml_block(path: Path) -> dict[str, str | bool]:
    if not path.is_file():
        raise HandoffError(f"missing handoff document: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```yaml\s*\n(.*?)\n```", text, flags=re.DOTALL)
    if not match:
        raise HandoffError(f"missing first yaml block: {path.relative_to(ROOT)}")

    values: dict[str, str | bool] = {}
    for line_number, raw_line in enumerate(match.group(1).splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise HandoffError(
                f"invalid yaml-like line {line_number} in {path.relative_to(ROOT)}: {raw_line}"
            )
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key or key in values:
            raise HandoffError(f"invalid or duplicate key {key!r} in {path.relative_to(ROOT)}")
        values[key] = _parse_scalar(raw_value)
    return values


def require_fields(name: str, values: dict[str, object], fields: set[str]) -> None:
    missing = sorted(fields - values.keys())
    if missing:
        raise HandoffError(f"{name} missing fields: {', '.join(missing)}")


def expect_equal(field: str, task: dict[str, object], result: dict[str, object]) -> None:
    if task[field] != result[field]:
        raise HandoffError(
            f"task/result mismatch for {field}: {task[field]!r} != {result[field]!r}"
        )


def as_int(values: dict[str, object], field: str) -> int:
    try:
        return int(str(values[field]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HandoffError(f"{field} must be an integer") from exc


def as_float(values: dict[str, object], field: str) -> float:
    try:
        return float(str(values[field]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HandoffError(f"{field} must be numeric") from exc


def validate_trial_task(task: dict[str, object]) -> None:
    required = {
        "trial_protocol_path",
        "day0_required",
        "real_data_requires_day0_pass",
        "real_data_authorization_required",
        "minimum_quality_questions",
        "minimum_owner_sample_questions",
        "minimum_quality_score_percent",
        "minimum_source_accuracy_percent",
        "maximum_false_positive_percent",
    }
    require_fields("trial task", task, required)
    for field in (
        "day0_required",
        "real_data_requires_day0_pass",
        "real_data_authorization_required",
    ):
        if task[field] is not True:
            raise HandoffError(f"trial task {field} must be true")

    protocol = ROOT / str(task["trial_protocol_path"])
    if not protocol.is_file():
        raise HandoffError(f"missing trial protocol: {task['trial_protocol_path']}")
    if as_int(task, "minimum_quality_questions") < 20:
        raise HandoffError("minimum_quality_questions must be at least 20")
    if as_int(task, "minimum_owner_sample_questions") < 10:
        raise HandoffError("minimum_owner_sample_questions must be at least 10")
    if as_float(task, "minimum_quality_score_percent") < 90:
        raise HandoffError("minimum_quality_score_percent must be at least 90")
    if as_float(task, "minimum_source_accuracy_percent") < 95:
        raise HandoffError("minimum_source_accuracy_percent must be at least 95")
    if as_float(task, "maximum_false_positive_percent") > 5:
        raise HandoffError("maximum_false_positive_percent must be at most 5")


def validate_task(task: dict[str, object]) -> None:
    common = {
        "task_id",
        "status",
        "repository",
        "product_pr",
        "product_branch",
    }
    require_fields("task", task, common)
    if task["status"] not in {"ACTIVE", "IDLE"}:
        raise HandoffError("task status must be ACTIVE or IDLE")

    if task["status"] == "IDLE":
        require_fields("idle task", task, {"local_execution_allowed"})
        if task["task_id"] != "NONE":
            raise HandoffError("IDLE task_id must be NONE")
        if task["local_execution_allowed"] is not False:
            raise HandoffError("IDLE task must set local_execution_allowed: false")
        return

    required = {
        "execution_mode",
        "product_commit",
        "artifact_name",
        "artifact_id",
        "report_branch",
        "report_path",
        "public_summary_path",
        "public_hashes_path",
        "result_receipt_path",
        "cleanup_before_required",
        "cleanup_after_required",
        "remote_verification_required",
        "owner_confirmation_required",
    }
    require_fields("active task", task, required)
    if not isinstance(task["product_commit"], str) or not SHA40.fullmatch(task["product_commit"]):
        raise HandoffError("task product_commit must be a lowercase 40-character SHA")
    for field in (
        "cleanup_before_required",
        "cleanup_after_required",
        "remote_verification_required",
        "owner_confirmation_required",
    ):
        if task[field] is not True:
            raise HandoffError(f"task {field} must be true")
    if task["result_receipt_path"] != "docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md":
        raise HandoffError("task result_receipt_path must use the canonical result receipt")
    if not str(task["report_branch"]).startswith("acceptance/"):
        raise HandoffError("task report_branch must start with acceptance/")
    if not str(task["report_path"]).startswith("docs/TEST_REPORTS/"):
        raise HandoffError("task report_path must be under docs/TEST_REPORTS/")
    if task["execution_mode"] == TRIAL_MODE:
        validate_trial_task(task)


def validate_trial_result(task: dict[str, object], result: dict[str, object]) -> None:
    required = {
        "trial_protocol_path",
        "day0_result",
        "stage1_result",
        "stage2_result",
        "real_data_authorized",
        "quality_questions_total",
        "owner_sample_questions",
        "quality_score_percent",
        "source_accuracy_percent",
        "false_positive_percent",
        "codex_mcp_success_percent",
        "duplicate_formal_content_count",
        "production_pollution_count",
        "owner_config_preserved",
    }
    require_fields("trial result", result, required)
    expect_equal("trial_protocol_path", task, result)

    for field in ("day0_result", "stage1_result", "stage2_result"):
        if result[field] not in STAGE_RESULTS:
            raise HandoffError(f"{field} has invalid result {result[field]!r}")

    if result["day0_result"] != "PASS":
        if result["stage1_result"] != "NOT_RUN" or result["stage2_result"] != "NOT_RUN":
            raise HandoffError("Stage 1/2 must remain NOT_RUN until Day 0 passes")
        if result["real_data_authorized"] is True:
            raise HandoffError("real data cannot be authorized before Day 0 passes")

    if result["status"] in {"PENDING", "RUNNING"}:
        return

    if result["verdict"] == "PASS":
        if result["day0_result"] != "PASS" or result["stage1_result"] != "PASS":
            raise HandoffError("PASS requires Day 0 and Stage 1 PASS")
        if result["real_data_authorized"] is not True:
            raise HandoffError("PASS requires explicit real-data authorization")
        if as_int(result, "quality_questions_total") < as_int(task, "minimum_quality_questions"):
            raise HandoffError("PASS requires enough quality questions")
        if as_int(result, "owner_sample_questions") < as_int(task, "minimum_owner_sample_questions"):
            raise HandoffError("PASS requires enough owner-sampled questions")
        if as_float(result, "quality_score_percent") < as_float(task, "minimum_quality_score_percent"):
            raise HandoffError("PASS quality_score_percent is below threshold")
        if as_float(result, "source_accuracy_percent") < as_float(
            task, "minimum_source_accuracy_percent"
        ):
            raise HandoffError("PASS source_accuracy_percent is below threshold")
        if as_float(result, "false_positive_percent") > as_float(
            task, "maximum_false_positive_percent"
        ):
            raise HandoffError("PASS false_positive_percent exceeds threshold")
        if as_float(result, "codex_mcp_success_percent") < 95:
            raise HandoffError("PASS requires codex_mcp_success_percent >= 95")
        if as_int(result, "duplicate_formal_content_count") != 0:
            raise HandoffError("PASS requires zero duplicate formal content")
        if as_int(result, "production_pollution_count") != 0:
            raise HandoffError("PASS requires zero Production pollution")
        if result["owner_config_preserved"] != "PASS":
            raise HandoffError("PASS requires owner_config_preserved PASS")


def validate_result(task: dict[str, object], result: dict[str, object]) -> None:
    if task.get("status") == "IDLE":
        required = {
            "task_id",
            "status",
            "verdict",
            "repository",
            "product_pr",
        }
        require_fields("idle result", result, required)
        for field in ("task_id", "repository", "product_pr"):
            expect_equal(field, task, result)
        if result["status"] != "IDLE":
            raise HandoffError("IDLE task requires result status IDLE")
        if result["verdict"] != "NOT_RUN":
            raise HandoffError("IDLE task requires result verdict NOT_RUN")
        return

    required = {
        "task_id",
        "status",
        "verdict",
        "execution_mode",
        "repository",
        "product_pr",
        "product_commit",
        "task_instruction_commit",
        "report_branch",
        "report_commit",
        "report_path",
        "public_summary_path",
        "public_hashes_path",
        "cleanup_before",
        "cleanup_after",
        "remote_branch_verified",
        "remote_commit_verified",
        "remote_report_verified",
        "remote_result_verified",
        "pr_comment_verified",
        "local_temp_root_absent",
        "owner_observation",
        "started_at",
        "finished_at",
    }
    require_fields("result", result, required)
    if result["status"] not in {"PENDING", "RUNNING", "COMPLETED", "BLOCKED_SUBMISSION"}:
        raise HandoffError("result status is invalid")
    if result["verdict"] not in {"PENDING", "PASS", "FAIL", "BLOCKED"}:
        raise HandoffError("result verdict is invalid")

    for field in (
        "task_id",
        "execution_mode",
        "repository",
        "product_pr",
        "product_commit",
        "report_branch",
        "report_path",
        "public_summary_path",
        "public_hashes_path",
    ):
        expect_equal(field, task, result)

    instruction_commit = result["task_instruction_commit"]
    if result["status"] in {"PENDING", "RUNNING"}:
        if instruction_commit != "PENDING" and (
            not isinstance(instruction_commit, str) or not SHA40.fullmatch(instruction_commit)
        ):
            raise HandoffError("pending task_instruction_commit must be PENDING or a 40-character SHA")
    elif not isinstance(instruction_commit, str) or not SHA40.fullmatch(instruction_commit):
        raise HandoffError("final result requires a lowercase 40-character task_instruction_commit")

    if task["execution_mode"] == TRIAL_MODE:
        validate_trial_result(task, result)

    if result["status"] in {"PENDING", "RUNNING"}:
        return
    if result["verdict"] == "PENDING":
        raise HandoffError("final result cannot keep verdict PENDING")
    if result["status"] == "BLOCKED_SUBMISSION":
        if result["verdict"] != "BLOCKED":
            raise HandoffError("BLOCKED_SUBMISSION requires verdict BLOCKED")
        return

    report_commit = result["report_commit"]
    if not isinstance(report_commit, str) or not SHA40.fullmatch(report_commit):
        raise HandoffError("COMPLETED result requires the pushed report-content commit SHA")
    if result["cleanup_before"] != "PASS" or result["cleanup_after"] != "PASS":
        raise HandoffError("COMPLETED result requires cleanup_before and cleanup_after PASS")
    for field in (
        "remote_branch_verified",
        "remote_commit_verified",
        "remote_report_verified",
        "remote_result_verified",
        "pr_comment_verified",
        "local_temp_root_absent",
    ):
        if result[field] is not True:
            raise HandoffError(f"COMPLETED result requires {field}: true")
    if result["owner_observation"] not in {"PASS", "FAIL", "NOT_REQUIRED"}:
        raise HandoffError("COMPLETED result requires owner_observation PASS, FAIL or NOT_REQUIRED")
    for field in ("started_at", "finished_at"):
        value = result[field]
        if not isinstance(value, str) or not ISO_TIME.fullmatch(value):
            raise HandoffError(f"COMPLETED result requires ISO 8601 {field} with timezone")


def validate(ref_name: str | None = None) -> None:
    task = parse_yaml_block(TASK_PATH)
    result = parse_yaml_block(RESULT_PATH)
    validate_task(task)
    validate_result(task, result)

    if ref_name and ref_name.startswith("acceptance/"):
        if task["status"] != "ACTIVE" or result["status"] != "COMPLETED":
            raise HandoffError(
                "acceptance/* branch requires an ACTIVE task with LOCAL_EXECUTION_RESULT status COMPLETED"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref-name", default=None)
    args = parser.parse_args()
    try:
        validate(args.ref_name)
    except HandoffError as exc:
        print(f"LOCAL_EXECUTION_HANDOFF: FAIL\n{exc}", file=sys.stderr)
        return 1
    print("LOCAL_EXECUTION_HANDOFF: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
