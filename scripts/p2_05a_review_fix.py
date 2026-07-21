from __future__ import annotations

import re
from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing contract block: {label}")
    return text.replace(old, new, 1)


def replace_pattern(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"missing contract pattern: {label} ({count})")
    return updated


api_path = "src/control/api.py"
api = read(api_path)
api = replace_once(
    api,
    "class CaptureMediaRequest(CaptureCommonRequest):\n    input_path: str = Field(min_length=1)\n    allow_ocr: bool = False\n    allow_transcription: bool = False\n    extract_keyframes: bool = False\n",
    "class CaptureMediaRequest(CaptureCommonRequest):\n    input_path: str = Field(min_length=1)\n    allow_ocr: bool = False\n    allow_transcription: bool = False\n    extract_keyframes: bool = False\n    extract_audio: bool = False\n",
    "CaptureMediaRequest.extract_audio",
)
write(api_path, api)

capture_path = "src/control/capture.py"
capture = read(capture_path)
capture = replace_once(capture, "import logging\nimport threading\n", "import json\nimport logging\nimport threading\n", "capture json import")
capture = replace_once(
    capture,
    "from pathlib import Path\n",
    "from datetime import datetime, timezone\nfrom pathlib import Path, PureWindowsPath\n",
    "capture datetime/path imports",
)
capture = replace_once(
    capture,
    '                "extract_keyframes": bool(payload.get("extract_keyframes", False)),\n            },',
    '                "extract_keyframes": bool(payload.get("extract_keyframes", False)),\n                "extract_audio": bool(payload.get("extract_audio", False)),\n            },',
    "media extract_audio option",
)

status_block = '''    def status(self) -> dict[str, Any]:
        mode = self._mode().value
        service_status = self.capture_service.status()
        return {
            "capture_mode": mode,
            "mode": _MODE_LABELS[mode],
            "paused": mode == "paused",
            "submitted": int(service_status.get("submitted") or 0),
            "queue": self.queue.stats(),
        }

'''
status_new = '''    def status(self) -> dict[str, Any]:
        mode = self._mode().value
        service_status = self.capture_service.status()
        queue_stats = self.queue.stats()
        return {
            "capture_mode": mode,
            "mode": mode,
            "mode_label": _MODE_LABELS[mode],
            "paused": mode == "paused",
            "worker_state": "available",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "submitted": int(service_status.get("submitted") or 0),
            "queue": queue_stats,
            **{
                status: int(queue_stats.get(status, 0))
                for status in ("queued", "running", "retrying", "completed", "failed", "cancelled")
            },
        }

'''
capture = replace_once(capture, status_block, status_new, "capture status DTO")

capabilities_block = '''    def capabilities(self) -> dict[str, Any]:
        return {
            "capture_mode": self._mode().value,
            "inputs": {name: {"enabled": True, "enqueue_only": True} for name in ("text", "web", "file", "media")},
            "operations": {
                "cancel": ["queued", "retrying"],
                "retry": ["failed", "cancelled"],
                "running_termination": False,
            },
        }

'''
capabilities_new = '''    def capabilities(self) -> dict[str, Any]:
        mode = self._mode().value
        policy = self.capture_service.policy
        heavy_allowed = policy.permits_heavy_media()
        return {
            "capture_mode": mode,
            "state": "paused" if mode == "paused" else "healthy",
            "inputs": {name: {"enabled": True, "enqueue_only": True} for name in ("text", "web", "file", "media")},
            "operations": {
                "cancel": ["queued", "retrying"],
                "retry": ["failed", "cancelled"],
                "running_termination": False,
            },
            "file_modes": ["web_snapshot", "chatgpt_export", "codex_report"],
            "media": {
                "ocr": bool(policy.allow_ocr),
                "transcription": bool(policy.allow_video_transcription),
                "keyframes": heavy_allowed,
                "extract_audio": heavy_allowed,
                "reasons": {} if heavy_allowed else {"low_power": "当前采集策略禁止重媒体处理"},
            },
        }

'''
capture = replace_once(capture, capabilities_block, capabilities_new, "capture capabilities DTO")

capture = replace_once(
    capture,
    '            "file_name": Path(str(row.get("input_path") or "")).name or None,',
    '            "file_name": self._basename(str(row.get("input_path") or "")),',
    "portable job basename",
)

