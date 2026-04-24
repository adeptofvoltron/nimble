# Story 2.10: Cross-Platform Context Capture (Windows + macOS)

Status: done

## Story

As a skill author on Windows or macOS,
I want `build_context()` to return real values for `clipboard`, `active_app`, and `selection` — not empty strings,
So that my skills work the same way regardless of which OS I'm running.

## Acceptance Criteria

1. **Given** `build_context()` is called on Windows
   **When** text is in the clipboard
   **Then** `clipboard` returns that text via PowerShell `Get-Clipboard`

2. **Given** `build_context()` is called on Windows
   **When** an application window is focused
   **Then** `active_app` returns the window title via `ctypes` (no extra deps)

3. **Given** `build_context()` is called on Windows
   **When** text is selected in any application
   **Then** `selection` returns that text via clipboard simulation (save → Ctrl+C → read → restore); `""` on any failure

4. **Given** `build_context()` is called on macOS
   **When** text is in the clipboard
   **Then** `clipboard` returns that text via `pbpaste`

5. **Given** `build_context()` is called on macOS
   **When** an application is in the foreground
   **Then** `active_app` returns the app name via `osascript`

6. **Given** `build_context()` is called on macOS
   **When** text is selected in any application
   **Then** `selection` returns that text via clipboard simulation (save → Cmd+C → read → restore); `""` on any failure

7. **Given** clipboard simulation is used for `selection`
   **When** the simulation completes (or fails at any step)
   **Then** the original clipboard content is restored — the user's clipboard is not permanently modified

8. **Given** all OS calls use `timeout=0.1`
   **When** any subprocess hangs
   **Then** it is killed and the field returns `""` — within the 200ms hotkey budget (NFR1)

## Tasks / Subtasks

- [x] Task 1: Update `nimble/context/assembler.py` — extend `_get_clipboard()` (AC: 1, 4, 8)
  - [x] Add `is_mac` and `is_windows` to the import from `nimble.platform` (existing import already has `is_linux`)
  - [x] Restructure `_get_clipboard()` with `if is_linux(): ...`, `if is_windows(): ...`, `if is_mac(): ...`, `return ""`
  - [x] Windows path: `subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"], capture_output=True, text=True, timeout=0.1)` — return `result.stdout` if returncode 0 else `""`
  - [x] macOS path: `subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=0.1)` — return `result.stdout` if returncode 0 else `""`
  - [x] Wrap each platform block in `try: ... except Exception: return ""`
  - [x] Keep existing Linux `xclip` path unchanged

- [x] Task 2: Update `nimble/context/assembler.py` — extend `_get_active_app()` (AC: 2, 5, 8)
  - [x] Restructure `_get_active_app()` with `if is_linux(): ...`, `if is_windows(): ...`, `if is_mac(): ...`, `return ""`
  - [x] Windows path: use `ctypes` (stdlib) to call `GetForegroundWindow` + `GetWindowTextW` — see Dev Notes for exact pattern and required `# type: ignore[attr-defined]` comments
  - [x] macOS path: `subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true'], capture_output=True, text=True, timeout=0.1)` — return `result.stdout.strip()` if returncode 0 else `""`
  - [x] Wrap each platform block in `try: ... except Exception: return ""`
  - [x] Keep existing Linux `xdotool` path unchanged

- [x] Task 3: Update `nimble/context/assembler.py` — extend `_get_selection()` with clipboard simulation (AC: 3, 6, 7, 8)
  - [x] Add `import time` to top-level imports in `assembler.py`
  - [x] Restructure `_get_selection()` with `if is_linux(): ...`, `if is_windows(): ...`, `if is_mac(): ...`, `return ""`
  - [x] Windows path: implement clipboard simulation helper — see Dev Notes for step-by-step and exact pynput import pattern
  - [x] macOS path: implement clipboard simulation helper — see Dev Notes for step-by-step and exact pynput import pattern
  - [x] Clipboard simulation must always attempt to restore the original clipboard content before returning, even if the selection read fails
  - [x] Wrap entire clipboard simulation sequence in `try: ... except Exception: return ""` — any failure returns `""` immediately without restoration attempt (restoration is best-effort)
  - [x] Keep existing Linux `xclip -selection primary` path unchanged

