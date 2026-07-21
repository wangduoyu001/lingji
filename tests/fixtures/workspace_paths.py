"""Test workspace path helpers for non-system-drive test isolation.

P0 tests on Windows rely on tempfile.TemporaryDirectory() which creates
directories on C:\\ - the system drive. WorkspaceResolver._reject_system_drive_text
and _reject_system_drive correctly reject C:\\ for production safety, so we provide
a controlled escape hatch for test roots without weakening production security.
"""
from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Generator


@contextlib.contextmanager
def allow_test_workspace_root(test_root: Path) -> Generator[None, None, None]:
    """Temporarily allow paths under *test_root* through the system-drive check.

    Usage inside `unittest.TestCase.setUp`::

        def setUp(self) -> None:
            self.temp_dir = tempfile.TemporaryDirectory()
            self.addCleanup(self.temp_dir.cleanup)
            root = Path(self.temp_dir.name)
            self._allow_cm = allow_test_workspace_root(root)
            self._allow_cm.__enter__()
            self.addCleanup(self._allow_cm.__exit__, None, None, None)
            # ... workspace creation that calls WorkspaceResolver.resolve(...) ...
    """
    import src.runtime.workspace as _ws

    original_text = _ws._reject_system_drive_text
    original_path = _ws._reject_system_drive
    test_path = Path(test_root).resolve()

    def _patched_text(value: str, label: str) -> None:
        candidate = Path(value).resolve(strict=False)
        try:
            candidate.relative_to(test_path)
            return
        except ValueError:
            pass
        return original_text(value, label)

    def _patched_path(candidate: Path, label: str) -> None:
        try:
            candidate.resolve(strict=False).relative_to(test_path)
            return
        except ValueError:
            pass
        return original_path(candidate, label)

    _ws._reject_system_drive_text = _patched_text
    _ws._reject_system_drive = _patched_path
    try:
        yield
    finally:
        _ws._reject_system_drive_text = original_text
        _ws._reject_system_drive = original_path
