# Story 2.2: X11 Hotkey Adapter (Linux)

Status: done

## Story

As a Linux user running X11,
I want the daemon to capture my configured keyboard shortcuts from any application context,
So that my skills execute regardless of which window is focused.

## Acceptance Criteria

1. **Given** `nimble/hotkeys/x11.py` implements `HotkeyAdapter` using pynput
   **When** `register("ctrl+shift+d", callback)` is called and the user presses Ctrl+Shift+D
   **Then** `callback` is invoked within 200ms

2. **Given** `X11HotkeyAdapter.start()` is called on a Wayland-only session (no XWayland — `$WAYLAND_DISPLAY` is set but `$DISPLAY` is not)
   **Then** it raises `RuntimeError` with message: `"Nimble requires XWayland on Wayland sessions. Install XWayland or set DISPLAY to your X11 display."`
   **And** the error surfaces as an actionable startup message (FR4)

3. **Given** `start()` is called on a Wayland session where XWayland is available (`$WAYLAND_DISPLAY` set **and** `$DISPLAY` set)
   **Then** the adapter starts normally — Wayland + XWayland is a supported configuration

4. **Given** the adapter is running
   **When** `stop()` is called
   **Then** the pynput listener is cleanly terminated with no dangling threads

## Tasks / Subtasks

- [x] Task 1: Implement `register()` in `nimble/hotkeys/x11.py` (AC: 1)
  - [x] Parse Nimble shortcut format (`ctrl+shift+d`) to pynput `GlobalHotKeys` format (`<ctrl>+<shift>+d`)
  - [x] Store registered shortcuts in `self._hotkeys: dict[str, Callable[[], None]]`
  - [x] Do NOT start the listener yet — `start()` does that

- [x] Task 2: Implement `start()` in `nimble/hotkeys/x11.py` (AC: 1, 2, 3)
  - [x] Wayland detection: if `os.environ.get("WAYLAND_DISPLAY")` and not `os.environ.get("DISPLAY")` → raise `RuntimeError` with exact message from AC2
  - [x] Build `pynput.keyboard.GlobalHotKeys(self._hotkeys)` from registered shortcuts
  - [x] Store listener in `self._listener`
  - [x] Call `self._listener.start()` — runs pynput listener in background thread

- [x] Task 3: Implement `stop()` in `nimble/hotkeys/x11.py` (AC: 4)
  - [x] Call `self._listener.stop()` if listener exists
  - [x] Call `self._listener.join()` to wait for clean thread exit
  - [x] Guard: if `_listener` is None (stop called before start), no-op

- [x] Task 4: Write unit tests in `tests/unit/hotkeys/test_x11.py` (AC: 2, 3, 4)
  - [x] Test Wayland-only raises RuntimeError (mock `os.environ`)
  - [x] Test Wayland + XWayland starts normally (mock `os.environ`, mock pynput)
  - [x] Test `stop()` before `start()` is a no-op (no crash)
  - [x] Test `stop()` after `start()` calls `listener.stop()` and `listener.join()`
  - [x] Do NOT write a test that calls `start()` against real pynput on CI

- [x] Task 5: Verify all AC locally
  - [x] `mypy nimble/` — exits 0, no issues
  - [x] `pytest` — all tests pass
  - [x] `black --check nimble/ tests/` — exits 0
  - [x] `flake8 nimble/ tests/` — exits 0

## Dev Notes

### What Exists — Replace These Stubs

`nimble/hotkeys/x11.py` currently has stub bodies:
```python
def register(self, shortcut: str, callback: Callable[[], None]) -> None:
    raise NotImplementedError("Implemented in Story 2.2")
def start(self) -> None:
    raise NotImplementedError("Implemented in Story 2.2")
def stop(self) -> None:
    raise NotImplementedError("Implemented in Story 2.2")
```
**Replace all three bodies. Do not recreate the file from scratch — preserve the class structure and imports.**

### pynput API — `GlobalHotKeys` is the Right Tool

Use `pynput.keyboard.GlobalHotKeys`, NOT `pynput.keyboard.Listener`. `GlobalHotKeys` is purpose-built for registering named shortcuts and handles the key-combination tracking internally.

