# Story 4.6: Platform Edge Case Handling (Wayland + Windows Reserved Hotkeys + macOS Accessibility)

Status: done

## Story

As a user on an unsupported or restricted platform configuration,
I want actionable error messages at daemon startup rather than silent failures,
so that I know exactly what to fix and how.

## Acceptance Criteria

1. **Given** `nimble start` is run on Linux with `$WAYLAND_DISPLAY` set and no XWayland available
   **When** the X11 adapter initialises
   **Then** the daemon exits with a notification and stdout message: `"Nimble requires XWayland on Wayland sessions. Install XWayland or set DISPLAY to your X11 display."` (FR4)

2. **Given** `nimble start` is run on Linux with `$WAYLAND_DISPLAY` set but XWayland is available (`$DISPLAY` is set)
   **When** the X11 adapter initialises
   **Then** the daemon starts normally — Wayland + XWayland is a supported configuration

3. **Given** a binding in `config.yaml` matches a known Windows-reserved hotkey (e.g. `win+l`)
   **When** `nimble start` runs on Windows
   **Then** a `WARNING` log entry and startup notification identifies the reserved binding by name (FR5)
   **And** the daemon starts — the warning is non-fatal

4. **Given** `build_context()` is called on macOS and Accessibility access has not been granted
   **When** clipboard simulation is used for `selection`
   **Then** the daemon logs a one-time INFO message: `"macOS: Accessibility not granted — selection uses clipboard simulation. Grant access in System Settings → Privacy & Security → Accessibility for more reliable capture."`
   **And** the daemon continues normally — this is non-fatal (NFR13)

## Tasks / Subtasks

- [x] Task 1: Add `reserved_hotkeys_found` property to `WindowsHotkeyAdapter` (AC: 3)
  - [x] Add `self._reserved_found: list[str] = []` to `WindowsHotkeyAdapter.__init__`
  - [x] In `start()`, when `pynput_key in _WINDOWS_RESERVED_HOTKEYS`, append to `self._reserved_found` (alongside existing `logger.warning` call — do NOT remove it)
  - [x] Add `@property def reserved_hotkeys_found(self) -> list[str]: return list(self._reserved_found)` — return a copy so callers can't mutate internal state

- [x] Task 2: Catch adapter `RuntimeError` in daemon and send notification (AC: 1)
  - [x] In `nimble/daemon.py::run()`, wrap `adapter.start()` in `try/except RuntimeError as exc:`
  - [x] In the except block: call `notifier.send("Nimble — startup error", str(exc))`
  - [x] In the except block: call `print(str(exc))` for the required stdout message
  - [x] In the except block: call `sys.exit(1)`
  - [x] AC2 (Wayland + XWayland) is already passing — the X11 adapter already handles it

- [x] Task 3: Send daemon notification for Windows reserved hotkeys (AC: 3)
  - [x] In `nimble/daemon.py::run()`, after `adapter.start()` (inside the `try` block or after):
  - [x] Check `if hasattr(adapter, "reserved_hotkeys_found"):` — duck-typed, no new imports needed
  - [x] For each key in `adapter.reserved_hotkeys_found`, call `notifier.send("Nimble — startup warning", f"Binding {key!r} is a Windows-reserved hotkey and may not fire reliably (FR5)")`

- [x] Task 4: Add one-time macOS INFO log in `_get_selection()` (AC: 4)
  - [x] Add `import logging` to `nimble/context/assembler.py`
  - [x] Add `logger = logging.getLogger(__name__)` module-level (below imports)
  - [x] Add `_macos_accessibility_warned = False` module-level flag below logger
  - [x] In `_get_selection()` macOS branch (`if is_mac():`), before the try block, add:
    ```python
    global _macos_accessibility_warned
    if not _macos_accessibility_warned:
        logger.info(
            "macOS: Accessibility not granted — selection uses clipboard simulation. "
            "Grant access in System Settings → Privacy & Security → Accessibility "
            "for more reliable capture."
        )
        _macos_accessibility_warned = True
    ```

