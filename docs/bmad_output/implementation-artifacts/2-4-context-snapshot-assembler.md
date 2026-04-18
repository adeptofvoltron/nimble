# Story 2.4: Context Snapshot Assembler

Status: done

## Story

As a skill author,
I want the daemon to capture a full context snapshot at the moment a hotkey fires,
So that my skill receives the selected text, clipboard content, active application, and cursor position without me having to query them manually.

## Acceptance Criteria

1. **Given** `nimble/context/assembler.py` exports `build_context() -> dict[str, Any]`
   **When** called at hotkey-fire time
   **Then** it returns a dict with keys `selection` (str), `clipboard` (str), `active_app` (str), `mouse_position` ([int, int]) — never null values (empty string for unavailable text fields)

2. **Given** no text is selected
   **When** `build_context()` is called
   **Then** `selection` is `""` — not `None`

3. **Given** context is built
   **When** it is serialized to JSON
   **Then** all fields round-trip without loss (strings stay strings, `mouse_position` stays a 2-element integer array)

4. **Given** NFR7 — context must not be captured continuously
   **When** `build_context()` is inspected
   **Then** it performs a one-shot OS query per call — no background threads, no polling

## Tasks / Subtasks

- [x] Task 1: Create `nimble/context/` package with `assembler.py` (AC: 1, 2, 3, 4)
  - [x] Create `nimble/context/__init__.py` — empty package marker
  - [x] Implement `_get_selection() -> str` — X11 primary selection via `xclip -o -selection primary`; `""` on any failure or non-Linux
  - [x] Implement `_get_clipboard() -> str` — clipboard via `xclip -o -selection clipboard`; `""` on any failure or non-Linux
  - [x] Implement `_get_active_app() -> str` — window name via `xdotool getactivewindow getwindowname`; `""` on any failure or non-Linux
  - [x] Implement `_get_mouse_position() -> list[int]` — via lazy `from pynput import mouse`, returns `[int(x), int(y)]`; `[0, 0]` on any failure
  - [x] Implement `build_context() -> dict[str, Any]` — assembles all four helpers into a single dict
  - [x] Wrap ALL OS calls in `try/except Exception` — every helper must be silent on failure, never raise, never return `None`
  - [x] All subprocess calls must use `timeout=0.1` to cap latency within the 200ms hotkey budget (NFR1)

- [x] Task 2: Create test file `tests/unit/context/test_assembler.py` (AC: 1, 2, 3, 4)
  - [x] Create `tests/unit/context/__init__.py` — empty, mirrors source structure
  - [x] Test `build_context()` returns dict with exactly the four required keys
  - [x] Test all values are correct types: str/str/str/list[int, int]
  - [x] Test `selection` is `""` when subprocess returns non-zero exit code
  - [x] Test `selection` is `""` when subprocess returns exit code 0 with empty stdout (no primary selection)
  - [x] Test `clipboard` is `""` when subprocess returns non-zero exit code
  - [x] Test `active_app` is `""` when subprocess returns non-zero exit code
  - [x] Test `mouse_position` is `[0, 0]` when pynput raises
  - [x] Test JSON round-trip: `json.loads(json.dumps(ctx))` equals `ctx`, and `mouse_position` is a list of 2 ints
  - [x] Mock ALL subprocess and pynput calls — never call real xclip/xdotool/OS APIs in tests

- [x] Task 3: Verify quality gates (AC: 1)
  - [x] `mypy nimble/ tests/` — exits 0
  - [x] `pytest` — all tests pass (existing 22 tests + 9 new context tests = 31 total)
  - [x] `black --check nimble/ tests/` — exits 0
  - [x] `flake8 nimble/ tests/` — exits 0

## Dev Notes

### Role in the Daemon Architecture

`build_context()` is the bridge between a hotkey event and the worker IPC payload. It will be called by `nimble/skills/runner.py` (Story 2.6) immediately when a hotkey fires, BEFORE writing JSON to the worker's stdin:

```
pynput hotkey event
  → daemon dispatches to runner.py (Story 2.6)
  → runner.py calls build_context()   ← THIS STORY
  → runner.py builds IPC payload: {"invocation_id": ..., "context": <result>}
  → runner.py writes payload to worker stdin
  → worker/entrypoint.py (Story 2.5) reconstructs Context from payload
```

The dict returned by `build_context()` is placed verbatim into the `"context"` field of the IPC payload. No transformation layer exists between assembler output and IPC.

### IPC Contract — Return Shape Is a Hard Constraint

The worker side (Story 2.5, `worker/context.py`) reconstructs a `Context` object from exactly this shape. Any deviation causes a crash in the worker subprocess.

```python
# Exact required return shape — field names and types are contractual
{
    "selection": "",                # str — never None, "" when unavailable
    "clipboard": "copied text",     # str — never None, "" when unavailable
    "active_app": "VS Code",        # str — never None, "" when unavailable
    "mouse_position": [1280, 720],  # list[int] — exactly 2 ints, never None
}
```

