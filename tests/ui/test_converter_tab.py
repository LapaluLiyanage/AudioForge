from audioforge.ui.converter_tab import ConverterTab


def test_add_files_populates_table(qtbot):
    tab = ConverterTab()
    qtbot.addWidget(tab)

    tab.add_files(["/music/track1.wav", "/music/track2.mp3"])

    assert tab.file_table.rowCount() == 2
    assert tab.file_table.item(0, 0).text() == "track1.wav"


def test_convert_all_disabled_when_no_files(qtbot):
    tab = ConverterTab()
    qtbot.addWidget(tab)
    assert not tab.convert_all_btn.isEnabled()

    tab.add_files(["/music/track1.wav"])
    assert tab.convert_all_btn.isEnabled()