- [x] Task 5: Write tests for `reserved_hotkeys_found` property (AC: 3)
  - [x] `tests/unit/hotkeys/test_windows.py` — add:
    - [x] `test_start_populates_reserved_hotkeys_found()` — register `"win+l"`, start adapter, assert `adapter.reserved_hotkeys_found == ["<win>+l"]`
    - [x] `test_start_reserved_hotkeys_found_empty_for_normal_shortcut()` — register `"ctrl+shift+d"`, start adapter, assert `adapter.reserved_hotkeys_found == []`

- [x] Task 6: Write tests for macOS one-time INFO log (AC: 4)
  - [x] `tests/unit/context/test_assembler.py` — add:
    - [x] `test_selection_mac_logs_accessibility_info_on_first_call()` — reset flag to False, call `_get_selection()` on mocked macOS, assert INFO message in caplog
    - [x] `test_selection_mac_logs_accessibility_info_only_once()` — reset flag to False, call `_get_selection()` twice on mocked macOS, assert INFO message appears exactly once in caplog

- [x] Task 7: Write tests for daemon startup edge cases (AC: 1, 3)
  - [x] `tests/unit/test_daemon.py` — add:
    - [x] `test_run_exits_on_adapter_start_runtime_error()` — mock `get_adapter()` to return an adapter whose `start()` raises `RuntimeError("test error")`, mock `load_config`, `validate_skill_paths`, `FakeNotifier`, assert `sys.exit(1)` is raised
    - [x] `test_run_sends_notification_on_adapter_start_runtime_error()` — same setup, assert `notifier.send()` called with message containing `"test error"`
    - [x] `test_run_sends_notification_for_each_reserved_hotkey()` — mock adapter with `reserved_hotkeys_found = ["<win>+l", "<win>+d"]`, assert `notifier.send()` called twice with "startup warning" in title

- [x] Task 8: Verify quality gates
  - [x] `.venv/bin/pytest tests/unit/ -q` — 210 pass (baseline 203 + 7 new tests)
  - [x] `.venv/bin/mypy nimble/ tests/ worker/` — exits 0 (3 pre-existing errors in test_platform.py unchanged)
  - [x] `.venv/bin/black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Patch] `WindowsHotkeyAdapter.start()` does not reset tracked reserved keys between starts [`nimble/hotkeys/windows.py`]  
- [x] [Review][Patch] Missing regression test for repeated `start()` behavior of `reserved_hotkeys_found` (stale/duplicate entries risk) [`tests/unit/hotkeys/test_windows.py`]

## Dev Notes

### What Already EXISTS — Do NOT Reinvent

**`nimble/hotkeys/x11.py::X11HotkeyAdapter.start()` (lines 31–38)** — ALREADY raises `RuntimeError` with the exact Wayland error message when `$WAYLAND_DISPLAY` is set and `$DISPLAY` is not. Do NOT modify this logic. AC1 detection is done; the only gap is daemon.py not catching the exception.

**`nimble/hotkeys/windows.py::WindowsHotkeyAdapter.start()` (lines 49–55)** — ALREADY logs `WARNING` for reserved hotkeys via `logger.warning(...)`. Keep this log; the task is only to ALSO store the found keys and expose them for the daemon to send a notification. Do NOT remove the existing logger.warning call.

**`_WINDOWS_RESERVED_HOTKEYS` set in `nimble/hotkeys/windows.py` (lines 14–23)** — already contains the complete set. Do NOT modify it.

**`tests/unit/hotkeys/test_x11.py`** — AC2 (Wayland+XWayland starts normally) already tested at `test_start_succeeds_with_xwayland_present`. AC1 (Wayland without XWayland raises RuntimeError) already tested at `test_start_raises_on_wayland_without_xwayland`. Do NOT duplicate these tests.

**`tests/unit/hotkeys/test_windows.py`** — WARNING log for reserved hotkeys already tested at `test_start_warns_on_reserved_hotkey` and `test_start_warns_on_ctrl_alt_del_shorthand`. Do NOT duplicate these tests. New tests only cover the `reserved_hotkeys_found` property behaviour.

**`nimble/platform.py::is_mac()`** — already exists. Import it in assembler.py if not already imported (it IS already imported: `from nimble.platform import is_linux, is_mac, is_windows`).

**`nimble/context/assembler.py`** — macOS `_get_selection()` (lines 70–112) already implements clipboard simulation correctly. The only gap is the missing one-time INFO log. Do NOT change the simulation logic.

**Baseline test count: 203 tests pass** (including `test_daemon.py` and `test_watcher.py` — both collect and pass, contrary to older story notes).

### `daemon.py` adapter.start() Error Handling

Current `daemon.py::run()` (line 60):
```python
adapter.start()
write_pid(os.getpid())
```

Replace with:
```python
try:
    adapter.start()
