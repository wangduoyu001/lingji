from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .connectors import Runner


@dataclass(frozen=True)
class ExecutableAttempt:
    path: str
    state: str
    detail: str


@dataclass(frozen=True)
class ExecutableResolution:
    name: str
    state: str
    selected: str
    candidates: tuple[str, ...]
    attempts: tuple[ExecutableAttempt, ...]

    @property
    def launchable(self) -> bool:
        return bool(self.selected) and self.state == "verified"

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "state": self.state,
            "selected": self.selected,
            "candidate_count": len(self.candidates),
            "candidates": list(self.candidates),
            "attempts": [asdict(item) for item in self.attempts],
        }


def executable_invocation(
    executable: str | Path,
    arguments: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> list[str]:
    """Return a fixed-argument invocation for an executable or Windows shim.

    ``.cmd`` and ``.bat`` files require ``cmd.exe`` on Windows. The command line
    is created with ``subprocess.list2cmdline`` from a server-controlled argument
    list; no owner-provided shell fragment is accepted.
    """

    # An explicitly supplied empty mapping is an isolation boundary.  Falling
    # back to the process environment here would make fixture-only scans probe
    # the owner's PATH and can turn "not found" into a misleading result.
    environment = dict(os.environ) if env is None else dict(env)
    selected_platform = platform or os.name
    path = str(Path(executable).expanduser())
    suffix = Path(path).suffix.casefold()
    if selected_platform == "nt" and suffix in {".cmd", ".bat"}:
        comspec = str(environment.get("COMSPEC") or "").strip()
        if not comspec:
            system_root = str(environment.get("SystemRoot") or r"C:\Windows").strip()
            comspec = str(Path(system_root) / "System32" / "cmd.exe")
        fixed_command = subprocess.list2cmdline([path, *[str(item) for item in arguments]])
        return [comspec, "/d", "/s", "/c", fixed_command]
    return [path, *[str(item) for item in arguments]]


def enumerate_executable_candidates(
    name: str,
    *,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
    preferred_candidates: Sequence[str] = (),
) -> list[str]:
    """Enumerate deterministic PATH/npm candidates without recursive disk scans."""

    # See ``executable_invocation``: empty is deliberately different from
    # omitted for owner-data isolation.
    environment = dict(os.environ) if env is None else dict(env)
    selected_platform = platform or os.name
    windows = selected_platform == "nt"
    path_value = str(environment.get("PATH") or "")
    separator = ";" if windows else os.pathsep
    raw_directories = [part.strip().strip('"') for part in path_value.split(separator) if part.strip()]
    if windows:
        appdata = str(environment.get("APPDATA") or "").strip()
        localappdata = str(environment.get("LOCALAPPDATA") or "").strip()
        if appdata:
            raw_directories.append(str(Path(appdata) / "npm"))
        if localappdata:
            raw_directories.append(str(Path(localappdata) / "npm"))

    suffix = Path(name).suffix
    if suffix:
        filenames = [name]
    elif windows:
        raw_extensions = str(environment.get("PATHEXT") or ".COM;.EXE;.BAT;.CMD")
        extensions = [item.strip() for item in raw_extensions.split(";") if item.strip()]
        filenames = [name, *[f"{name}{extension.lower()}" for extension in extensions]]
    else:
        filenames = [name]

    result: list[str] = []
    seen: set[str] = set()

    def add(candidate: str | Path | None, *, require_file: bool) -> None:
        if not candidate:
            return
        path = Path(str(candidate)).expanduser()
        if require_file and not path.is_file():
            return
        if require_file and not windows and not os.access(path, os.X_OK):
            return
        normalized = str(path.resolve(strict=False))
        key = normalized.casefold() if windows else normalized
        if key in seen:
            return
        seen.add(key)
        result.append(normalized)

    for candidate in preferred_candidates:
        add(candidate, require_file=False)

    discovered = shutil.which(name, path=path_value or None)
    add(discovered, require_file=False)

    for directory in raw_directories:
        for filename in filenames:
            add(Path(directory) / filename, require_file=True)

    return result


def resolve_launchable_executable(
    name: str,
    *,
    env: Mapping[str, str] | None,
    runner: Runner,
    timeout_seconds: float,
    platform: str | None = None,
    preferred_candidates: Sequence[str] = (),
    probe_arguments: Sequence[str] = ("--version",),
) -> ExecutableResolution:
    """Try every deterministic candidate and select the first one that executes."""

    environment = dict(env or {})
    selected_platform = platform or os.name
    candidates = enumerate_executable_candidates(
        name,
        env=environment,
        platform=selected_platform,
        preferred_candidates=preferred_candidates,
    )
    attempts: list[ExecutableAttempt] = []
    probe_timeout = max(1.0, min(float(timeout_seconds), 6.0))

    for candidate in candidates:
        command = executable_invocation(
            candidate,
            probe_arguments,
            env=environment,
            platform=selected_platform,
        )
        try:
            completed = runner(command, probe_timeout)
        except subprocess.TimeoutExpired:
            attempts.append(ExecutableAttempt(candidate, "timeout", "version probe timed out"))
            continue
        except PermissionError as exc:
            attempts.append(
                ExecutableAttempt(candidate, "access_denied", str(exc).strip() or "access denied")
            )
            continue
        except OSError as exc:
            detail = str(exc).strip() or type(exc).__name__
            state = "access_denied" if "denied" in detail.casefold() else "launch_failed"
            attempts.append(ExecutableAttempt(candidate, state, detail[:300]))
            continue

        if completed.returncode == 0:
            attempts.append(ExecutableAttempt(candidate, "verified", "version probe succeeded"))
            return ExecutableResolution(
                name=name,
                state="verified",
                selected=candidate,
                candidates=tuple(candidates),
                attempts=tuple(attempts),
            )
        detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
        attempts.append(ExecutableAttempt(candidate, "rejected", detail[:300]))

    return ExecutableResolution(
        name=name,
        state="not_found" if not candidates else "launch_blocked",
        selected="",
        candidates=tuple(candidates),
        attempts=tuple(attempts),
    )
