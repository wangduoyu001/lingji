from __future__ import annotations

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from second_brain.desktop.api_client import ApiClient
from second_brain.desktop.pages import (
    AcceptancePage,
    ActivityPage,
    ConflictPage,
    DashboardPage,
    ImportPage,
    KnowledgePage,
    MemoryPage,
    SearchPage,
    SystemPage,
)
from second_brain.desktop.startup_manager import StartupManager
from second_brain.desktop.workers import ApiWorker


class MainWindow(QMainWindow):
    def __init__(self, client: ApiClient, startup: StartupManager):
        super().__init__()
        self.client = client
        self.startup = startup
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle("灵机第二大脑")
        self.setObjectName("LingJiSecondBrainWindow")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)
        self._build()
        self.statusBar().showMessage("桌面控制台已连接，当前为验收库")

    def _build(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.navigation = QListWidget()
        self.navigation.setFixedWidth(210)
        labels = ["系统总览", "一键验收", "聊天导入", "记忆审核", "搜索与上下文", "冲突处理", "Obsidian知识", "任务与时间线", "系统与监听器"]
        for label in labels:
            QListWidgetItem(label, self.navigation)
        root_layout.addWidget(self.navigation)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 12, 16, 12)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        top_layout = QHBoxLayout(topbar)
        brand = QLabel("灵机第二大脑 · Windows 本地控制台")
        brand.setStyleSheet("font-size:17px;font-weight:700;")
        top_layout.addWidget(brand)
        top_layout.addStretch()
        top_layout.addWidget(QLabel("运行空间"))
        self.workspace = QComboBox()
        self.workspace.setObjectName("workspaceSelector")
        self.workspace.addItem("验收库（安全测试）", "acceptance")
        self.workspace.addItem("正式库", "production")
        self.workspace.currentIndexChanged.connect(self.change_workspace)
        top_layout.addWidget(self.workspace)
        self.workspace_banner = QLabel("验收库：可安全重置")
        self.workspace_banner.setObjectName("workspaceBanner")
        self.workspace_banner.setStyleSheet("background:#dcfce7;color:#166534;padding:7px 12px;border-radius:5px;")
        top_layout.addWidget(self.workspace_banner)
        right_layout.addWidget(topbar)

        self.pages = QStackedWidget()
        self.page_items = [
            DashboardPage(self), AcceptancePage(self), ImportPage(self), MemoryPage(self),
            SearchPage(self), ConflictPage(self), KnowledgePage(self), ActivityPage(self), SystemPage(self),
        ]
        for page in self.page_items:
            self.pages.addWidget(page)
        right_layout.addWidget(self.pages, 1)
        root_layout.addWidget(right, 1)
        self.setCentralWidget(root)

        self.navigation.currentRowChanged.connect(self.change_page)
        self.navigation.setCurrentRow(0)

    @property
    def system_page(self) -> SystemPage:
        return self.page_items[-1]

    def change_page(self, index: int) -> None:
        if index < 0:
            return
        self.pages.setCurrentIndex(index)
        page = self.page_items[index]
        if hasattr(page, "refresh"):
            page.refresh()

    def change_workspace(self) -> None:
        self.client.workspace = self.workspace.currentData()
        if self.client.workspace == "production":
            self.workspace_banner.setText("正式库：写操作需二次确认")
            self.workspace_banner.setStyleSheet("background:#fee2e2;color:#991b1b;padding:7px 12px;border-radius:5px;font-weight:700;")
        else:
            self.workspace_banner.setText("验收库：可安全重置")
            self.workspace_banner.setStyleSheet("background:#dcfce7;color:#166534;padding:7px 12px;border-radius:5px;")
        current = self.page_items[self.pages.currentIndex()]
        if hasattr(current, "refresh"):
            current.refresh()
        self.show_status(f"已切换到：{self.workspace.currentText()}")

    def run_operation(self, operation, success, busy_text: str) -> None:
        self.show_status(busy_text)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        worker = ApiWorker(operation)
        worker.signals.success.connect(success)
        worker.signals.success.connect(lambda _: self.show_status("操作成功"))
        worker.signals.error.connect(self.show_error)
        worker.signals.finished.connect(self._operation_finished)
        self.thread_pool.start(worker)

    def _operation_finished(self) -> None:
        if QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

    def show_error(self, message: str) -> None:
        self.statusBar().showMessage(f"失败：{message}", 15000)
        QMessageBox.critical(self, "操作失败", message)

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 10000)

    def confirm_write(self, text: str) -> bool:
        if self.client.workspace == "production":
            text = f"当前是正式库。\n\n{text}\n\n该操作会写入正式记忆数据。"
        return QMessageBox.question(self, "确认操作", text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def ask_text(self, title: str, label: str) -> tuple[str, bool]:
        return QInputDialog.getMultiLineText(self, title, label)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.thread_pool.waitForDone(3000)
        if self.system_page.stop_api_on_exit.isChecked():
            self.startup.stop_backend()
        event.accept()
