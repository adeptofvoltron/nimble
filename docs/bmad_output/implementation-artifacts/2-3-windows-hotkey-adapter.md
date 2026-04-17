# Story 2.3: Windows Hotkey Adapter

Status: done

## Story

As a Windows user,
I want the daemon to capture my configured keyboard shortcuts globally,
So that my skills execute regardless of which application is in focus.

## Acceptance Criteria

1. **Given** `nimble/hotkeys/windows.py` implements `HotkeyAdapter` using pynput
   **When** `register("ctrl+shift+d", callback)` is called and the user presses Ctrl+Shift+D
   **Then** `callback` is invoked within 200ms

2. **Given** a binding is registered for a known Windows-reserved combination (e.g. `win+l`)
   **When** `WindowsHotkeyAdapter.start()` is called
   **Then** a `WARNING` log entry is written identifying the reserved shortcut (FR5)
   **And** the daemon starts normally — the warning is non-fatal

3. **Given** `stop()` is called while the adapter is running
   **When** the adapter shuts down
   **Then** the pynput listener terminates cleanly with no dangling threads

## Tasks / Subtasks

- [x] Task 1: Extract `_to_pynput_format` and `_MODIFIERS` from `x11.py` into `base.py` (AC: 1)
  - [x] Move `_MODIFIERS` set and `_to_pynput_format()` from `nimble/hotkeys/x11.py` to `nimble/hotkeys/base.py` (module level, not inside the class)
  - [x] Update `nimble/hotkeys/x11.py` to import from `nimble.hotkeys.base` instead of defining locally
  - [x] Verify `test_x11.py` import of `_to_pynput_format` from `x11` still works (re-export if needed) OR update the import in `test_x11.py` to come from `base`

- [x] Task 2: Implement `register()` in `nimble/hotkeys/windows.py` (AC: 1)
  - [x] Add `__init__` with `self._hotkeys: dict[str, Callable[[], None]] = {}` and `self._listener: GlobalHotKeys | None = None`
  - [x] `register()` stores pynput-formatted shortcut in `self._hotkeys` using `_to_pynput_format`

- [x] Task 3: Implement `start()` in `nimble/hotkeys/windows.py` (AC: 1, 2)
  - [x] Guard: if `_listener` is not None → raise `RuntimeError("Hotkey adapter is already started; call stop() before start().")`
  - [x] Check each registered key in `self._hotkeys` against `_WINDOWS_RESERVED_HOTKEYS`; log `WARNING` for each match (non-fatal — continue)
  - [x] Use lazy `_pynput_keyboard()` import pattern — identical to x11.py's pattern
  - [x] Build `GlobalHotKeys(self._hotkeys)` and start it

- [x] Task 4: Implement `stop()` in `nimble/hotkeys/windows.py` (AC: 3)
  - [x] Guard: if `_listener` is None → no-op (stop before start is safe)
  - [x] Call `_listener.stop()` then `_listener.join()` for clean thread exit
  - [x] Set `self._listener = None` after stop (idempotent stop, learned from 2.2 review)

- [x] Task 5: Write unit tests in `tests/unit/hotkeys/test_windows.py` (AC: 1, 2, 3)
  - [x] Test reserved hotkey logs a WARNING (`win+l`)
  - [x] Test non-reserved shortcut does NOT log a warning
  - [x] Test `start()` twice without `stop()` raises RuntimeError
  - [x] Test `stop()` before `start()` is a no-op
  - [x] Test `stop()` calls `listener.stop()` and `listener.join()`
  - [x] Test `stop()` twice after `start()` is a no-op (idempotent)
  - [x] All tests must mock pynput — never call real Win32 APIs in tests

- [x] Task 6: Verify all AC locally
  - [x] `mypy nimble/ tests/ worker/` — exits 0
  - [x] `pytest` — all tests pass
  - [x] `black --check nimble/ tests/` — exits 0
  - [x] `flake8 nimble/ tests/` — exits 0

### Review Findings

- [x] [Review][Decision] Duplicate shortcut registration policy — **Resolved (2026-04-17):** reject duplicate with `ValueError` in `WindowsHotkeyAdapter` and `X11HotkeyAdapter` for consistent behavior.

