from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from second_brain.config import ROOT


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def set_table(table: QTableWidget, rows: list[dict], columns: list[tuple[str, str]]) -> None:
    table.clear()
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels([label for _, label in columns])
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, (key, _) in enumerate(columns):
            item = QTableWidgetItem(str(row.get(key, "") if row.get(key) is not None else ""))
            item.setData(Qt.ItemDataRole.UserRole, row)
            table.setItem(row_index, column_index, item)
    table.resizeColumnsToContents()
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)


class BasePage(QWidget):
    def __init__(self, shell, title: str):
        super().__init__()
        self.shell = shell
        self.layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("title")
        self.layout.addWidget(heading)

    def run(self, operation, success, busy_text: str = "正在处理…") -> None:
        self.shell.run_operation(operation, success, busy_text)

    def confirm_write(self, text: str) -> bool:
        return self.shell.confirm_write(text)


class DashboardPage(BasePage):
    def __init__(self, shell):
        super().__init__(shell, "系统总览")
        toolbar = QHBoxLayout()
        refresh = QPushButton("刷新全部状态")
        refresh.setObjectName("refreshStatusButton")
        refresh.clicked.connect(self.refresh)
        toolbar.addWidget(refresh)
        toolbar.addStretch()
        self.layout.addLayout(toolbar)
        self.cards = QGridLayout()
        self.card_values: dict[str, QLabel] = {}
        for index, (key, label) in enumerate(
            [("api", "API"), ("ollama", "Ollama"), ("qdrant", "Qdrant"), ("watcher", "监听器"),
             ("memories", "记忆"), ("knowledge", "知识文档"), ("tasks", "Codex任务"), ("vectors", "向量")]
        ):
            card = QFrame()
            card.setObjectName("card")
            box = QVBoxLayout(card)
            box.addWidget(QLabel(label))
            value = QLabel("-")
            value.setObjectName("cardValue")
            box.addWidget(value)
            self.card_values[key] = value
            self.cards.addWidget(card, index // 4, index % 4)
        self.layout.addLayout(self.cards)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.layout.addWidget(self.details, 1)

    def refresh(self) -> None:
        self.run(lambda: self.shell.client.get("/system/status", workspace="production"), self.show_status, "正在读取系统状态…")

    def show_status(self, data: dict) -> None:
        workspace = self.shell.client.workspace
        current = data.get(workspace, {})
        counts = current.get("counts", {})
        qdrant = current.get("qdrant", {})
        self.card_values["api"].setText("正常" if data.get("api") == "ok" else "失败")
        self.card_values["ollama"].setText("正常" if data.get("ollama") else "失败")
        self.card_values["qdrant"].setText("正常" if qdrant.get("ready") else "失败")
        self.card_values["watcher"].setText("运行中" if data.get("watcher", {}).get("running") else "已停止")
        self.card_values["memories"].setText(str(counts.get("memories", 0)))
        self.card_values["knowledge"].setText(str(counts.get("knowledge_documents", 0)))
        self.card_values["tasks"].setText(str(counts.get("tasks", 0)))
        self.card_values["vectors"].setText(str(qdrant.get("vectors", 0)))
        self.details.setPlainText(pretty(current))


class AcceptancePage(BasePage):
    COLUMNS = [("name", "测试"), ("status", "状态"), ("duration_ms", "耗时(ms)"), ("expected", "预期"), ("actual", "实际")]

    def __init__(self, shell):
        super().__init__(shell, "一键验收中心")
        actions = QHBoxLayout()
        reset = QPushButton("重置验收库")
        reset.setObjectName("acceptanceResetButton")
        reset.clicked.connect(self.reset)
        run_all = QPushButton("运行全部验收")
        run_all.setObjectName("acceptanceRunAllButton")
        run_all.clicked.connect(self.run_all)
        latest = QPushButton("查看最近结果")
        latest.clicked.connect(self.latest)
        export = QPushButton("导出报告")
        export.clicked.connect(self.export)
        for button in (reset, run_all, latest, export):
            actions.addWidget(button)
        actions.addStretch()
        self.layout.addLayout(actions)
        self.summary = QLabel("尚未运行验收")
        self.summary.setObjectName("acceptanceSummary")
        self.layout.addWidget(self.summary)
        self.table = QTableWidget()
        self.table.setObjectName("acceptanceTable")
        self.layout.addWidget(self.table, 1)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(180)
        self.layout.addWidget(self.detail)
        self.table.itemSelectionChanged.connect(self.select_result)
        self.report: dict = {}

    def reset(self) -> None:
        self.run(lambda: self.shell.client.post("/acceptance/reset", workspace="acceptance"), self.after_reset, "正在重置验收库…")

    def after_reset(self, data: dict) -> None:
        self.report = {}
        self.summary.setText(f"验收库已重置：{data.get('database')}")
        set_table(self.table, [], self.COLUMNS)

    def run_all(self) -> None:
        self.run(lambda: self.shell.client.post("/acceptance/run-all", workspace="acceptance"), self.show_report, "正在运行全部验收，请稍候…")

    def latest(self) -> None:
        self.run(lambda: self.shell.client.get("/acceptance/results/latest", workspace="acceptance"), self.show_report)

    def show_report(self, report: dict) -> None:
        self.report = report
        self.summary.setText(f"通过 {report.get('passed', 0)} 项，失败 {report.get('failed', 0)} 项")
        set_table(self.table, report.get("results", []), self.COLUMNS)

    def select_result(self) -> None:
        row = self.table.currentRow()
        if row >= 0 and self.table.item(row, 0):
            self.detail.setPlainText(pretty(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)))

    def export(self) -> None:
        if not self.report:
            QMessageBox.information(self, "提示", "没有可导出的验收结果")
            return
        default = ROOT / "output" / "desktop-validation" / "acceptance-report.json"
        default.parent.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "导出验收报告", str(default), "JSON (*.json)")
        if path:
            Path(path).write_text(pretty(self.report), encoding="utf-8")
            self.shell.show_status(f"报告已保存：{path}")


