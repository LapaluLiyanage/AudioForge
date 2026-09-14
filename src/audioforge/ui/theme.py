"""Dark theme QSS for the whole application."""

DARK_STYLESHEET = """
QWidget { background-color: #1e1f22; color: #e6e6e6; font-size: 13px; }
QMainWindow { background-color: #1e1f22; }
QTabWidget::pane { border: 1px solid #33353a; }
QTabBar::tab { background: #2a2b2e; padding: 8px 16px; color: #c8c8c8; }
QTabBar::tab:selected { background: #3a3d42; color: #ffffff; }
QPushButton { background-color: #3a3d42; border: 1px solid #4a4d52; padding: 6px 12px; border-radius: 4px; }
QPushButton:hover { background-color: #4a4d52; }
QPushButton:disabled { color: #6a6a6a; }
QLineEdit, QComboBox, QSpinBox { background-color: #2a2b2e; border: 1px solid #4a4d52; padding: 4px; border-radius: 3px; }
QTableWidget { background-color: #232427; gridline-color: #33353a; }
QProgressBar { border: 1px solid #4a4d52; border-radius: 3px; text-align: center; }
QProgressBar::chunk { background-color: #5a8fdc; }
QHeaderView::section { background-color: #2a2b2e; padding: 4px; border: none; }
"""
