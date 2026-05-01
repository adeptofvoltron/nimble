from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

from nimble.platform import is_linux, is_mac, is_windows

logger = logging.getLogger(__name__)

_macos_accessibility_warned = False


def _get_selection() -> str:
    if is_linux():
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
    if is_windows():
        try:
            from pynput.keyboard import Controller, Key

            save_result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=0.1,
            )
            if save_result.returncode != 0:
                return ""
            saved = save_result.stdout
            kbd = Controller()
            clipboard_touched = False
            try:
                kbd.press(Key.ctrl)
                kbd.press("c")
                kbd.release("c")
                kbd.release(Key.ctrl)
                clipboard_touched = True
                time.sleep(0.05)
                read_result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    timeout=0.1,
                )
                return read_result.stdout if read_result.returncode == 0 else ""
            finally:
                if clipboard_touched:
                    try:
                        subprocess.run(
                            [
                                "powershell",
                                "-NoProfile",
                                "-Command",
                                "$input | Set-Clipboard",
                            ],
                            input=saved,
                            text=True,
                            timeout=0.1,
                            capture_output=True,
                        )
                    except Exception:
                        pass
        except Exception:
            return ""
    if is_mac():
        global _macos_accessibility_warned
        if not _macos_accessibility_warned:
            logger.info(
                "macOS: Accessibility not granted —"
                " selection uses clipboard simulation."
                " Grant access in System Settings"
                " → Privacy & Security → Accessibility"
                " for more reliable capture."
            )
            _macos_accessibility_warned = True
        try:
            from pynput.keyboard import Controller, Key

            save_result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                timeout=0.1,
            )
            if save_result.returncode != 0:
                return ""
            saved = save_result.stdout
            kbd = Controller()
            clipboard_touched = False
            try:
                kbd.press(Key.cmd)
                kbd.press("c")
                kbd.release("c")
                kbd.release(Key.cmd)
                clipboard_touched = True
                time.sleep(0.05)
                read_result = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    text=True,
                    timeout=0.1,
                )
                return read_result.stdout if read_result.returncode == 0 else ""
            finally:
                if clipboard_touched:
                    try:
                        subprocess.run(
                            ["pbcopy"],
                            input=saved,
                            text=True,
                            timeout=0.1,
                            capture_output=True,
                        )
                    except Exception:
                        pass
        except Exception:
            return ""
    return ""


def _get_clipboard() -> str:
    if is_linux():
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
    if is_windows():
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=0.1,
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    if is_mac():
        try:
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                timeout=0.1,
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    return ""


def _get_active_app() -> str:
    if is_linux():
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
    if is_windows():
        try:
            import ctypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        except Exception:
            return ""
    if is_mac():
        try:
            script = (
                'tell application "System Events" to get name of '
                "first application process whose frontmost is true"
            )
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=0.1,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""
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