class ImportPage(BasePage):
    def __init__(self, shell):
        super().__init__(shell, "AI 聊天导入")
        form = QFormLayout()
        self.source = QComboBox()
        self.source.addItems(["chatgpt", "codex", "claude", "gemini", "ai_chat"])
        self.title = QLineEdit("桌面导入测试")
        self.project = QLineEdit("acceptance-project")
        self.user_message = QTextEdit()
        self.assistant_message = QTextEdit()
        self.distill = QCheckBox("导入后立即蒸馏")
        self.distill.setChecked(True)
        form.addRow("来源平台", self.source)
        form.addRow("会话标题", self.title)
        form.addRow("所属项目", self.project)
        form.addRow("用户消息", self.user_message)
        form.addRow("AI 消息", self.assistant_message)
        form.addRow("", self.distill)
        self.layout.addLayout(form)
        actions = QHBoxLayout()
        submit = QPushButton("导入当前表单")
        submit.setObjectName("importConversationButton")
        submit.clicked.connect(self.submit)
        choose = QPushButton("选择 JSON 文件")
        choose.clicked.connect(self.choose_json)
        actions.addWidget(submit)
        actions.addWidget(choose)
        actions.addStretch()
        self.layout.addLayout(actions)
        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.layout.addWidget(self.result, 1)

    def submit(self) -> None:
        if not self.user_message.toPlainText().strip():
            QMessageBox.warning(self, "缺少内容", "请填写用户消息")
            return
        if not self.confirm_write("将这段聊天写入当前记忆空间？"):
            return
        messages = [{"role": "user", "content": self.user_message.toPlainText()}]
        if self.assistant_message.toPlainText().strip():
            messages.append({"role": "assistant", "content": self.assistant_message.toPlainText()})
        payload = {
            "conversation": {
                "source": self.source.currentText(),
                "title": self.title.text(),
                "project": self.project.text() or "global",
                "messages": messages,
            },
            "distill": self.distill.isChecked(),
        }
        self.run(lambda: self.shell.client.post("/memory/import", payload), lambda data: self.result.setPlainText(pretty(data)), "正在导入聊天…")

    def choose_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择聊天 JSON", str(ROOT / "data"), "JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            conversation = data.get("conversation", data)
            payload = {"conversation": conversation, "distill": self.distill.isChecked()}
        except Exception as exc:
            QMessageBox.critical(self, "JSON 错误", str(exc))
            return
        if self.confirm_write("将所选 JSON 写入当前记忆空间？"):
            self.run(lambda: self.shell.client.post("/memory/import", payload), lambda result: self.result.setPlainText(pretty(result)), "正在导入 JSON…")


