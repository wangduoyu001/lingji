from __future__ import annotations

from pathlib import Path

import pytest

from src.assistant_hub.imports import AssistantImportPlanner


def test_plan_discovers_supported_exports_without_exposing_paths(tmp_path: Path) -> None:
    home = tmp_path / "owner"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    chatgpt = downloads / "chatgpt-export.zip"
    codex = downloads / "codex-work-report.json"
    chatgpt.write_bytes(b"not-opened-by-planner")
    codex.write_text('{"schema_version": 1}', encoding="utf-8")

    planner = AssistantImportPlanner(
        storage_path=tmp_path / "storage",
        home=home,
        env={"USERPROFILE": str(home)},
    )
    payload = planner.plan()

    assert payload["safety"]["metadata_only"] is True
    assert payload["safety"]["content_read"] is False
    assert payload["summary"]["candidate_count"] == 2

    sources = {item["id"]: item for item in payload["sources"]}
    assert sources["chatgpt"]["state"] == "candidate_ready"
    assert sources["codex"]["state"] == "candidate_ready"
    assert sources["chatgpt"]["owner_action_count"] == 1
    assert sources["codex"]["owner_action_count"] == 1

    all_candidates = [
        candidate
        for source in payload["sources"]
        for candidate in source["candidates"]
    ]
    assert {item["display_name"] for item in all_candidates} == {
        "chatgpt-export.zip",
        "codex-work-report.json",
    }
    assert all("input_path" not in item for item in all_candidates)
    assert all(str(tmp_path) not in str(item) for item in all_candidates)


def test_plan_returns_one_guided_action_when_no_export_exists(tmp_path: Path) -> None:
    home = tmp_path / "owner"
    (home / "Downloads").mkdir(parents=True)
    planner = AssistantImportPlanner(storage_path=tmp_path / "storage", home=home, env={})

    payload = planner.plan()
    sources = {item["id"]: item for item in payload["sources"]}

    assert sources["chatgpt"]["state"] == "guided_action_required"
    assert sources["chatgpt"]["owner_action_count"] == 1
    assert "选择官方导出包并立即导入" in sources["chatgpt"]["primary_action"]
    assert sources["codex"]["state"] == "guided_action_required"
    assert sources["claude_code"]["state"] == "not_supported"
    assert sources["workbuddy"]["state"] == "not_supported"


def test_explicit_empty_environment_does_not_scan_host_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = tmp_path / "owner"
    host_profile = tmp_path / "host-profile"
    host_downloads = host_profile / "Downloads"
    host_downloads.mkdir(parents=True)
    (host_downloads / "chatgpt-export.zip").write_bytes(b"must-not-be-discovered")
    monkeypatch.setenv("USERPROFILE", str(host_profile))

    planner = AssistantImportPlanner(storage_path=tmp_path / "storage", home=owner, env={})

    assert planner.plan()["summary"]["candidate_count"] == 0


def test_authorized_candidate_is_resolved_only_from_fresh_allowlist(tmp_path: Path) -> None:
    home = tmp_path / "owner"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    export = downloads / "chatgpt-export.zip"
    export.write_bytes(b"payload")
    planner = AssistantImportPlanner(storage_path=tmp_path / "storage", home=home, env={})

    candidate = planner.plan()["sources"][0]["candidates"][0]
    selected = planner.resolve_authorized_candidate(candidate["candidate_id"])

    assert selected["source_id"] == "chatgpt"
    assert selected["adapter_name"] == "chatgpt_export"
    assert Path(selected["input_path"]) == export.resolve()
    assert planner.expected_confirmation(candidate["candidate_id"]).startswith(
        "AUTHORIZE_ASSISTANT_IMPORT_"
    )

    export.unlink()
    with pytest.raises(ValueError, match="no longer available"):
        planner.resolve_authorized_candidate(candidate["candidate_id"])


def test_unrelated_files_are_not_candidates(tmp_path: Path) -> None:
    home = tmp_path / "owner"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    (downloads / "private-notes.json").write_text("{}", encoding="utf-8")
    (downloads / "random.zip").write_bytes(b"zip")
    (downloads / "codex-session.jsonl").write_text("{}", encoding="utf-8")

    planner = AssistantImportPlanner(storage_path=tmp_path / "storage", home=home, env={})
    assert planner.plan()["summary"]["candidate_count"] == 0
