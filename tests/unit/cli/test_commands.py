from __future__ import annotations

import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from nimble.cli.commands import app
from nimble.manifest.parser import ConfigError, NimbleConfig

runner = CliRunner()


def test_start_no_existing_daemon(tmp_path: Path) -> None:
    pid_seq = [None, None, 9999]
    running_seq = [True]

    with (
        patch("nimble.cli.commands.state.read_pid", side_effect=pid_seq),
        patch("nimble.cli.commands.state.is_running", side_effect=running_seq),
        patch("nimble.cli.commands.subprocess.Popen"),
    ):
        result = runner.invoke(app, ["start"])

    assert result.exit_code == 0
    assert "9999" in result.output


def test_start_already_running() -> None:
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=12345),
        patch("nimble.cli.commands.state.is_running", return_value=True),
    ):
        result = runner.invoke(app, ["start"])

    assert result.exit_code == 1
    assert "already running" in result.output


def test_start_stale_pid_cleaned_up() -> None:
    pid_seq = [99999, None, 1234]
    running_seq = [False, True]

    with (
        patch("nimble.cli.commands.state.read_pid", side_effect=pid_seq),
        patch("nimble.cli.commands.state.is_running", side_effect=running_seq),
        patch("nimble.cli.commands.state.remove_pid") as mock_remove,
        patch("nimble.cli.commands.subprocess.Popen"),
    ):
        result = runner.invoke(app, ["start"])

    mock_remove.assert_called_once()
    assert result.exit_code == 0


def test_stop_running_daemon() -> None:
    is_running_seq = [True, True, True, False]

    with (
        patch("nimble.cli.commands.state.read_pid", return_value=12345),
        patch("nimble.cli.commands.state.is_running", side_effect=is_running_seq),
        patch("os.kill") as mock_kill,
    ):
        result = runner.invoke(app, ["stop"])

    assert result.exit_code == 0
    assert "stopped" in result.output
    mock_kill.assert_called_once_with(12345, signal.SIGTERM)


def test_stop_no_daemon() -> None:
    with patch("nimble.cli.commands.state.read_pid", return_value=None):
        result = runner.invoke(app, ["stop"])

    assert result.exit_code == 1


def test_restart_calls_stop_then_start() -> None:
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=1234),
        patch("nimble.cli.commands.state.is_running", return_value=True),
        patch("nimble.cli.commands._do_stop", return_value=True) as mock_stop,
        patch("nimble.cli.commands._do_start", return_value=5678) as mock_start,
    ):
        result = runner.invoke(app, ["restart"])

    assert result.exit_code == 0
    mock_stop.assert_called_once()
    mock_start.assert_called_once()
    assert "5678" in result.output


def test_restart_fails_if_stop_fails() -> None:
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=1234),
        patch("nimble.cli.commands.state.is_running", return_value=True),
        patch("nimble.cli.commands._do_stop", return_value=False),
        patch("nimble.cli.commands._do_start") as mock_start,
    ):
        result = runner.invoke(app, ["restart"])

    assert result.exit_code == 1
    mock_start.assert_not_called()


def test_start_fails_if_spawn_raises() -> None:
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=None),
        patch("nimble.cli.commands.subprocess.Popen", side_effect=FileNotFoundError),
    ):
        result = runner.invoke(app, ["start"])

    assert result.exit_code == 1


def test_stop_removes_pid_after_shutdown() -> None:
    is_running_seq = [True, True, False]
    with (
        patch("nimble.cli.commands.state.read_pid", return_value=12345),
        patch("nimble.cli.commands.state.is_running", side_effect=is_running_seq),
        patch("os.kill"),
        patch("nimble.cli.commands.state.remove_pid") as mock_remove,
    ):
        result = runner.invoke(app, ["stop"])

    assert result.exit_code == 0
    mock_remove.assert_called_once()


def test_validate_valid_config() -> None:
    with patch(
        "nimble.manifest.parser.load_config",
        return_value=NimbleConfig(skills=[]),
    ):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "config.yaml is valid" in result.output


def test_validate_invalid_config() -> None:
    with patch(
        "nimble.manifest.parser.load_config",
        side_effect=ConfigError("config.yaml line 3: found character '\\t'"),
    ):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "line 3" in result.output


def test_validate_missing_config(tmp_path: Path) -> None:
    with patch(
        "nimble.manifest.parser.load_config",
        side_effect=FileNotFoundError,
    ):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_validate_unreadable_config() -> None:
    with patch(
        "nimble.manifest.parser.load_config",
        side_effect=PermissionError("permission denied"),
    ):
        result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
    assert "Failed to read config.yaml" in result.output


def test_terminate_windows_openprocess_failure_raises() -> None:
    fake_kernel32 = MagicMock()
    fake_kernel32.OpenProcess.return_value = 0
    fake_ctypes = MagicMock(windll=MagicMock(kernel32=fake_kernel32))

    with patch.dict("sys.modules", {"ctypes": fake_ctypes}):
        try:
            from nimble.cli.commands import _terminate_windows

            _terminate_windows(1)
        except OSError:
            pass
        else:
            raise AssertionError("expected OSError")
