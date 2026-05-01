from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import nimble.daemon as daemon_module
from nimble.state import SkillState
from nimble.skills.registry import SkillConfig, SkillRegistry, SkillWorker
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
        patch("nimble.daemon.write_state"),
        patch("nimble.daemon.remove_state"),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("threading.Event", return_value=mock_stop_event),
        patch("nimble.daemon.threading.Thread"),
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
        patch("nimble.daemon.write_state"),
        patch("nimble.daemon.remove_state"),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("threading.Event", return_value=mock_stop_event),
        patch("nimble.daemon.threading.Thread"),
    ):
        mock_load_config.return_value.skills = []
        daemon_module.run(tmp_path)

    assert fake_notifier.sent[0] == ("Nimble", "Nimble daemon running.")


def test_run_exits_on_adapter_start_runtime_error(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()
    mock_adapter = MagicMock()
    mock_adapter.start.side_effect = RuntimeError("XWayland not found")
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter", return_value=mock_adapter),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        pytest.raises(SystemExit) as exc_info,
    ):
        from nimble.daemon import run

        run(tmp_path)
    assert exc_info.value.code == 1


def test_run_sends_notification_on_adapter_start_runtime_error(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()
    mock_adapter = MagicMock()
    mock_adapter.start.side_effect = RuntimeError("XWayland not found")
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter", return_value=mock_adapter),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        pytest.raises(SystemExit),
    ):
        from nimble.daemon import run

        run(tmp_path)
    assert len(fake_notifier.sent) == 1
    _, body = fake_notifier.sent[0]
    assert "XWayland not found" in body


def test_run_writes_state_on_startup(tmp_path: Path) -> None:
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter"),
        patch("nimble.daemon.Notifier"),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.ConfigWatcher"),
        patch("nimble.daemon.write_state") as mock_write_state,
        patch("nimble.daemon.remove_state"),
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.threading.Event") as mock_event_cls,
        patch("nimble.daemon.threading.Thread"),
    ):
        mock_event_cls.return_value.wait.side_effect = KeyboardInterrupt
        with pytest.raises((KeyboardInterrupt, SystemExit)):
            daemon_module.run(tmp_path)
    assert mock_write_state.called


def test_run_heartbeat_checks_dead_workers_and_rewrites_state(tmp_path: Path) -> None:
    class _ImmediateThread:
        def __init__(self, target: object) -> None:
            self._target = target

        def start(self) -> None:
            if callable(self._target):
                self._target()

    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter"),
        patch("nimble.daemon.Notifier"),
        patch("nimble.daemon.configure_logging"),
        patch(
            "nimble.daemon._build_skill_states",
            side_effect=[
                [
                    SkillState(
                        name="skill",
                        source="local",
                        binding="ctrl+a",
                        status="loaded",
                        worker_pid=1001,
                    )
                ],
                [
                    SkillState(
                        name="skill",
                        source="local",
                        binding="ctrl+a",
                        status="disabled",
                        worker_pid=None,
                    )
                ],
            ],
        ),
        patch("nimble.daemon.SkillRunner") as mock_runner_cls,
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.ConfigWatcher"),
        patch("nimble.daemon.write_state") as mock_write_state,
        patch("nimble.daemon.remove_state"),
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.threading.Event") as mock_event_cls,
        patch("nimble.daemon.threading.Thread") as mock_thread_cls,
    ):
        mock_event_cls.return_value.wait.side_effect = [False, True, KeyboardInterrupt]
        mock_thread_cls.side_effect = lambda *a, **kw: _ImmediateThread(kw["target"])
        with pytest.raises((KeyboardInterrupt, SystemExit)):
            daemon_module.run(tmp_path)

    assert mock_runner_cls.return_value.check_for_dead_workers.called
    assert mock_write_state.call_count >= 2


