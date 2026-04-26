# Story 3.5: Input Dialog Tool Primitives (`tools.input.ask` / `tools.input.select`)

Status: done

## Story

As a skill author,
I want to prompt the user for text input or a selection choice mid-skill,
so that I can build interactive workflows that require user input at execution time.

## Acceptance Criteria

1. **Given** `tools.input.ask("Enter search query:")` is called
   **When** the dialog appears
   **Then** the user can type a string and confirm, and the entered string is returned to the skill

2. **Given** `tools.input.select("Choose action:", ["Summarize", "Translate", "Explain"])` is called
   **When** the dialog appears
   **Then** the user can pick one option, and the selected string is returned to the skill

3. **Given** the user dismisses either dialog without confirming
   **When** the dialog closes
   **Then** the tool returns `None` — the skill can check for this and exit gracefully

## Tasks / Subtasks

- [x] Task 1: Create `nimble/tools/input.py` with `InputTool` class (AC: 1, 2, 3)
  - [x] Add `from __future__ import annotations` at top
  - [x] Add `import logging` and `logger = logging.getLogger(__name__)` at module level
  - [x] Add `from typing import Any` import for internal helper type annotation
  - [x] Define `class InputTool` with no constructor arguments
  - [x] Implement `ask(self, prompt: str) -> str | None`:
    - Lazy import: `import tkinter as tk` then `from tkinter import simpledialog`
    - Create hidden root: `root = tk.Tk(); root.withdraw()`
    - Nested `try/finally`: call `simpledialog.askstring("Nimble", prompt)` in try, `root.destroy()` in finally
    - Outer `except Exception as exc`: re-raise as `RuntimeError(f"Input dialog is not available: {exc}") from exc`
    - Return type: `str | None` (None when user cancels — this is normal, NOT an error)
  - [x] Implement `select(self, prompt: str, choices: list[str]) -> str | None`:
    - Lazy import: `import tkinter as tk`
    - Create hidden root: `root = tk.Tk(); root.withdraw()`
    - Nested `try/finally`: call `_run_select_dialog(root, prompt, choices)` in try, `root.destroy()` in finally
    - Outer `except Exception as exc`: re-raise as `RuntimeError(f"Input dialog is not available: {exc}") from exc`
    - Return type: `str | None`
  - [x] Implement module-level `_run_select_dialog(parent: Any, prompt: str, choices: list[str]) -> str | None`:
    - Uses `tk.Toplevel`, `tk.Label`, `tk.Listbox`, `tk.Frame`, `tk.Button`
    - `result: list[str | None] = [None]` — list wrapper allows closure mutation
    - `on_ok()` closure: reads `listbox.curselection()`, sets `result[0]` if selection, destroys window
    - `on_cancel()` closure: destroys window without setting result
    - `win.grab_set()` — blocks other Tk interaction while dialog is open
    - `win.wait_window()` — blocks until window is destroyed
    - Returns `result[0]`
  - [x] Full `mypy --strict` compliance — all params and return types annotated

- [x] Task 2: Update `nimble/tools/__init__.py` to add `input` field to `ToolRegistry` (AC: 1, 2, 3)
  - [x] Add `from nimble.tools.input import InputTool` import — insert alphabetically: after `ClipboardTool`, before `PopupTool` (a, c, **i**, p, t)
  - [x] Add `input: InputTool` field to `ToolRegistry` dataclass — append after `tts: TtsTool`
  - [x] **`input` shadows Python builtin:** Valid Python — dataclass field `input` shadows the builtin `input()` only inside the class definition scope. Outside, `tools.input.ask()` is attribute access on the registry, not the builtin. mypy handles this correctly.

- [x] Task 3: Update `worker/entrypoint.py` to instantiate `InputTool` in `_build_tools()` (AC: 1, 2)
  - [x] Add `from nimble.tools.input import InputTool  # noqa: E402` import after existing `TtsTool` import (line ~27)
  - [x] Update `_build_tools()` return to add `input=InputTool()` — split to multi-line for black compliance if needed (88-char limit)
  - [x] No other changes to `entrypoint.py`

