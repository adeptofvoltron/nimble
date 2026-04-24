import sys

from nimble.hotkeys.base import HotkeyAdapter
from nimble.platform import is_linux, is_windows


def get_adapter() -> HotkeyAdapter:
    if is_linux():
        from nimble.hotkeys.x11 import X11HotkeyAdapter

        return X11HotkeyAdapter()
    elif is_windows():
        from nimble.hotkeys.windows import WindowsHotkeyAdapter

        return WindowsHotkeyAdapter()
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