- [x] Task 4: Update `tests/unit/context/test_assembler.py` — Windows path tests (AC: 1, 2, 3, 7)
  - [x] Add `test_clipboard_windows_returns_powershell_output()`: patch `is_windows`→True, `is_linux`→False, `subprocess.run`→returncode 0 with stdout `"win text"`; assert `_get_clipboard() == "win text"`
  - [x] Add `test_clipboard_windows_empty_on_failure()`: patch `is_windows`→True, `is_linux`→False, `subprocess.run`→returncode 1; assert `_get_clipboard() == ""`
  - [x] Add `test_active_app_windows_returns_window_title()`: patch `is_windows`→True, `is_linux`→False; mock `ctypes` module in `sys.modules` with fake windll that returns a buffer with value `"My App"`; assert `_get_active_app() == "My App"` — see Dev Notes for ctypes mock pattern
  - [x] Add `test_active_app_windows_empty_on_ctypes_failure()`: patch `is_windows`→True, `is_linux`→False; mock ctypes to raise `AttributeError`; assert `_get_active_app() == ""`
  - [x] Add `test_selection_windows_happy_path()`: patch `is_windows`→True, `is_linux`→False; mock `subprocess.run` to return `"saved"` on first call and `"selected text"` on second; mock pynput Controller in sys.modules; mock `time.sleep`; assert `_get_selection() == "selected text"`
  - [x] Add `test_selection_windows_restores_clipboard()`: same setup; record calls to `subprocess.run`; verify the restore call (`$input | Set-Clipboard`) is made with `input="saved"`
  - [x] Add `test_selection_windows_empty_on_failure()`: patch `is_windows`→True, `is_linux`→False; mock `subprocess.run` to raise `FileNotFoundError`; assert `_get_selection() == ""`

- [x] Task 5: Update `tests/unit/context/test_assembler.py` — macOS path tests (AC: 4, 5, 6, 7)
  - [x] Add `test_clipboard_mac_returns_pbpaste_output()`: patch `is_mac`→True, `is_linux`→False, `is_windows`→False; mock `subprocess.run`→returncode 0, stdout `"mac text"`; assert `_get_clipboard() == "mac text"`
  - [x] Add `test_clipboard_mac_empty_on_failure()`: patch `is_mac`→True, `is_linux`→False, `is_windows`→False; mock `subprocess.run`→returncode 1; assert `_get_clipboard() == ""`
  - [x] Add `test_active_app_mac_returns_osascript_output()`: patch `is_mac`→True, `is_linux`→False, `is_windows`→False; mock `subprocess.run`→returncode 0, stdout `"Safari\n"`; assert `_get_active_app() == "Safari"`
  - [x] Add `test_active_app_mac_empty_on_failure()`: same setup with returncode 1; assert `_get_active_app() == ""`
  - [x] Add `test_selection_mac_happy_path()`: patch `is_mac`→True, `is_linux`→False, `is_windows`→False; mock `subprocess.run` sequence (pbpaste→"saved", pbpaste→"selected", pbcopy restore→ok); mock pynput Controller; mock `time.sleep`; assert `_get_selection() == "selected"`
  - [x] Add `test_selection_mac_restores_clipboard()`: verify restore call uses `pbcopy` with `input="saved"`
  - [x] Add `test_selection_mac_empty_on_failure()`: mock `subprocess.run` to raise `FileNotFoundError`; assert `_get_selection() == ""`

- [x] Task 6: Verify quality gates (AC: all)
  - [x] `mypy nimble/ tests/ worker/` — exits 0; the `# type: ignore[attr-defined]` comments on ctypes.windll lines suppress expected Windows-only attr errors
  - [x] `pytest` — all existing 104 tests pass plus new context tests
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### Role in the Daemon Architecture

`assembler.py` is called by `nimble/skills/runner.py` immediately when a hotkey fires, BEFORE writing the JSON IPC payload to the worker's stdin. The IPC contract for `context` fields is unchanged — this story only fills in previously-empty values on Windows and macOS.

```
pynput hotkey event (X11 / Windows / macOS)
  → runner.py calls build_context()   ← THIS STORY: now returns real values on all platforms
  → runner.py builds: {"invocation_id": ..., "context": <result>}
  → writes to worker stdin
  → worker/context.py reconstructs Context object
```

The `dict[str, Any]` shape returned by `build_context()` is a hard contract with `worker/context.py`. Do NOT add, rename, or remove keys — only fill values that were previously `""`.

### Import Changes to assembler.py

```python
# BEFORE (current)
from nimble.platform import is_linux

# AFTER (this story)
import time
from nimble.platform import is_linux, is_mac, is_windows
```

`time` is stdlib — no new dependencies. `pynput` is already in `pyproject.toml` dependencies — import it lazily inside the clipboard simulation blocks (same pattern as `_get_mouse_position` uses `from pynput import mouse`).

