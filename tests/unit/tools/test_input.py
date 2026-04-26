from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from nimble.tools.input import InputTool


def test_ask_returns_entered_text() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    mock_tkinter.simpledialog.askstring.return_value = "hello"
    with patch.dict(
        "sys.modules",
        {
            "tkinter": mock_tkinter,
            "tkinter.simpledialog": mock_tkinter.simpledialog,
        },
    ):
        result = tool.ask("Enter:")
    assert result == "hello"


def test_ask_returns_none_on_cancel() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    mock_tkinter.simpledialog.askstring.return_value = None
    with patch.dict(
        "sys.modules",
        {
            "tkinter": mock_tkinter,
            "tkinter.simpledialog": mock_tkinter.simpledialog,
        },
    ):
        result = tool.ask("Enter:")
    assert result is None


def test_ask_raises_runtime_error_when_tkinter_unavailable() -> None:
    tool = InputTool()
    with patch.dict("sys.modules", {"tkinter": None}):
        with pytest.raises(RuntimeError, match="Input dialog is not available"):
            tool.ask("Enter:")


def test_ask_calls_simpledialog_with_correct_args() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    mock_tkinter.simpledialog.askstring.return_value = "result"
    with patch.dict(
        "sys.modules",
        {
            "tkinter": mock_tkinter,
            "tkinter.simpledialog": mock_tkinter.simpledialog,
        },
    ):
        tool.ask("My prompt")
    mock_tkinter.simpledialog.askstring.assert_called_once_with("Nimble", "My prompt")


def test_select_returns_chosen_option() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    with patch.dict("sys.modules", {"tkinter": mock_tkinter}):
        with patch("nimble.tools.input._run_select_dialog", return_value="Summarize"):
            result = tool.select("Choose:", ["Summarize", "Translate"])
    assert result == "Summarize"


def test_select_returns_none_on_dismiss() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    with patch.dict("sys.modules", {"tkinter": mock_tkinter}):
        with patch("nimble.tools.input._run_select_dialog", return_value=None):
            result = tool.select("Choose:", ["A", "B"])
    assert result is None


def test_select_raises_runtime_error_when_tkinter_unavailable() -> None:
    tool = InputTool()
    with patch.dict("sys.modules", {"tkinter": None}):
        with pytest.raises(RuntimeError, match="Input dialog is not available"):
            tool.select("Choose:", ["A", "B"])