class MemoryPage(BasePage):
    COLUMNS = [("memory_type", "类型"), ("title", "标题"), ("project", "项目"), ("status", "状态"), ("importance", "重要度"), ("confidence", "可信度"), ("updated_at", "更新时间")]

    def __init__(self, shell):
        super().__init__(shell, "记忆审核中心")
        filters = QHBoxLayout()
        self.status_filter = QComboBox()
        self.status_filter.addItems(["", "pending", "active", "conflicted", "superseded", "rejected", "archived"])
        self.type_filter = QComboBox()
        self.type_filter.addItems(["", "RULE", "DECISION", "PREFERENCE", "TASK", "LESSON", "FACT", "EPISODE"])
        self.project_filter = QLineEdit()
        self.project_filter.setPlaceholderText("项目")
        self.query = QLineEdit()
        self.query.setPlaceholderText("标题或内容")
        refresh = QPushButton("查询")
        refresh.clicked.connect(self.refresh)
        for widget in (QLabel("状态"), self.status_filter, QLabel("类型"), self.type_filter, self.project_filter, self.query, refresh):
            filters.addWidget(widget)
        self.layout.addLayout(filters)
        split = QSplitter()
        self.table = QTableWidget()
        self.table.setObjectName("memoryTable")
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        split.addWidget(self.table)
        split.addWidget(self.detail)
        split.setSizes([750, 450])
        self.layout.addWidget(split, 1)
        actions = QHBoxLayout()
        approve = QPushButton("批准")
        approve.setObjectName("approveMemoryButton")
        approve.clicked.connect(lambda: self.review("approve"))
        reject = QPushButton("拒绝")
        reject.setObjectName("rejectMemoryButton")
        reject.clicked.connect(lambda: self.review("reject"))
        supersede = QPushButton("新规则覆盖")
        supersede.clicked.connect(self.supersede)
        for button in (approve, reject, supersede):
            actions.addWidget(button)
        actions.addStretch()
        self.layout.addLayout(actions)
        self.table.itemSelectionChanged.connect(self.load_detail)

    def refresh(self) -> None:
        params = {"status": self.status_filter.currentText(), "memory_type": self.type_filter.currentText(), "project": self.project_filter.text(), "query": self.query.text(), "limit": 300}
        self.run(lambda: self.shell.client.get("/memory/list", params=params), lambda data: set_table(self.table, data.get("items", []), self.COLUMNS), "正在读取记忆…")

    def selected(self) -> dict | None:
        row = self.table.currentRow()
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) if row >= 0 and self.table.item(row, 0) else None

    def load_detail(self) -> None:
        item = self.selected()
        if item:
            self.run(lambda: self.shell.client.get(f"/memory/{item['id']}"), lambda data: self.detail.setPlainText(pretty(data)))

    def review(self, action: str) -> None:
        item = self.selected()
        if not item:
            QMessageBox.information(self, "提示", "请先选择一条记忆")
            return
        label = "批准" if action == "approve" else "拒绝"
        if not self.confirm_write(f"确认{label}记忆“{item['title']}”？"):
            return
        self.run(lambda: self.shell.client.post(f"/memory/{action}", {"memory_id": item["id"], "reason": "desktop review"}), lambda _: self.refresh(), f"正在{label}…")

    def supersede(self) -> None:
        item = self.selected()
        if not item:
            QMessageBox.information(self, "提示", "请先选择旧规则")
            return
        content, ok = self.shell.ask_text("新规则内容", "请输入替代后的规则")
        if not ok or not content.strip() or not self.confirm_write("确认使用新规则覆盖当前规则？"):
            return
        payload = {"old_memory_id": item["id"], "new_memory": {"memory_type": item["memory_type"], "title": item["title"], "content": content, "project": item.get("project") or "global"}, "reason": "desktop supersede"}
        self.run(lambda: self.shell.client.post("/memory/supersede", payload), lambda _: self.refresh(), "正在覆盖规则…")


