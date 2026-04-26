from pathlib import Path

import pytest

from nimble.notifier import Notifier
from tests.unit.hotkeys.fake_adapter import FakeHotkeyAdapter


class FakeNotifier(Notifier):
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, title: str, body: str) -> None:
        self.sent.append((title, body))


@pytest.fixture
def fake_adapter() -> FakeHotkeyAdapter:
    return FakeHotkeyAdapter()


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text("skills: []\nbindings: []\n")
    return config


@pytest.fixture
def fake_notifier() -> FakeNotifier:
    return FakeNotifier()