except RuntimeError as exc:
    notifier.send("Nimble — startup error", str(exc))
    print(str(exc))
    sys.exit(1)
write_pid(os.getpid())
started = True
```

Then immediately after the try/except, add the Windows reserved hotkey notification:
```python
if hasattr(adapter, "reserved_hotkeys_found"):
    for key in adapter.reserved_hotkeys_found:
        notifier.send(
            "Nimble — startup warning",
            f"Binding {key!r} is a Windows-reserved hotkey and may not fire reliably (FR5)",
        )
```

**Why `hasattr` instead of `isinstance(adapter, WindowsHotkeyAdapter)`:** avoids importing `WindowsHotkeyAdapter` in daemon.py (which would work fine but adds a coupling). Duck-typing keeps daemon.py platform-agnostic. If a future adapter also exposes `reserved_hotkeys_found`, the daemon will handle it automatically.

**Note:** `sys` is already imported in `daemon.py` (line 7). No new imports needed beyond what's already there.

### `windows.py` `reserved_hotkeys_found` Property

Add to `__init__`:
```python
self._reserved_found: list[str] = []
```

In `start()`, modify the existing WARNING block (keep logger.warning, just also append):
```python
for pynput_key in self._hotkeys:
    if pynput_key in _WINDOWS_RESERVED_HOTKEYS:
        logger.warning(
            "Shortcut %r is a Windows-reserved hotkey and may not"
            " fire reliably (FR5)",
            pynput_key,
        )
        self._reserved_found.append(pynput_key)
```

Add property after `stop()`:
```python
@property
def reserved_hotkeys_found(self) -> list[str]:
    return list(self._reserved_found)
```

### `assembler.py` macOS One-Time INFO Log

Add at top of file after `from typing import Any`:
```python
import logging

logger = logging.getLogger(__name__)

_macos_accessibility_warned = False
```

In `_get_selection()`, the macOS branch currently starts at line 70 with `if is_mac():`. Insert the one-time log at the very top of the macOS branch:
```python
if is_mac():
    global _macos_accessibility_warned
    if not _macos_accessibility_warned:
        logger.info(
            "macOS: Accessibility not granted — selection uses clipboard simulation. "
            "Grant access in System Settings → Privacy & Security → Accessibility "
            "for more reliable capture."
        )
        _macos_accessibility_warned = True
    try:
        # ... rest of existing macOS implementation unchanged ...
```

### Test Patterns for New `reserved_hotkeys_found` Tests

Follow the exact pattern of existing tests in `test_windows.py` — mock `_pynput_keyboard` and call `adapter.start()`:

```python
def test_start_populates_reserved_hotkeys_found() -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.register("win+l", lambda: None)
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
        adapter.start()
    assert adapter.reserved_hotkeys_found == ["<win>+l"]

def test_start_reserved_hotkeys_found_empty_for_normal_shortcut() -> None:
    adapter = WindowsHotkeyAdapter()
    adapter.register("ctrl+shift+d", lambda: None)
    mock_listener = MagicMock()
    mock_keyboard = MagicMock()
    mock_keyboard.GlobalHotKeys = MagicMock(return_value=mock_listener)
    with patch("nimble.hotkeys.windows._pynput_keyboard", return_value=mock_keyboard):
        adapter.start()
    assert adapter.reserved_hotkeys_found == []
```

### Test Patterns for macOS One-Time INFO Log Tests

**Critical:** Reset the module-level flag before each test. Use `assembler._macos_accessibility_warned = False` directly (it's a module attribute, not a class attribute):

```python
import nimble.context.assembler as assembler

