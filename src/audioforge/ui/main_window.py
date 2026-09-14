from PySide6.QtWidgets import QMainWindow, QTabWidget

from audioforge import config
from audioforge.core import queue_db
from audioforge.ui.download_tab import DownloadTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioForge")
        self.resize(900, 600)

        self.db_conn = queue_db.connect(config.get_db_path())

        self.tabs = QTabWidget()
        download_tab = DownloadTab(db_conn=self.db_conn)
        self.tabs.addTab(download_tab, "Download")
        self.setCentralWidget(self.tabs)
