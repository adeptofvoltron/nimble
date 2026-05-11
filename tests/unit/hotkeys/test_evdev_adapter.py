from __future__ import annotations

import os
import threading
from unittest.mock import MagicMock, patch

import pytest
from evdev import ecodes

from nimble.hotkeys.evdev_adapter import EvdevAdapter, _parse_shortcut


def _make_mock_evdev(
    keyboard_paths: tuple[str, ...] = ("/dev/input/event0",),
) -> MagicMock:
    mock_evdev = MagicMock()
    mock_evdev.ecodes.EV_KEY = ecodes.EV_KEY
    mock_evdev.list_devices.return_value = list(keyboard_paths)

    def make_device(path: str) -> MagicMock:
        dev = MagicMock()
        dev.path = path
        dev.fd = abs(hash(path)) % 900 + 100
        dev.capabilities.return_value = {ecodes.EV_KEY: []}
        return dev

    mock_evdev.InputDevice.side_effect = make_device
    return mock_evdev


def _build_real_modifier_map() -> dict[int, str]:
    return {
        ecodes.KEY_LEFTCTRL: "ctrl", ecodes.KEY_RIGHTCTRL: "ctrl",
        ecodes.KEY_LEFTSHIFT: "shift", ecodes.KEY_RIGHTSHIFT: "shift",
        ecodes.KEY_LEFTALT: "alt", ecodes.KEY_RIGHTALT: "alt",
        ecodes.KEY_LEFTMETA: "super", ecodes.KEY_RIGHTMETA: "super",
    }


def test_parse_shortcut_single_modifier() -> None:
    mods, code = _parse_shortcut("ctrl+l")
    assert mods == frozenset({"ctrl"})
    assert code == ecodes.KEY_L


def test_parse_shortcut_multiple_modifiers() -> None:
    mods, code = _parse_shortcut("ctrl+shift+h")
    assert mods == frozenset({"ctrl", "shift"})
    assert code == ecodes.KEY_H


def test_parse_shortcut_raises_no_trigger_key() -> None:
    with pytest.raises(ValueError, match="exactly one non-modifier"):
        _parse_shortcut("ctrl+shift")


def test_parse_shortcut_raises_unknown_key() -> None:
    with pytest.raises(ValueError, match="Cannot map"):
        _parse_shortcut("ctrl+notakey")


def test_register_raises_on_duplicate() -> None:
    adapter = EvdevAdapter()
    adapter.register("ctrl+l", lambda: None)
    with pytest.raises(ValueError, match="already registered"):
        adapter.register("ctrl+l", lambda: None)


def test_stop_before_start_is_noop() -> None:
    adapter = EvdevAdapter()
    adapter.stop()


def test_open_keyboard_devices_returns_keyboards() -> None:
    mock_evdev = _make_mock_evdev()
    adapter = EvdevAdapter()
    devices = adapter._open_keyboard_devices(mock_evdev)
    assert len(devices) == 1


def test_open_keyboard_devices_skips_non_keyboard_devices() -> None:
    mock_evdev = _make_mock_evdev()
    non_kb = MagicMock()
    non_kb.capabilities.return_value = {}
    mock_evdev.InputDevice.side_effect = lambda path: non_kb
    adapter = EvdevAdapter()
    devices = adapter._open_keyboard_devices(mock_evdev)
    assert devices == []
    non_kb.close.assert_called_once()


def test_open_keyboard_devices_raises_on_permission_error() -> None:
    mock_evdev = _make_mock_evdev()
    mock_evdev.InputDevice.side_effect = PermissionError("denied")
    adapter = EvdevAdapter()
    with pytest.raises(RuntimeError, match="input"):
        adapter._open_keyboard_devices(mock_evdev)


def test_start_raises_when_no_keyboard_devices() -> None:
    mock_evdev = _make_mock_evdev(keyboard_paths=())
    adapter = EvdevAdapter()
    with patch("nimble.hotkeys.evdev_adapter._evdev", return_value=mock_evdev):
        with pytest.raises(RuntimeError, match="No keyboard devices"):
            adapter.start()


def test_run_loop_fires_callback_on_matching_hotkey() -> None:
    adapter = EvdevAdapter()
    fired = threading.Event()
    adapter.register("ctrl+l", fired.set)
    trigger_code = adapter._hotkeys["ctrl+l"][1]
    modifier_map = _build_real_modifier_map()

    pipe_r, pipe_w = os.pipe()
    adapter._pipe_r = pipe_r

    ev_ctrl = MagicMock(type=ecodes.EV_KEY, code=ecodes.KEY_LEFTCTRL, value=1)
    ev_l = MagicMock(type=ecodes.EV_KEY, code=trigger_code, value=1)

    mock_dev = MagicMock()
    mock_dev.fd = 5
    mock_dev.path = "/dev/input/event0"

    read_count = [0]

    def fake_read() -> list:
        read_count[0] += 1
        if read_count[0] == 1:
            return [ev_ctrl, ev_l]
        raise BlockingIOError()

    mock_dev.read.side_effect = fake_read

    select_results = iter([([5], [], []), ([pipe_r], [], [])])
    with patch("select.select", side_effect=lambda *a, **kw: next(select_results)):
        try:
            adapter._run_loop([mock_dev], modifier_map)
        finally:
            os.close(pipe_r)
            os.close(pipe_w)
    fired.wait(timeout=2)
    assert fired.is_set()


def test_run_loop_does_not_fire_with_wrong_modifiers() -> None:
    adapter = EvdevAdapter()
    fired = threading.Event()
    adapter.register("ctrl+shift+l", fired.set)
    trigger_code = adapter._hotkeys["ctrl+shift+l"][1]
    modifier_map = _build_real_modifier_map()

    pipe_r, pipe_w = os.pipe()
    adapter._pipe_r = pipe_r

    ev_ctrl = MagicMock(type=ecodes.EV_KEY, code=ecodes.KEY_LEFTCTRL, value=1)
    ev_l = MagicMock(type=ecodes.EV_KEY, code=trigger_code, value=1)

    mock_dev = MagicMock()
    mock_dev.fd = 5
    mock_dev.path = "/dev/input/event0"

    read_count = [0]

    def fake_read() -> list:
        read_count[0] += 1
        if read_count[0] == 1:
            return [ev_ctrl, ev_l]
        raise BlockingIOError()

    mock_dev.read.side_effect = fake_read

    select_results = iter([([5], [], []), ([pipe_r], [], [])])
    with patch("select.select", side_effect=lambda *a, **kw: next(select_results)):
        try:
            adapter._run_loop([mock_dev], modifier_map)
        finally:
            os.close(pipe_r)
            os.close(pipe_w)
    assert not fired.is_set()


def test_register_after_start_succeeds_and_fires() -> None:
    mock_evdev = _make_mock_evdev()
    mock_evdev.ecodes.ecodes = ecodes.ecodes
    mock_evdev.events.KeyEvent.key_down = 1
    mock_evdev.events.KeyEvent.key_up = 0
    stop_event = threading.Event()

    def fake_select(rlist, wlist, xlist, *args, **kwargs):
        stop_event.wait(timeout=5)
        return ([rlist[-1]], [], [])

    adapter = EvdevAdapter()
    fired = threading.Event()

    with patch("nimble.hotkeys.evdev_adapter._evdev", return_value=mock_evdev):
        with patch("select.select", side_effect=fake_select):
            adapter.start()
            adapter.register("ctrl+l", fired.set)
            stop_event.set()
            adapter.stop()

    assert "ctrl+l" in adapter._hotkeys
