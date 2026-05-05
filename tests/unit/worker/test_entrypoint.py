import importlib
import io
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import worker.entrypoint as entrypoint_mod
from worker.context import Context


class _FakeSkill:
    configuration: dict[str, str]

    def run(self, context: Context, tools: Any) -> None:
        pass


class _ErrorSkill:
    def run(self, context: Context, tools: Any) -> None:
        raise KeyError("missing_key")


def _make_payload(invocation_id: str = "test-uuid-1234") -> str:
    return json.dumps(
        {
            "invocation_id": invocation_id,
            "context": {
                "selection": "hello",
                "clipboard": "world",
                "active_app": "Terminal",
                "mouse_position": [100, 200],
            },
        }
    )


def _run_with_lines(skill_instance: Any, *lines: str) -> list[dict[str, Any]]:
    stdin_text = "\n".join(lines) + "\n"
    stdout_buf = io.StringIO()
    fake_class = MagicMock(return_value=skill_instance)

    with (
        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
        patch("sys.stdin", io.StringIO(stdin_text)),
        patch("sys.stdout", stdout_buf),
    ):
        entrypoint_mod.run("fake/path.py", "FakeSkill")

    results = []
    for raw in stdout_buf.getvalue().splitlines():
        raw = raw.strip()
        if raw:
            results.append(json.loads(raw))
    return results


