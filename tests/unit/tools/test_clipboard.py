from __future__ import annotations

from unittest.mock import MagicMock, patch

from nimble.tools.clipboard import ClipboardTool


def test_get_returns_clipboard_text() -> None:
    tool = ClipboardTool()
    mock_clipboard = MagicMock()
    mock_clipboard.paste.return_value = "hello"
    with patch.dict("sys.modules", {"plyer": MagicMock(clipboard=mock_clipboard)}):
        assert tool.get() == "hello"


def test_get_returns_empty_string_when_clipboard_empty() -> None:
    tool = ClipboardTool()
    mock_clipboard = MagicMock()
    mock_clipboard.paste.return_value = None
    with patch.dict("sys.modules", {"plyer": MagicMock(clipboard=mock_clipboard)}):
        assert tool.get() == ""


def test_get_returns_string_for_non_string_clipboard_value() -> None:
    tool = ClipboardTool()
    mock_clipboard = MagicMock()
    mock_clipboard.paste.return_value = 123
    with patch.dict("sys.modules", {"plyer": MagicMock(clipboard=mock_clipboard)}):
        assert tool.get() == "123"


def test_set_calls_plyer_copy() -> None:
    tool = ClipboardTool()
    mock_clipboard = MagicMock()
    with patch.dict("sys.modules", {"plyer": MagicMock(clipboard=mock_clipboard)}):
        tool.set("out")
    mock_clipboard.copy.assert_called_once_with("out")


def test_get_handles_plyer_failure_gracefully() -> None:
    tool = ClipboardTool()
    mock_clipboard = MagicMock()
    mock_clipboard.paste.side_effect = RuntimeError("fail")
    with patch.dict("sys.modules", {"plyer": MagicMock(clipboard=mock_clipboard)}):
        assert tool.get() == ""


def test_set_handles_plyer_failure_gracefully() -> None:
    tool = ClipboardTool()
    mock_clipboard = MagicMock()
    mock_clipboard.copy.side_effect = RuntimeError("fail")
    with patch.dict("sys.modules", {"plyer": MagicMock(clipboard=mock_clipboard)}):
        tool.set("text")  # must not raise


def test_get_handles_plyer_import_failure() -> None:
    tool = ClipboardTool()
    with patch.dict("sys.modules", {"plyer": None}):
        assert tool.get() == ""


def test_set_handles_plyer_import_failure() -> None:
    tool = ClipboardTool()
    with patch.dict("sys.modules", {"plyer": None}):
        tool.set("text")


def test_get_logs_warning_on_failure() -> None:
    tool = ClipboardTool()
    mock_clipboard = MagicMock()
    mock_clipboard.paste.side_effect = RuntimeError("fail")
    with patch.dict("sys.modules", {"plyer": MagicMock(clipboard=mock_clipboard)}):
        with patch("nimble.tools.clipboard.logger.warning") as mock_warning:
            result = tool.get()
    assert result == ""
    mock_warning.assert_called_once_with("clipboard.get failed", exc_info=True)


def test_set_logs_warning_on_failure() -> None:
    tool = ClipboardTool()
    mock_clipboard = MagicMock()
    mock_clipboard.copy.side_effect = RuntimeError("fail")
    with patch.dict("sys.modules", {"plyer": MagicMock(clipboard=mock_clipboard)}):
        with patch("nimble.tools.clipboard.logger.warning") as mock_warning:
            tool.set("text")
    mock_warning.assert_called_once_with("clipboard.set failed", exc_info=True)
