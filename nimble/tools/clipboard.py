from __future__ import annotations

import logging
import subprocess

from nimble.platform import is_linux, is_mac, is_windows

logger = logging.getLogger(__name__)


class ClipboardTool:
    def get(self) -> str:
        if is_linux():
            try:
                result = subprocess.run(
                    ["xclip", "-o", "-selection", "clipboard"],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                )
                return result.stdout if result.returncode == 0 else ""
            except Exception:
                logger.warning("clipboard.get failed", exc_info=True)
                return ""
        if is_windows():
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                )
                return result.stdout if result.returncode == 0 else ""
            except Exception:
                logger.warning("clipboard.get failed", exc_info=True)
                return ""
        if is_mac():
            try:
                result = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                )
                return result.stdout if result.returncode == 0 else ""
            except Exception:
                logger.warning("clipboard.get failed", exc_info=True)
                return ""
        return ""

    def set(self, text: str) -> None:
        if is_linux():
            try:
                # xclip must stay alive as clipboard owner; write stdin and
                # close it so xclip receives the data, then return without
                # waiting — xclip runs in background until another app takes
                # the selection.
                proc = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                proc.stdin.write(text.encode("utf-8"))  # type: ignore[union-attr]
                proc.stdin.close()  # type: ignore[union-attr]
                return
            except Exception:
                logger.warning("clipboard.set failed", exc_info=True)
                return
        if is_windows():
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Set-Clipboard", "-Value", text],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                )
                return
            except Exception:
                logger.warning("clipboard.set failed", exc_info=True)
                return
        if is_mac():
            try:
                subprocess.run(
                    ["pbcopy"],
                    input=text,
                    text=True,
                    timeout=1.0,
                    capture_output=True,
                )
                return
            except Exception:
                logger.warning("clipboard.set failed", exc_info=True)
                return
