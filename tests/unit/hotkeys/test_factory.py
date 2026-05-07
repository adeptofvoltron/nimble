from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

from nimble.hotkeys import get_adapter
from nimble.hotkeys.evdev_adapter import EvdevAdapter
from nimble.hotkeys.windows import WindowsHotkeyAdapter
from nimble.hotkeys.x11 import X11HotkeyAdapter


def test_get_adapter_returns_x11_on_pure_x11() -> None:
    with patch.object(sys, "platform", "linux"):
        with patch.dict(os.environ, {"DISPLAY": ":0", "WAYLAND_DISPLAY": ""}, clear=False):
            adapter = get_adapter()
    assert isinstance(adapter, X11HotkeyAdapter)
    assert not isinstance(adapter, EvdevAdapter)


def test_get_adapter_returns_evdev_on_xwayland() -> None:
    with patch.object(sys, "platform", "linux"):
        with patch.dict(
            os.environ, {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}
        ):
            adapter = get_adapter()
    assert isinstance(adapter, EvdevAdapter)


def test_get_adapter_returns_evdev_on_pure_wayland() -> None:
    with patch.object(sys, "platform", "linux"):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ""}, clear=False):
            adapter = get_adapter()
    assert isinstance(adapter, EvdevAdapter)


def test_get_adapter_returns_windows_on_win32() -> None:
    with patch.object(sys, "platform", "win32"):
        adapter = get_adapter()
    assert isinstance(adapter, WindowsHotkeyAdapter)


def test_get_adapter_raises_on_unsupported_platform() -> None:
    with patch.object(sys, "platform", "darwin"):
        with pytest.raises(RuntimeError, match="Unsupported platform: darwin"):
            get_adapter()