- [x] [Review][Patch] Strengthen Windows adapter unit test assertions [`tests/unit/hotkeys/test_windows.py`] — **Resolved (2026-04-17):** exact dict assertion for register; reserved-hotkey test requires both `reserved` and `<win>+l` in the log message; added coverage for `ctrl+alt+del` shorthand.

- [x] [Review][Patch] Ctrl+Alt+Del reserved warning may not trigger for common shorthand [`nimble/hotkeys/windows.py`] — **Resolved (2026-04-17):** added `<ctrl>+<alt>+del` to `_WINDOWS_RESERVED_HOTKEYS`.

- [x] [Review][Defer] `stop()` uses `join()` without timeout [`nimble/hotkeys/windows.py:59`] — deferred, pre-existing

## Dev Notes

### What Exists — Replace These Stubs

`nimble/hotkeys/windows.py` currently has stub bodies:
```python
class WindowsHotkeyAdapter(HotkeyAdapter):
    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        raise NotImplementedError("Implemented in Story 2.3")
    def start(self) -> None:
        raise NotImplementedError("Implemented in Story 2.3")
    def stop(self) -> None:
        raise NotImplementedError("Implemented in Story 2.3")
```
**Replace all stub bodies and add `__init__`. Do not recreate the file from scratch — preserve the class structure and imports.**

### Shared Format Conversion — Move to `base.py`

Both `x11.py` and `windows.py` need `_to_pynput_format`. The function is currently defined only in `x11.py`. Move it to `base.py` to avoid cross-module coupling:

**`nimble/hotkeys/base.py` — add below imports, before the class:**
```python
_MODIFIERS = {"ctrl", "shift", "alt", "cmd", "super", "win"}

def _to_pynput_format(shortcut: str) -> str:
    parts = shortcut.lower().split("+")
    return "+".join(f"<{p}>" if p in _MODIFIERS else p for p in parts)
```

Note `"win"` is added to `_MODIFIERS` here because Windows bindings use `win+l` style and `win` must become `<win>` in pynput format. The x11.py version did not need `win` since it's not used on Linux.

**`nimble/hotkeys/x11.py` — update to import:**
```python
from nimble.hotkeys.base import HotkeyAdapter, _to_pynput_format, _MODIFIERS
```
Remove the local `_MODIFIERS` and `_to_pynput_format` definitions from `x11.py`.

**`tests/unit/hotkeys/test_x11.py` — update import if needed:**
```python
from nimble.hotkeys.base import _to_pynput_format  # if test_x11 uses it directly
# OR keep: from nimble.hotkeys.x11 import _to_pynput_format  (re-export from x11.py if preferred)
```

### pynput API — `GlobalHotKeys` Works Identically on Windows

`pynput.keyboard.GlobalHotKeys` is the correct API for Windows too — it handles Win32 hotkey registration internally. Same interface as X11:

```python
from pynput import keyboard

listener = keyboard.GlobalHotKeys({
    "<ctrl>+<shift>+d": callback,
    "<win>+<shift>+d": callback2,
})
listener.start()   # non-blocking — background thread
# ...
listener.stop()
listener.join()    # wait for clean exit
```

`win` key maps to `<win>` in pynput format. Same modifier angle-bracket wrapping rule applies.

### Lazy pynput Import — Required for CI Safety

Use the exact same lazy import pattern as `x11.py` — pynput must not be imported at module level. `WindowsHotkeyAdapter` is only loaded when `sys.platform == "win32"` (see `__init__.py`), but tests run on Linux CI, so the module may be imported without a display/Win32 environment.

```python
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nimble.hotkeys.base import HotkeyAdapter, _to_pynput_format

if TYPE_CHECKING:
    from pynput.keyboard import GlobalHotKeys

logger = logging.getLogger(__name__)


def _pynput_keyboard() -> Any:
    """Lazy import so importing this module doesn't require Win32 APIs."""
    from pynput import keyboard
    return keyboard
```

### Windows Reserved Hotkeys Check

Define the reserved set at module level. Log a `WARNING` in `start()` for any registered binding that matches — non-fatal, daemon starts regardless:

```python
_WINDOWS_RESERVED_HOTKEYS = {
    "<win>+l",        # lock screen — intercepted by Windows before apps
    "<ctrl>+<alt>+<delete>",  # security screen — kernel-intercepted
    "<win>+d",        # show/hide desktop
    "<win>+e",        # file explorer
    "<win>+r",        # run dialog
    "<win>+s",        # search
    "<win>+tab",      # task view
}
```

