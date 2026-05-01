import json
import logging
from unittest.mock import MagicMock, patch

import pytest

import nimble.context.assembler as assembler
from nimble.context.assembler import (
    _get_active_app,
    _get_clipboard,
    _get_mouse_position,
    _get_selection,
    build_context,
)


def _mock_run(returncode: int, stdout: str) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def test_build_context_returns_required_keys() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "text")
    ):
        with patch(
            "nimble.context.assembler._get_mouse_position", return_value=[100, 200]
        ):
            ctx = build_context()
    assert set(ctx.keys()) == {"selection", "clipboard", "active_app", "mouse_position"}


def test_build_context_correct_types() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "hello")
    ):
        with patch(
            "nimble.context.assembler._get_mouse_position", return_value=[10, 20]
        ):
            ctx = build_context()
    assert isinstance(ctx["selection"], str)
    assert isinstance(ctx["clipboard"], str)
    assert isinstance(ctx["active_app"], str)
    assert isinstance(ctx["mouse_position"], list)
    assert len(ctx["mouse_position"]) == 2
    assert all(isinstance(v, int) for v in ctx["mouse_position"])


def test_selection_empty_on_subprocess_failure() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(1, "")
    ):
        assert _get_selection() == ""


def test_selection_empty_on_success_with_empty_stdout() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "")
    ):
        assert _get_selection() == ""


def test_clipboard_empty_on_subprocess_failure() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(1, "")
    ):
        assert _get_clipboard() == ""


def test_active_app_empty_on_subprocess_failure() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(1, "")
    ):
        assert _get_active_app() == ""


def test_mouse_position_happy_path() -> None:
    mock_mouse = MagicMock()
    mock_mouse.Controller.return_value.position = (1920, 1080)
    fake_modules = {"pynput": MagicMock(mouse=mock_mouse), "pynput.mouse": mock_mouse}
    with patch.dict("sys.modules", fake_modules):
        result = _get_mouse_position()
    assert result == [1920, 1080]
    assert all(isinstance(v, int) for v in result)


def test_mouse_position_fallback_on_exception() -> None:
    mock_mouse = MagicMock()
    mock_mouse.Controller.side_effect = RuntimeError("no display server")
    fake_modules = {"pynput": MagicMock(mouse=mock_mouse), "pynput.mouse": mock_mouse}
    with patch.dict("sys.modules", fake_modules):
        result = _get_mouse_position()
    assert result == [0, 0]


def test_build_context_json_round_trip() -> None:
    with patch(
        "nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "selected")
    ):
        with patch(
            "nimble.context.assembler._get_mouse_position", return_value=[800, 600]
        ):
            ctx = build_context()
    deserialized = json.loads(json.dumps(ctx))
    assert deserialized == ctx
    assert deserialized["mouse_position"] == [800, 600]
    assert isinstance(deserialized["mouse_position"][0], int)


# ---------------------------------------------------------------------------
# Windows clipboard tests (AC: 1, 8)
# ---------------------------------------------------------------------------


def test_clipboard_windows_returns_powershell_output() -> None:
    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            return_value=_mock_run(0, "win text"),
        ),
    ):
        assert _get_clipboard() == "win text"


def test_clipboard_windows_empty_on_failure() -> None:
    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            return_value=_mock_run(1, ""),
        ),
    ):
        assert _get_clipboard() == ""


# ---------------------------------------------------------------------------
# Windows active_app tests (AC: 2, 8)
# ---------------------------------------------------------------------------


def test_active_app_windows_returns_window_title() -> None:
    mock_windll = MagicMock()
    mock_windll.user32.GetForegroundWindow.return_value = 1
    mock_windll.user32.GetWindowTextLengthW.return_value = 5
    mock_buf = MagicMock()
    mock_buf.value = "My App"

    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch("ctypes.windll", mock_windll, create=True),
        patch("ctypes.create_unicode_buffer", return_value=mock_buf),
    ):
        result = assembler._get_active_app()
    assert result == "My App"


def test_active_app_windows_empty_on_ctypes_failure() -> None:
    mock_windll = MagicMock()
    mock_windll.user32.GetForegroundWindow.side_effect = AttributeError("no windll")

    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch("ctypes.windll", mock_windll, create=True),
    ):
        result = assembler._get_active_app()
    assert result == ""