```python
from pynput import keyboard

listener = keyboard.GlobalHotKeys({
    "<ctrl>+<shift>+d": callback,
})
listener.start()   # non-blocking — starts background thread
# ...
listener.stop()
listener.join()    # waits for clean thread exit
```

### Shortcut Format Conversion

Nimble config uses `ctrl+shift+d`; pynput uses `<ctrl>+<shift>+d`. All modifier keys need angle brackets. Regular letter/number keys do not.

```python
_MODIFIERS = {"ctrl", "shift", "alt", "cmd", "super"}

def _to_pynput_format(shortcut: str) -> str:
    parts = shortcut.lower().split("+")
    return "+".join(
        f"<{p}>" if p in _MODIFIERS else p for p in parts
    )
```

### Wayland Detection Logic

Check at `start()` time, not at `register()` time:

```python
import os

def start(self) -> None:
    wayland = os.environ.get("WAYLAND_DISPLAY")
    x11 = os.environ.get("DISPLAY")
    if wayland and not x11:
        raise RuntimeError(
            "Nimble requires XWayland on Wayland sessions. "
            "Install XWayland or set DISPLAY to your X11 display."
        )
    self._listener = keyboard.GlobalHotKeys(self._hotkeys)
    self._listener.start()
```

Per architecture: Wayland detection belongs in `nimble/hotkeys/x11.py` — NOT in `daemon.py` (Architecture Boundary 4).

### Required Final State of `nimble/hotkeys/x11.py`

```python
import os
from collections.abc import Callable

from pynput import keyboard

from nimble.hotkeys.base import HotkeyAdapter

_MODIFIERS = {"ctrl", "shift", "alt", "cmd", "super"}


def _to_pynput_format(shortcut: str) -> str:
    parts = shortcut.lower().split("+")
    return "+".join(f"<{p}>" if p in _MODIFIERS else p for p in parts)


class X11HotkeyAdapter(HotkeyAdapter):
    def __init__(self) -> None:
        self._hotkeys: dict[str, Callable[[], None]] = {}
        self._listener: keyboard.GlobalHotKeys | None = None

    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        self._hotkeys[_to_pynput_format(shortcut)] = callback

    def start(self) -> None:
        wayland = os.environ.get("WAYLAND_DISPLAY")
        x11 = os.environ.get("DISPLAY")
        if wayland and not x11:
            raise RuntimeError(
                "Nimble requires XWayland on Wayland sessions. "
                "Install XWayland or set DISPLAY to your X11 display."
            )
        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener.join()
```

### Unit Test Approach — Mock pynput for CI Safety

