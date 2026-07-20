from __future__ import annotations

import json
import subprocess
import urllib.request
from typing import Any, Callable


class SafeRunner:
    def __init__(self, command_runner: Callable[..., Any] | None = None, url_reader: Callable[..., Any] | None = None):
        self.command_runner = command_runner or self._run_command
        self.url_reader = url_reader or self._read_json_url

    def command(self, args: list[str], *, timeout: float = 3.0) -> dict[str, Any]:
        try:
            raw = self.command_runner(args, timeout=timeout)
        except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
            return {"returncode": 1, "stdout": "", "stderr": self.safe_error(exc)}
        if isinstance(raw, dict):
            return {
                "returncode": int(raw.get("returncode", 1)),
                "stdout": str(raw.get("stdout") or ""),
                "stderr": str(raw.get("stderr") or ""),
            }
        return {
            "returncode": int(getattr(raw, "returncode", 1)),
            "stdout": str(getattr(raw, "stdout", "") or ""),
            "stderr": str(getattr(raw, "stderr", "") or ""),
        }

    def json_url(self, url: str, *, timeout: float = 3.0) -> dict[str, Any]:
        return self.url_reader(url, timeout=timeout)

    @staticmethod
    def _run_command(args: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

    @staticmethod
    def _read_json_url(url: str, *, timeout: float) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "LingJi/1.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def safe_error(exc: Exception) -> str:
        return f"{exc.__class__.__name__}: {exc}"[:500]
