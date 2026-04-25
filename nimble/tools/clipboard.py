from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ClipboardTool:
    def get(self) -> str:
        try:
            from plyer import clipboard as plyer_clipboard

            result = plyer_clipboard.paste()
            return "" if result is None else str(result)
        except Exception:
            logger.warning("clipboard.get failed", exc_info=True)
            return ""

    def set(self, text: str) -> None:
        try:
            from plyer import clipboard as plyer_clipboard

            plyer_clipboard.copy(text)
        except Exception:
            logger.warning("clipboard.set failed", exc_info=True)
