from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.control.project_memory_api import register_project_memory_routes


class Context:
    def build(self, *args, **kwargs): return {"project_id": args[1]}
class Review:
    def list_candidates(self, *args): return {"items": [], "total": 0}
    def get_candidate(self, memory_id): raise RuntimeError("down")


class RecordingReview:
    def __init__(self):
        self.calls = []

    def approve(self, *args, **kwargs): self.calls.append(("approve", args, kwargs)); return {"status": "active"}
    def edit_and_approve(self, *args, **kwargs): self.calls.append(("edit", args, kwargs)); return {"status": "active"}
    def reject(self, *args, **kwargs): self.calls.append(("reject", args, kwargs)); return {"status": "rejected"}
    def archive_core_memory(self, *args, **kwargs): self.calls.append(("archive", args, kwargs)); return {"status": "archived"}
    def correct_core_memory(self, *args, **kwargs): self.calls.append(("correct", args, kwargs)); return {"status": "active", "id": "new"}
    def invalidate_core_memory(self, *args, **kwargs): self.calls.append(("invalidate", args, kwargs)); return {"status": "invalidated"}


def test_project_memory_api_auth_and_503():
    app = FastAPI(); register_project_memory_routes(app, Context(), Review(), token_validator=lambda value: value == "ok")
    client = TestClient(app)
    assert client.post("/api/context/project", json={"project_id": "P"}).status_code == 401
    assert client.post("/api/context/project", headers={"X-LingJi-Token": "ok"}, json={"project_id": "P"}).status_code == 200
    assert client.get("/api/memory/review/candidates/M", headers={"X-LingJi-Token": "ok"}).status_code == 503


def test_project_memory_mutations_require_authentication():
    app = FastAPI(); register_project_memory_routes(app, Context(), RecordingReview(), token_validator=lambda value: value == "ok")
    client = TestClient(app)
    body = {"owner_confirmed": True, "expected_content_hash": "hash", "reason": "reason", "content": "content"}
    paths = [
        "/api/memory/review/candidates/M/approve",
        "/api/memory/review/candidates/M/edit-approve",
        "/api/memory/review/candidates/M/reject",
        "/api/memory/core/M/archive",
        "/api/memory/core/M/correct",
        "/api/memory/core/M/invalidate",
    ]
    assert all(client.post(path, json=body).status_code == 401 for path in paths)


def test_project_memory_archive_requires_expected_content_hash():
    app = FastAPI(); register_project_memory_routes(app, Context(), RecordingReview(), token_validator=lambda value: value == "ok")
    client = TestClient(app)

    response = client.post(
        "/api/memory/core/M/archive",
        headers={"X-LingJi-Token": "ok"},
        json={"owner_confirmed": True, "reason": "reason"},
    )

    assert response.status_code == 422


def test_project_memory_invalidate_preserves_valid_to_and_response_schema():
    review = RecordingReview()
    app = FastAPI(); register_project_memory_routes(app, Context(), review, token_validator=lambda value: value == "ok")
    client = TestClient(app)

    response = client.post(
        "/api/memory/core/M/invalidate",
        headers={"X-LingJi-Token": "ok"},
        json={"owner_confirmed": True, "expected_content_hash": "hash", "reason": "过时", "valid_to": "2026-08-30T00:00:00Z"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "invalidated"}
    assert review.calls[-1][2]["valid_to"] == "2026-08-30T00:00:00Z"


def test_project_memory_correct_passes_owner_reason_content_and_replacement_id():
    review = RecordingReview()
    app = FastAPI(); register_project_memory_routes(app, Context(), review, token_validator=lambda value: value == "ok")
    client = TestClient(app)

    response = client.post(
        "/api/memory/core/M/correct",
        headers={"X-LingJi-Token": "ok"},
        json={"owner_confirmed": True, "expected_content_hash": "hash", "reason": "主人修正", "content": "canonical replacement"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "active", "id": "new"}
    assert review.calls[-1][2]["content"] == "canonical replacement"
    assert review.calls[-1][2]["reason"] == "主人修正"
