from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nimble.hotkeys.base import HotkeyAdapter, _to_pynput_format

if TYPE_CHECKING:
    from pynput.keyboard import GlobalHotKeys


def _pynput_keyboard() -> Any:
    """Import pynput lazily so importing this module does not require a display."""
    from pynput import keyboard

    return keyboard


class X11HotkeyAdapter(HotkeyAdapter):
    def __init__(self) -> None:
        self._hotkeys: dict[str, Callable[[], None]] = {}
        self._listener: GlobalHotKeys | None = None

    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        key = _to_pynput_format(shortcut)
        if key in self._hotkeys:
            raise ValueError(f"Hotkey already registered: {shortcut!r}")
        self._hotkeys[key] = callback

    def start(self) -> None:
        wayland = os.environ.get("WAYLAND_DISPLAY")
        x11 = os.environ.get("DISPLAY")
        if wayland and not x11:
            raise RuntimeError(
                "Nimble requires XWayland on Wayland sessions. "
                "Install XWayland or set DISPLAY to your X11 display."
            )
        if self._listener is not None:
            raise RuntimeError(
                "Hotkey adapter is already started; call stop() before start()."
            )
        keyboard = _pynput_keyboard()
        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener.join()
            self._listener = None
