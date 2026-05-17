# WaylandXWaylandAdapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `WaylandXWaylandAdapter` that makes Nimble's global hotkeys work out-of-the-box on Ubuntu Wayland+XWayland by spawning an invisible X11 keepalive window at daemon start.

**Architecture:** `WaylandXWaylandAdapter` extends `X11HotkeyAdapter`, overriding `start()` to create a 1×1 `InputOnly` X11 window before starting pynput, and `stop()` to destroy it after. The factory `get_adapter()` detects `WAYLAND_DISPLAY + DISPLAY` and returns the new adapter; pure-Wayland (no `DISPLAY`) raises a clear error.

**Tech Stack:** Python 3.10+, pynput (already a dependency), python-xlib (already installed as pynput dependency), pytest, unittest.mock.

---

## File map

| File | Change |
|---|---|
| `nimble/hotkeys/wayland.py` | CREATE — WaylandXWaylandAdapter |
| `nimble/hotkeys/__init__.py` | MODIFY — factory detection |
| `tests/unit/hotkeys/test_wayland.py` | CREATE — adapter unit tests |
| `tests/unit/hotkeys/test_factory.py` | MODIFY — 2 new cases + fix existing X11 case |

---

## Task 1: WaylandXWaylandAdapter

**Files:**
- Create: `nimble/hotkeys/wayland.py`
- Create: `tests/unit/hotkeys/test_wayland.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/hotkeys/test_wayland.py`:

```python
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from nimble.hotkeys.wayland import WaylandXWaylandAdapter


def _make_mocks() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
    mock_win = MagicMock()
    mock_root = MagicMock()
    mock_root.create_window.return_value = mock_win
    mock_screen = MagicMock()
    mock_screen.root = mock_root
    mock_disp = MagicMock()
    mock_disp.screen.return_value = mock_screen
    mock_display_mod = MagicMock()
    mock_display_mod.Display.return_value = mock_disp
    mock_X = MagicMock()
    mock_X.InputOnly = 2
    mock_X.CopyFromParent = 0
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys.return_value = MagicMock()
    return mock_win, mock_disp, mock_display_mod, mock_X, mock_keyboard


def _start(
    adapter: WaylandXWaylandAdapter,
    mock_display_mod: MagicMock,
    mock_X: MagicMock,
    mock_keyboard: MagicMock,
) -> None:
    with (
        patch("nimble.hotkeys.wayland._xlib_display", return_value=mock_display_mod),
        patch("nimble.hotkeys.wayland._xlib_x", return_value=mock_X),
        patch("nimble.hotkeys.x11._pynput_keyboard", return_value=mock_keyboard),
        patch.dict(os.environ, {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}),
    ):
        adapter.start()


def test_start_creates_inputonly_window_before_listener() -> None:
    adapter = WaylandXWaylandAdapter()
    mock_win, mock_disp, mock_display_mod, mock_X, mock_keyboard = _make_mocks()
    mock_listener = mock_keyboard.GlobalHotKeys.return_value

    call_order: list[str] = []
    mock_win.map.side_effect = lambda: call_order.append("map")
    mock_disp.flush.side_effect = lambda: call_order.append("flush")
    mock_listener.start.side_effect = lambda: call_order.append("listener_start")

    _start(adapter, mock_display_mod, mock_X, mock_keyboard)

    mock_disp.screen.return_value.root.create_window.assert_called_once_with(
        0, 0, 1, 1, 0, 0, mock_X.InputOnly, mock_X.CopyFromParent
    )
    assert call_order == ["map", "flush", "listener_start"]


def test_stop_destroys_window_after_listener() -> None:
    adapter = WaylandXWaylandAdapter()
    mock_win, mock_disp, mock_display_mod, mock_X, mock_keyboard = _make_mocks()
    mock_listener = mock_keyboard.GlobalHotKeys.return_value

    call_order: list[str] = []
    mock_listener.stop.side_effect = lambda: call_order.append("listener_stop")
    mock_listener.join.side_effect = lambda: call_order.append("listener_join")
    mock_win.destroy.side_effect = lambda: call_order.append("win_destroy")
    mock_disp.close.side_effect = lambda: call_order.append("disp_close")

    _start(adapter, mock_display_mod, mock_X, mock_keyboard)
    adapter.stop()

    assert call_order == ["listener_stop", "listener_join", "win_destroy", "disp_close"]


def test_stop_before_start_is_noop() -> None:
    adapter = WaylandXWaylandAdapter()
    adapter.stop()


def test_register_duplicate_raises_value_error() -> None:
    adapter = WaylandXWaylandAdapter()
    adapter.register("ctrl+shift+h", lambda: None)
    with pytest.raises(ValueError, match="already registered"):
        adapter.register("ctrl+shift+h", lambda: None)


def test_start_raises_when_display_open_fails() -> None:
    adapter = WaylandXWaylandAdapter()
    mock_display_mod = MagicMock()
    mock_display_mod.Display.side_effect = Exception("no display")
    mock_X = MagicMock()

    with (
        patch("nimble.hotkeys.wayland._xlib_display", return_value=mock_display_mod),
        patch("nimble.hotkeys.wayland._xlib_x", return_value=mock_X),
        patch.dict(os.environ, {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}),
    ):
        with pytest.raises(RuntimeError, match="cannot open X display"):
            adapter.start()


def test_stop_window_destroy_failure_does_not_raise() -> None:
    adapter = WaylandXWaylandAdapter()
    mock_win, mock_disp, mock_display_mod, mock_X, mock_keyboard = _make_mocks()
    mock_win.destroy.side_effect = Exception("oops")

    _start(adapter, mock_display_mod, mock_X, mock_keyboard)
    adapter.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/unit/hotkeys/test_wayland.py -v
```