### _get_clipboard() — Implementation

```python
def _get_clipboard() -> str:
    if is_linux():
        try:
            result = subprocess.run(
                ["xclip", "-o", "-selection", "clipboard"],
                capture_output=True, text=True, timeout=0.1,
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    if is_windows():
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=0.1,
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    if is_mac():
        try:
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True, text=True, timeout=0.1,
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""
    return ""
```

### _get_active_app() — Windows via ctypes

ctypes is stdlib; no extra dependencies. `ctypes.windll` is Windows-only and unknown to mypy when running on Linux — suppress with `# type: ignore[attr-defined]`.

```python
if is_windows():
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()  # type: ignore[attr-defined]
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)  # type: ignore[attr-defined]
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)  # type: ignore[attr-defined]
        return buf.value
    except Exception:
        return ""
```

`buf.value` is `str` — no cast needed. The `except Exception` handles all ctypes failures including `OSError` from missing windll attributes on non-Windows systems.

### _get_active_app() — macOS via osascript

```python
if is_mac():
    try:
        result = subprocess.run(
            [
                "osascript", "-e",
                'tell application "System Events" to get name of first application process whose frontmost is true',
            ],
            capture_output=True, text=True, timeout=0.1,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""
```

### _get_selection() — Clipboard Simulation (Windows and macOS)

Clipboard simulation replaces the primary-selection approach (X11-only). The sequence for BOTH platforms is: save → keypress → wait → read → restore.

**Windows implementation:**

```python
if is_windows():
    try:
        from pynput.keyboard import Controller, Key
        # 1. Save current clipboard
        save_result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=0.1,
        )
        saved = save_result.stdout if save_result.returncode == 0 else ""
        # 2. Simulate Ctrl+C
        kbd = Controller()
        kbd.press(Key.ctrl)
        kbd.press("c")
        kbd.release("c")
        kbd.release(Key.ctrl)
        # 3. Wait for clipboard update
        time.sleep(0.05)
        # 4. Read selection
        read_result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=0.1,
        )
        selection = read_result.stdout if read_result.returncode == 0 else ""
        # 5. Restore original clipboard (best-effort)
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
            input=saved, text=True, timeout=0.1, capture_output=True,
        )
        return selection
    except Exception:
        return ""
```

**macOS implementation:**

```python
if is_mac():
    try:
        from pynput.keyboard import Controller, Key
        # 1. Save current clipboard
        save_result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=0.1,
        )
        saved = save_result.stdout if save_result.returncode == 0 else ""
        # 2. Simulate Cmd+C
        kbd = Controller()
        kbd.press(Key.cmd)
        kbd.press("c")
        kbd.release("c")
        kbd.release(Key.cmd)
        # 3. Wait for clipboard update
        time.sleep(0.05)
        # 4. Read selection
        read_result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=0.1,
        )
        selection = read_result.stdout if read_result.returncode == 0 else ""
        # 5. Restore original clipboard (best-effort)
        subprocess.run(
            ["pbcopy"], input=saved, text=True, timeout=0.1, capture_output=True,
        )
        return selection
    except Exception:
        return ""
```

**Key points:**
- `time.sleep(0.05)` is 50ms — this plus two subprocess calls stays within the 200ms budget (NFR1) in the common case. Do NOT increase this value.
- The restore subprocess call (step 5) is intentionally outside the `except` block but inside the outer `try` — if it fails, the exception is caught and `""` is returned. The "best-effort" comment reflects this: if we can't restore, we don't crash, but the user's clipboard may be left with the selection content rather than the original.
- `$input | Set-Clipboard` (Windows) reads stdin — this avoids shell injection for arbitrary clipboard content. Do NOT embed the `saved` string into the PowerShell command string.
- `pbcopy` (macOS) reads from stdin — same reason.
- The entire sequence is wrapped in `try: ... except Exception: return ""` — ANY failure anywhere returns `""` without a partial state.
- pynput is imported lazily inside the function body — consistent with `_get_mouse_position()` pattern. This prevents import-time failures in headless CI.

### Latency Budget (NFR1)

The 200ms hotkey-to-execution budget is shared across all `build_context()` calls:

| Step | Typical latency | Cap (`timeout=0.1`) |
|---|---|---|
| _get_selection clipboard simulation | ~60–80ms (2 subproc + 50ms sleep) | ~260ms worst case |
| _get_clipboard | ~5–15ms | 100ms |
| _get_active_app | <5ms (ctypes, no subprocess) | N/A |
| _get_mouse_position | <1ms (pynput in-process) | N/A |

