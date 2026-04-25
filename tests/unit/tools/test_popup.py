from __future__ import annotations

from unittest.mock import MagicMock, patch

from nimble.tools.popup import PopupTool


def test_show_calls_plyer_notify() -> None:
    tool = PopupTool()
    mock_notification = MagicMock()
    with patch.dict(
        "sys.modules", {"plyer": MagicMock(notification=mock_notification)}
    ):
        tool.show("Hello, Nimble!")
    mock_notification.notify.assert_called_once_with(
        title="Nimble", message="Hello, Nimble!", app_name="Nimble"
    )


def test_show_with_empty_string_does_not_raise() -> None:
    tool = PopupTool()
    mock_notification = MagicMock()
    with patch.dict(
        "sys.modules", {"plyer": MagicMock(notification=mock_notification)}
    ):
        tool.show("")
    mock_notification.notify.assert_called_once_with(
        title="Nimble", message="", app_name="Nimble"
    )


def test_show_handles_plyer_failure_gracefully() -> None:
    tool = PopupTool()
    mock_notification = MagicMock()
    mock_notification.notify.side_effect = RuntimeError("notify failed")
    with patch("nimble.tools.popup.logger.warning") as mock_warning:
        with patch.dict(
            "sys.modules", {"plyer": MagicMock(notification=mock_notification)}
        ):
            tool.show("text")  # must not propagate the exception
    mock_warning.assert_called_once_with("popup.show failed", exc_info=True)


def test_show_handles_plyer_import_failure() -> None:
    tool = PopupTool()
    with patch("nimble.tools.popup.logger.warning") as mock_warning:
        with patch.dict("sys.modules", {"plyer": None}):
            tool.show("text")  # must not raise even if plyer is unavailable
    mock_warning.assert_called_once_with("popup.show failed", exc_info=True)