- [x] Task 4: Add `tests/unit/tools/test_input.py` (AC: 1, 2, 3)
  - [x] `test_ask_returns_entered_text()` — mock tkinter, assert `ask("Enter:")` returns the mocked string
  - [x] `test_ask_returns_none_on_cancel()` — mock `simpledialog.askstring` to return None, assert `ask("Enter:")` returns None
  - [x] `test_ask_raises_runtime_error_when_tkinter_unavailable()` — `patch.dict("sys.modules", {"tkinter": None})`, assert `RuntimeError` raised matching "Input dialog is not available"
  - [x] `test_ask_calls_simpledialog_with_correct_args()` — mock tkinter, assert `simpledialog.askstring` called with `("Nimble", "Enter:")` exactly
  - [x] `test_select_returns_chosen_option()` — patch `nimble.tools.input._run_select_dialog` to return `"Summarize"`, assert `select(...)` returns `"Summarize"`
  - [x] `test_select_returns_none_on_dismiss()` — patch `_run_select_dialog` to return None, assert `select(...)` returns None
  - [x] `test_select_raises_runtime_error_when_tkinter_unavailable()` — `patch.dict("sys.modules", {"tkinter": None})`, assert `RuntimeError` raised

- [x] Task 5: Verify quality gates (AC: all)
  - [x] `mypy nimble/ tests/ worker/` — exits 0 on new files; 7 pre-existing errors in test_platform.py, watcher.py, manifest/parser.py, tools/ai.py unchanged
  - [x] `python3 -m pytest` — 153 passed (146 pre-existing + 7 new input tests); 2 pre-existing collection errors unrelated to this story
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Decision] `config.yaml` hotkey changed with Story 3.5 work — **Resolved (2026-04-26):** Keep `skills.hello_world.binding` as `ctrl+l`; Dev Notes and file lists updated so `config.yaml` is documented as touched by this branch.

- [x] [Review][Patch] Unused module logger in `nimble/tools/input.py` — **Resolved:** `logger.warning(..., exc_info=True)` added in both `except` paths before re-raising `RuntimeError`.

- [x] [Review][Defer] `_run_select_dialog` internals not directly tested [nimble/tools/input.py:40-71] — deferred; deliberate spec decision to test `select()` via public API with `_run_select_dialog` patched; listbox, `on_ok`/`on_cancel`, and `curselection` indexing unexercised by unit tests
- [x] [Review][Defer] `grab_set()` may fail silently on some X11/EWMH window managers without prior `win.update()` [nimble/tools/input.py:47] — deferred; standard tkinter mitigation is `win.update()` before `win.grab_set()`; theoretical under normal desktop use
- [x] [Review][Defer] `except Exception` masks internal bugs as misleading `RuntimeError("Input dialog is not available")` [nimble/tools/input.py:21-23,35-37] — deferred; consistent with TTS sibling pattern; construction errors and `root.destroy()` failures surface as dependency errors
- [x] [Review][Defer] Double-destroy: `root.destroy()` runs after `win` already destroyed inside `_run_select_dialog` [nimble/tools/input.py] — deferred; tkinter tolerates silent double-destroy; cosmetic resource management oddity
- [x] [Review][Defer] Thread-safety: `ask()`/`select()` must be called from the main thread; cross-thread use raises misleading error [nimble/tools/input.py:10] — deferred; pre-existing pattern across all tool primitives; document in skill authoring guide
- [x] [Review][Defer] `ask()` returns `""` for empty-field OK (falsy but not `None`) — callers using `if result:` mishandle this [nimble/tools/input.py:13-22] — deferred; tkinter `simpledialog.askstring` design; not a spec violation; document in skill authoring guide
- [x] [Review][Defer] `select()` accepts `choices=[]` with no guard — renders zero-height listbox, OK returns `None` indistinguishable from cancel [nimble/tools/input.py:24] — deferred; out of spec scope; add `ValueError` guard in future hardening story
- [x] [Review][Defer] No test for `root.destroy()` path when `askstring` raises after `tk.Tk()` succeeds [tests/unit/tools/test_input.py] — deferred; unavailability tests patch tkinter=None so `Tk()` never runs; the `finally` guard is unverified by the current suite

## Dev Notes

### Role in the Daemon Architecture

