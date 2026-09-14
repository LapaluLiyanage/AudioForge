from audioforge.ui.download_tab import DownloadTab


def test_add_to_queue_disabled_until_url_entered(qtbot):
    tab = DownloadTab(db_conn=None)
    qtbot.addWidget(tab)

    assert not tab.add_to_queue_btn.isEnabled()

    qtbot.keyClicks(tab.url_input, "https://youtube.com/watch?v=abc")

    assert tab.add_to_queue_btn.isEnabled()


def test_bit_depth_disabled_for_lossy_formats(qtbot):
    tab = DownloadTab(db_conn=None)
    qtbot.addWidget(tab)

    tab.format_combo.setCurrentText("mp3")

    assert not tab.bit_depth_combo.isEnabled()

    tab.format_combo.setCurrentText("flac")

    assert tab.bit_depth_combo.isEnabled()
