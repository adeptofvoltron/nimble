from __future__ import annotations

from unittest.mock import patch

import nimble.platform as platform_module
from nimble.platform import is_linux, is_mac, is_windows


def test_is_linux_true() -> None:
    with patch.object(platform_module.sys, "platform", "linux"):
        assert is_linux() is True
        assert is_windows() is False
        assert is_mac() is False


def test_is_windows_true() -> None:
    with patch.object(platform_module.sys, "platform", "win32"):
        assert is_windows() is True
        assert is_linux() is False
        assert is_mac() is False


def test_is_mac_true() -> None:
    with patch.object(platform_module.sys, "platform", "darwin"):
        assert is_mac() is True
        assert is_linux() is False
        assert is_windows() is False