def test_selection_mac_logs_accessibility_info_on_first_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assembler._macos_accessibility_warned = False  # reset flag
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)
    run_responses = [_mock_run(0, ""), _mock_run(0, ""), _mock_run(0, "")]
    with (
        patch("nimble.context.assembler.is_mac", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_windows", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=run_responses),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict("sys.modules", {
            "pynput": MagicMock(keyboard=mock_pynput_keyboard),
            "pynput.keyboard": mock_pynput_keyboard,
        }),
        caplog.at_level(logging.INFO, logger="nimble.context.assembler"),
    ):
        assembler._get_selection()
    assert any("Accessibility not granted" in r.message for r in caplog.records)

def test_selection_mac_logs_accessibility_info_only_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assembler._macos_accessibility_warned = False  # reset flag
    # ... same mocking setup ...
    with caplog.at_level(logging.INFO, logger="nimble.context.assembler"):
        assembler._get_selection()
        assembler._get_selection()
    assert sum(1 for r in caplog.records if "Accessibility not granted" in r.message) == 1
```

### Test Patterns for Daemon Startup Tests

`tests/unit/test_daemon.py` already imports `FakeNotifier` from `tests.conftest`. Follow the exact style of existing tests in that file:

```python
def test_run_exits_on_adapter_start_runtime_error(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()
    mock_adapter = MagicMock()
    mock_adapter.start.side_effect = RuntimeError("XWayland not found")
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter", return_value=mock_adapter),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        pytest.raises(SystemExit) as exc_info,
    ):
        from nimble.daemon import run
        run(tmp_path)
    assert exc_info.value.code == 1

def test_run_sends_notification_on_adapter_start_runtime_error(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()
    mock_adapter = MagicMock()
    mock_adapter.start.side_effect = RuntimeError("XWayland not found")
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter", return_value=mock_adapter),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        pytest.raises(SystemExit),
    ):
        run(tmp_path)
    assert len(fake_notifier.sent) == 1
    _, body = fake_notifier.sent[0]
    assert "XWayland not found" in body
