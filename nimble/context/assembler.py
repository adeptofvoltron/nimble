from __future__ import annotations

import subprocess
from typing import Any

from nimble.platform import is_linux


def _get_selection() -> str:
    if not is_linux():
        return ""
    try:
        result = subprocess.run(
            ["xclip", "-o", "-selection", "primary"],
            capture_output=True,
            text=True,
            timeout=0.1,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def _get_clipboard() -> str:
    if not is_linux():
        return ""
    try:
        result = subprocess.run(
            ["xclip", "-o", "-selection", "clipboard"],
            capture_output=True,
            text=True,
            timeout=0.1,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def _get_active_app() -> str:
    if not is_linux():
        return ""
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
            timeout=0.1,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _get_mouse_position() -> list[int]:
    try:
        from pynput import mouse  # lazy import — safe in all environments

        pos = mouse.Controller().position
        return [int(pos[0]), int(pos[1])]
    except Exception:
        return [0, 0]


def build_context() -> dict[str, Any]:
    return {
        "selection": _get_selection(),
        "clipboard": _get_clipboard(),
        "active_app": _get_active_app(),
        "mouse_position": _get_mouse_position(),
    }
