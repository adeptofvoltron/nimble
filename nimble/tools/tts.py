from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class TtsTool:
    def speak(self, text: str) -> None:
        try:
            from plyer import tts as plyer_tts

            plyer_tts.speak(text)
        except Exception as exc:
            raise RuntimeError(f"TTS is not available: {exc}") from exc
