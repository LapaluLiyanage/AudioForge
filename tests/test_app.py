from unittest.mock import MagicMock

from audioforge import app


def test_main_returns_early_without_constructing_main_window_on_decline(qtbot, monkeypatch):
    monkeypatch.setattr(app, "show_disclaimer_if_needed", lambda: False)
    mock_main_window_cls = MagicMock()
    monkeypatch.setattr(app, "MainWindow", mock_main_window_cls)

    result = app.main()

    assert result == 0
    mock_main_window_cls.assert_not_called()
