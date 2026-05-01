from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import nimble.daemon as daemon_module
from nimble.skills.runner import DispatchResult, SkillError

from tests.conftest import FakeNotifier


def test_dispatch_fires_notification_on_skill_error() -> None:
    notifier = FakeNotifier()
    error = SkillError(
        type="ValueError", message="oops", skill_file="skills/foo.py", line=42
    )
    dispatch_result = DispatchResult(invocation_id="x", status="error", error=error)
    mock_runner = MagicMock()
    mock_runner.dispatch.return_value = dispatch_result

    with patch("nimble.daemon.build_context", return_value={}):
        daemon_module._dispatch("my-skill", mock_runner, notifier)

    assert len(notifier.sent) == 1


def test_dispatch_notification_title_and_body_format() -> None:
    notifier = FakeNotifier()
    error = SkillError(
        type="ValueError", message="oops", skill_file="skills/foo.py", line=42
    )
    dispatch_result = DispatchResult(invocation_id="x", status="error", error=error)
    mock_runner = MagicMock()
    mock_runner.dispatch.return_value = dispatch_result

    with patch("nimble.daemon.build_context", return_value={}):
        daemon_module._dispatch("my-skill", mock_runner, notifier)

    title, body = notifier.sent[0]
    assert title == "Nimble — my-skill"
    assert body == "ValueError: oops in skills/foo.py line 42"


def test_dispatch_no_notification_on_success() -> None:
    notifier = FakeNotifier()
    dispatch_result = DispatchResult(invocation_id="x", status="ok")
    mock_runner = MagicMock()
    mock_runner.dispatch.return_value = dispatch_result

    with patch("nimble.daemon.build_context", return_value={}):
        daemon_module._dispatch("my-skill", mock_runner, notifier)

    assert notifier.sent == []


def test_dispatch_logs_error_on_skill_failure() -> None:
    notifier = FakeNotifier()
    error = SkillError(
        type="ValueError", message="oops", skill_file="skills/foo.py", line=42
    )
    dispatch_result = DispatchResult(invocation_id="x", status="error", error=error)
    mock_runner = MagicMock()
    mock_runner.dispatch.return_value = dispatch_result

    with (
        patch("nimble.daemon.build_context", return_value={}),
        patch("nimble.daemon.logger") as mock_logger,
    ):
        daemon_module._dispatch("my-skill", mock_runner, notifier)

    mock_logger.error.assert_called_once()


def test_dispatch_thread_exception_fires_same_notification_format() -> None:
    notifier = FakeNotifier()
    error = SkillError(
        type="RuntimeError",
        message="thread blew up",
        skill_file="skills/bar.py",
        line=99,
    )
    dispatch_result = DispatchResult(invocation_id="y", status="error", error=error)
    mock_runner = MagicMock()
    mock_runner.dispatch.return_value = dispatch_result

    with patch("nimble.daemon.build_context", return_value={}):
        daemon_module._dispatch("thread-skill", mock_runner, notifier)

    assert len(notifier.sent) == 1
    title, body = notifier.sent[0]
    assert title == "Nimble — thread-skill"
    assert body == "RuntimeError: thread blew up in skills/bar.py line 99"


def test_startup_notification_fires(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()
    mock_stop_event = MagicMock()
    mock_stop_event.wait.return_value = None

    with (
        patch("nimble.daemon.configure_logging"),
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
        patch("nimble.daemon.configure_logging"),
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
