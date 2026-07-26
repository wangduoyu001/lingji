from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from second_brain.desktop.api_client import ApiClient
from second_brain.desktop.main_window import MainWindow
from second_brain.desktop.startup_manager import StartupManager
from second_brain.desktop.theme import APP_STYLE


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--validation-screenshot")
    parser.add_argument("--validation-page", type=int, default=0)
    parser.add_argument("--validation-exit", action="store_true")
    args, _ = parser.parse_known_args(argv[1:])
    return args


def main() -> int:
    args = parse_args(sys.argv)
    app = QApplication(sys.argv)
    app.setApplicationName("灵机第二大脑")
    app.setOrganizationName("LingJi")
    app.setStyleSheet(APP_STYLE)
    startup = StartupManager()
    ready, message = startup.ensure_backend()
    if not ready:
        QMessageBox.critical(None, "灵机第二大脑启动失败", message)
        return 1
    window = MainWindow(ApiClient(), startup)
    window.show()
    if args.validation_screenshot:
        def capture() -> None:
            window.navigation.setCurrentRow(max(0, min(args.validation_page, window.pages.count() - 1)))
            page = window.page_items[window.navigation.currentRow()]
            if args.validation_page == 1 and hasattr(page, "latest"):
                page.latest()
            destination = Path(args.validation_screenshot).resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            QTimer.singleShot(
                2500,
                lambda: (
                    window.grab().save(str(destination), "PNG"),
                    app.quit() if args.validation_exit else None,
                ),
            )

        QTimer.singleShot(1200, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