CI runs headless Linux. `pynput` import is fine (it's a package-level import in x11.py), but calling `GlobalHotKeys.start()` on headless CI will fail. Use `unittest.mock.patch` to mock the listener in tests.

```python
# tests/unit/hotkeys/test_x11.py
import os
from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest

from nimble.hotkeys.x11 import X11HotkeyAdapter, _to_pynput_format


def test_shortcut_format_conversion() -> None:
    assert _to_pynput_format("ctrl+shift+d") == "<ctrl>+<shift>+d"
    assert _to_pynput_format("ctrl+a") == "<ctrl>+a"


def test_start_raises_on_wayland_without_xwayland() -> None:
    adapter = X11HotkeyAdapter()
    with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False):
        os.environ.pop("DISPLAY", None)
        with pytest.raises(RuntimeError, match="XWayland"):
            adapter.start()


def test_start_succeeds_with_xwayland_present() -> None:
    adapter = X11HotkeyAdapter()
    mock_listener = MagicMock()
    with patch("nimble.hotkeys.x11.keyboard.GlobalHotKeys", return_value=mock_listener):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}):
            adapter.start()
    mock_listener.start.assert_called_once()


def test_stop_before_start_is_noop() -> None:
    adapter = X11HotkeyAdapter()
    adapter.stop()  # must not raise


def test_stop_calls_listener_stop_and_join() -> None:
    adapter = X11HotkeyAdapter()
    mock_listener = MagicMock()
    with patch("nimble.hotkeys.x11.keyboard.GlobalHotKeys", return_value=mock_listener):
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
            os.environ.pop("WAYLAND_DISPLAY", None)
            adapter.start()
    adapter.stop()
    mock_listener.stop.assert_called_once()
    mock_listener.join.assert_called_once()
```

### Architecture Guardrails

| Rule | Reason |
|---|---|
| `pynput` import at module level in `x11.py` is OK | `get_adapter()` lazy-imports `X11HotkeyAdapter` — pynput is never loaded on Windows or in CI tests |
| Never import `x11` directly in `daemon.py` | Boundary 4 — always via `get_adapter()` |
| Do NOT change `nimble/hotkeys/__init__.py` | Lazy import pattern established in 2.1 protects CI |
| `collections.abc.Callable`, not `typing.Callable` | mypy --strict convention established in story 1.2 |
| `keyboard.GlobalHotKeys | None` type annotation | Python 3.10+ union syntax; mypy --strict requires it |
| Absolute imports only | `from nimble.hotkeys.base import HotkeyAdapter` — never relative |

### Files This Story Modifies / Creates

```
nimble/hotkeys/x11.py                   ← REPLACE stub bodies with real implementation
tests/unit/hotkeys/test_x11.py          ← NEW — Wayland + listener unit tests
```

No other files are touched. `nimble/hotkeys/__init__.py`, `base.py`, `windows.py`, and `fake_adapter.py` are all unchanged.

### Cross-Story Context

- **Story 2.1** established the lazy import pattern in `__init__.py` and the stub in `x11.py` — do not change these structures, only replace method bodies
- **Story 2.3** does the same for `windows.py` — do not pre-empt it
- **Story 2.8** (`daemon.py`) calls `get_adapter()` which returns `X11HotkeyAdapter` on Linux; it calls `register()` for each binding, then `start()` — the interface must be correct here
- **Story 4.6** adds more detailed Wayland error handling — this story only needs the RuntimeError; the system notification wrapper happens later

### mypy Note on `GlobalHotKeys | None`

mypy --strict requires the type annotation on `self._listener`. Use the pipe union syntax (Python 3.10+):
```python
self._listener: keyboard.GlobalHotKeys | None = None
```
`ignore_missing_imports = true` in `pyproject.toml` means missing pynput stubs won't cause errors, but the code must still be structurally type-correct.

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
None — implementation was straightforward following Dev Notes exactly.

### Completion Notes List
- Replaced all three stub bodies in `nimble/hotkeys/x11.py` with full implementation
- Added module-level `_MODIFIERS` set and `_to_pynput_format()` helper function
- `register()` stores pynput-formatted shortcuts in `self._hotkeys`
- `start()` performs Wayland detection and raises `RuntimeError` on Wayland-without-XWayland; builds and starts `GlobalHotKeys` listener
- `stop()` guards against None listener (no-op if called before start), then calls `stop()` + `join()` for clean thread exit
- 5 unit tests in `tests/unit/hotkeys/test_x11.py` — all pass, all CI-safe (pynput mocked)
- Full suite: 10/10 pass; mypy, black, flake8 all exit 0

### File List
- `nimble/hotkeys/x11.py` — replaced stub bodies with real implementation
- `tests/unit/hotkeys/test_x11.py` — new unit tests (5 tests)

### Review Findings

- [x] [Review][Patch] Headless CI / no DISPLAY — resolved: pynput is imported only via `_pynput_keyboard()` inside `start()` after Wayland checks; unit tests patch `_pynput_keyboard` so collection and CI run without `DISPLAY`. [`nimble/hotkeys/x11.py`, `tests/unit/hotkeys/test_x11.py`]

- [x] [Review][Patch] Double `start()` without `stop()` — resolved: `start()` raises `RuntimeError` if `_listener` is already set. [`nimble/hotkeys/x11.py`]

- [x] [Review][Patch] `stop()` clears listener — resolved: `stop()` sets `_listener = None` after `stop()`/`join()`; added `test_stop_twice_after_start_is_noop`. [`nimble/hotkeys/x11.py`, `tests/unit/hotkeys/test_x11.py`]

## Change Log

- 2026-04-17: Story created by bmad-create-story workflow
- 2026-04-17: Story implemented by dev agent (claude-sonnet-4-6)
- 2026-04-17: Code review (CR) — findings appended above
- 2026-04-17: Code review patches applied (lazy pynput import, double-start guard, idempotent `stop()`, tests)