def test_startup_fails_on_invalid_nimble_ai_config_json() -> None:
    stdin_text = _make_payload("abc-123") + "\n"
    stdout_buf = io.StringIO()
    fake_class = MagicMock(return_value=_FakeSkill())
    with (
        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
        patch.dict(os.environ, {"NIMBLE_AI_CONFIG": "not-json-brace"}, clear=False),
        patch("sys.stdin", io.StringIO(stdin_text)),
        patch("sys.stdout", stdout_buf),
    ):
        entrypoint_mod.run("fake/path.py", "FakeSkill")

    lines = [ln for ln in stdout_buf.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 1
    response = json.loads(lines[0])
    assert response["status"] == "error"
    assert response["invocation_id"] == ""
    assert "NIMBLE_AI_CONFIG" in response["error"]["message"]


def test_startup_fails_on_missing_keys_in_nimble_ai_config() -> None:
    stdin_text = _make_payload("abc-123") + "\n"
    stdout_buf = io.StringIO()
    fake_class = MagicMock(return_value=_FakeSkill())
    bad_config = json.dumps({"provider": "anthropic", "model": "x"})
    with (
        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
        patch.dict(os.environ, {"NIMBLE_AI_CONFIG": bad_config}, clear=False),
        patch("sys.stdin", io.StringIO(stdin_text)),
        patch("sys.stdout", stdout_buf),
    ):
        entrypoint_mod.run("fake/path.py", "FakeSkill")

    lines = [ln for ln in stdout_buf.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 1
    response = json.loads(lines[0])
    assert response["status"] == "error"
    assert "api_key_env" in response["error"]["message"]


def test_happy_path_produces_ok_response() -> None:
    results = _run_with_lines(_FakeSkill(), _make_payload("abc-123"))
    assert len(results) == 2
    assert results[0]["status"] == "ok"
    assert results[0]["invocation_id"] == ""  # startup handshake
    assert results[1]["status"] == "ok"
    assert results[1]["invocation_id"] == "abc-123"
    assert results[1]["error"] is None


def test_error_path_produces_error_response() -> None:
    results = _run_with_lines(_ErrorSkill(), _make_payload("err-uuid"))
    assert len(results) == 2
    r = results[1]
    assert r["status"] == "error"
    assert r["invocation_id"] == "err-uuid"
    assert r["error"]["type"] == "KeyError"
    assert r["error"]["message"] != ""


def test_worker_survives_error_and_processes_next() -> None:
    lines = [_make_payload("first-id"), _make_payload("second-id")]
    results = _run_with_lines(_ErrorSkill(), *lines)
    assert len(results) == 3
    assert results[1]["status"] == "error"
    assert results[1]["invocation_id"] == "first-id"
    assert results[2]["status"] == "error"
    assert results[2]["invocation_id"] == "second-id"


def test_sys_path_contains_repo_root() -> None:
    repo_root = str(Path(entrypoint_mod.__file__).parent.parent)
    assert repo_root in sys.path


def test_log_path_env_wires_file_handler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path = str(tmp_path / "nimble.log")
    monkeypatch.setenv("NIMBLE_LOG_PATH", log_path)

    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    try:
        with patch("logging.FileHandler") as mock_fh:
            importlib.reload(entrypoint_mod)
        mock_fh.assert_called_once_with(log_path)
        fmt_arg = mock_fh.return_value.setFormatter.call_args[0][0]
        assert fmt_arg._fmt == "%(asctime)s %(levelname)s %(name)s: %(message)s"
    finally:
        root.setLevel(original_level)
        for h in root.handlers[:]:
            if h not in original_handlers:
                root.removeHandler(h)
        monkeypatch.delenv("NIMBLE_LOG_PATH", raising=False)


def test_no_log_path_env_adds_null_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBLE_LOG_PATH", raising=False)

    root = logging.getLogger()
    original_handlers = root.handlers[:]

    try:
        importlib.reload(entrypoint_mod)
        new_handlers = [h for h in root.handlers if h not in original_handlers]
        assert len(new_handlers) == 1
        assert isinstance(new_handlers[0], logging.NullHandler)
    finally:
        for h in root.handlers[:]:
            if h not in original_handlers:
                root.removeHandler(h)


# ---------------------------------------------------------------------------
# Lifecycle hook tests
# ---------------------------------------------------------------------------


class _OnLoadSkill:
    def __init__(self) -> None:
        self.loaded = False
        self.load_config: Any = None

    def on_load(self, config: Any) -> None:
        self.loaded = True
        self.load_config = config

    def run(self, context: Context, tools: Any) -> None:
        pass


class _OnLoadFailSkill:
    def on_load(self, config: Any) -> None:
        raise ValueError("API key not set")

    def run(self, context: Context, tools: Any) -> None:
        pass


class _OnErrorEnrichSkill:
    def on_error(self, exc: BaseException) -> None:
        exc.args = (*exc.args, "enriched context")

    def run(self, context: Context, tools: Any) -> None:
        raise RuntimeError("original message")


class _OnErrorRaisingSkill:
    def on_error(self, exc: BaseException) -> None:
        raise TypeError("on_error blew up")

    def run(self, context: Context, tools: Any) -> None:
        raise ValueError("original error")


class _OnUnloadSkill:
    def __init__(self) -> None:
        self.unloaded = False

    def on_unload(self) -> None:
        self.unloaded = True

    def run(self, context: Context, tools: Any) -> None:
        pass


def test_on_load_called_before_ipc_loop() -> None:
    skill = _OnLoadSkill()
    results = _run_with_lines(skill, _make_payload("abc-123"))
    assert skill.loaded is True
    assert isinstance(skill.load_config, dict)
    assert len(results) == 2
    assert results[1]["status"] == "ok"
    assert results[1]["invocation_id"] == "abc-123"


def test_on_load_receives_empty_dict_for_non_object_skill_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill = _OnLoadSkill()
    monkeypatch.setenv("NIMBLE_SKILL_CONFIG", "[]")
    try:
        _run_with_lines(skill, _make_payload("abc-123"))
        assert skill.loaded is True
        assert skill.load_config == {}
    finally:
        monkeypatch.delenv("NIMBLE_SKILL_CONFIG", raising=False)


def test_on_load_failure_writes_error_response() -> None:
    skill = _OnLoadFailSkill()
    results = _run_with_lines(skill, _make_payload("abc-123"))
    assert len(results) == 1
    r = results[0]
    assert r["status"] == "error"
    assert r["invocation_id"] == ""
    assert r["phase"] == "on_load"
    assert "API key not set" in r["error"]["message"]


def test_on_error_called_when_run_raises() -> None:
    skill = _OnErrorEnrichSkill()
    results = _run_with_lines(skill, _make_payload("err-id"))
    assert len(results) == 2
    r = results[1]
    assert r["status"] == "error"
    assert "enriched context" in r["error"]["message"]


def test_on_error_itself_raising_uses_original_exception() -> None:
    skill = _OnErrorRaisingSkill()
    results = _run_with_lines(skill, _make_payload("err-id"))
    assert len(results) == 2
    r = results[1]
    assert r["status"] == "error"
    assert r["error"]["type"] == "ValueError"
    assert "original error" in r["error"]["message"]


def test_on_unload_called_after_ipc_loop() -> None:
    skill = _OnUnloadSkill()
    _run_with_lines(skill)  # empty stdin — loop exits immediately
    assert skill.unloaded is True


def test_success_handshake_written_before_ipc_loop() -> None:
    results = _run_with_lines(_FakeSkill(), _make_payload("inv-id"))
    assert len(results) == 2
    handshake = results[0]
    assert handshake["invocation_id"] == ""
    assert handshake["status"] == "ok"
    invocation = results[1]
    assert invocation["invocation_id"] == "inv-id"
    assert invocation["status"] == "ok"


def test_thread_excepthook_serialises_to_stdout() -> None:
    stdout_buf = io.StringIO()
    entrypoint_mod._invocation_local.invocation_id = "thread-test-id"

    try:
        raise RuntimeError("thread boom")
    except RuntimeError as exc:
        real_exc = exc

    exc_args = threading.ExceptHookArgs(
        (type(real_exc), real_exc, real_exc.__traceback__, threading.current_thread())
    )

    with patch("sys.stdout", stdout_buf):
        entrypoint_mod._thread_excepthook(exc_args)

    output = stdout_buf.getvalue().strip()
    assert output, "Expected output from thread excepthook"
    response = json.loads(output)
    assert response["status"] == "error"
    assert response["invocation_id"] == "thread-test-id"
    assert response["error"]["type"] == "RuntimeError"
    assert "boom" in response["error"]["message"]
    assert response["error"]["skill_file"] != ""
    assert response["error"]["line"] > 0


# ---------------------------------------------------------------------------
# skill.configuration injection tests (AC: 4, 5, 6, 7)
# ---------------------------------------------------------------------------


def test_worker_sets_skill_configuration_before_on_load() -> None:
    on_load_config: dict[str, Any] = {}

    class _ConfigSkill:
        configuration: dict[str, str]

        def on_load(self, config: dict[str, Any]) -> None:
            on_load_config.update(config)

        def run(self, context: Context, tools: Any) -> None:
            pass

    skill_instance = _ConfigSkill()
    stdout_buf = io.StringIO()
    fake_class = MagicMock(return_value=skill_instance)

    env = {
        **os.environ,
        "NIMBLE_SKILL_CONFIG": json.dumps(
            {
                "name": "translator",
                "source": "local",
                "binding": "ctrl+t",
                "path": "skills/translator/skill.py",
                "class_name": "Translator",
                "configuration": {"target_language": "es"},
            }
        ),
    }
    with (
        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
        patch("sys.stdin", io.StringIO("")),
        patch("sys.stdout", stdout_buf),
        patch.dict(os.environ, env, clear=True),
    ):
        entrypoint_mod.run("fake/path.py", "FakeSkill")

    assert skill_instance.configuration == {"target_language": "es"}
    assert on_load_config["name"] == "translator"
    assert on_load_config["configuration"] == {"target_language": "es"}


def test_worker_configuration_defaults_to_empty_dict() -> None:
    skill_instance = _FakeSkill()
    stdout_buf = io.StringIO()
    fake_class = MagicMock(return_value=skill_instance)

    env = {
        **os.environ,
        "NIMBLE_SKILL_CONFIG": json.dumps(
            {
                "name": "my_skill",
                "source": "local",
                "binding": "ctrl+x",
                "path": "skills/my_skill/skill.py",
                "class_name": "MySkill",
            }
        ),
    }
    with (
        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
        patch("sys.stdin", io.StringIO("")),
        patch("sys.stdout", stdout_buf),
        patch.dict(os.environ, env, clear=True),
    ):
        entrypoint_mod.run("fake/path.py", "FakeSkill")

    assert skill_instance.configuration == {}


def test_worker_skill_run_accesses_configuration_with_values() -> None:
    """AC 5: skill's run() can access self.configuration values"""
    config_accessed: dict[str, Any] = {}

    class _RunConfigSkill:
        configuration: dict[str, str]

        def run(self, context: Context, tools: Any) -> None:
            config_accessed.update(self.configuration)

        def on_load(self, config: dict[str, Any]) -> None:
            pass

    skill_instance = _RunConfigSkill()
    stdout_buf = io.StringIO()
    fake_class = MagicMock(return_value=skill_instance)

    invocation_input = json.dumps(
        {
            "invocation_id": "test-123",
            "context": {
                "selection": "",
                "clipboard": "",
                "active_app": "",
                "mouse_position": [0, 0],
            },
        }
    )

    env = {
        **os.environ,
        "NIMBLE_SKILL_CONFIG": json.dumps(
            {
                "name": "translator",
                "source": "local",
                "binding": "ctrl+t",
                "path": "skills/translator/skill.py",
                "class_name": "Translator",
                "configuration": {"target_language": "es", "fallback": "en"},
            }
        ),
    }
    with (
        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
        patch("sys.stdin", io.StringIO(invocation_input + "\n")),
        patch("sys.stdout", stdout_buf),
        patch.dict(os.environ, env, clear=True),
    ):
        entrypoint_mod.run("fake/path.py", "Translator")

    assert config_accessed == {"target_language": "es", "fallback": "en"}


def test_worker_skill_run_accesses_empty_configuration_no_error() -> None:
    """AC 6: skill's run() accesses self.configuration == {} without AttributeError"""
    config_value: dict[str, Any] = {}

    class _RunNoConfigSkill:
        configuration: dict[str, str]

        def run(self, context: Context, tools: Any) -> None:
            config_value.update(self.configuration)

    skill_instance = _RunNoConfigSkill()
    stdout_buf = io.StringIO()
    fake_class = MagicMock(return_value=skill_instance)

    invocation_input = json.dumps(
        {
            "invocation_id": "test-456",
            "context": {
                "selection": "",
                "clipboard": "",
                "active_app": "",
                "mouse_position": [0, 0],
            },
        }
    )

    env = {
        **os.environ,
        "NIMBLE_SKILL_CONFIG": json.dumps(
            {
                "name": "my_skill",
                "source": "local",
                "binding": "ctrl+x",
                "path": "skills/my_skill/skill.py",
                "class_name": "MySkill",
            }
        ),
    }
    with (
        patch.object(entrypoint_mod, "_load_skill_class", return_value=fake_class),
        patch("sys.stdin", io.StringIO(invocation_input + "\n")),
        patch("sys.stdout", stdout_buf),
        patch.dict(os.environ, env, clear=True),
    ):
        entrypoint_mod.run("fake/path.py", "MySkill")

    assert config_value == {}