# ---------------------------------------------------------------------------
# Windows selection tests (AC: 3, 7, 8)
# ---------------------------------------------------------------------------


def test_selection_windows_happy_path() -> None:
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_key.ctrl = "ctrl_key"
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)

    run_responses = [
        _mock_run(0, "saved text"),  # save (Get-Clipboard)
        _mock_run(0, "selected text"),  # read (Get-Clipboard after Ctrl+C)
        _mock_run(0, ""),  # restore ($input | Set-Clipboard)
    ]

    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=run_responses),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict(
            "sys.modules",
            {
                "pynput": MagicMock(keyboard=mock_pynput_keyboard),
                "pynput.keyboard": mock_pynput_keyboard,
            },
        ),
    ):
        result = assembler._get_selection()
    assert result == "selected text"


def test_selection_windows_restores_clipboard() -> None:
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_key.ctrl = "ctrl_key"
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)

    run_calls: list[MagicMock] = []

    def recording_run(*args: object, **kwargs: object) -> MagicMock:
        run_calls.append(MagicMock(args=args, kwargs=kwargs))
        if len(run_calls) == 1:
            return _mock_run(0, "saved text")
        elif len(run_calls) == 2:
            return _mock_run(0, "selected text")
        return _mock_run(0, "")

    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=recording_run),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict(
            "sys.modules",
            {
                "pynput": MagicMock(keyboard=mock_pynput_keyboard),
                "pynput.keyboard": mock_pynput_keyboard,
            },
        ),
    ):
        assembler._get_selection()

    assert len(run_calls) == 3
    restore_kwargs = run_calls[2].kwargs
    assert restore_kwargs.get("input") == "saved text"


def test_selection_windows_empty_on_failure() -> None:
    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            side_effect=FileNotFoundError("powershell not found"),
        ),
    ):
        assert assembler._get_selection() == ""


def test_selection_windows_empty_when_save_fails_returncode() -> None:
    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            return_value=_mock_run(1, "ignored"),
        ),
    ):
        assert assembler._get_selection() == ""


def test_selection_windows_restores_clipboard_after_read_raises() -> None:
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_key.ctrl = "ctrl_key"
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)

    run_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def run_side_effect(*args: object, **kwargs: object) -> MagicMock:
        run_calls.append((args, kwargs))
        n = len(run_calls)
        if n == 1:
            return _mock_run(0, "saved text")
        if n == 2:
            raise TimeoutError("read failed")
        return _mock_run(0, "")

    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=run_side_effect),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict(
            "sys.modules",
            {
                "pynput": MagicMock(keyboard=mock_pynput_keyboard),
                "pynput.keyboard": mock_pynput_keyboard,
            },
        ),
    ):
        assert assembler._get_selection() == ""

    assert len(run_calls) >= 3
    restore_cmd = run_calls[2][0][0]
    assert isinstance(restore_cmd, list)
    assert any("Set-Clipboard" in str(part) for part in restore_cmd)
    assert run_calls[2][1].get("input") == "saved text"


# ---------------------------------------------------------------------------
# macOS clipboard tests (AC: 4, 8)
# ---------------------------------------------------------------------------


def test_clipboard_mac_returns_pbpaste_output() -> None:
    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            return_value=_mock_run(0, "mac text"),
        ),
    ):
        assert _get_clipboard() == "mac text"


def test_clipboard_mac_empty_on_failure() -> None:
    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            return_value=_mock_run(1, ""),
        ),
    ):
        assert _get_clipboard() == ""


# ---------------------------------------------------------------------------
# macOS active_app tests (AC: 5, 8)
# ---------------------------------------------------------------------------


def test_active_app_mac_returns_osascript_output() -> None:
    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            return_value=_mock_run(0, "Safari\n"),
        ),
    ):
        assert _get_active_app() == "Safari"


def test_active_app_mac_empty_on_failure() -> None:
    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            return_value=_mock_run(1, ""),
        ),
    ):
        assert _get_active_app() == ""


# ---------------------------------------------------------------------------
# macOS selection tests (AC: 6, 7, 8)
# ---------------------------------------------------------------------------


