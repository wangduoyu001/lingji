from __future__ import annotations

import subprocess
from pathlib import Path

from src.assistant_hub.executable_resolution import (
    enumerate_executable_candidates,
    executable_invocation,
    resolve_launchable_executable,
)


def test_windows_candidate_order_keeps_alias_then_finds_npm_cmd(tmp_path: Path) -> None:
    windows_apps = tmp_path / "WindowsApps"
    npm = tmp_path / "Roaming" / "npm"
    windows_apps.mkdir(parents=True)
    npm.mkdir(parents=True)
    alias = windows_apps / "codex.exe"
    shim = npm / "codex.cmd"
    alias.write_bytes(b"alias")
    shim.write_text("@echo off\n", encoding="utf-8")

    env = {
        "PATH": f"{windows_apps};{npm}",
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "APPDATA": str(tmp_path / "Roaming"),
        "SystemRoot": r"C:\Windows",
    }
    candidates = enumerate_executable_candidates(
        "codex",
        env=env,
        platform="nt",
        preferred_candidates=[str(alias)],
    )

    assert candidates[0].casefold().endswith("windowsapps/codex.exe")
    assert any(item.casefold().endswith("npm/codex.cmd") for item in candidates)


def test_resolver_skips_access_denied_alias_and_selects_cmd_shim(tmp_path: Path) -> None:
    windows_apps = tmp_path / "WindowsApps"
    npm = tmp_path / "Roaming" / "npm"
    windows_apps.mkdir(parents=True)
    npm.mkdir(parents=True)
    alias = windows_apps / "codex.exe"
    shim = npm / "codex.cmd"
    alias.write_bytes(b"alias")
    shim.write_text("@echo off\n", encoding="utf-8")

    calls: list[list[str]] = []

    def runner(command, timeout):
        calls.append(list(command))
        command_text = " ".join(command).casefold()
        if "windowsapps" in command_text:
            raise PermissionError(13, "Access is denied", str(alias))
        if "codex.cmd" in command_text and "--version" in command_text:
            return subprocess.CompletedProcess(command, 0, "codex 1.0", "")
        return subprocess.CompletedProcess(command, 1, "", "unexpected")

    resolution = resolve_launchable_executable(
        "codex",
        env={
            "PATH": f"{windows_apps};{npm}",
            "PATHEXT": ".COM;.EXE;.BAT;.CMD",
            "APPDATA": str(tmp_path / "Roaming"),
            "SystemRoot": r"C:\Windows",
        },
        runner=runner,
        timeout_seconds=5,
        platform="nt",
        preferred_candidates=[str(alias)],
    )

    assert resolution.state == "verified"
    assert resolution.launchable is True
    assert resolution.selected.casefold().endswith("npm/codex.cmd")
    assert [item.state for item in resolution.attempts] == ["access_denied", "verified"]
    assert calls[1][0].casefold().endswith("system32/cmd.exe")
    assert calls[1][1:4] == ["/d", "/s", "/c"]


def test_all_blocked_candidates_remain_launch_blocked(tmp_path: Path) -> None:
    first = tmp_path / "codex.exe"
    second = tmp_path / "codex.cmd"
    first.write_bytes(b"alias")
    second.write_text("@echo off\n", encoding="utf-8")

    def denied(command, timeout):
        raise PermissionError(13, "Access is denied", command[0])

    resolution = resolve_launchable_executable(
        "codex",
        env={"PATH": str(tmp_path), "PATHEXT": ".EXE;.CMD"},
        runner=denied,
        timeout_seconds=1,
        platform="nt",
        preferred_candidates=[str(first)],
    )

    assert resolution.state == "launch_blocked"
    assert resolution.launchable is False
    assert resolution.selected == ""
    assert len(resolution.attempts) == 2
    assert all(item.state == "access_denied" for item in resolution.attempts)


def test_cmd_invocation_uses_fixed_comspec_arguments(tmp_path: Path) -> None:
    shim = tmp_path / "codex.cmd"
    invocation = executable_invocation(
        shim,
        ["mcp", "list"],
        env={"COMSPEC": r"C:\Windows\System32\cmd.exe"},
        platform="nt",
    )

    assert invocation[:4] == [r"C:\Windows\System32\cmd.exe", "/d", "/s", "/c"]
    assert "codex.cmd" in invocation[4]
    assert "mcp list" in invocation[4]
