from PySide6.QtWidgets import QMainWindow, QTabWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioForge")
        self.resize(900, 600)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