JSON serialization rules (from architecture.md §Worker IPC Protocol):
- `mouse_position` is always a 2-element array `[x, y]` — never a dict, never null
- `selection` and `clipboard` are always strings — never null (use `""` for empty)

### Required Final State of `nimble/context/assembler.py`

```python
from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)


def _get_selection() -> str:
    if sys.platform != "linux":
        return ""
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


def _get_clipboard() -> str:
    if sys.platform != "linux":
        return ""
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


def _get_active_app() -> str:
    if sys.platform != "linux":
        return ""
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
```

### Unit Test Approach — Mock All OS Calls for CI Safety

CI runs Linux but xclip and xdotool may not be installed. All subprocess calls and pynput must be mocked. Patch at the module level, not at the subprocess level:

```python
# tests/unit/context/test_assembler.py
import json
from unittest.mock import MagicMock, patch

from nimble.context.assembler import (
    _get_active_app,
    _get_clipboard,
    _get_mouse_position,
    _get_selection,
    build_context,
)


def _mock_run(returncode: int, stdout: str) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def test_build_context_returns_required_keys() -> None:
    with patch("nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "text")):
        with patch("nimble.context.assembler._get_mouse_position", return_value=[100, 200]):
            ctx = build_context()
    assert set(ctx.keys()) == {"selection", "clipboard", "active_app", "mouse_position"}


def test_build_context_correct_types() -> None:
    with patch("nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "hello")):
        with patch("nimble.context.assembler._get_mouse_position", return_value=[10, 20]):
            ctx = build_context()
    assert isinstance(ctx["selection"], str)
    assert isinstance(ctx["clipboard"], str)
    assert isinstance(ctx["active_app"], str)
    assert isinstance(ctx["mouse_position"], list)
    assert len(ctx["mouse_position"]) == 2
    assert all(isinstance(v, int) for v in ctx["mouse_position"])


def test_selection_empty_on_subprocess_failure() -> None:
    with patch("nimble.context.assembler.subprocess.run", return_value=_mock_run(1, "")):
        assert _get_selection() == ""


def test_clipboard_empty_on_subprocess_failure() -> None:
    with patch("nimble.context.assembler.subprocess.run", return_value=_mock_run(1, "")):
        assert _get_clipboard() == ""


def test_active_app_empty_on_subprocess_failure() -> None:
    with patch("nimble.context.assembler.subprocess.run", return_value=_mock_run(1, "")):
        assert _get_active_app() == ""


def test_mouse_position_happy_path() -> None:
    mock_ctrl = MagicMock()
    mock_ctrl.return_value.position = (1920, 1080)
    with patch("pynput.mouse.Controller", mock_ctrl):
        result = _get_mouse_position()
    assert result == [1920, 1080]
    assert all(isinstance(v, int) for v in result)


def test_mouse_position_fallback_on_exception() -> None:
    mock_ctrl = MagicMock()
    mock_ctrl.side_effect = RuntimeError("no display server")
    with patch("pynput.mouse.Controller", mock_ctrl):
        result = _get_mouse_position()
    assert result == [0, 0]


def test_build_context_json_round_trip() -> None:
    with patch("nimble.context.assembler.subprocess.run", return_value=_mock_run(0, "selected")):
        with patch("nimble.context.assembler._get_mouse_position", return_value=[800, 600]):
            ctx = build_context()
    deserialized = json.loads(json.dumps(ctx))
    assert deserialized == ctx
    assert deserialized["mouse_position"] == [800, 600]
    assert isinstance(deserialized["mouse_position"][0], int)
```

### Architecture Guardrails

| Rule | Reason |
|---|---|
| `build_context()` return type `dict[str, Any]` | IPC contract — worker reconstructs Context from this exact shape |
| All helpers return `""` / `[0, 0]` on failure | NFR13: no silent failures; daemon never crashes from context capture |
| `subprocess.run(..., timeout=0.1)` | NFR1: 200ms hotkey budget — context capture must not stall |
| Lazy pynput import inside `_get_mouse_position()` | CI safety pattern from stories 2.2 and 2.3 — pynput must not load at import time |
| `sys.platform != "linux"` guard for subprocess helpers | Valid v1 behavior: Windows returns `""` for text fields |
| No background threads, no polling | NFR7: context captured only at hotkey-fire time |
| Absolute imports only | Architecture convention — `from nimble.context.assembler import build_context` |
| `mypy --strict` | All parameters and return types annotated |

### Platform Notes (v1)

**Linux X11:** All four fields captured. Requires `xclip` and `xdotool` to be installed on the user's system. Both are standard packages available in all major Linux distributions. On success, `selection` and `clipboard` are raw `xclip` stdout (not `.strip()`), so skills may see a trailing newline or other exact bytes from the buffer; `active_app` still uses `.strip()` on `xdotool` output.

