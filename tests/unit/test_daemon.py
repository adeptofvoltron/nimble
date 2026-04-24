from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import nimble.daemon as daemon_module

from tests.conftest import FakeNotifier


def test_startup_notification_fires(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()
    mock_stop_event = MagicMock()
    mock_stop_event.wait.return_value = None

    with (
        patch("nimble.daemon.get_adapter"),
        patch("nimble.daemon.load_config") as mock_load_config,
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.SkillRunner"),
        patch("nimble.daemon.ConfigWatcher"),
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("threading.Event", return_value=mock_stop_event),
    ):
        mock_load_config.return_value.skills = []
        daemon_module.run(tmp_path)

    assert ("Nimble", "Nimble daemon running.") in fake_notifier.sent


def test_startup_notification_title_and_body(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()
    mock_stop_event = MagicMock()
    mock_stop_event.wait.return_value = None

    with (
        patch("nimble.daemon.get_adapter"),
        patch("nimble.daemon.load_config") as mock_load_config,
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.SkillRunner"),
        patch("nimble.daemon.ConfigWatcher"),
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("threading.Event", return_value=mock_stop_event),
    ):
        mock_load_config.return_value.skills = []
        daemon_module.run(tmp_path)

    assert fake_notifier.sent[0] == ("Nimble", "Nimble daemon running.")
