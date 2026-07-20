from __future__ import annotations

import os
import unittest

try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from second_brain.desktop.main_window import MainWindow
    _HAS_PYSIDE6 = True
except ImportError:
    _HAS_PYSIDE6 = False
    MainWindow = None  # type: ignore[assignment]


class FakeClient:
    def __init__(self) -> None:
        self.workspace = "acceptance"

    def get(self, path: str, **kwargs):
        if path == "/system/status":
            empty = {
                "counts": {"memories": 0, "knowledge_documents": 0, "tasks": 0},
                "qdrant": {"ready": True, "vectors": 0},
            }
            return {
                "api": "ok",
                "ollama": True,
                "watcher": {"running": False},
                "production": empty,
                "acceptance": empty,
            }
        return {}

    def post(self, path: str, payload=None, **kwargs):
        return {}


class FakeStartup:
    def __init__(self) -> None:
        self.stopped = False

    def stop_backend(self) -> None:
        self.stopped = True


@unittest.skipIf(not _HAS_PYSIDE6, "PySide6 not installed - old desktop UI replaced by Tauri")
class DesktopWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.client = FakeClient()
        self.startup = FakeStartup()
        self.window = MainWindow(self.client, self.startup)
        self.window.show()
        QTest.qWait(100)

    def tearDown(self) -> None:
        self.window.close()
        QTest.qWait(50)

    def test_window_title(self) -> None:
        self.assertIn("灵机 - 控制中心", self.window.windowTitle())

    def test_status_display(self) -> None:
        """window shows ollama status after fetch."""
        status = self.window.fetch_status()
        self.assertIsNotNone(status)
        self.assertTrue(status.get("ollama"))

    def test_close_stops_backend(self) -> None:
        self.assertFalse(self.startup.stopped)
        self.window.close()
        QTest.qWait(50)
        self.assertTrue(self.startup.stopped)

    def test_desktop_ui_is_runnable(self) -> None:
        self.assertTrue(self.window.isVisible())