Check in `start()` after the double-start guard:
```python
for pynput_key in self._hotkeys:
    if pynput_key in _WINDOWS_RESERVED_HOTKEYS:
        logger.warning(
            "Shortcut %r is a Windows-reserved hotkey and may not fire reliably (FR5)",
            pynput_key,
        )
```

The raw pynput-formatted key is used for the check (e.g. `"<win>+l"`) since `self._hotkeys` is already converted by `register()`.

### Required Final State of `nimble/hotkeys/windows.py`

```python
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nimble.hotkeys.base import HotkeyAdapter, _to_pynput_format

if TYPE_CHECKING:
    from pynput.keyboard import GlobalHotKeys

logger = logging.getLogger(__name__)

_WINDOWS_RESERVED_HOTKEYS = {
    "<win>+l",
    "<ctrl>+<alt>+<delete>",
    "<win>+d",
    "<win>+e",
    "<win>+r",
    "<win>+s",
    "<win>+tab",
}


def _pynput_keyboard() -> Any:
    """Lazy import so importing this module doesn't require Win32 APIs."""
    from pynput import keyboard
    return keyboard


class WindowsHotkeyAdapter(HotkeyAdapter):
    def __init__(self) -> None:
        self._hotkeys: dict[str, Callable[[], None]] = {}
        self._listener: GlobalHotKeys | None = None

    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        self._hotkeys[_to_pynput_format(shortcut)] = callback

    def start(self) -> None:
        if self._listener is not None:
            raise RuntimeError(
                "Hotkey adapter is already started; call stop() before start()."
            )
        for pynput_key in self._hotkeys:
            if pynput_key in _WINDOWS_RESERVED_HOTKEYS:
                logger.warning(
                    "Shortcut %r is a Windows-reserved hotkey and may not fire reliably (FR5)",
                    pynput_key,
                )
        keyboard = _pynput_keyboard()
        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener.join()
            self._listener = None
```

### Unit Test Approach — Mock pynput for CI Safety

CI runs Linux. `windows.py` may be imported during collection; `_pynput_keyboard()` must never be called at import time. Patch `nimble.hotkeys.windows._pynput_keyboard` in tests that call `start()`.

```python
# tests/unit/hotkeys/test_windows.py
import logging
from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest

from nimble.hotkeys.windows import WindowsHotkeyAdapter, _WINDOWS_RESERVED_HOTKEYS


def test_register_stores_pynput_format() -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.register("ctrl+shift+d", lambda: None)
    assert "<ctrl>+<shift>+d" in adapter._hotkeys


def test_start_warns_on_reserved_hotkey(caplog: pytest.LogCaptureFixture) -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.register("win+l", lambda: None)
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with caplog.at_level(logging.WARNING, logger="nimble.hotkeys.windows"):
        with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
            adapter.start()
    assert any("win" in r.message.lower() or "reserved" in r.message.lower()
               for r in caplog.records)
    mock_listener.start.assert_called_once()  # warning is non-fatal


def test_start_no_warning_for_normal_shortcut(caplog: pytest.LogCaptureFixture) -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.register("ctrl+shift+d", lambda: None)
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with caplog.at_level(logging.WARNING, logger="nimble.hotkeys.windows"):
        with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
            adapter.start()
    assert len(caplog.records) == 0


def test_start_twice_without_stop_raises() -> None:
    adapter = WindowsHotkeyAdapter()
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
        adapter.start()
        with pytest.raises(RuntimeError, match="already started"):
            adapter.start()


def test_stop_before_start_is_noop() -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.stop()  # must not raise


def test_stop_calls_listener_stop_and_join() -> None:
    adapter = WindowsHotkeyAdapter()
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
        adapter.start()
    adapter.stop()
    mock_listener.stop.assert_called_once()
    mock_listener.join.assert_called_once()


def test_stop_twice_after_start_is_noop() -> None:
    adapter = WindowsHotkeyAdapter()
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
        adapter.start()
    adapter.stop()
    adapter.stop()  # second stop must be a no-op
    mock_listener.stop.assert_called_once()
    mock_listener.join.assert_called_once()
```

### Architecture Guardrails

