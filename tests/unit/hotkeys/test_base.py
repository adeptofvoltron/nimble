import pytest

from nimble.hotkeys.base import HotkeyAdapter


def test_hotkeyAdapter_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        HotkeyAdapter()  # type: ignore[abstract]
