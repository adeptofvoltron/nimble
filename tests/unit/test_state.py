from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import nimble.state as state_module
from nimble.state import is_running, read_pid, remove_pid, write_pid


def test_write_and_read_pid(tmp_path: Path) -> None:
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "PID_FILE", tmp_path / "nimble.pid"),
    ):
        write_pid(12345)
        assert read_pid() == 12345


def test_read_pid_returns_none_if_no_file(tmp_path: Path) -> None:
    with patch.object(state_module, "PID_FILE", tmp_path / "nimble.pid"):
        assert read_pid() is None


def test_remove_pid_deletes_file(tmp_path: Path) -> None:
    pid_file = tmp_path / "nimble.pid"
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "PID_FILE", pid_file),
    ):
        write_pid(12345)
        assert pid_file.exists()
        remove_pid()
        assert not pid_file.exists()


def test_remove_pid_noop_if_absent(tmp_path: Path) -> None:
    with patch.object(state_module, "PID_FILE", tmp_path / "nimble.pid"):
        remove_pid()  # should not raise


def test_is_running_process_exists() -> None:
    with patch("os.kill", return_value=None):
        assert is_running(12345) is True


def test_is_running_process_dead() -> None:
    with patch("os.kill", side_effect=ProcessLookupError):
        assert is_running(99999) is False
