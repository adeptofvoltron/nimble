from collections.abc import Callable

from tests.unit.hotkeys.fake_adapter import FakeHotkeyAdapter


def test_fake_adapter_register_records_shortcut() -> None:
    adapter = FakeHotkeyAdapter()
    callback: Callable[[], None] = lambda: None
    adapter.register("ctrl+shift+d", callback)
    assert "ctrl+shift+d" in adapter.registered
