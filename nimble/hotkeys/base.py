import abc
from collections.abc import Callable

_MODIFIERS = {"ctrl", "shift", "alt", "cmd", "super", "win"}


def _to_pynput_format(shortcut: str) -> str:
    parts = shortcut.lower().split("+")
    return "+".join(f"<{p}>" if p in _MODIFIERS else p for p in parts)


class HotkeyAdapter(abc.ABC):
    @abc.abstractmethod
    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        """Register a global hotkey that invokes callback when pressed."""

    @abc.abstractmethod
    def start(self) -> None:
        """Start the hotkey listener."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the hotkey listener and clean up resources."""
