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
    assert len(results) == 1
    assert results[0]["status"] == "ok"
    assert results[0]["invocation_id"] == "abc-123"
    assert results[0]["error"] is None


def test_error_path_produces_error_response() -> None:
    results = _run_with_lines(_ErrorSkill(), _make_payload("err-uuid"))
    assert len(results) == 1
    r = results[0]
    assert r["status"] == "error"
    assert r["invocation_id"] == "err-uuid"
    assert r["error"]["type"] == "KeyError"
    assert r["error"]["message"] != ""


def test_worker_survives_error_and_processes_next() -> None:
    lines = [_make_payload("first-id"), _make_payload("second-id")]
    results = _run_with_lines(_ErrorSkill(), *lines)
    assert len(results) == 2
    assert results[0]["status"] == "error"
    assert results[0]["invocation_id"] == "first-id"
    assert results[1]["status"] == "error"
    assert results[1]["invocation_id"] == "second-id"


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
    finally:
        root.setLevel(original_level)
        for h in root.handlers[:]:
            if h not in original_handlers:
                root.removeHandler(h)
        monkeypatch.delenv("NIMBLE_LOG_PATH", raising=False)


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
