from __future__ import annotations

import sys


def is_windows() -> bool:
    return sys.platform == "win32"


def is_linux() -> bool:
    return sys.platform == "linux"


def is_mac() -> bool:
    return sys.platform == "darwin"
