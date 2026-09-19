from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from audioforge import config
from audioforge.core import queue_db
from audioforge.ui.converter_tab import ConverterTab
from audioforge.ui.download_tab import DownloadTab
from audioforge.ui.queue_grid import QueueGrid
from audioforge.ui.settings_dialog import SettingsDialog

SIDEBAR_WIDTH = 76
RIGHT_PANEL_WIDTH = 340


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioForge")
        self.resize(1240, 760)

        self.db_conn = queue_db.connect(config.get_db_path())

        self.queue_grid = QueueGrid()
        self.download_tab = DownloadTab(db_conn=self.db_conn, queue_grid=self.queue_grid)
        self.converter_tab = ConverterTab(queue_grid=self.queue_grid)
        self.queue_grid.changed.connect(self._refresh_status_pill)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_center(), 1)
        root.addWidget(self._build_right_panel())

        self.setCentralWidget(central)
        self._build_menu()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 26, 0, 26)
        layout.setSpacing(22)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        logo = QLabel("Af")
        logo.setObjectName("logo")
        logo.setFixedSize(34, 34)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch(1)
        return sidebar

    def _build_center(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Conversion queue")
        title.setObjectName("screenTitle")
        header.addWidget(title)

        self.status_pill = QLabel("Idle")
        self.status_pill.setObjectName("statusPill")
        header.addWidget(self.status_pill)
        header.addStretch(1)
        layout.addLayout(header)

        layout.addWidget(self.queue_grid, 1)
        return container

    def _build_right_panel(self) -> QScrollArea:
        panel = QScrollArea()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(RIGHT_PANEL_WIDTH)
        panel.setWidgetResizable(True)
        panel.setFrameShape(QFrame.Shape.NoFrame)

        host = QWidget()
        host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(24, 26, 24, 26)
        layout.setSpacing(20)
        layout.addWidget(self.download_tab)
        layout.addWidget(self.converter_tab)
        layout.addWidget(self.converter_tab.output_card)
        layout.addStretch(1)

        panel.setWidget(host)
        return panel

    def _refresh_status_pill(self) -> None:
        self.status_pill.setText("Converting" if self.queue_grid.has_active_items() else "Idle")

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self._open_settings_dialog)
        file_menu.addAction(settings_action)

    def _open_settings_dialog(self) -> None:
        settings = QSettings("AudioForge", "AudioForge")
        dialog = SettingsDialog(settings, self)
        dialog.exec()

    def closeEvent(self, event) -> None:
        self.download_tab.shutdown()
        self.converter_tab.shutdown()
        self.db_conn.close()
        event.accept()
