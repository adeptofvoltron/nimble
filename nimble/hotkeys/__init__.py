import sys

from nimble.hotkeys.base import HotkeyAdapter


def get_adapter() -> HotkeyAdapter:
    if sys.platform == "linux":
        from nimble.hotkeys.x11 import X11HotkeyAdapter

        return X11HotkeyAdapter()
    elif sys.platform == "win32":
        from nimble.hotkeys.windows import WindowsHotkeyAdapter

        return WindowsHotkeyAdapter()
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
