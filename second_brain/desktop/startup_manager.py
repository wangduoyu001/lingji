from __future__ import annotations

import subprocess
import time
from pathlib import Path

import requests

from second_brain.config import ROOT


class StartupManager:
    def __init__(self, base_url: str = "http://127.0.0.1:8765"):
        self.base_url = base_url
        self.started_backend = False

    def healthy(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/health", timeout=2).ok
        except requests.RequestException:
            return False

    def ensure_backend(self, timeout_seconds: int = 15) -> tuple[bool, str]:
        if self.healthy():
            return True, "后台服务已运行"
        script = ROOT / "scripts" / "second_brain" / "start-api.ps1"
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if self.healthy():
                self.started_backend = True
                return True, "后台服务已自动启动"
            time.sleep(0.5)
        return False, "后台服务启动超时，请检查 logs/second_brain/api.stderr.log"

    def stop_backend(self) -> None:
        script = ROOT / "scripts" / "second_brain" / "stop-api.ps1"
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            cwd=ROOT,
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