```

For the Windows notification test, mock an adapter that has `reserved_hotkeys_found`:
```python
def test_run_sends_notification_for_each_reserved_hotkey(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()
    mock_adapter = MagicMock(spec=["start", "stop", "register", "reserved_hotkeys_found"])
    mock_adapter.reserved_hotkeys_found = ["<win>+l", "<win>+d"]
    with (
        patch("nimble.daemon.load_config", return_value=MagicMock(skills=[], ai=None)),
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.get_adapter", return_value=mock_adapter),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
        patch("nimble.daemon.configure_logging"),
        patch("nimble.daemon.SkillRunner"),
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.ConfigWatcher"),
        patch("nimble.daemon.threading.Event") as mock_event,
    ):
        mock_event.return_value.wait.side_effect = KeyboardInterrupt
        with pytest.raises((KeyboardInterrupt, SystemExit)):
            run(tmp_path)
    warning_sends = [s for s in fake_notifier.sent if "startup warning" in s[0]]
    assert len(warning_sends) == 2
```

**Note on test_daemon.py imports:** The file imports `pytest` implicitly through `pytest.raises` usage. Check existing imports in the file to confirm `pytest` is imported before adding tests.

### Architecture Compliance

- Wayland detection stays in `nimble/hotkeys/x11.py` (already there). Daemon only catches the `RuntimeError`.
- Windows reserved hotkey DETECTION stays in `nimble/hotkeys/windows.py` (already there). Daemon reads the result and sends notification.
- macOS one-time INFO log belongs in `nimble/context/assembler.py::_get_selection()` — not in daemon.py.
- Do NOT add platform detection logic to `daemon.py::run()` itself — the adapters own that.
- `mypy --strict` enforced — `reserved_hotkeys_found` return type is `list[str]`, `_reserved_found` is `list[str]`, new logger is `logging.Logger`, flag is `bool`.

### Out of Scope for This Story

- macOS `HotkeyAdapter` implementation (`hotkeys/macos.py`) — deferred; `get_adapter()` still raises `RuntimeError("Unsupported platform: darwin")` for macOS
- Detecting whether macOS Accessibility access is actually granted programmatically — the one-time INFO log fires unconditionally on macOS (v1 always uses clipboard simulation regardless)
- `nimble start` `input group` check on Linux — mentioned in PRD but not in story AC
- Expanding `_WINDOWS_RESERVED_HOTKEYS` beyond the current set — out of scope

### File List to Touch

- `nimble/hotkeys/windows.py` — add `_reserved_found` field, append in `start()`, add `reserved_hotkeys_found` property
- `nimble/daemon.py` — wrap `adapter.start()` in try/except RuntimeError; add reserved hotkey notification block
- `nimble/context/assembler.py` — add `import logging`, `logger`, `_macos_accessibility_warned` flag, one-time INFO log in `_get_selection()`
- `tests/unit/hotkeys/test_windows.py` — add 2 tests for `reserved_hotkeys_found`
- `tests/unit/context/test_assembler.py` — add `import logging` (top), reset flag in new tests, add 2 new macOS INFO log tests
- `tests/unit/test_daemon.py` — add 3 tests for Wayland exit and Windows notification

### Baseline (Before This Story)

```
Tests: 203 passed (0 collection errors — test_daemon.py and test_watcher.py both collect and pass)
mypy: 3 pre-existing errors in tests/unit/platform/test_platform.py — unchanged; 0 errors in nimble/
black: clean
flake8: clean (nimble/ tests/ worker/ only)
```

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 4.6] — acceptance criteria, FR4, FR5, NFR13
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Platform Edge Case Handling] — Wayland in x11.py, Windows detection in windows.py, error message strings
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Error Handling Patterns] — notification pipeline pattern, never silent failures
- [Source: nimble/hotkeys/x11.py:31-38] — Wayland RuntimeError already implemented
- [Source: nimble/hotkeys/windows.py:14-55] — reserved hotkey set and WARNING log already implemented
- [Source: nimble/context/assembler.py:70-112] — macOS `_get_selection()` clipboard simulation already implemented
- [Source: nimble/daemon.py] — adapter.start() call location, notifier and sys available
- [Source: tests/unit/hotkeys/test_x11.py] — existing Wayland tests (do NOT duplicate)
- [Source: tests/unit/hotkeys/test_windows.py] — existing reserved hotkey WARNING tests (do NOT duplicate)
- [Source: tests/unit/context/test_assembler.py] — existing macOS selection test patterns to follow
- [Source: tests/unit/test_daemon.py] — existing daemon test patterns with FakeNotifier to follow
- [Source: tests/conftest.py] — FakeNotifier fixture

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `_reserved_found: list[str]` field and `reserved_hotkeys_found` property to `WindowsHotkeyAdapter`. The property returns a copy to prevent mutation of internal state.
- Wrapped `adapter.start()` in `try/except RuntimeError` in `daemon.py::run()`. On error: sends notification, prints to stdout, exits with code 1.
- Added duck-typed `hasattr(adapter, "reserved_hotkeys_found")` check after `adapter.start()` — sends one startup warning notification per reserved hotkey found. No new imports needed.
- Added `import logging`, module-level `logger`, and `_macos_accessibility_warned` flag to `assembler.py`. One-time INFO log fires in macOS `_get_selection()` branch before the try block.
- 7 new tests added (203 → 210). All pass. mypy clean on nimble/. black and flake8 clean.

### File List

- nimble/hotkeys/windows.py
- nimble/daemon.py
- nimble/context/assembler.py
- tests/unit/hotkeys/test_windows.py
- tests/unit/context/test_assembler.py
- tests/unit/test_daemon.py

## Change Log

- 2026-05-01: Implemented Story 4.6 — platform edge case handling. Added `reserved_hotkeys_found` property to `WindowsHotkeyAdapter`; daemon now catches `RuntimeError` from `adapter.start()` and exits with notification+stdout; daemon sends startup warning notifications for Windows reserved hotkeys; assembler logs one-time macOS accessibility INFO message. 7 new tests (203 → 210 passing).
