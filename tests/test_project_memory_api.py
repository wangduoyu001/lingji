from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.control.project_memory_api import register_project_memory_routes


class Context:
    def build(self, *args, **kwargs): return {"project_id": args[1]}
class Review:
    def list_candidates(self, *args): return {"items": [], "total": 0}
    def get_candidate(self, memory_id): raise RuntimeError("down")


def test_project_memory_api_auth_and_503():
    app = FastAPI(); register_project_memory_routes(app, Context(), Review(), token_validator=lambda value: value == "ok")
    client = TestClient(app)
    assert client.post("/api/context/project", json={"project_id": "P"}).status_code == 401
    assert client.post("/api/context/project", headers={"X-LingJi-Token": "ok"}, json={"project_id": "P"}).status_code == 200
    assert client.get("/api/memory/review/candidates/M", headers={"X-LingJi-Token": "ok"}).status_code == 503
