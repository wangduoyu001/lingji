from __future__ import annotations

import json

import requests


BASE = "http://127.0.0.1:8765"


def post(path: str, payload: dict) -> dict:
    response = requests.post(f"{BASE}{path}", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


conversation = {
    "conversation_id": "acceptance-second-brain-isolation-v1",
    "source": "codex_acceptance",
    "title": "Second-brain isolation acceptance",
    "project": "lingji",
    "messages": [
        {
            "role": "user",
            "content": "最终决定：第二大脑使用独立分支和D盘并行目录。必须保持原灵机启动链路不变。",
        }
    ],
}

first = post("/memory/import", {"conversation": conversation, "distill": True})
second = post("/memory/import", {"conversation": conversation, "distill": True})
candidates = first["results"][0].get("memory_candidates", [])
approved = post("/memory/approve", {"memory_id": candidates[0]["id"], "reason": "acceptance verification"}) if candidates else None
search = post("/memory/search", {"query": "第二大脑独立分支", "project": "lingji", "top_k": 5})
context = post("/memory/context", {"project": "lingji", "task": "继续第二大脑升级", "max_tokens": 1200})
task = post(
    "/memory/codex-task",
    {
        "project": "lingji",
        "request": "Verify isolated second-brain MVP",
        "status": "success",
        "result": "API and isolation checks passed",
        "files_changed": [],
        "tests": ["python -m unittest -v tests.test_second_brain"],
        "lessons": [],
    },
)

print(
    json.dumps(
        {
            "first_imported": first["results"][0]["imported"],
            "second_duplicate": second["results"][0]["duplicate"],
            "approved_status": approved["memory"]["status"] if approved else None,
            "search_results": len(search["results"]),
            "context_rules": len(context["active_rules"]),
            "codex_task_recorded": task["recorded"],
        },
        ensure_ascii=False,
        indent=2,
    )
)
