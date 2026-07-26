from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.control.api import create_control_app
from src.control.capture import CaptureControlError


class FakeCaptureControl:
    def __init__(self):
        self.calls = []
        self.paused = False

    @staticmethod
    def _result(kind, payload):
        duplicate = payload.get("text") == "duplicate"
        return {
            "capture_id": f"cap-{kind}",
            "status": "duplicate" if duplicate else "queued",
            "job_id": "job-existing" if duplicate else f"job-{kind}",
            "duplicate": duplicate,
            "reason": "same content" if duplicate else "",
        }

    def submit_text(self, payload):
        self.calls.append(("text", payload))
        if self.paused:
            raise CaptureControlError("CAPTURE_PAUSED", "Capture is paused", status_code=409)
        return self._result("text", payload)

    def submit_web(self, payload):
        self.calls.append(("web", payload))
        return self._result("web", payload)

    def submit_file(self, payload):
        self.calls.append(("file", payload))
        return self._result("file", payload)

    def submit_media(self, payload):
        self.calls.append(("media", payload))
        return self._result("media", payload)

    def submit_share(self, payload):
        self.calls.append(("share", payload))
        return self._result("share", payload)

    def status(self):
        mode = "paused" if self.paused else "low_power"
        return {"capture_mode": mode, "mode": mode, "mode_label": mode.upper(), "paused": self.paused, "queued": 2, "running": 1, "retrying": 0, "completed": 3, "failed": 0, "cancelled": 1, "updated_at": "2026-07-21T00:00:00+00:00"}

    def capabilities(self):
        return {"capture_mode": "low_power", "state": "healthy", "inputs": {"text": {"enabled": True}}, "file_modes": ["web_snapshot", "chatgpt_export", "codex_report"], "media": {"ocr": False, "transcription": False, "keyframes": False, "extract_audio": False, "reasons": {}}}

    def list_jobs(self, **kwargs):
        self.calls.append(("list", kwargs))
        return {"items": [], "pagination": {**kwargs, "total": 0}, "stats": {}}

    def get_job(self, job_id):
        if job_id == "missing":
            raise CaptureControlError("CAPTURE_JOB_NOT_FOUND", "Capture job not found", status_code=404)
        return {"job_id": job_id, "status": "queued", "result_refs": {"memory_id": "MEM-1"}, "result_summary": "{\"memory_count\": 1}"}

    def retry_job(self, job_id):
        if job_id == "running":
            raise CaptureControlError("CAPTURE_JOB_RUNNING", "Running capture jobs cannot be retried", status_code=409)
        return {"job_id": job_id, "status": "queued"}

    def cancel_job(self, job_id):
        if job_id == "running":
            raise CaptureControlError("CAPTURE_JOB_RUNNING", "Running capture jobs cannot be cancelled", status_code=409)
        return {"job_id": job_id, "status": "cancelled"}

    def pause(self):
        self.paused = True
        return self.status()

    def resume(self):
        self.paused = False
        return self.status()


class FakeControl:
    def __init__(self):
        self.capture_control = FakeCaptureControl()


def client():
    settings = SimpleNamespace(storage_path=Path("/tmp"), runtime_settings_file=Path("runtime.json"))
    control = FakeControl()
    context = TestClient(create_control_app(settings, service=control, token="secret"))
    return context, control


def test_capture_routes_require_token():
    context, _ = client()
    with context as api:
        assert api.get("/api/capture/status").status_code == 401
        assert api.post("/api/capture/text", json={"text": "hello"}).status_code == 401


def test_capture_submission_status_codes_and_share_forwarding():
    context, control = client()
    headers = {"X-LingJi-Token": "secret"}
    with context as api:
        queued = api.post("/api/capture/text", headers=headers, json={"text": "hello"})
        duplicate = api.post("/api/capture/text", headers=headers, json={"text": "duplicate"})
        share = api.post("/api/share", headers=headers, json={"text": "legacy"})
    assert queued.status_code == 202
    assert queued.json()["job_id"] == "job-text"
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert share.status_code == 202
    assert control.capture_control.calls[-1][0] == "share"


def test_capture_status_pagination_pause_resume_and_errors():
    context, _ = client()
    headers = {"X-LingJi-Token": "secret"}
    with context as api:
        page = api.get(
            "/api/capture/jobs?status=queued&source_type=web&q=abc&limit=12&offset=3",
            headers=headers,
        )
        missing = api.get("/api/capture/jobs/missing", headers=headers)
        running = api.post("/api/capture/jobs/running/cancel", headers=headers)
        pause = api.post("/api/capture/pause", headers=headers)
        paused_submit = api.post("/api/capture/text", headers=headers, json={"text": "blocked"})
        resume = api.post("/api/capture/resume", headers=headers)
    assert page.status_code == 200
    assert page.json()["pagination"]["limit"] == 12
    assert page.json()["pagination"]["offset"] == 3
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "CAPTURE_JOB_NOT_FOUND"
    assert running.status_code == 409
    assert running.json()["detail"]["code"] == "CAPTURE_JOB_RUNNING"
    assert pause.json()["paused"] is True
    assert paused_submit.status_code == 409
    assert paused_submit.json()["detail"]["code"] == "CAPTURE_PAUSED"
    assert resume.json()["paused"] is False


def test_invalid_capture_payload_returns_422():
    context, _ = client()
    headers = {"X-LingJi-Token": "secret"}
    with context as api:
        assert api.post("/api/capture/text", headers=headers, json={"text": ""}).status_code == 422
        assert api.get("/api/capture/jobs?limit=201", headers=headers).status_code == 422



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
