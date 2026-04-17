from collections.abc import Callable

from nimble.hotkeys.base import HotkeyAdapter


class X11HotkeyAdapter(HotkeyAdapter):
    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        raise NotImplementedError("Implemented in Story 2.2")

    def start(self) -> None:
        raise NotImplementedError("Implemented in Story 2.2")

    def stop(self) -> None:
        raise NotImplementedError("Implemented in Story 2.2")