result_helpers_pattern = r'''    @staticmethod\n    def _result_summary\(result: Mapping\[str, Any\]\) -> dict\[str, Any\]:\n.*?        return refs\n'''
result_helpers_new = '''    @staticmethod
    def _basename(value: str) -> str | None:
        if not value:
            return None
        windows_name = PureWindowsPath(value).name
        posix_name = Path(value).name
        return windows_name if "\\\\" in value else posix_name

    @staticmethod
    def _result_summary(result: Mapping[str, Any]) -> str | None:
        allowed = ("execution_id", "source_type", "adapter", "adapter_version", "indexed", "document_count", "memory_count")
        summary = {
            key: result[key]
            for key in allowed
            if key in result and isinstance(result[key], (str, int, float, bool, type(None)))
        }
        return json.dumps(summary, ensure_ascii=False, sort_keys=True) if summary else None

    @staticmethod
    def _result_refs(result: Mapping[str, Any]) -> dict[str, str] | None:
        refs: dict[str, str] = {}
        structured = result.get("structured_read_model")
        containers = (result, structured if isinstance(structured, Mapping) else {})
        for container in containers:
            for key in ("memory_id", "source_id", "conversation_id", "message_id"):
                value = container.get(key)
                if isinstance(value, str) and value:
                    refs[key] = value
        return refs or None
'''
capture = replace_pattern(capture, result_helpers_pattern, result_helpers_new, "result summary/ref helpers")
write(capture_path, capture)

queue_test_path = "tests/test_extraction_queue.py"
queue_test = read(queue_test_path)
queue_test = replace_once(queue_test, "import sqlite3\n", "import sqlite3\nfrom contextlib import closing\n", "closing import")
queue_test = replace_once(
    queue_test,
    '''        with sqlite3.connect(self.db_path) as connection:
            plan = connection.execute(
                "EXPLAIN QUERY PLAN SELECT * FROM extraction_jobs WHERE source_type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                ("web", 2, 1),
            ).fetchall()
''',
    '''        with closing(sqlite3.connect(self.db_path)) as connection:
            with closing(connection.execute(
                "EXPLAIN QUERY PLAN SELECT * FROM extraction_jobs WHERE source_type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                ("web", 2, 1),
            )) as cursor:
                plan = cursor.fetchall()
''',
    "SQLite explicit close",
)
write(queue_test_path, queue_test)

control_test_path = "tests/test_capture_control.py"
control_test = read(control_test_path)
control_test = replace_once(
    control_test,
    '    assert service.status()["mode"] == "PAUSED"\n',
    '    assert service.status()["mode"] == "paused"\n    assert service.status()["mode_label"] == "PAUSED"\n',
    "status mode assertions",
)
write(control_test_path, control_test)

api_test_path = "tests/test_capture_api.py"
api_test = read(api_test_path)
api_test = replace_once(
    api_test,
    '        return {"capture_mode": "paused" if self.paused else "low_power", "paused": self.paused}\n',
    '        mode = "paused" if self.paused else "low_power"\n        return {"capture_mode": mode, "mode": mode, "mode_label": mode.upper(), "paused": self.paused, "queued": 2, "running": 1, "retrying": 0, "completed": 3, "failed": 0, "cancelled": 1, "updated_at": "2026-07-21T00:00:00+00:00"}\n',
    "fake status DTO",
)
api_test = replace_once(
    api_test,
    '        return {"inputs": {"text": {"enabled": True}}}\n',
    '        return {"capture_mode": "low_power", "state": "healthy", "inputs": {"text": {"enabled": True}}, "file_modes": ["web_snapshot", "chatgpt_export", "codex_report"], "media": {"ocr": False, "transcription": False, "keyframes": False, "extract_audio": False, "reasons": {}}}\n',
    "fake capabilities DTO",
)
api_test = replace_once(
    api_test,
    '        return {"job_id": job_id, "status": "queued"}\n',
    '        return {"job_id": job_id, "status": "queued", "result_refs": {"memory_id": "MEM-1"}, "result_summary": "{\\"memory_count\\": 1}"}\n',
    "fake job DTO",
)
api_test += '''


def test_capture_http_contract_matches_desktop_client():
    context, _ = client()
    headers = {"X-LingJi-Token": "secret"}
    with context as api:
        status = api.get("/api/capture/status", headers=headers).json()
        capabilities = api.get("/api/capture/capabilities", headers=headers).json()
        job = api.get("/api/capture/jobs/job-1", headers=headers).json()
    assert status["mode"] == "low_power"
    assert status["mode_label"] == "LOW_POWER"
    assert status["queued"] == 2
    assert status["running"] == 1
    assert status["updated_at"]
    assert capabilities["file_modes"] == ["web_snapshot", "chatgpt_export", "codex_report"]
    assert "media" in capabilities
    assert job["result_refs"] == {"memory_id": "MEM-1"}
    assert isinstance(job["result_summary"], str)
'''
write(api_test_path, api_test)
