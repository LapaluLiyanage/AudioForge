"""AudioForge entry point."""
import sys

from PySide6.QtWidgets import QApplication

from audioforge.ui.disclaimer_dialog import show_disclaimer_if_needed
from audioforge.ui.main_window import MainWindow
from audioforge.ui.theme import DARK_STYLESHEET


def main() -> int:
    # Reuse an existing QApplication instance if one is already running (e.g.
    # under pytest-qt, which creates one for the test session) rather than
    # constructing a second one, which PySide6 refuses.
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    if not show_disclaimer_if_needed():
        return 0
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
