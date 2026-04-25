from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PopupTool:
    def show(self, text: str) -> None:
        try:
            from plyer import notification

            notification.notify(title="Nimble", message=text, app_name="Nimble")
        except Exception:
            logger.warning("popup.show failed", exc_info=True)
