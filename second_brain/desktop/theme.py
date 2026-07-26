APP_STYLE = """
QWidget { font-family: "Microsoft YaHei UI"; font-size: 13px; color: #1f2937; }
QMainWindow, QStackedWidget, QStackedWidget > QWidget { background: #f3f5f8; }
QListWidget { background: #172033; color: #e5e7eb; border: none; padding: 10px; }
QListWidget::item { padding: 12px 14px; margin: 2px; border-radius: 6px; }
QListWidget::item:selected { background: #315efb; color: white; }
QFrame#topbar, QFrame#card { background: white; border: 1px solid #dfe3ea; border-radius: 8px; }
QLabel#title { font-size: 22px; font-weight: 700; }
QLabel#cardValue { font-size: 24px; font-weight: 700; color: #315efb; }
QPushButton { background: #315efb; color: white; border: none; border-radius: 6px; padding: 8px 14px; }
QPushButton:hover { background: #2448ca; }
QPushButton:disabled { background: #aeb7cc; }
QPushButton#danger { background: #c53b3b; }
QPushButton#secondary { background: #64748b; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox { background: white; border: 1px solid #cfd5df; border-radius: 5px; padding: 6px; }
QTableWidget { background: white; border: 1px solid #dfe3ea; gridline-color: #e5e7eb; }
QHeaderView::section { background: #eef1f6; padding: 7px; border: none; font-weight: 600; }
QStatusBar { background: white; border-top: 1px solid #dfe3ea; }
"""