| Rule | Reason |
|---|---|
| Lazy `_pynput_keyboard()` import | CI runs on Linux; Win32 pynput backend must not load at import time |
| Never import `windows` directly in `daemon.py` | Boundary 4 — always via `get_adapter()` in `nimble/hotkeys/__init__.py` |
| `_to_pynput_format` lives in `base.py` | Shared between x11 and windows — no cross-sibling imports |
| `_listener = None` after stop | Idempotent stop pattern — learned from 2.2 code review |
| `if _listener is not None` guard in start | Double-start raises RuntimeError — learned from 2.2 code review |
| `collections.abc.Callable`, not `typing.Callable` | mypy --strict convention established in story 1.2 |
| Absolute imports only | `from nimble.hotkeys.base import HotkeyAdapter` — never relative |
| `"win"` in `_MODIFIERS` in base.py | `win+l` must produce `<win>+l` — not needed by X11 but required for Windows |

### Files This Story Modifies / Creates

```
nimble/hotkeys/base.py              ← ADD _MODIFIERS + _to_pynput_format (move from x11.py)
nimble/hotkeys/x11.py               ← UPDATE to import _to_pynput_format from base (remove local def)
nimble/hotkeys/windows.py           ← REPLACE stub bodies + add __init__
tests/unit/hotkeys/test_windows.py  ← NEW — 7 unit tests
tests/unit/hotkeys/test_x11.py      ← UPDATE import of _to_pynput_format if test imports from base
```

No other files are touched. `__init__.py`, `fake_adapter.py`, and all other test files are unchanged.

### Cross-Story Context

- **Story 2.1** established the lazy import pattern in `__init__.py` (`sys.platform == "win32"` check), the `HotkeyAdapter` ABC in `base.py`, and the stub in `windows.py` — do not change `__init__.py`
- **Story 2.2** implemented `x11.py` and was reviewed; key patterns refined during review: lazy pynput import via `_pynput_keyboard()`, double-start guard, idempotent `stop()` with `_listener = None`. Apply ALL these patterns identically to `windows.py`
- **Story 2.8** (`daemon.py`) calls `get_adapter()` which returns `WindowsHotkeyAdapter` on Windows; it calls `register()` per binding, then `start()` — the interface must be correct
- **Story 4.5/4.6** adds more platform edge case handling — this story only needs the WARNING log for reserved hotkeys; a system notification wrapper (if needed) comes later

### Project Structure Notes

- `nimble/hotkeys/base.py` is the correct home for `_to_pynput_format` — it is the shared contract layer for all adapter implementations
- `_WINDOWS_RESERVED_HOTKEYS` is local to `windows.py` — not shared with x11, not in base.py
- Test file at `tests/unit/hotkeys/test_windows.py` mirrors the source at `nimble/hotkeys/windows.py` (test location convention from architecture)

### References

- [Source: docs/bmad_output/planning-artifacts/architecture.md#Naming Patterns] — snake_case, absolute imports, mypy --strict
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Boundary 4] — platform adapter must not be imported directly in daemon.py
- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 2.3] — acceptance criteria
- [Source: docs/bmad_output/implementation-artifacts/2-2-x11-hotkey-adapter-linux.md#Review Findings] — lazy import, double-start guard, idempotent stop patterns
- [Source: docs/bmad_output/planning-artifacts/epics.md#Requirements] — FR5 (Windows reserved hotkey warning)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Moved `_MODIFIERS` and `_to_pynput_format` from `x11.py` to `base.py`; added `"win"` to `_MODIFIERS` for Windows key support.
- Updated `x11.py` to import from `base`; updated `test_x11.py` import accordingly.
- Implemented `WindowsHotkeyAdapter` with `__init__`, `register()`, `start()`, `stop()` using lazy pynput import, double-start guard, reserved hotkey WARNING, and idempotent stop pattern.
- 7 unit tests added in `test_windows.py`; all mock pynput for CI safety. All 19 tests pass, mypy/black/flake8 exit 0.

### File List

- nimble/hotkeys/base.py
- nimble/hotkeys/x11.py
- nimble/hotkeys/windows.py
- tests/unit/hotkeys/test_windows.py
- tests/unit/hotkeys/test_x11.py

## Change Log

- 2026-04-17: Implemented WindowsHotkeyAdapter; moved shared format utilities to base.py; added 7 unit tests (claude-sonnet-4-6)
