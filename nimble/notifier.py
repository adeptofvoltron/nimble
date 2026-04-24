from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class Notifier:
    def send(self, title: str, body: str) -> None:
        try:
            from plyer import notification

            notification.notify(title=title, message=body, app_name="Nimble")
        except Exception:
            logger.warning("Notifier failed to send notification", exc_info=True)
