from audioforge.ui.main_window import MainWindow


def test_main_window_has_correct_title(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "AudioForge"
