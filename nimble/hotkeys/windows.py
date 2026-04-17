from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nimble.hotkeys.base import HotkeyAdapter, _to_pynput_format

if TYPE_CHECKING:
    from pynput.keyboard import GlobalHotKeys

logger = logging.getLogger(__name__)

_WINDOWS_RESERVED_HOTKEYS = {
    "<win>+l",
    "<ctrl>+<alt>+<delete>",
    "<ctrl>+<alt>+del",
    "<win>+d",
    "<win>+e",
    "<win>+r",
    "<win>+s",
    "<win>+tab",
}


def _pynput_keyboard() -> Any:
    """Lazy import so importing this module doesn't require Win32 APIs."""
    from pynput import keyboard

    return keyboard


class WindowsHotkeyAdapter(HotkeyAdapter):
    def __init__(self) -> None:
        self._hotkeys: dict[str, Callable[[], None]] = {}
        self._listener: GlobalHotKeys | None = None

    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        key = _to_pynput_format(shortcut)
        if key in self._hotkeys:
            raise ValueError(f"Hotkey already registered: {shortcut!r}")
        self._hotkeys[key] = callback

    def start(self) -> None:
        if self._listener is not None:
            raise RuntimeError(
                "Hotkey adapter is already started; call stop() before start()."
            )
        for pynput_key in self._hotkeys:
            if pynput_key in _WINDOWS_RESERVED_HOTKEYS:
                logger.warning(
                    "Shortcut %r is a Windows-reserved hotkey and may not"
                    " fire reliably (FR5)",
                    pynput_key,
                )
        keyboard = _pynput_keyboard()
        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener.join()
            self._listener = None
