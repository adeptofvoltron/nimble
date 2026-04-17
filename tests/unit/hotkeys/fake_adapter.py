from collections.abc import Callable

from nimble.hotkeys.base import HotkeyAdapter


class FakeHotkeyAdapter(HotkeyAdapter):
    def __init__(self) -> None:
        self.registered: list[str] = []

    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        self.registered.append(shortcut)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