Clipboard simulation is the dominant cost. Worst-case timeout-driven latency (260ms) can exceed the 200ms budget — this is an accepted limitation documented in `deferred-work.md`. The typical case (~80ms) is well within budget. Do NOT add additional `time.sleep` calls.

### Mocking ctypes in Tests

The ctypes windll mock must simulate the full chain of calls. Recommended approach:

```python
import ctypes
from unittest.mock import MagicMock, patch

def test_active_app_windows_returns_window_title() -> None:
    mock_windll = MagicMock()
    mock_windll.user32.GetForegroundWindow.return_value = 1
    mock_windll.user32.GetWindowTextLengthW.return_value = 5
    mock_windll.user32.GetWindowTextW.side_effect = (
        lambda hwnd, buf, n: buf.__setitem__(slice(None), "My App")
    )
    # create_unicode_buffer must return a buffer whose .value is "My App"
    mock_buf = MagicMock()
    mock_buf.value = "My App"

    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch("ctypes.windll", mock_windll, create=True),
        patch("ctypes.create_unicode_buffer", return_value=mock_buf),
    ):
        from nimble.context import assembler
        result = assembler._get_active_app()
    assert result == "My App"
```

The `create=True` argument to `patch` is required when patching an attribute that may not exist on the target object in the test environment (i.e., `ctypes.windll` on Linux). Alternatively, mock the entire `ctypes` module in `sys.modules` — simpler but more verbose.

### Mocking pynput in Clipboard Simulation Tests

Follow the pattern from `test_mouse_position_happy_path` — inject a fake module into `sys.modules`:

```python
from unittest.mock import MagicMock, call, patch

def test_selection_windows_happy_path() -> None:
    mock_controller_instance = MagicMock()
    mock_controller_cls = MagicMock(return_value=mock_controller_instance)
    mock_key = MagicMock()
    mock_key.ctrl = "ctrl_key"
    mock_pynput_keyboard = MagicMock(Controller=mock_controller_cls, Key=mock_key)

    run_responses = [
        MagicMock(returncode=0, stdout="saved text"),   # save (Get-Clipboard)
        MagicMock(returncode=0, stdout="selected text"), # read (Get-Clipboard after Ctrl+C)
        MagicMock(returncode=0, stdout=""),             # restore ($input | Set-Clipboard)
    ]

    with (
        patch("nimble.context.assembler.is_windows", return_value=True),
        patch("nimble.context.assembler.is_linux", return_value=False),
        patch("nimble.context.assembler.is_mac", return_value=False),
        patch("nimble.context.assembler.subprocess.run", side_effect=run_responses),
        patch("nimble.context.assembler.time.sleep"),
        patch.dict("sys.modules", {
            "pynput": MagicMock(keyboard=mock_pynput_keyboard),
            "pynput.keyboard": mock_pynput_keyboard,
        }),
    ):
        result = assembler._get_selection()
    assert result == "selected text"
```

For the restore verification test, check that the third `subprocess.run` call was made with `input="saved text"`.

### Patching is_windows / is_linux / is_mac in Tests

The platform helpers are imported at the module level in `assembler.py`. Patch them at the assembler namespace, not at `nimble.platform`:

```python
# ✅ correct
patch("nimble.context.assembler.is_windows", return_value=True)
patch("nimble.context.assembler.is_linux", return_value=False)
patch("nimble.context.assembler.is_mac", return_value=False)

# ❌ wrong — patches the source but assembler already has a local reference
patch("nimble.platform.is_windows", return_value=True)
```

Apply all three together in every platform-specific test — leaving one unpatched means the real `sys.platform` is used, which will return the actual test environment value (Linux in CI).

### Existing Tests Are Unaffected

The existing `test_assembler.py` tests do NOT patch `is_linux`. They run on Linux CI, where `is_linux()` returns `True`, so the Linux path is always taken. After the refactor, the Linux path is still the first branch — all existing tests continue to pass without modification. Do NOT modify any existing test in the file.

### Deferred Work Resolved by This Story

From `docs/bmad_output/implementation-artifacts/deferred-work.md`:
> `is_mac()` has no call sites — macOS hotkey adapter not yet implemented; `get_adapter()` raises `RuntimeError` on darwin. Resolves in Story 2.10.

This story adds `is_mac()` call sites in `assembler.py`, resolving that deferred note. The macOS hotkey adapter (`nimble/hotkeys/macos.py`) is still deferred — `get_adapter()` still raises `RuntimeError` on darwin. Context capture now works on macOS; hotkey dispatch does not.