**Windows:** String fields (`selection`, `clipboard`, `active_app`) return `""` in v1 — Windows context capture is deferred. `mouse_position` works cross-platform via pynput. Windows context enrichment is addressed in a future story.

### Files This Story Creates

```
nimble/context/__init__.py              ← NEW (empty package marker)
nimble/context/assembler.py            ← NEW (build_context + four helpers)
tests/unit/context/__init__.py         ← NEW (empty, mirrors source structure)
tests/unit/context/test_assembler.py   ← NEW (9 unit tests)
```

Application code is only the new paths above. Sprint tracking (`docs/bmad_output/implementation-artifacts/sprint-status.yaml`) and this story file are updated as part of the normal story workflow, not as runtime Nimble modules.

### Cross-Story Context

- **Story 2.5** (`worker/context.py`) creates the `Context` class the worker reconstructs from this dict — field names must match exactly
- **Story 2.6** (`nimble/skills/runner.py`) calls `build_context()` and wraps the result in the IPC JSON payload — no intermediary transformation
- **Story 4.6** adds Windows reserved hotkey warnings; may also extend this assembler with Windows context capture

### References

- [Source: docs/bmad_output/planning-artifacts/architecture.md#Worker IPC Protocol] — exact JSON field names, types, and constraints
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Daemon Process Model] — where build_context fits in the dispatch flow
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Naming Patterns] — snake_case, absolute imports, mypy --strict
- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 2.4] — acceptance criteria
- [Source: docs/bmad_output/planning-artifacts/epics.md#NonFunctional Requirements] — NFR1 (200ms), NFR7 (no continuous monitoring), NFR13 (no silent failures)
- [Source: docs/bmad_output/implementation-artifacts/2-3-windows-hotkey-adapter.md#Dev Notes] — lazy pynput import pattern for CI safety

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Black reformatted `tests/unit/context/test_assembler.py` (line length on nested `with patch(...)` blocks) — applied and re-verified all gates.

### Completion Notes List

- ✅ Created `nimble/context/__init__.py` and `nimble/context/assembler.py` with `build_context()` and four helper functions.
- ✅ All helpers guard with `sys.platform != "linux"` and `try/except Exception` — never raise, never return None.
- ✅ `subprocess.run` calls use `timeout=0.1` enforcing NFR1 (200ms hotkey budget).
- ✅ Lazy `from pynput import mouse` inside `_get_mouse_position()` per CI safety pattern from stories 2.2/2.3.
- ✅ 9 unit tests created; all subprocess and pynput calls mocked — no real OS APIs called in tests.
- ✅ JSON round-trip verified: all fields survive `json.dumps` / `json.loads` without loss.
- ✅ Quality gates: mypy 0 issues (22 files), pytest 31/31, black clean, flake8 clean.

### File List

- `nimble/context/__init__.py` (new)
- `nimble/context/assembler.py` (new)
- `tests/unit/context/__init__.py` (new)
- `tests/unit/context/test_assembler.py` (new)

### Change Log

- 2026-04-18: Implemented Story 2.4 — Context Snapshot Assembler. Added `nimble/context/` package with `build_context()` returning selection, clipboard, active_app, and mouse_position. 8 unit tests added; all 30 tests pass.
- 2026-04-18: Code review follow-up — removed unused logging in `assembler.py`, clarified Dev Notes on touched tracking files, added `test_selection_empty_on_success_with_empty_stdout`; story marked done.

### Review Findings

- [x] [Review][Decision] ~~Strip vs raw for `selection` / `clipboard`?~~ **Resolved (2026-04-18):** **Raw** — keep `xclip` stdout unchanged for `selection` and `clipboard` so the IPC payload preserves exact buffer bytes; `active_app` continues to use `.strip()` on window titles. Documented under Platform Notes (v1).

- [x] [Review][Patch] Remove dead `logger` / `logging` import if unused [`nimble/context/assembler.py:8`]

- [x] [Review][Patch] Dev Notes claim “No existing files are modified” is inaccurate — `sprint-status.yaml` and this story file are updated as part of delivery; tighten the wording so future readers are not misled [`2-4-context-snapshot-assembler.md:284`]

- [x] [Review][Patch] Add an explicit unit test for “no primary selection” as **exit code 0 with empty stdout** (not only non-zero exit), so AC2 is covered as written [`tests/unit/context/test_assembler.py`]

- [x] [Review][Defer] Worst-case latency: up to three `subprocess.run(..., timeout=0.1)` calls plus mouse capture may approach or exceed the 200ms hotkey budget under slow or contended systems — track against NFR1 when integrating with runner (Story 2.6) [`nimble/context/assembler.py`] — deferred, pre-existing NFR tension
