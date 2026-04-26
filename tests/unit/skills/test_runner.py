import json
import sys
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nimble.skills.registry import SkillConfig, SkillRegistry
from nimble.skills.runner import DispatchResult, SkillRunner
from tests.conftest import FakeNotifier


def _make_config(name: str = "my-skill", source: str = "local") -> SkillConfig:
    return SkillConfig(
        name=name,
        source=source,  # type: ignore[arg-type]
        binding="ctrl+shift+a",
        path="/path/to/skill.py",
        class_name="MySkill",
    )


def _make_fake_proc(response: Mapping[str, object]) -> MagicMock:
    proc = MagicMock()
    proc.poll.return_value = None
    response_line = (json.dumps(response) + "\n").encode("utf-8")
    proc.stdout.readline.return_value = response_line
    proc.stdin = MagicMock()
    proc.stderr = MagicMock()
    return proc


def _make_runner(
    registry: SkillRegistry | None = None,
    notifier: FakeNotifier | None = None,
) -> SkillRunner:
    return SkillRunner(
        registry=registry or SkillRegistry(),
        notifier=notifier or FakeNotifier(),
        repo_root=Path("/fake/repo"),
    )


# ---------------------------------------------------------------------------
# spawn_workers tests
# ---------------------------------------------------------------------------


def test_spawn_workers_local_uses_sys_executable() -> None:
    config = _make_config(source="local")
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    ok_response = {"invocation_id": "abc", "status": "ok", "error": None}
    fake_proc = _make_fake_proc(ok_response)

    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        runner.spawn_workers([config])
        args, _ = mock_popen.call_args
        cmd = args[0]
        assert cmd[0] == sys.executable


def test_spawn_workers_community_uses_venv_python() -> None:
    config = _make_config(name="my-skill", source="community")
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    ok_response = {"invocation_id": "abc", "status": "ok", "error": None}
    fake_proc = _make_fake_proc(ok_response)

    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        runner.spawn_workers([config])
        args, _ = mock_popen.call_args
        cmd = args[0]
        if sys.platform == "win32":
            assert cmd[0].endswith("python.exe")
            assert "Scripts" in cmd[0]
        else:
            assert cmd[0].endswith("python")
            assert "bin" in cmd[0]
        assert ".nimble" in cmd[0]
        assert "my-skill" in cmd[0]


def test_spawn_workers_registers_worker() -> None:
    config = _make_config()
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    fake_proc = _make_fake_proc({"invocation_id": "abc", "status": "ok", "error": None})

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    assert registry.get("my-skill") is not None


# ---------------------------------------------------------------------------
# dispatch tests
# ---------------------------------------------------------------------------


def test_dispatch_happy_path() -> None:
    config = _make_config()
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    invocation_id = "test-uuid-1234"
    ok_response = {"invocation_id": invocation_id, "status": "ok", "error": None}
    fake_proc = _make_fake_proc(ok_response)

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    result = runner.dispatch("my-skill", {"selection": "hello"})
    assert isinstance(result, DispatchResult)
    assert result.status == "ok"
    assert result.error is None


def test_dispatch_error_response() -> None:
    config = _make_config()
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    error_response = {
        "invocation_id": "err-uuid",
        "status": "error",
        "error": {
            "type": "KeyError",
            "message": "bad key",
            "skill_file": "skill.py",
            "line": 14,
        },
    }
    fake_proc = _make_fake_proc(error_response)

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    result = runner.dispatch("my-skill", {})
    assert result.status == "error"
    assert result.error is not None
    assert result.error.type == "KeyError"


def test_dispatch_on_dead_worker_raises() -> None:
    config = _make_config()
    registry = SkillRegistry()
    notifier = FakeNotifier()
    runner = _make_runner(registry=registry, notifier=notifier)

    fake_proc = _make_fake_proc({"invocation_id": "x", "status": "ok", "error": None})

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    fake_proc.poll.return_value = 1  # dead before dispatch

    with pytest.raises(RuntimeError, match="is not running"):
        runner.dispatch("my-skill", {})


def test_dispatch_unknown_skill_raises() -> None:
    runner = _make_runner()
    with pytest.raises(RuntimeError, match="No worker registered"):
        runner.dispatch("unknown-skill", {})


def test_dispatch_worker_dies_during_readline_raises() -> None:
    config = _make_config()
    registry = SkillRegistry()
    notifier = FakeNotifier()
    runner = _make_runner(registry=registry, notifier=notifier)

    fake_proc = _make_fake_proc({})
    fake_proc.poll.return_value = None  # alive before dispatch
    fake_proc.stdout.readline.return_value = b""  # empty = worker died

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    with pytest.raises(RuntimeError, match="died during dispatch"):
        runner.dispatch("my-skill", {})


