from collections.abc import Callable

from nimble.hotkeys.base import HotkeyAdapter


class WindowsHotkeyAdapter(HotkeyAdapter):
    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        raise NotImplementedError("Implemented in Story 2.3")

    def start(self) -> None:
        raise NotImplementedError("Implemented in Story 2.3")

    def stop(self) -> None:
        raise NotImplementedError("Implemented in Story 2.3")
