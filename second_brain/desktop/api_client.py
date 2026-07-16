from __future__ import annotations

from typing import Any

import requests


class ApiError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8765", workspace: str = "acceptance"):
        self.base_url = base_url.rstrip("/")
        self.workspace = workspace

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
        params: dict | None = None,
        timeout: int = 180,
        workspace: str | None = None,
    ) -> Any:
        headers = {"X-LingJi-Workspace": workspace or self.workspace}
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                json=payload,
                params={key: value for key, value in (params or {}).items() if value not in (None, "")},
                headers=headers,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise ApiError(f"无法连接第二大脑服务：{exc}") from exc
        if not response.ok:
            try:
                detail = response.json().get("detail") or response.json().get("message")
            except ValueError:
                detail = response.text
            raise ApiError(f"{response.status_code}: {detail}")
        if not response.content:
            return {}
        return response.json()

    def get(self, path: str, *, params: dict | None = None, workspace: str | None = None) -> Any:
        return self.request("GET", path, params=params, workspace=workspace)

    def post(self, path: str, payload: dict | None = None, *, workspace: str | None = None) -> Any:
        return self.request("POST", path, payload=payload or {}, workspace=workspace)