def test_selection_mac_happy_path() -> None:
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_key.cmd = "cmd_key"
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)

    run_responses = [
        _mock_run(0, "saved"),  # save (pbpaste)
        _mock_run(0, "selected"),  # read (pbpaste after Cmd+C)
        _mock_run(0, ""),  # restore (pbcopy)
    ]

    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=run_responses),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict(
            "sys.modules",
            {
                "pynput": MagicMock(keyboard=mock_pynput_keyboard),
                "pynput.keyboard": mock_pynput_keyboard,
            },
        ),
    ):
        result = assembler._get_selection()
    assert result == "selected"


def test_selection_mac_restores_clipboard() -> None:
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_key.cmd = "cmd_key"
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)

    run_calls: list[MagicMock] = []

    def recording_run(*args: object, **kwargs: object) -> MagicMock:
        run_calls.append(MagicMock(args=args, kwargs=kwargs))
        if len(run_calls) == 1:
            return _mock_run(0, "saved")
        elif len(run_calls) == 2:
            return _mock_run(0, "selected")
        return _mock_run(0, "")

    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=recording_run),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict(
            "sys.modules",
            {
                "pynput": MagicMock(keyboard=mock_pynput_keyboard),
                "pynput.keyboard": mock_pynput_keyboard,
            },
        ),
    ):
        assembler._get_selection()

    assert len(run_calls) == 3
    restore_kwargs = run_calls[2].kwargs
    assert restore_kwargs.get("input") == "saved"


def test_selection_mac_empty_on_failure() -> None:
    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            side_effect=FileNotFoundError("pbpaste not found"),
        ),
    ):
        assert assembler._get_selection() == ""


def test_selection_mac_empty_when_save_fails_returncode() -> None:
    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch(
            "nimble.context.assembler.subprocess.run",
            return_value=_mock_run(1, "ignored"),
        ),
    ):
        assert assembler._get_selection() == ""


def test_selection_mac_restores_clipboard_after_read_raises() -> None:
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_key.cmd = "cmd_key"
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)

    run_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def run_side_effect(*args: object, **kwargs: object) -> MagicMock:
        run_calls.append((args, kwargs))
        n = len(run_calls)
        if n == 1:
            return _mock_run(0, "saved")
        if n == 2:
            raise TimeoutError("read failed")
        return _mock_run(0, "")

    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=run_side_effect),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict(
            "sys.modules",
            {
                "pynput": MagicMock(keyboard=mock_pynput_keyboard),
                "pynput.keyboard": mock_pynput_keyboard,
            },
        ),
    ):
        assert assembler._get_selection() == ""

    assert len(run_calls) >= 3
    assert run_calls[2][0][0] == ["pbcopy"]
    assert run_calls[2][1].get("input") == "saved"


# ---------------------------------------------------------------------------
# macOS one-time accessibility INFO log tests (AC: 4)
# ---------------------------------------------------------------------------


def test_selection_mac_logs_accessibility_info_on_first_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assembler._macos_accessibility_warned = False
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)
    run_responses = [_mock_run(0, ""), _mock_run(0, ""), _mock_run(0, "")]
    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=run_responses),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict(
            "sys.modules",
            {
                "pynput": MagicMock(keyboard=mock_pynput_keyboard),
                "pynput.keyboard": mock_pynput_keyboard,
            },
        ),
        caplog.at_level(logging.INFO, logger="nimble.context.assembler"),
    ):
        assembler._get_selection()
    assert any("Accessibility not granted" in r.message for r in caplog.records)


def test_selection_mac_logs_accessibility_info_only_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assembler._macos_accessibility_warned = False
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)
    run_responses = [
        _mock_run(0, ""),
        _mock_run(0, ""),
        _mock_run(0, ""),
        _mock_run(0, ""),
        _mock_run(0, ""),
        _mock_run(0, ""),
    ]
    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=run_responses),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict(
            "sys.modules",
            {
                "pynput": MagicMock(keyboard=mock_pynput_keyboard),
                "pynput.keyboard": mock_pynput_keyboard,
            },
        ),
        caplog.at_level(logging.INFO, logger="nimble.context.assembler"),
    ):
        assembler._get_selection()
        assembler._get_selection()
    assert (
        sum(1 for r in caplog.records if "Accessibility not granted" in r.message) == 1
    )
