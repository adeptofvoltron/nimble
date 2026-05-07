from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from nimble.hotkeys.wayland import WaylandXWaylandAdapter


def _make_mocks() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    mock_win = MagicMock()
    mock_root = MagicMock()
    mock_root.create_window.return_value = mock_win
    mock_screen = MagicMock()
    mock_screen.root = mock_root
    mock_disp = MagicMock()
    mock_disp.screen.return_value = mock_screen
    mock_display_mod = MagicMock()
    mock_display_mod.Display.return_value = mock_disp
    mock_X = MagicMock()
    mock_X.InputOnly = 2
    mock_X.CopyFromParent = 0
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys.return_value = MagicMock()
    return mock_win, mock_disp, mock_display_mod, mock_X, mock_keyboard


def _start(
    adapter: WaylandXWaylandAdapter,
    mock_display_mod: MagicMock,
    mock_X: MagicMock,
    mock_keyboard: MagicMock,
) -> None:
    with (
        patch("nimble.hotkeys.wayland._xlib_display", return_value=mock_display_mod),
        patch("nimble.hotkeys.wayland._xlib_x", return_value=mock_X),
        patch("nimble.hotkeys.x11._pynput_keyboard", return_value=mock_keyboard),
        patch.dict(os.environ, {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}),
    ):
        adapter.start()


def test_start_creates_inputonly_window_before_listener() -> None:
    adapter = WaylandXWaylandAdapter()
    mock_win, mock_disp, mock_display_mod, mock_X, mock_keyboard = _make_mocks()
    mock_listener = mock_keyboard.GlobalHotKeys.return_value

    call_order: list[str] = []
    mock_win.map.side_effect = lambda: call_order.append("map")
    mock_disp.flush.side_effect = lambda: call_order.append("flush")
    mock_listener.start.side_effect = lambda: call_order.append("listener_start")

    _start(adapter, mock_display_mod, mock_X, mock_keyboard)

    mock_disp.screen.return_value.root.create_window.assert_called_once_with(
        0, 0, 1, 1, 0, 0, mock_X.InputOnly, mock_X.CopyFromParent
    )
    assert call_order == ["map", "flush", "listener_start"]


def test_stop_destroys_window_after_listener() -> None:
    adapter = WaylandXWaylandAdapter()
    mock_win, mock_disp, mock_display_mod, mock_X, mock_keyboard = _make_mocks()
    mock_listener = mock_keyboard.GlobalHotKeys.return_value

    call_order: list[str] = []
    mock_listener.stop.side_effect = lambda: call_order.append("listener_stop")
    mock_listener.join.side_effect = lambda: call_order.append("listener_join")
    mock_win.destroy.side_effect = lambda: call_order.append("win_destroy")
    mock_disp.close.side_effect = lambda: call_order.append("disp_close")

    _start(adapter, mock_display_mod, mock_X, mock_keyboard)
    adapter.stop()

    assert call_order == ["listener_stop", "listener_join", "win_destroy", "disp_close"]


def test_stop_before_start_is_noop() -> None:
    adapter = WaylandXWaylandAdapter()
    adapter.stop()


def test_register_duplicate_raises_value_error() -> None:
    adapter = WaylandXWaylandAdapter()
    adapter.register("ctrl+shift+h", lambda: None)
    with pytest.raises(ValueError, match="already registered"):
        adapter.register("ctrl+shift+h", lambda: None)


def test_start_raises_when_display_open_fails() -> None:
    adapter = WaylandXWaylandAdapter()
    mock_display_mod = MagicMock()
    mock_display_mod.Display.side_effect = Exception("no display")
    mock_X = MagicMock()

    with (
        patch("nimble.hotkeys.wayland._xlib_display", return_value=mock_display_mod),
        patch("nimble.hotkeys.wayland._xlib_x", return_value=mock_X),
        patch.dict(os.environ, {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}),
    ):
        with pytest.raises(RuntimeError, match="cannot open X display"):
            adapter.start()


def test_stop_window_destroy_failure_does_not_raise() -> None:
    adapter = WaylandXWaylandAdapter()
    mock_win, mock_disp, mock_display_mod, mock_X, mock_keyboard = _make_mocks()
    mock_win.destroy.side_effect = Exception("oops")

    _start(adapter, mock_display_mod, mock_X, mock_keyboard)
    adapter.stop()
