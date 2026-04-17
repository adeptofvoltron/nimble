import logging
from unittest.mock import MagicMock, patch

import pytest

from nimble.hotkeys.windows import WindowsHotkeyAdapter


def test_register_stores_pynput_format() -> None:
    adapter = WindowsHotkeyAdapter()

    def cb() -> None:
        return None

    adapter.register("ctrl+shift+d", cb)
    assert adapter._hotkeys == {"<ctrl>+<shift>+d": cb}


def test_register_duplicate_raises_value_error() -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.register("ctrl+shift+d", lambda: None)
    with pytest.raises(ValueError, match="already registered"):
        adapter.register("ctrl+shift+d", lambda: None)


def test_start_warns_on_reserved_hotkey(caplog: pytest.LogCaptureFixture) -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.register("win+l", lambda: None)
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with caplog.at_level(logging.WARNING, logger="nimble.hotkeys.windows"):
        with patch(
            "nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard
        ):
            adapter.start()
    assert any(
        "reserved" in r.message.lower() and "<win>+l" in r.message
        for r in caplog.records
    )
    mock_listener.start.assert_called_once()


def test_start_warns_on_ctrl_alt_del_shorthand(
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.register("ctrl+alt+del", lambda: None)
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with caplog.at_level(logging.WARNING, logger="nimble.hotkeys.windows"):
        with patch(
            "nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard
        ):
            adapter.start()
    assert any(
        "reserved" in r.message.lower() and "<ctrl>+<alt>+del" in r.message
        for r in caplog.records
    )


def test_start_no_warning_for_normal_shortcut(caplog: pytest.LogCaptureFixture) -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.register("ctrl+shift+d", lambda: None)
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with caplog.at_level(logging.WARNING, logger="nimble.hotkeys.windows"):
        with patch(
            "nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard
        ):
            adapter.start()
    assert len(caplog.records) == 0


def test_start_twice_without_stop_raises() -> None:
    adapter = WindowsHotkeyAdapter()
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
        adapter.start()
        with pytest.raises(RuntimeError, match="already started"):
            adapter.start()


def test_stop_before_start_is_noop() -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.stop()  # must not raise


def test_stop_calls_listener_stop_and_join() -> None:
    adapter = WindowsHotkeyAdapter()
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
        adapter.start()
    adapter.stop()
    mock_listener.stop.assert_called_once()
    mock_listener.join.assert_called_once()


def test_stop_twice_after_start_is_noop() -> None:
    adapter = WindowsHotkeyAdapter()
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
        adapter.start()
    adapter.stop()
    adapter.stop()  # second stop must be a no-op
    mock_listener.stop.assert_called_once()
    mock_listener.join.assert_called_once()
