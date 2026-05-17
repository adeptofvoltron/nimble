from __future__ import annotations

import os
import sys

from nimble.hotkeys.base import HotkeyAdapter
from nimble.platform import is_linux, is_windows


def get_adapter() -> HotkeyAdapter:
    if is_linux():
        display = os.environ.get("DISPLAY")
        if display:
            from nimble.hotkeys.x11 import X11HotkeyAdapter

            return X11HotkeyAdapter()
        from nimble.hotkeys.evdev_adapter import EvdevAdapter

        return EvdevAdapter()
    elif is_windows():
        from nimble.hotkeys.windows import WindowsHotkeyAdapter

        return WindowsHotkeyAdapter()
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