def test_dispatch_write_failure_disables_worker_and_raises() -> None:
    config = _make_config()
    registry = SkillRegistry()
    notifier = FakeNotifier()
    runner = _make_runner(registry=registry, notifier=notifier)

    fake_proc = _make_fake_proc({"invocation_id": "x", "status": "ok", "error": None})
    fake_proc.stdin.write.side_effect = BrokenPipeError("broken pipe")

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    with pytest.raises(RuntimeError, match="died during dispatch write"):
        runner.dispatch("my-skill", {})

    assert registry.get("my-skill").status == "failed"  # type: ignore[union-attr]
    assert len(notifier.sent) == 1


def test_dispatch_malformed_error_payload_returns_protocol_error() -> None:
    config = _make_config()
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    bad_error_response = {
        "invocation_id": "bad-err",
        "status": "error",
        "error": "not-a-dict",
    }
    fake_proc = _make_fake_proc(bad_error_response)

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    result = runner.dispatch("my-skill", {})
    assert result.status == "error"
    assert result.error is not None
    assert result.error.type == "ProtocolError"


def test_dispatch_invalid_status_returns_protocol_error() -> None:
    config = _make_config()
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    invalid_status_response = {
        "invocation_id": "bad-status",
        "status": "unexpected",
        "error": None,
    }
    fake_proc = _make_fake_proc(invalid_status_response)

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    result = runner.dispatch("my-skill", {})
    assert result.status == "error"
    assert result.error is not None
    assert result.error.type == "ProtocolError"


# ---------------------------------------------------------------------------
# check_for_dead_workers tests
# ---------------------------------------------------------------------------


def test_check_for_dead_workers_disables_and_notifies() -> None:
    config = _make_config()
    registry = SkillRegistry()
    notifier = FakeNotifier()
    runner = _make_runner(registry=registry, notifier=notifier)

    fake_proc = _make_fake_proc({"invocation_id": "x", "status": "ok", "error": None})

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    # Simulate worker dying
    fake_proc.poll.return_value = 1

    runner.check_for_dead_workers()

    assert registry.get("my-skill").status == "failed"  # type: ignore[union-attr]
    assert len(notifier.sent) == 1


def test_check_for_dead_workers_leaves_alive_workers() -> None:
    config = _make_config()
    registry = SkillRegistry()
    notifier = FakeNotifier()
    runner = _make_runner(registry=registry, notifier=notifier)

    fake_proc = _make_fake_proc({"invocation_id": "x", "status": "ok", "error": None})
    fake_proc.poll.return_value = None  # still alive

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    runner.check_for_dead_workers()

    assert registry.get("my-skill").status == "loaded"  # type: ignore[union-attr]
    assert len(notifier.sent) == 0


def test_check_for_dead_workers_skips_already_failed_worker() -> None:
    config = _make_config()
    registry = SkillRegistry()
    notifier = FakeNotifier()
    runner = _make_runner(registry=registry, notifier=notifier)

    fake_proc = _make_fake_proc({"invocation_id": "x", "status": "ok", "error": None})
    fake_proc.poll.return_value = None

    with patch("subprocess.Popen", return_value=fake_proc):
        runner.spawn_workers([config])

    registry.disable("my-skill")
    fake_proc.poll.return_value = 1

    runner.check_for_dead_workers()
    assert len(notifier.sent) == 0


# ---------------------------------------------------------------------------
# shutdown tests
# ---------------------------------------------------------------------------


def test_shutdown_terminates_all_workers() -> None:
    configs = [_make_config("skill-a"), _make_config("skill-b")]
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    procs = [
        _make_fake_proc({"invocation_id": "x", "status": "ok", "error": None}),
        _make_fake_proc({"invocation_id": "y", "status": "ok", "error": None}),
    ]

    call_count = 0

    def fake_popen(cmd: list[str], **kwargs: object) -> MagicMock:
        nonlocal call_count
        proc = procs[call_count]
        call_count += 1
        return proc

    with patch("subprocess.Popen", side_effect=fake_popen):
        runner.spawn_workers(configs)

    runner.shutdown()

    for proc in procs:
        proc.terminate.assert_called_once()
        proc.wait.assert_called_once()


def test_spawn_workers_passes_log_path_env() -> None:
    config = _make_config()
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    fake_proc = _make_fake_proc({"invocation_id": "abc", "status": "ok", "error": None})

    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        runner.spawn_workers([config])

    env = mock_popen.call_args.kwargs["env"]
    assert "NIMBLE_LOG_PATH" in env
    assert env["NIMBLE_LOG_PATH"].endswith("nimble.log")


def test_spawn_workers_partial_failure_cleans_up_started_workers() -> None:
    configs = [_make_config("skill-a"), _make_config("skill-b")]
    registry = SkillRegistry()
    runner = _make_runner(registry=registry)

    first_proc = _make_fake_proc({"invocation_id": "x", "status": "ok", "error": None})

    with patch(
        "subprocess.Popen",
        side_effect=[first_proc, RuntimeError("spawn failed")],
    ):
        with pytest.raises(RuntimeError, match="spawn failed"):
            runner.spawn_workers(configs)

    first_proc.terminate.assert_called_once()
