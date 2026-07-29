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


def validate_task(task: dict[str, object]) -> None:
    required = {
        "task_id",
        "status",
        "repository",
        "product_pr",
        "product_branch",
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
    require_fields("task", task, required)
    if task["status"] not in {"ACTIVE", "IDLE"}:
        raise HandoffError("task status must be ACTIVE or IDLE")
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


def validate_result(task: dict[str, object], result: dict[str, object]) -> None:
    required = {
        "task_id",
        "status",
        "verdict",
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
    if not isinstance(instruction_commit, str) or not SHA40.fullmatch(instruction_commit):
        raise HandoffError("result task_instruction_commit must be a lowercase 40-character SHA")

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

    if ref_name and ref_name.startswith("acceptance/") and result["status"] != "COMPLETED":
        raise HandoffError(
            "acceptance/* branch must end with LOCAL_EXECUTION_RESULT status COMPLETED"
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
