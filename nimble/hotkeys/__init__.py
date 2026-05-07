from __future__ import annotations

import os
import sys

from nimble.hotkeys.base import HotkeyAdapter
from nimble.platform import is_linux, is_windows


def get_adapter() -> HotkeyAdapter:
    if is_linux():
        wayland = os.environ.get("WAYLAND_DISPLAY")
        display = os.environ.get("DISPLAY")
        if wayland and not display:
            raise RuntimeError(
                "Nimble requires XWayland on pure Wayland sessions. "
                "Install XWayland or set DISPLAY to your X11 display."
            )
        if wayland and display:
            from nimble.hotkeys.wayland import WaylandXWaylandAdapter

            return WaylandXWaylandAdapter()
        from nimble.hotkeys.x11 import X11HotkeyAdapter

        return X11HotkeyAdapter()
    elif is_windows():
        from nimble.hotkeys.windows import WindowsHotkeyAdapter

        return WindowsHotkeyAdapter()
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
