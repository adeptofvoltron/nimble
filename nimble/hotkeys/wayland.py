from __future__ import annotations

import logging
import os
from typing import Any

from nimble.hotkeys.x11 import X11HotkeyAdapter

logger = logging.getLogger(__name__)


def _xlib_display() -> Any:
    from Xlib import display
    return display


def _xlib_x() -> Any:
    from Xlib import X
    return X


class WaylandXWaylandAdapter(X11HotkeyAdapter):
    def __init__(self) -> None:
        super().__init__()
        self._keepalive_display: Any = None
        self._keepalive_win: Any = None

    def start(self) -> None:
        display_mod = _xlib_display()
        X = _xlib_x()
        display_name = os.environ.get("DISPLAY", ":0")
        try:
            d = display_mod.Display(display_name)
        except Exception as exc:
            raise RuntimeError(
                f"WaylandXWaylandAdapter: cannot open X display {display_name!r}: {exc}"
            ) from exc
        screen = d.screen()
        try:
            win = screen.root.create_window(
                0, 0, 1, 1, 0,
                0,
                X.InputOnly,
                X.CopyFromParent,
            )
            win.map()
            d.flush()
        except Exception as exc:
            d.close()
            raise RuntimeError(
                f"WaylandXWaylandAdapter: cannot create keepalive window: {exc}"
            ) from exc
        self._keepalive_display = d
        self._keepalive_win = win
        try:
            super().start()
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        super().stop()
        if self._keepalive_win is not None:
            try:
                self._keepalive_win.destroy()
            except Exception:
                logger.warning("Failed to destroy keepalive window", exc_info=True)
            self._keepalive_win = None
        if self._keepalive_display is not None:
            try:
                self._keepalive_display.close()
            except Exception:
                logger.warning("Failed to close Xlib display", exc_info=True)
            self._keepalive_display = None