class SearchPage(BasePage):
    def __init__(self, shell):
        super().__init__(shell, "搜索与 Codex 上下文")
        tabs = QTabWidget()
        tabs.addTab(self._search_tab(), "记忆搜索")
        tabs.addTab(self._context_tab(), "Codex 上下文")
        self.layout.addWidget(tabs, 1)

    def _search_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.search_query = QLineEdit()
        self.search_query.setPlaceholderText("输入查询")
        self.search_project = QLineEdit("acceptance-project")
        self.search_active = QCheckBox("仅 active")
        self.search_active.setChecked(True)
        self.search_knowledge = QCheckBox("包含 Obsidian")
        self.search_knowledge.setChecked(True)
        button = QPushButton("搜索")
        button.setObjectName("searchButton")
        button.clicked.connect(self.search)
        for widget in (self.search_query, self.search_project, self.search_active, self.search_knowledge, button):
            row.addWidget(widget)
        layout.addLayout(row)
        self.search_result = QTextEdit()
        self.search_result.setReadOnly(True)
        layout.addWidget(self.search_result)
        return page

    def _context_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.context_project = QLineEdit("acceptance-project")
        self.context_task = QTextEdit()
        self.context_task.setPlaceholderText("输入 Codex 当前任务")
        button = QPushButton("生成上下文")
        button.setObjectName("contextButton")
        button.clicked.connect(self.context)
        layout.addWidget(QLabel("项目"))
        layout.addWidget(self.context_project)
        layout.addWidget(QLabel("当前任务"))
        layout.addWidget(self.context_task)
        layout.addWidget(button)
        self.context_result = QTextEdit()
        self.context_result.setReadOnly(True)
        layout.addWidget(self.context_result, 1)
        return page

    def search(self) -> None:
        payload = {"query": self.search_query.text(), "project": self.search_project.text() or None, "active_only": self.search_active.isChecked(), "include_knowledge": self.search_knowledge.isChecked(), "top_k": 20}
        self.run(lambda: self.shell.client.post("/memory/search", payload), lambda data: self.search_result.setPlainText(pretty(data)), "正在搜索…")

    def context(self) -> None:
        payload = {"project": self.context_project.text() or "global", "task": self.context_task.toPlainText(), "max_tokens": 6000}
        self.run(lambda: self.shell.client.post("/memory/context", payload), lambda data: self.context_result.setPlainText(pretty(data)), "正在生成上下文…")


class ConflictPage(BasePage):
    COLUMNS = [("id", "冲突ID"), ("memory_id", "新记忆"), ("conflicting_memory_id", "旧记忆"), ("reason", "原因"), ("created_at", "时间")]

    def __init__(self, shell):
        super().__init__(shell, "冲突与规则覆盖")
        refresh = QPushButton("刷新冲突")
        refresh.clicked.connect(self.refresh)
        self.layout.addWidget(refresh, 0, Qt.AlignmentFlag.AlignLeft)
        self.table = QTableWidget()
        self.layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        for action, label in (("keep_old", "保留旧规则"), ("use_new", "采用新规则"), ("keep_both", "两条都保留"), ("resolved", "标记已解决")):
            button = QPushButton(label)
            button.clicked.connect(lambda _=False, value=action: self.resolve(value))
            actions.addWidget(button)
        actions.addStretch()
        self.layout.addLayout(actions)

    def refresh(self) -> None:
        self.run(lambda: self.shell.client.get("/memory/conflicts"), lambda data: set_table(self.table, data.get("conflicts", []), self.COLUMNS))

    def resolve(self, action: str) -> None:
        row = self.table.currentRow()
        item = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) if row >= 0 and self.table.item(row, 0) else None
        if not item or not self.confirm_write("确认解决所选冲突？"):
            return
        self.run(lambda: self.shell.client.post(f"/memory/conflicts/{item['id']}/resolve", {"action": action, "reason": "desktop conflict resolution"}), lambda _: self.refresh(), "正在解决冲突…")


class KnowledgePage(BasePage):
    COLUMNS = [("title", "标题"), ("project", "项目"), ("source_path", "路径"), ("version", "版本"), ("chunk_count", "分块"), ("updated_at", "更新时间")]

    def __init__(self, shell):
        super().__init__(shell, "Obsidian 知识管理")
        actions = QHBoxLayout()
        refresh = QPushButton("刷新文档")
        refresh.clicked.connect(self.refresh)
        index = QPushButton("索引 Markdown")
        index.clicked.connect(self.index_file)
        scan = QPushButton("单次扫描")
        scan.clicked.connect(self.scan_once)
        for button in (refresh, index, scan):
            actions.addWidget(button)
        actions.addStretch()
        self.layout.addLayout(actions)
        split = QSplitter()
        self.table = QTableWidget()
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        split.addWidget(self.table)
        split.addWidget(self.detail)
        self.layout.addWidget(split, 1)
        self.table.itemSelectionChanged.connect(self.load_detail)

    def refresh(self) -> None:
        self.run(lambda: self.shell.client.get("/knowledge/documents"), lambda data: set_table(self.table, data.get("documents", []), self.COLUMNS), "正在读取知识文档…")

    def load_detail(self) -> None:
        row = self.table.currentRow()
        item = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) if row >= 0 and self.table.item(row, 0) else None
        if item:
            self.run(lambda: self.shell.client.get(f"/knowledge/documents/{item['id']}"), lambda data: self.detail.setPlainText(pretty(data)))

    def index_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 Markdown", str(ROOT / "data"), "Markdown (*.md)")
        if path and self.confirm_write("确认索引所选 Markdown？"):
            self.run(lambda: self.shell.client.post("/knowledge/index", {"path": path}), lambda data: (self.detail.setPlainText(pretty(data)), self.refresh()), "正在索引文档…")

    def scan_once(self) -> None:
        if self.confirm_write("确认扫描当前空间限定目录？"):
            self.run(lambda: self.shell.client.post("/system/watcher/scan-once"), lambda data: (self.detail.setPlainText(pretty(data)), self.refresh()), "正在执行单次扫描…")


