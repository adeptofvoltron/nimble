from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

import nimble.state as state_module
from nimble.state import (
    SkillState,
    is_running,
    read_pid,
    read_state,
    remove_pid,
    remove_state,
    write_pid,
    write_state,
)


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


def test_write_state_creates_valid_json(tmp_path: Path) -> None:
    skills = [
        SkillState(
            name="hello-world",
            source="local",
            binding="ctrl+shift+h",
            status="loaded",
            worker_pid=9999,
        )
    ]
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "STATE_FILE", tmp_path / "state.json"),
    ):
        write_state(12345, "2026-05-01T10:00:00+00:00", "1.0.0", skills)
        data = json.loads((tmp_path / "state.json").read_text())

    assert data["pid"] == 12345
    assert data["started_at"] == "2026-05-01T10:00:00+00:00"
    assert data["daemon_version"] == "1.0.0"
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "hello-world"
    assert data["skills"][0]["worker_pid"] == 9999


def test_write_state_skill_entry_fields(tmp_path: Path) -> None:
    skills = [
        SkillState(
            name="log-diagnosis",
            source="local",
            binding="ctrl+shift+d",
            status="loaded",
            worker_pid=12346,
        )
    ]
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "STATE_FILE", tmp_path / "state.json"),
    ):
        write_state(1, "2026-05-01T00:00:00+00:00", "1.0.0", skills)
        data = json.loads((tmp_path / "state.json").read_text())

    entry = data["skills"][0]
    assert entry["name"] == "log-diagnosis"
    assert entry["source"] == "local"
    assert entry["binding"] == "ctrl+shift+d"
    assert entry["status"] == "loaded"
    assert entry["worker_pid"] == 12346


def test_write_state_worker_pid_none_for_dead_worker(tmp_path: Path) -> None:
    skills = [
        SkillState(
            name="s", source="local", binding="ctrl+a", status="failed", worker_pid=None
        )
    ]
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "STATE_FILE", tmp_path / "state.json"),
    ):
        write_state(1, "2026-05-01T00:00:00+00:00", "1.0.0", skills)
        data = json.loads((tmp_path / "state.json").read_text())

    assert data["skills"][0]["worker_pid"] is None


def test_write_state_is_atomic(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "STATE_FILE", state_file),
        patch("pathlib.Path.rename", side_effect=OSError("disk full")),
        pytest.raises(OSError),
    ):
        write_state(1, "2026-05-01T00:00:00+00:00", "1.0.0", [])
    assert not state_file.exists()


def test_remove_state_deletes_file(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "STATE_FILE", state_file),
    ):
        write_state(1, "2026-05-01T00:00:00+00:00", "1.0.0", [])
        assert state_file.exists()
        remove_state()

    assert not state_file.exists()


def test_remove_state_noop_if_absent(tmp_path: Path) -> None:
    with patch.object(state_module, "STATE_FILE", tmp_path / "state.json"):
        remove_state()  # should not raise


def test_read_state_returns_none_when_file_missing(tmp_path: Path) -> None:
    with patch.object(state_module, "STATE_FILE", tmp_path / "state.json"):
        assert read_state() is None


def test_read_state_returns_none_on_permission_error(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    with (
        patch.object(state_module, "STATE_FILE", state_file),
        patch("pathlib.Path.read_text", side_effect=PermissionError("denied")),
    ):
        assert read_state() is None


def test_write_state_is_thread_safe(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    errors: list[Exception] = []

    def _writer(worker_id: int) -> None:
        try:
            for i in range(30):
                write_state(
                    worker_id,
                    f"2026-05-01T00:00:{i:02d}+00:00",
                    "1.0.0",
                    [
                        SkillState(
                            name=f"s-{worker_id}",
                            source="local",
                            binding="ctrl+a",
                            status="loaded",
                            worker_pid=worker_id,
                        )
                    ],
                )
        except Exception as exc:
            errors.append(exc)

    with (
        patch.object(state_module, "NIMBLE_DIR", tmp_path),
        patch.object(state_module, "STATE_FILE", state_file),
    ):
        t1 = threading.Thread(target=_writer, args=(1,))
        t2 = threading.Thread(target=_writer, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        data = json.loads(state_file.read_text())

    assert errors == []
    assert data["pid"] in {1, 2}
    assert data["skills"][0]["name"] in {"s-1", "s-2"}
