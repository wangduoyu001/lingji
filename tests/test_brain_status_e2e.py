import pytest
import subprocess
import sys
import time
import os
import json
import urllib.request

API_PORT = 8767
BASE = f"http://127.0.0.1:{API_PORT}"
TOKEN = "e2e-test"


def _start_server():
    """Start the LingJi API server as a subprocess for E2E testing."""
    cmd = (
        "from src.control.api import create_control_app;"
        "from src.config import Settings;import uvicorn;"
        's=Settings(_env_file=None,vault_dir="_e2e_vault",'
        'storage_dir="_e2e_storage",backup_dir="_e2e_backups",'
        'log_dir="_e2e_logs",llm_model="qwen3:8b",'
        'embed_model="bge-m3",startup_min_free_gb=0);'
        'app=create_control_app(s,service=None,token="e2e-test");'
        f'uvicorn.run(app,host="127.0.0.1",port={API_PORT},log_level="error")'
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", cmd],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    return proc


def _api_get(path):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"X-LingJi-Token": TOKEN},
    )
    return urllib.request.urlopen(req, timeout=5)


@pytest.mark.integration
class TestBrainStatusE2E:
    """E2E tests for the Brain Status dashboard API and frontend dist."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        self.proc = None
        yield
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def _ensure_server(self):
        if self.proc is None:
            self.proc = _start_server()
            if self.proc.poll() is not None:
                pytest.fail("API server failed to start")

    def test_brain_status_endpoint(self):
        """GET /api/brain/status returns aggregated brain health data."""
        self._ensure_server()
        r = _api_get("/api/brain/status")
        data = json.loads(r.read().decode())
        assert r.status == 200
        assert "memory_count" in data
        assert data.get("chat_model") == "qwen3:8b"
        assert "installed_models" in data
        assert "system_status" in data
        assert "processing_status" in data

    def test_overview_endpoint(self):
        """GET /api/overview returns OK."""
        self._ensure_server()
        r2 = _api_get("/api/overview")
        assert r2.status == 200

    def test_frontend_dist_exists(self):
        """Frontend dist directory has compiled JS bundles."""
        dist = os.path.join("desktop", "lingji-control", "dist")
        if not os.path.isdir(dist):
            pytest.skip("Frontend dist not built – run UI build first")
        index = os.path.join(dist, "index.html")
        assert os.path.isfile(index), "index.html missing"
        assets_dir = os.path.join(dist, "assets")
        assert os.path.isdir(assets_dir), "assets dir missing"
        js_files = [f for f in os.listdir(assets_dir) if f.endswith(".js")]
        assert len(js_files) >= 2, f"Expected >=2 JS bundles, got {len(js_files)}"
