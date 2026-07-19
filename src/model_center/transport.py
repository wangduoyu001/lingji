from __future__ import annotations

from typing import Any

import requests


class OllamaInventoryTransport:
    """Small HTTP adapter used only for read-only inventory endpoints."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def get_json(self, url: str, timeout: float = 3.0) -> dict[str, Any]:
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def post_json(self, url: str, payload: dict[str, Any], timeout: float = 3.0) -> dict[str, Any]:
        response = self.session.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        body = response.json()
        return body if isinstance(body, dict) else {}

    def close(self) -> None:
        self.session.close()
