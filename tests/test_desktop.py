from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from second_brain.desktop.main_window import MainWindow


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

    def test_window_has_all_native_pages(self) -> None:
        self.assertEqual(self.window.pages.count(), 9)
        self.assertEqual(self.window.navigation.count(), 9)
        self.assertEqual(self.window.objectName(), "LingJiSecondBrainWindow")
        self.assertEqual(self.window.client.workspace, "acceptance")

    def test_workspace_switch_has_visual_warning(self) -> None:
        self.window.workspace.setCurrentIndex(1)
        QTest.qWait(100)
        self.assertEqual(self.client.workspace, "production")
        self.assertIn("#fee2e2", self.window.workspace_banner.styleSheet())
        self.window.workspace.setCurrentIndex(0)
        QTest.qWait(100)
        self.assertEqual(self.client.workspace, "acceptance")
        self.assertIn("#dcfce7", self.window.workspace_banner.styleSheet())

    def test_close_keeps_api_by_default(self) -> None:
        self.assertFalse(self.window.system_page.stop_api_on_exit.isChecked())
        self.window.close()
        self.assertFalse(self.startup.stopped)


if __name__ == "__main__":
    unittest.main()
