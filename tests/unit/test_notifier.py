from __future__ import annotations

from unittest.mock import MagicMock, patch

from nimble.notifier import Notifier


def test_send_calls_plyer_notify() -> None:
    mock_notification = MagicMock()
    with patch.dict(
        "sys.modules", {"plyer": MagicMock(notification=mock_notification)}
    ):
        Notifier().send("T", "B")
    mock_notification.notify.assert_called_once_with(
        title="T", message="B", app_name="Nimble"
    )


def test_send_swallows_plyer_exception() -> None:
    mock_notification = MagicMock()
    mock_notification.notify.side_effect = Exception("plyer error")
    with patch.dict(
        "sys.modules", {"plyer": MagicMock(notification=mock_notification)}
    ):
        Notifier().send("T", "B")