Expected: `ModuleNotFoundError: No module named 'nimble.hotkeys.wayland'`

- [ ] **Step 3: Implement `nimble/hotkeys/wayland.py`**

```python
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
        super().start()

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/unit/hotkeys/test_wayland.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add nimble/hotkeys/wayland.py tests/unit/hotkeys/test_wayland.py
git commit -m "feat(hotkeys): add WaylandXWaylandAdapter with X11 keepalive window"
```

---

## Task 2: Factory update

**Files:**
- Modify: `nimble/hotkeys/__init__.py`
- Modify: `tests/unit/hotkeys/test_factory.py`

- [ ] **Step 1: Write the failing factory tests**

Replace the entire contents of `tests/unit/hotkeys/test_factory.py` with:

```python
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

from nimble.hotkeys import get_adapter
from nimble.hotkeys.wayland import WaylandXWaylandAdapter
from nimble.hotkeys.windows import WindowsHotkeyAdapter
from nimble.hotkeys.x11 import X11HotkeyAdapter


def test_get_adapter_returns_x11_on_pure_x11() -> None:
    with patch.object(sys, "platform", "linux"):
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
            os.environ.pop("WAYLAND_DISPLAY", None)
            adapter = get_adapter()
    assert isinstance(adapter, X11HotkeyAdapter)
    assert not isinstance(adapter, WaylandXWaylandAdapter)


def test_get_adapter_returns_wayland_adapter_on_xwayland() -> None:
    with patch.object(sys, "platform", "linux"):
        with patch.dict(
            os.environ, {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}
        ):
            adapter = get_adapter()
    assert isinstance(adapter, WaylandXWaylandAdapter)


def test_get_adapter_raises_on_pure_wayland_no_display() -> None:
    with patch.object(sys, "platform", "linux"):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False):
            os.environ.pop("DISPLAY", None)
            with pytest.raises(RuntimeError, match="XWayland"):
                get_adapter()


def test_get_adapter_returns_windows_on_win32() -> None:
    with patch.object(sys, "platform", "win32"):
        adapter = get_adapter()
    assert isinstance(adapter, WindowsHotkeyAdapter)


def test_get_adapter_raises_on_unsupported_platform() -> None:
    with patch.object(sys, "platform", "darwin"):
        with pytest.raises(RuntimeError, match="Unsupported platform: darwin"):
            get_adapter()
```

- [ ] **Step 2: Run tests to verify the two new cases fail**

```bash
.venv/bin/pytest tests/unit/hotkeys/test_factory.py -v
```

Expected: `test_get_adapter_returns_wayland_adapter_on_xwayland FAILED` and `test_get_adapter_raises_on_pure_wayland_no_display FAILED`

- [ ] **Step 3: Update `nimble/hotkeys/__init__.py`**

```python
from __future__ import annotations

import os
import sys

from nimble.hotkeys.base import HotkeyAdapter
from nimble.platform import is_linux, is_windows


def get_adapter() -> HotkeyAdapter:
    if is_linux():
        wayland = os.environ.get("WAYLAND_DISPLAY")
        display = os.environ.get("DISPLAY")
        if wayland and not display:
            raise RuntimeError(
                "Nimble requires XWayland on pure Wayland sessions. "
                "Install XWayland or set DISPLAY to your X11 display."
            )
        if wayland and display:
            from nimble.hotkeys.wayland import WaylandXWaylandAdapter

            return WaylandXWaylandAdapter()
        from nimble.hotkeys.x11 import X11HotkeyAdapter

        return X11HotkeyAdapter()
    elif is_windows():
        from nimble.hotkeys.windows import WindowsHotkeyAdapter

        return WindowsHotkeyAdapter()
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
```

- [ ] **Step 4: Run the full test suite**

```bash
.venv/bin/pytest tests/ -v
```

Expected: all tests pass (354 existing + 7 new wayland + 5 factory = 366 total)

- [ ] **Step 5: Commit**

```bash
git add nimble/hotkeys/__init__.py tests/unit/hotkeys/test_factory.py
git commit -m "feat(hotkeys): factory detects Wayland+XWayland and returns WaylandXWaylandAdapter"
```

---

## Task 3: Live smoke test

- [ ] **Step 1: Stop any running daemon**

```bash
.venv/bin/nimble stop 2>/dev/null || true
```

- [ ] **Step 2: Start daemon and confirm it picks the Wayland adapter**

```bash
DISPLAY=:0 .venv/bin/nimble start --debug
sleep 1
.venv/bin/nimble status
```

Expected:
```
Daemon: pid=XXXXX  started_at=...  daemon_version=1.0.0

Skills:
  hello_world          local        ctrl+l               loaded
```

- [ ] **Step 3: Trigger the hotkey and confirm dispatch in logs**

```bash
DISPLAY=:0 .venv/bin/python trigger_skill.py ctrl+l
sleep 2
tail -5 "$(.venv/bin/python -c "from nimble.logging_setup import LOG_PATH; print(LOG_PATH)")"
```

Expected log line: `DEBUG nimble.skills.runner: Skill hello_world dispatch completed in XX.Xms`

Expected on desktop: notification popup "Hello from Nimble! The daemon is working."

- [ ] **Step 4: Stop the daemon**

```bash
.venv/bin/nimble stop
```
