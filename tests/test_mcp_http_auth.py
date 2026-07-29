from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.mcp_http import BearerTokenMiddleware, run_authenticated_mcp_http


def test_bearer_middleware_rejects_missing_and_wrong_tokens() -> None:
    app = FastAPI()

    @app.get("/mcp")
    def mcp_probe():
        return {"ok": True}

    client = TestClient(BearerTokenMiddleware(app, "secret"))
    missing = client.get("/mcp")
    wrong = client.get("/mcp", headers={"Authorization": "Bearer wrong"})

    assert missing.status_code == 401
    assert missing.json() == {"error": "unauthorized"}
    assert missing.headers["www-authenticate"] == "Bearer"
    assert wrong.status_code == 401


def test_bearer_middleware_allows_exact_token() -> None:
    app = FastAPI()

    @app.get("/mcp")
    def mcp_probe():
        return {"ok": True}

    client = TestClient(BearerTokenMiddleware(app, "secret"))
    response = client.get("/mcp", headers={"Authorization": "Bearer secret"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_mcp_http_refuses_non_loopback_binding() -> None:
    with pytest.raises(ValueError, match="loopback"):
        run_authenticated_mcp_http(token="secret", host="0.0.0.0", port=8767)


def test_mcp_http_requires_token() -> None:
    with pytest.raises(ValueError, match="token"):
        run_authenticated_mcp_http(token="", host="127.0.0.1", port=8767)
