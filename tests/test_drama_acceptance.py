from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.plugins.drama_intelligence.acceptance import (
    DramaAcceptanceError,
    load_acceptance_questions,
    run_acceptance,
    write_acceptance_report,
)


class _AcceptanceService:
    workspace = "acceptance"

    def status(self):
        return {
            "workspace": self.workspace,
            "structured": {"dramas": 10, "revision": 7},
            "semantic": {"state": "ready", "collection": "lingji_drama_acceptance"},
        }

    def search(self, query, *, limit=10, drama_id=None, chunk_type=None):
        if "继承人" in query:
            return {
                "results": [
                    {
                        "chunk_id": "chunk-1",
                        "drama_id": "drama-1",
                        "drama_title": "身份反转",
                        "source_ref": "drama-1:e001:s002:p001",
                        "text": "林晚在董事会上公开继承人身份。",
                        "heading": "第二场 董事会",
                        "characters": ["林晚", "赵明"],
                        "episode_number": 1,
                        "citation": {
                            "source_ref": "drama-1:e001:s002:p001",
                            "normalized_path": "acceptance/derived/drama/full_text.md",
                            "source_locator": {"locator": "line:20..line:24"},
                        },
                    }
                ],
                "warnings": [],
            }
        return {
            "results": [],
            "warnings": [{"code": "semantic_unavailable", "message": "test fallback"}],
        }


def test_owner_data_acceptance_scores_gates_and_writes_evidence(tmp_path: Path) -> None:
    dataset = tmp_path / "questions.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "q001",
                        "query": "谁公开了继承人身份",
                        "expected": {
                            "contains_all": ["继承人", "公开"],
                            "characters": ["林晚"],
                            "episode_numbers": [1],
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "id": "q002",
                        "query": "不存在的桥段",
                        "expected": {
                            "contains_any": ["不存在"],
                            "characters": ["赵明"],
                            "episode_numbers": [2],
                        },
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    questions = load_acceptance_questions(dataset)
    report = run_acceptance(
        _AcceptanceService(),
        questions,
        minimum_dramas=10,
        minimum_questions=2,
        retrieval_target=0.50,
        character_target=0.50,
        episode_target=0.50,
    )

    assert report["overall_pass"] is True
    assert report["dataset"]["question_count"] == 2
    assert report["dataset"]["character_labeled"] == 2
    assert report["metrics"]["retrieval_accuracy"] == 0.5
    assert report["metrics"]["top1_accuracy"] == 0.5
    assert report["metrics"]["citation_accuracy"] == 0.5
    assert report["metrics"]["character_accuracy"] == 0.5
    assert report["metrics"]["episode_event_accuracy"] == 0.5
    assert report["questions"][0]["matched_source_ref"] == "drama-1:e001:s002:p001"
    assert report["questions"][1]["warning_codes"] == ["semantic_unavailable"]

    paths = write_acceptance_report(report, tmp_path / "reports")
    json_report = Path(paths["json"])
    markdown_report = Path(paths["markdown"])
    assert json_report.is_file()
    assert markdown_report.is_file()
    assert json.loads(json_report.read_text(encoding="utf-8"))["overall_pass"] is True
    assert "Drama Memory Owner-Data Acceptance" in markdown_report.read_text(encoding="utf-8")


def test_acceptance_dataset_rejects_unscorable_questions(tmp_path: Path) -> None:
    dataset = tmp_path / "bad.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "q001",
                "query": "谁是女主",
                "expected": {"characters": ["林晚"]},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(DramaAcceptanceError, match="retrieval label"):
        load_acceptance_questions(dataset)