class ActivityPage(BasePage):
    def __init__(self, shell):
        super().__init__(shell, "Codex 任务、项目与时间线")
        refresh = QPushButton("刷新全部")
        refresh.clicked.connect(self.refresh)
        self.layout.addWidget(refresh, 0, Qt.AlignmentFlag.AlignLeft)
        tabs = QTabWidget()
        self.tasks = QTextEdit(); self.tasks.setReadOnly(True)
        self.projects = QTextEdit(); self.projects.setReadOnly(True)
        self.timeline = QTextEdit(); self.timeline.setReadOnly(True)
        tabs.addTab(self.tasks, "Codex 任务")
        tabs.addTab(self.projects, "项目")
        tabs.addTab(self.timeline, "时间线")
        self.layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        self.run(
            lambda: {
                "tasks": self.shell.client.get("/memory/tasks"),
                "projects": self.shell.client.get("/memory/projects"),
                "timeline": self.shell.client.get("/memory/timeline"),
            },
            self.show_data,
            "正在读取活动数据…",
        )

    def show_data(self, data: dict) -> None:
        self.tasks.setPlainText(pretty(data["tasks"]))
        self.projects.setPlainText(pretty(data["projects"]))
        self.timeline.setPlainText(pretty(data["timeline"]))


class SystemPage(BasePage):
    def __init__(self, shell):
        super().__init__(shell, "系统与监听器")
        actions = QGridLayout()
        definitions = [
            ("查看状态", self.refresh), ("启动监听器", lambda: self.watcher("start")),
            ("停止监听器", lambda: self.watcher("stop")), ("执行单次扫描", self.scan),
            ("重建 Qdrant", self.rebuild), ("查看 API 日志", lambda: self.logs("api")),
            ("查看监听日志", lambda: self.logs("watcher")), ("打开日志目录", lambda: self.open_dir(ROOT / "logs" / "second_brain")),
            ("打开数据目录", lambda: self.open_dir(ROOT / "data")), ("打开原始归档", lambda: self.open_dir(ROOT / "data" / "raw")),
        ]
        for index, (label, callback) in enumerate(definitions):
            button = QPushButton(label)
            if label == "启动监听器":
                button.setObjectName("startWatcherButton")
            if label == "停止监听器":
                button.setObjectName("stopWatcherButton")
            button.clicked.connect(callback)
            actions.addWidget(button, index // 4, index % 4)
        self.layout.addLayout(actions)
        self.stop_api_on_exit = QCheckBox("退出桌面 UI 时同时停止 API（默认关闭）")
        self.layout.addWidget(self.stop_api_on_exit)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.layout.addWidget(self.output, 1)

    def refresh(self) -> None:
        self.run(lambda: self.shell.client.get("/system/status", workspace="production"), lambda data: self.output.setPlainText(pretty(data)))

    def watcher(self, action: str) -> None:
        self.run(lambda: self.shell.client.post(f"/system/watcher/{action}", workspace="production"), lambda data: self.output.setPlainText(pretty(data)), f"正在{action}监听器…")

    def scan(self) -> None:
        if self.confirm_write("确认扫描当前空间限定目录？"):
            self.run(lambda: self.shell.client.post("/system/watcher/scan-once"), lambda data: self.output.setPlainText(pretty(data)), "正在扫描…")

    def rebuild(self) -> None:
        if self.confirm_write("确认重建当前空间 Qdrant？"):
            self.run(lambda: self.shell.client.post("/memory/rebuild-qdrant"), lambda data: self.output.setPlainText(pretty(data)), "正在重建 Qdrant…")

    def logs(self, component: str) -> None:
        self.run(lambda: self.shell.client.get("/system/logs", params={"component": component}), lambda data: self.output.setPlainText("\n".join(data.get("lines", []))))

    @staticmethod
    def open_dir(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))
