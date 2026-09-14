"""AudioForge entry point."""
import sys

from PySide6.QtWidgets import QApplication

from audioforge.ui.main_window import MainWindow
from audioforge.ui.theme import DARK_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