### Files to Modify

```
nimble/context/assembler.py        ← extend _get_clipboard, _get_active_app, _get_selection
tests/unit/context/test_assembler.py  ← add Windows + macOS tests (do NOT modify existing tests)
```

### Files NOT to Modify

```
nimble/platform.py                 (is_windows / is_linux / is_mac already defined)
nimble/hotkeys/__init__.py         (macOS adapter not in scope for this story)
worker/context.py                  (IPC contract shape unchanged)
nimble/skills/runner.py            (no changes needed — build_context() caller)
tests/conftest.py                  (no new fixtures needed)
```

### Architecture Compliance

- `mypy --strict` scope includes `nimble/`, `tests/`, and `worker/` — `# type: ignore[attr-defined]` is the correct pattern for Windows-only ctypes attributes; do NOT add them to mypy `ignore_errors` list
- Absolute imports only: `from nimble.platform import is_linux, is_mac, is_windows`
- `from __future__ import annotations` is already at top of `assembler.py` — do not add it again
- No new dependencies: ctypes (stdlib), time (stdlib), pynput (already in pyproject.toml)
- All subprocess calls: `capture_output=True, timeout=0.1` — no exceptions

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 2.10] — acceptance criteria, FR2
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Technical Constraints] — macOS context capture: pbpaste, osascript, pynput keyboard simulation; ctypes for Windows active_app; no extra deps
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, import, type annotation, test rules
- [Source: nimble/context/assembler.py] — existing implementation to extend; Linux paths unchanged
- [Source: nimble/platform.py] — `is_windows()`, `is_linux()`, `is_mac()` already defined
- [Source: docs/bmad_output/implementation-artifacts/deferred-work.md] — is_mac() no call sites resolved here; worst-case latency note for assembler
- [Source: docs/bmad_output/implementation-artifacts/spec-platform-detection-utility.md] — platform.py design, `# type: ignore[attr-defined]` precedent
- [Source: docs/bmad_output/implementation-artifacts/2-9-startup-confirmation-hello-world-skill-and-bundled-test-hotkey.md#Dev Notes] — lazy pynput import pattern

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Extended `_get_clipboard()` with Windows (PowerShell `Get-Clipboard`) and macOS (`pbpaste`) paths; each wrapped in `try/except`, timeout=0.1, returns `""` on any failure.
- Extended `_get_active_app()` with Windows (ctypes `windll.user32` via local alias to keep lines ≤88 chars; one `# type: ignore[attr-defined]`) and macOS (`osascript` with concatenated script string for line-length compliance).
- Extended `_get_selection()` with full clipboard simulation for Windows (Ctrl+C via pynput) and macOS (Cmd+C via pynput); save → keypress → 50ms sleep → read → restore (best-effort); lazy pynput import consistent with `_get_mouse_position`.
- Added `import time` to top-level imports; updated platform import to include `is_mac, is_windows`.
- Added 14 new tests covering Windows and macOS paths for all three functions; all 118 tests pass.
- Pre-existing mypy errors in `tests/unit/test_platform.py` (3 `attr-defined` errors for `sys` export) were present before this story and are unchanged.

### File List

- `nimble/context/assembler.py`
- `tests/unit/context/test_assembler.py`

### Change Log

- 2026-04-24: Extended `build_context()` helpers for Windows and macOS — clipboard via PowerShell/pbpaste, active_app via ctypes/osascript, selection via clipboard simulation with pynput; 14 new unit tests added.

### Review Findings

- [x] [Review][Patch] Selection path can skip clipboard restore after the simulated copy — [`nimble/context/assembler.py`](nimble/context/assembler.py) **Fixed 2026-04-24:** after a successful save, copy runs inside an inner `try`/`finally` with `clipboard_touched`; restore runs in `finally` whenever the OS clipboard was mutated, including when `subprocess.run` for read raises. Early `return ""` if save `returncode != 0` (no copy, no restore). Regression tests: `test_selection_*_restores_clipboard_after_read_raises`, `test_selection_*_empty_when_save_fails_returncode`.
- [x] [Review][Defer] Hotkey latency vs NFR1 — [`nimble/context/assembler.py`](nimble/context/assembler.py) Windows/macOS `_get_selection()` can spend up to three sequential `timeout=0.1` subprocess calls plus `time.sleep(0.05)` in the worst case; cumulative wall clock can exceed the 200ms budget referenced in AC8/NFR1. Overlaps the existing assembler latency note in `deferred-work.md` from story 2-4; validate under real hotkey timing when convenient.
