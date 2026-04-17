import os
from collections.abc import Callable

from pynput import keyboard

from nimble.hotkeys.base import HotkeyAdapter

_MODIFIERS = {"ctrl", "shift", "alt", "cmd", "super"}


def _to_pynput_format(shortcut: str) -> str:
    parts = shortcut.lower().split("+")
    return "+".join(f"<{p}>" if p in _MODIFIERS else p for p in parts)


class X11HotkeyAdapter(HotkeyAdapter):
    def __init__(self) -> None:
        self._hotkeys: dict[str, Callable[[], None]] = {}
        self._listener: keyboard.GlobalHotKeys | None = None

    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        self._hotkeys[_to_pynput_format(shortcut)] = callback

    def start(self) -> None:
        wayland = os.environ.get("WAYLAND_DISPLAY")
        x11 = os.environ.get("DISPLAY")
        if wayland and not x11:
            raise RuntimeError(
                "Nimble requires XWayland on Wayland sessions. "
                "Install XWayland or set DISPLAY to your X11 display."
            )
        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener.join()