```
hotkey fires
  → runner.py dispatches JSON payload to worker stdin
  → worker/entrypoint.py calls _build_tools()
  → _build_tools() constructs ToolRegistry(ai=..., popup=..., clipboard=..., tts=..., input=InputTool())
  → skill.run(context, tools)
  → tools.input.ask("Enter query:")    ← opens tkinter dialog, blocks until user responds
  → returns str or None
```

`InputTool` is the fifth and final tool primitive in Epic 3. It lives at `nimble/tools/input.py` (already defined in the architecture's repository structure).

### Critical: Error Handling Matches TTS, Not Clipboard

| Tool | On failure | On cancel/dismiss |
|---|---|---|
| `popup.show()` | Swallow, log warning | N/A |
| `clipboard.get()` | Swallow, return `""` | N/A |
| `clipboard.set()` | Swallow, log warning | N/A |
| `tts.speak()` | Re-raise as `RuntimeError` | N/A |
| **`input.ask()`** | **Re-raise as `RuntimeError`** | **Return `None`** |
| **`input.select()`** | **Re-raise as `RuntimeError`** | **Return `None`** |

User cancellation (None return) is NOT an error — AC3 explicitly requires this. A dialog that can't open (no tkinter, no display) IS an error → `RuntimeError`.

### Library Decision: `tkinter` (stdlib) — No New Dependency

**Chosen:** `tkinter` — Python standard library. Do NOT add anything to `pyproject.toml`.

Why not alternatives:
- `plyer` — no input dialog support in plyer 2.1 (only notifications, TTS, clipboard)
- `zenity`/`kdialog` — Linux-only subprocesses, breaks cross-platform
- `PyQt`/`wx`/`customtkinter` — heavyweight third-party deps, contradicts architecture's minimal-dep philosophy

**tkinter availability by platform:**
- **Linux:** requires `python3-tk` system package. Present on most distros with Python. If missing: `ImportError` → caught, re-raised as `RuntimeError`. If no `$DISPLAY`: `TclError` from `tk.Tk()` → caught, re-raised as `RuntimeError`.
- **Windows:** Bundled with CPython Windows installer — always available.
- **macOS:** Bundled with CPython macOS installer — always available.

### Complete Implementation: `nimble/tools/input.py`

```python
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class InputTool:
    def ask(self, prompt: str) -> str | None:
        try:
            import tkinter as tk
            from tkinter import simpledialog

            root = tk.Tk()
            root.withdraw()
            try:
                return simpledialog.askstring("Nimble", prompt)
            finally:
                root.destroy()
        except Exception as exc:
            raise RuntimeError(f"Input dialog is not available: {exc}") from exc

    def select(self, prompt: str, choices: list[str]) -> str | None:
        try:
            import tkinter as tk

            root = tk.Tk()
            root.withdraw()
            try:
                return _run_select_dialog(root, prompt, choices)
            finally:
                root.destroy()
        except Exception as exc:
            raise RuntimeError(f"Input dialog is not available: {exc}") from exc


def _run_select_dialog(parent: Any, prompt: str, choices: list[str]) -> str | None:
    import tkinter as tk

    result: list[str | None] = [None]

    win = tk.Toplevel(parent)
    win.title("Nimble")
    win.grab_set()

    tk.Label(win, text=prompt).pack(padx=10, pady=(10, 0))

    listbox = tk.Listbox(win, selectmode=tk.SINGLE, height=min(len(choices), 10))
    for item in choices:
        listbox.insert(tk.END, item)
    listbox.pack(padx=10, pady=5)

    def on_ok() -> None:
        sel = listbox.curselection()
        if sel:
            result[0] = choices[sel[0]]
        win.destroy()

    def on_cancel() -> None:
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=(0, 10))
    tk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT)

    win.wait_window()
    return result[0]
```

**Why `result: list[str | None] = [None]`:** Python closures can't reassign enclosing-scope variables without `nonlocal`. Using a single-element list is a clean alternative that mypy handles correctly.

**Why `win.grab_set()` then `win.wait_window()`:** `grab_set()` makes this window modal (captures all events). `wait_window()` blocks until `win.destroy()` is called. This is the standard tkinter blocking-dialog pattern.

**Why nested `try/finally` inside outer `try/except`:** The outer `except Exception` catches everything including `TclError` (no display). The inner `finally` ensures `root.destroy()` always runs *if `root` was successfully created*. If `tk.Tk()` itself fails, `root` is never assigned, so `finally` is never entered — the exception propagates directly to the outer `except`.

### Updated `nimble/tools/__init__.py`

Current state (after Story 3.4):
```python
from __future__ import annotations

from dataclasses import dataclass

from nimble.tools.ai import AiTool
from nimble.tools.clipboard import ClipboardTool
from nimble.tools.popup import PopupTool
from nimble.tools.tts import TtsTool


@dataclass
class ToolRegistry:
    ai: AiTool
    popup: PopupTool
    clipboard: ClipboardTool
    tts: TtsTool
```

Target state (after Story 3.5):
```python
from __future__ import annotations

from dataclasses import dataclass

from nimble.tools.ai import AiTool
from nimble.tools.clipboard import ClipboardTool
from nimble.tools.input import InputTool
from nimble.tools.popup import PopupTool
from nimble.tools.tts import TtsTool


@dataclass
class ToolRegistry:
    ai: AiTool
    popup: PopupTool
    clipboard: ClipboardTool
    tts: TtsTool
    input: InputTool
```

Import alphabetical order: ai (a), clipboard (c), input (i), popup (p), tts (t) ✓

### Updated `worker/entrypoint.py` — `_build_tools()`

Add import after `from nimble.tools.tts import TtsTool  # noqa: E402`:
```python
from nimble.tools.input import InputTool  # noqa: E402
```

Change the return statement:
```python
return ToolRegistry(
    ai=AiTool(ai_config),
    popup=PopupTool(),
    clipboard=ClipboardTool(),
    tts=TtsTool(),
    input=InputTool(),
)
```

### ToolRegistry Breakage Check

Before starting, run:
```bash
grep -r "ToolRegistry(" tests/ worker/ nimble/
```

Only `worker/entrypoint.py::_build_tools()` constructs `ToolRegistry` directly (confirmed by grep — one result). Tests mock at module level. Adding `input: InputTool` as a new positional dataclass field means `_build_tools()` is the only site that needs updating.

### Test Pattern for `tests/unit/tools/test_input.py`

The implementation uses lazy imports (`import tkinter as tk` inside methods). Mock tkinter via `patch.dict("sys.modules", ...)` — same infrastructure as the plyer-based tools.

**Key insight:** `from tkinter import simpledialog` inside `ask()` resolves to `sys.modules["tkinter"].simpledialog`. When `sys.modules["tkinter"]` is a `MagicMock()`, attribute access on it returns another `MagicMock` automatically. So mocking just `"tkinter"` covers both `tk.Tk()` and `simpledialog.askstring()` calls.

```python
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from nimble.tools.input import InputTool


def test_ask_returns_entered_text() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    mock_tkinter.simpledialog.askstring.return_value = "hello"
    with patch.dict("sys.modules", {
        "tkinter": mock_tkinter,
        "tkinter.simpledialog": mock_tkinter.simpledialog,
    }):
        result = tool.ask("Enter:")
    assert result == "hello"


def test_ask_returns_none_on_cancel() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    mock_tkinter.simpledialog.askstring.return_value = None
    with patch.dict("sys.modules", {
        "tkinter": mock_tkinter,
        "tkinter.simpledialog": mock_tkinter.simpledialog,
    }):
        result = tool.ask("Enter:")
    assert result is None


def test_ask_raises_runtime_error_when_tkinter_unavailable() -> None:
    tool = InputTool()
    with patch.dict("sys.modules", {"tkinter": None}):
        with pytest.raises(RuntimeError, match="Input dialog is not available"):
            tool.ask("Enter:")


def test_ask_calls_simpledialog_with_correct_args() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    mock_tkinter.simpledialog.askstring.return_value = "result"
    with patch.dict("sys.modules", {
        "tkinter": mock_tkinter,
        "tkinter.simpledialog": mock_tkinter.simpledialog,
    }):
        tool.ask("My prompt")
    mock_tkinter.simpledialog.askstring.assert_called_once_with("Nimble", "My prompt")


def test_select_returns_chosen_option() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    with patch.dict("sys.modules", {"tkinter": mock_tkinter}):
        with patch("nimble.tools.input._run_select_dialog", return_value="Summarize"):
            result = tool.select("Choose:", ["Summarize", "Translate"])
    assert result == "Summarize"


def test_select_returns_none_on_dismiss() -> None:
    tool = InputTool()
    mock_tkinter = MagicMock()
    with patch.dict("sys.modules", {"tkinter": mock_tkinter}):
        with patch("nimble.tools.input._run_select_dialog", return_value=None):
            result = tool.select("Choose:", ["A", "B"])
    assert result is None


def test_select_raises_runtime_error_when_tkinter_unavailable() -> None:
    tool = InputTool()
    with patch.dict("sys.modules", {"tkinter": None}):
        with pytest.raises(RuntimeError, match="Input dialog is not available"):
            tool.select("Choose:", ["A", "B"])
```

### Architecture Compliance

- `nimble/tools/input.py` defined in architecture (`nimble/tools/` → FR18, FR19) — location is correct
- `tests/unit/tools/test_input.py` follows mirror structure established in Stories 3.1–3.4
- `mypy --strict` across `nimble/`, `tests/`, `worker/`
- Absolute imports: `from nimble.tools.input import InputTool` — never relative
- `@dataclass` for `ToolRegistry` — just add `input: InputTool` field after `tts`
- Lazy import in `input.py` — consistent with `popup.py`, `clipboard.py`, `tts.py` pattern
- No new `pyproject.toml` dependencies — `tkinter` is Python stdlib
- `from __future__ import annotations` at top of `input.py`

### New Files

```
nimble/tools/input.py              ← InputTool class + _run_select_dialog helper
tests/unit/tools/test_input.py     ← 7 unit tests
```

### Modified Files

```
nimble/tools/__init__.py           ← add InputTool import + input field to ToolRegistry
worker/entrypoint.py               ← add InputTool import; update _build_tools() return value
config.yaml                        ← `skills.hello_world.binding` set to `ctrl+l` (local dev preference; ships with this branch)
```

No changes to: `nimble/manifest/parser.py`, `nimble/skills/runner.py`, `nimble/daemon.py`, `pyproject.toml`

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 3.5] — acceptance criteria, FR18, FR19
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Repository Module Structure] — `nimble/tools/input.py` placement, `tests/unit/tools/test_input.py`
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, type annotations, absolute imports, test mirroring rules
- [Source: nimble/tools/tts.py] — error handling pattern (re-raise as RuntimeError — do NOT swallow)
- [Source: nimble/tools/popup.py] — lazy import pattern to follow
- [Source: nimble/tools/__init__.py] — current ToolRegistry structure to extend (add input after tts)
- [Source: worker/entrypoint.py] — existing `_build_tools()` return statement to update
- [Source: docs/bmad_output/implementation-artifacts/3-4-tts-tool-primitive-tools-tts-speak.md#Dev Notes] — ToolRegistry extension pattern, one construction site confirmed

## Dev Agent Record

### Implementation Notes

Implemented `InputTool` with `ask()` and `select()` methods using tkinter (stdlib, no new deps). Used lazy imports inside methods matching the popup/tts pattern. `_run_select_dialog` uses the list-wrapper closure trick for mutation in `on_ok()`. Added `# type: ignore[no-untyped-call]` on `curselection()` — tkinter stubs omit its return type. All 7 unit tests pass using `patch.dict("sys.modules", ...)` to mock tkinter without a display.

### Completion Notes

- All 5 tasks completed, all subtasks checked
- 7 new unit tests pass; full suite 153 passed (no regressions)
- mypy: 0 new errors in new files; 7 pre-existing errors unchanged
- black: exits 0 (reformatted test_input.py dict args to multi-line)
- flake8: exits 0
- All 3 ACs satisfied: ask returns string/None, select returns string/None, cancel returns None

## File List

### New Files
- `nimble/tools/input.py`
- `tests/unit/tools/test_input.py`

### Modified Files
- `nimble/tools/__init__.py`
- `worker/entrypoint.py`
- `config.yaml` (`hello_world` binding → `ctrl+l`)

## Change Log

- 2026-04-26: Implemented Story 3.5 — InputTool with ask/select dialogs via tkinter; wired into ToolRegistry and worker entrypoint; 7 unit tests added; all quality gates pass
- 2026-04-26: Code review — retained `config.yaml` binding change; documented in Dev Notes; diagnostic logging on input dialog failures in `input.py`; story marked done
