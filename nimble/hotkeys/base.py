import abc
from collections.abc import Callable


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
