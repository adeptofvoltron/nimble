import sys
from unittest.mock import patch

import pytest

from nimble.hotkeys import get_adapter
from nimble.hotkeys.windows import WindowsHotkeyAdapter
from nimble.hotkeys.x11 import X11HotkeyAdapter


def test_get_adapter_returns_x11_on_linux() -> None:
    with patch.object(sys, "platform", "linux"):
        adapter = get_adapter()
    assert isinstance(adapter, X11HotkeyAdapter)


def test_get_adapter_returns_windows_on_win32() -> None:
    with patch.object(sys, "platform", "win32"):
        adapter = get_adapter()
    assert isinstance(adapter, WindowsHotkeyAdapter)


def test_get_adapter_raises_on_unsupported_platform() -> None:
    with patch.object(sys, "platform", "darwin"):
        with pytest.raises(RuntimeError, match="Unsupported platform: darwin"):
            get_adapter()
