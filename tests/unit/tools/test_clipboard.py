from __future__ import annotations

from unittest.mock import MagicMock, patch

from nimble.tools.clipboard import ClipboardTool

_MOD = "nimble.tools.clipboard"
_IS_LINUX = f"{_MOD}.is_linux"
_IS_WINDOWS = f"{_MOD}.is_windows"
_IS_MAC = f"{_MOD}.is_mac"
_RUN = f"{_MOD}.subprocess.run"
_POPEN = f"{_MOD}.subprocess.Popen"
_WARN = f"{_MOD}.logger.warning"


def _completed(stdout: str = "", returncode: int = 0) -> MagicMock:
    return MagicMock(stdout=stdout, returncode=returncode)


def test_get_returns_clipboard_text() -> None:
    tool = ClipboardTool()
    with (
        patch(_IS_LINUX, return_value=True),
        patch(_RUN, return_value=_completed("hello")),
    ):
        assert tool.get() == "hello"


def test_get_returns_empty_string_when_clipboard_empty() -> None:
    tool = ClipboardTool()
    with (
        patch(_IS_LINUX, return_value=True),
        patch(_RUN, return_value=_completed("")),
    ):
        assert tool.get() == ""


def test_get_returns_empty_string_on_nonzero_exit() -> None:
    tool = ClipboardTool()
    with (
        patch(_IS_LINUX, return_value=True),
        patch(_RUN, return_value=_completed("out", 1)),
    ):
        assert tool.get() == ""


def test_set_calls_xclip_on_linux() -> None:
    tool = ClipboardTool()
    mock_proc = MagicMock()
    with (
        patch(_IS_LINUX, return_value=True),
        patch(_POPEN, return_value=mock_proc) as mock_popen,
    ):
        tool.set("hello")
    mock_popen.assert_called_once()
    assert mock_popen.call_args.args[0] == ["xclip", "-selection", "clipboard"]


def test_get_handles_subprocess_failure_gracefully() -> None:
    tool = ClipboardTool()
    with (
        patch(_IS_LINUX, return_value=True),
        patch(_RUN, side_effect=RuntimeError("fail")),
    ):
        assert tool.get() == ""


def test_set_handles_subprocess_failure_gracefully() -> None:
    tool = ClipboardTool()
    with (
        patch(_IS_LINUX, return_value=True),
        patch(_POPEN, side_effect=RuntimeError("fail")),
    ):
        tool.set("text")  # must not raise


def test_get_returns_empty_when_no_platform_matches() -> None:
    tool = ClipboardTool()
    with (
        patch(_IS_LINUX, return_value=False),
        patch(_IS_WINDOWS, return_value=False),
        patch(_IS_MAC, return_value=False),
    ):
        assert tool.get() == ""


def test_set_is_noop_when_no_platform_matches() -> None:
    tool = ClipboardTool()
    with (
        patch(_IS_LINUX, return_value=False),
        patch(_IS_WINDOWS, return_value=False),
        patch(_IS_MAC, return_value=False),
    ):
        tool.set("text")  # must not raise


def test_get_logs_warning_on_failure() -> None:
    tool = ClipboardTool()
    with (
        patch(_IS_LINUX, return_value=True),
        patch(_RUN, side_effect=RuntimeError("fail")),
        patch(_WARN) as mock_warning,
    ):
        result = tool.get()
    assert result == ""
    mock_warning.assert_called_once_with("clipboard.get failed", exc_info=True)


def test_set_logs_warning_on_failure() -> None:
    tool = ClipboardTool()
    with (
        patch(_IS_LINUX, return_value=True),
        patch(_POPEN, side_effect=RuntimeError("fail")),
        patch(_WARN) as mock_warning,
    ):
        tool.set("text")
    mock_warning.assert_called_once_with("clipboard.set failed", exc_info=True)
