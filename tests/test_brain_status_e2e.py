import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.control.api import create_control_app


TOKEN = "e2e-test"
AUTH_HEADERS = {"X-LingJi-Token": TOKEN}


class _DeterministicControlService:
    """Stable API-contract fixture without real ports, GPUs, or local services."""

    def brain_status(self) -> dict:
        return {
            "memory_count": 3,
            "memory_chunk_count": 7,
            "chat_model": "qwen3:8b",
            "embed_model": "bge-m3",
            "installed_models": 2,
            "system_status": "healthy",
            "processing_status": "idle",
        }

    def overview(self) -> dict:
        return {
            "health": {"status": "healthy"},
            "queue": {"stats": {}, "recent": []},
        }


@pytest.fixture
def control_client() -> TestClient:
    settings = Settings(
        _env_file=None,
        vault_dir="_e2e_vault",
        storage_dir="_e2e_storage",
        backup_dir="_e2e_backups",
        log_dir="_e2e_logs",
        llm_model="qwen3:8b",
        embed_model="bge-m3",
        startup_min_free_gb=0,
    )
    app = create_control_app(
        settings,
        service=_DeterministicControlService(),
        token=TOKEN,
    )
    with TestClient(app) as client:
        yield client


@pytest.mark.integration
class TestBrainStatusApiContract:
    """API wiring tests that remain deterministic in the full repository suite."""

    def test_brain_status_endpoint(self, control_client: TestClient):
        response = control_client.get("/api/brain/status", headers=AUTH_HEADERS)
        data = response.json()

        assert response.status_code == 200
        assert data["memory_count"] == 3
        assert data["chat_model"] == "qwen3:8b"
        assert data["installed_models"] == 2
        assert data["system_status"] == "healthy"
        assert data["processing_status"] == "idle"

    def test_overview_endpoint(self, control_client: TestClient):
        response = control_client.get("/api/overview", headers=AUTH_HEADERS)

        assert response.status_code == 200
        assert response.json()["health"]["status"] == "healthy"

    def test_local_control_token_is_required(self, control_client: TestClient):
        response = control_client.get("/api/brain/status")

        assert response.status_code == 401
