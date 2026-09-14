from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QTabWidget

from audioforge import config
from audioforge.core import queue_db
from audioforge.ui.download_tab import DownloadTab
from audioforge.ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioForge")
        self.resize(900, 600)

        self.db_conn = queue_db.connect(config.get_db_path())

        self.tabs = QTabWidget()
        self.download_tab = DownloadTab(db_conn=self.db_conn)
        self.tabs.addTab(self.download_tab, "Download")
        self.setCentralWidget(self.tabs)

        self._build_menu()

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
        self.db_conn.close()
        event.accept()
