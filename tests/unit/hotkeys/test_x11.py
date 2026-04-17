import os
from unittest.mock import MagicMock, patch

import pytest

from nimble.hotkeys.x11 import X11HotkeyAdapter, _to_pynput_format


def test_shortcut_format_conversion() -> None:
    assert _to_pynput_format("ctrl+shift+d") == "<ctrl>+<shift>+d"
    assert _to_pynput_format("ctrl+a") == "<ctrl>+a"


def test_start_raises_on_wayland_without_xwayland() -> None:
    adapter = X11HotkeyAdapter()
    env = {"WAYLAND_DISPLAY": "wayland-0"}
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("DISPLAY", None)
        with pytest.raises(RuntimeError, match="XWayland"):
            adapter.start()


def test_start_succeeds_with_xwayland_present() -> None:
    adapter = X11HotkeyAdapter()
    mock_listener = MagicMock()
    with patch("nimble.hotkeys.x11.keyboard.GlobalHotKeys", return_value=mock_listener):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}):
            adapter.start()
    mock_listener.start.assert_called_once()


def test_stop_before_start_is_noop() -> None:
    adapter = X11HotkeyAdapter()
    adapter.stop()  # must not raise


def test_stop_calls_listener_stop_and_join() -> None:
    adapter = X11HotkeyAdapter()
    mock_listener = MagicMock()
    with patch("nimble.hotkeys.x11.keyboard.GlobalHotKeys", return_value=mock_listener):
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
            os.environ.pop("WAYLAND_DISPLAY", None)
            adapter.start()
    adapter.stop()
    mock_listener.stop.assert_called_once()
    mock_listener.join.assert_called_once()