def test_run_removes_state_on_shutdown(tmp_path: Path) -> None:
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter"),
        patch("nimble.daemon.Notifier"),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.ConfigWatcher"),
        patch("nimble.daemon.write_state"),
        patch("nimble.daemon.remove_state") as mock_remove_state,
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.threading.Event") as mock_event_cls,
        patch("nimble.daemon.threading.Thread"),
    ):
        mock_event_cls.return_value.wait.side_effect = KeyboardInterrupt
        with pytest.raises((KeyboardInterrupt, SystemExit)):
            daemon_module.run(tmp_path)
    assert mock_remove_state.called


def test_run_sends_notification_for_each_reserved_hotkey(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()
    mock_adapter = MagicMock(
        spec=["start", "stop", "register", "reserved_hotkeys_found"]
    )
    mock_adapter.reserved_hotkeys_found = ["<win>+l", "<win>+d"]
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter", return_value=mock_adapter),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.ConfigWatcher"),
        patch("nimble.daemon.write_state"),
        patch("nimble.daemon.remove_state"),
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.threading.Event") as mock_event,
        patch("nimble.daemon.threading.Thread"),
    ):
        mock_event.return_value.wait.side_effect = KeyboardInterrupt
        with pytest.raises((KeyboardInterrupt, SystemExit)):
            from nimble.daemon import run

            run(tmp_path)
    warning_sends = [s for s in fake_notifier.sent if "startup warning" in s[0]]
    assert len(warning_sends) == 2


def test_reload_reenables_previously_disabled_skill(tmp_path: Path) -> None:
    registry = SkillRegistry()
    skill_cfg = SkillConfig(
        name="hello-world",
        source="local",
        binding="ctrl+shift+h",
        path="skills/hello.py",
        class_name="HelloSkill",
    )

    class _FakeRunner:
        def __init__(
            self,
            registry: SkillRegistry,
            notifier: object,
            repo_root: Path,
            ai_config: object = None,
            debug: bool = False,
        ) -> None:
            self._registry = registry

        def spawn_workers(self, configs: list[SkillConfig]) -> None:
            for cfg in configs:
                proc = MagicMock()
                proc.poll.return_value = None
                self._registry.register(
                    SkillWorker(
                        config=cfg,
                        process=proc,
                        status="loaded",
                        python_executable="python",
                    )
                )

        def check_for_dead_workers(self) -> None:
            return

        def shutdown(self) -> None:
            return

    class _FakeWatcher:
        def __init__(self, config_path: Path, callback: Callable[[Path], None]) -> None:
            self._config_path = config_path
            self._callback = callback

        def start(self) -> None:
            self._callback(self._config_path)
            self._callback(self._config_path)

        def stop(self) -> None:
            return

    mock_adapter = MagicMock()
    mock_event = MagicMock()
    mock_event.wait.return_value = True

    with (
        patch("nimble.daemon.SkillRegistry", return_value=registry),
        patch("nimble.daemon.SkillRunner", _FakeRunner),
        patch("nimble.daemon.ConfigWatcher", _FakeWatcher),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.get_adapter", return_value=mock_adapter),
        patch("nimble.daemon.Notifier"),
        patch(
            "nimble.daemon.load_config",
            return_value=MagicMock(skills=[skill_cfg], ai=None),
        ),
        patch(
            "nimble.daemon.validate_skill_paths",
            side_effect=[[skill_cfg], [], [skill_cfg]],
        ),
        patch(
            "nimble.daemon.yaml.safe_load",
            side_effect=[
                {"skills": [{"name": "hello-world", "disabled": True}]},
                {"skills": [{"name": "hello-world"}]},
            ],
        ),
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.write_state"),
        patch("nimble.daemon.remove_state"),
        patch("nimble.daemon.threading.Event", return_value=mock_event),
        patch("nimble.daemon.threading.Thread"),
    ):
        daemon_module.run(tmp_path)

    worker = registry.get("hello-world")
    assert worker is not None
    assert worker.status == "loaded"
