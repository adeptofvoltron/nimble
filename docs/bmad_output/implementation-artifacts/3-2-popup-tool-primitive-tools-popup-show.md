# Story 3.2: Popup Tool Primitive (`tools.popup.show`)

Status: done

## Story

As a skill author,
I want to call `tools.popup.show(text)` and have the result appear as a system notification,
So that I can surface skill output without the user switching windows.

## Acceptance Criteria

1. **Given** `tools.popup.show("Hello, Nimble!")` is called
   **When** the skill runs on Linux
   **Then** a system notification appears using the native mechanism (plyer/libnotify) with the provided text

2. **When** the skill runs on Windows
   **Then** a system notification appears using the native Win32 mechanism (NFR17)

3. **Given** the text passed to `popup.show()` is an empty string
   **When** the popup fires
   **Then** it displays gracefully — no crash or silent failure

## Tasks / Subtasks

- [x] Task 1: Create `nimble/tools/popup.py` with `PopupTool` class (AC: 1, 2, 3)
  - [x] Define `class PopupTool` with no constructor arguments
  - [x] Implement `show(self, text: str) -> None`
  - [x] Use lazy import of plyer inside `show()`: `from plyer import notification`
  - [x] Call `notification.notify(title="Nimble", message=text, app_name="Nimble")`
  - [x] Wrap in `try/except Exception` — log warning via `logger.warning("popup.show failed", exc_info=True)` on failure; do NOT re-raise (skill must not crash due to a notification failure)
  - [x] Add `logger = logging.getLogger(__name__)` at module level
  - [x] Full `mypy --strict` compliance: `from __future__ import annotations` at top; annotate all params and return types

- [x] Task 2: Update `nimble/tools/__init__.py` to add `popup` field to `ToolRegistry` (AC: 1, 2, 3)
  - [x] Add `from nimble.tools.popup import PopupTool` import
  - [x] Add `popup: PopupTool` field to `ToolRegistry` dataclass (after `ai: AiTool`)
  - [x] Do NOT add stub fields for stories 3.3–3.5 (clipboard, tts, input) — those come in future stories

- [x] Task 3: Update `worker/entrypoint.py` to instantiate `PopupTool` in `_build_tools()` (AC: 1, 2)
  - [x] Add `from nimble.tools.popup import PopupTool` import after the existing post-sys.path imports
  - [x] Update `_build_tools()` to pass `popup=PopupTool()` to `ToolRegistry`
  - [x] `PopupTool()` takes no constructor arguments — just instantiate directly
  - [x] Resulting call: `return ToolRegistry(ai=AiTool(ai_config), popup=PopupTool())`

- [x] Task 4: Add `tests/unit/tools/test_popup.py` (AC: 1, 2, 3)
  - [x] `test_show_calls_plyer_notify()` — mock `plyer.notification.notify`, call `show("Hello")`, assert `notify` called with `title="Nimble"`, `message="Hello"`, `app_name="Nimble"`
  - [x] `test_show_with_empty_string_does_not_raise()` — call `show("")` with plyer mocked, verify no exception raised and notify was called
  - [x] `test_show_handles_plyer_failure_gracefully()` — mock plyer to raise an exception, call `show("text")`, verify no exception propagates (tool swallows it)
  - [x] `test_show_handles_plyer_import_failure()` — use `patch.dict("sys.modules", {"plyer": None})`, call `show("text")`, verify no exception propagates

- [x] Task 5: Verify quality gates (AC: all)
  - [x] `mypy nimble/ tests/ worker/` — exits 0 (excluding pre-existing errors in test_platform.py)
  - [x] `pytest` — all tests pass (135 pre-existing + 4 new popup tests = 139 total)
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

### Review Findings

- [x] [Review][Patch] Decouple popup tests from real `plyer` import to avoid environment-sensitive failures [tests/unit/tools/test_popup.py:9]
- [x] [Review][Patch] Assert warning log emission on popup failure paths to preserve observability contract [tests/unit/tools/test_popup.py:24]

## Dev Notes

### Role in the Daemon Architecture

```
hotkey fires
  → runner.py dispatches JSON payload to worker stdin
  → worker/entrypoint.py calls _build_tools()
  → _build_tools() constructs ToolRegistry(ai=AiTool(ai_config), popup=PopupTool())
  → skill.run(context, tools)  ← tools.popup.show("...") now works
  → PopupTool.show() calls plyer.notification.notify() — native OS notification fires
```

This story wires the second tool into the existing `ToolRegistry`. It follows the same pattern as Story 3.1 (AI tool), but is simpler: `PopupTool` requires zero configuration, so there is no env var passing through `runner.py`, no config in `parser.py`, and no changes to `daemon.py`.

### Why plyer, not a custom notification adapter

`plyer` is already a core engine dependency (`pyproject.toml`). It wraps libnotify/D-Bus on Linux and Win32 notifications on Windows — exactly what NFR17 requires. The existing `nimble/notifier.py` uses the same library with the same lazy-import pattern. No new dep needed.

**Difference from `notifier.py`:** `Notifier` is the daemon-level error/system message channel (used in `runner.py` for skill failure alerts). `PopupTool` is the skill-facing output channel — what skill authors call to surface results to the user. They are intentionally separate.

### `nimble/tools/popup.py` — Complete Implementation

```python
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PopupTool:
    def show(self, text: str) -> None:
        try:
            from plyer import notification

            notification.notify(title="Nimble", message=text, app_name="Nimble")
        except Exception:
            logger.warning("popup.show failed", exc_info=True)
```

**Lazy import rationale:** plyer is available in author skill workers (which use `sys.executable`, the daemon's Python environment). Community skill workers run in isolated venvs that may not have plyer installed. The lazy import + try/except ensures a missing plyer degrades gracefully (warning log) rather than crashing the skill.

**Empty string behaviour:** `plyer` handles empty message strings without error — it simply shows a notification with an empty body. The AC requirement of "no crash or silent failure" is met: the notification fires, the call succeeds, no exception propagates.

### `nimble/tools/__init__.py` — Updated ToolRegistry

```python
from __future__ import annotations

from dataclasses import dataclass

from nimble.tools.ai import AiTool
from nimble.tools.popup import PopupTool


@dataclass
class ToolRegistry:
    ai: AiTool
    popup: PopupTool
```

Skills call `tools.popup.show(...)`. Future stories (3.3–3.5) will add `clipboard`, `tts`, and `input` fields. Do **NOT** add stub fields for those now.

### `worker/entrypoint.py` — Updated `_build_tools()`

The only change is adding the `PopupTool` import and including it in `ToolRegistry` construction:

```python
# After existing sys.path injection block, add:
from nimble.tools.popup import PopupTool  # noqa: E402

# Updated _build_tools():
def _build_tools() -> ToolRegistry:
    raw = os.environ.get("NIMBLE_AI_CONFIG", "")
    ai_config: AiConfig | None = None
    if raw:
        try:
            data = json.loads(raw)
            ai_config = AiConfig(
                provider=data["provider"],
                model=data["model"],
                api_key_env=data["api_key_env"],
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass  # malformed env var — treat as no AI config
    return ToolRegistry(ai=AiTool(ai_config), popup=PopupTool())
```

`PopupTool()` takes no arguments. The `ToolRegistry` dataclass constructor now requires both `ai` and `popup` to be provided — any existing test that constructs `ToolRegistry` directly will need updating if it passes only `ai=`.

### Test Patterns for `tests/unit/tools/test_popup.py`

plyer IS installed in the engine venv (core dep in pyproject.toml), so tests can patch it directly rather than mocking via `sys.modules`.

```python
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nimble.tools.popup import PopupTool


def test_show_calls_plyer_notify() -> None:
    tool = PopupTool()
    with patch("plyer.notification.notify") as mock_notify:
        tool.show("Hello, Nimble!")
    mock_notify.assert_called_once_with(
        title="Nimble", message="Hello, Nimble!", app_name="Nimble"
    )


def test_show_with_empty_string_does_not_raise() -> None:
    tool = PopupTool()
    with patch("plyer.notification.notify") as mock_notify:
        tool.show("")  # must not raise
    mock_notify.assert_called_once_with(title="Nimble", message="", app_name="Nimble")


def test_show_handles_plyer_failure_gracefully() -> None:
    tool = PopupTool()
    with patch("plyer.notification.notify", side_effect=RuntimeError("notify failed")):
        tool.show("text")  # must not propagate the exception


def test_show_handles_plyer_import_failure() -> None:
    tool = PopupTool()
    with patch.dict("sys.modules", {"plyer": None}):
        tool.show("text")  # must not raise even if plyer is unavailable
```

**Note on `patch.dict("sys.modules", {"plyer": None})`:** Setting a module to `None` in `sys.modules` causes `from plyer import notification` to raise `ImportError`. This simulates community skill venvs where plyer is not installed.

**Note on `patch("plyer.notification.notify")`:** This patches the actual `notify` function on the already-imported `plyer.notification` module object. It works because plyer is installed and `from plyer import notification` succeeds — we then intercept the `notify` call on that real module object.

### Existing Tests That Reference `ToolRegistry` Directly

Check `tests/unit/` for any test that constructs `ToolRegistry(ai=...)` directly — these will fail with a missing `popup` argument once the dataclass gains the new field. Search pattern:

```bash
grep -r "ToolRegistry(" tests/
```

Any found occurrences must be updated to also pass `popup=PopupTool()`.

From the Story 3.1 implementation, `ToolRegistry` was only constructed inside `worker/entrypoint.py`'s `_build_tools()`. Tests for the AI tool mock the SDK at the `sys.modules` level and call `AiTool.ask()` directly — they do not construct `ToolRegistry`. However, verify via the grep above before assuming no breakage.

### Architecture Compliance

- `mypy --strict` across `nimble/`, `tests/`, `worker/`
- Absolute imports: `from nimble.tools.popup import PopupTool` — never relative
- `@dataclass` for `ToolRegistry` (already; just add field)
- Lazy import in `popup.py` — consistent with `notifier.py` pattern
- No new `pyproject.toml` dependencies — plyer is already a core dep
- Test mirroring: `nimble/tools/popup.py` → `tests/unit/tools/test_popup.py`
- `from __future__ import annotations` at top of `popup.py` (consistent with all other `nimble/` modules)

### New Files

```
nimble/tools/popup.py              ← PopupTool class
tests/unit/tools/test_popup.py     ← 4 unit tests
```

### Modified Files

```
nimble/tools/__init__.py           ← add PopupTool import + popup field to ToolRegistry
worker/entrypoint.py               ← add PopupTool import; update _build_tools() return value
```

No changes to: `nimble/manifest/parser.py`, `nimble/skills/runner.py`, `nimble/daemon.py`, `config.yaml`

### Project Structure Notes

- `nimble/tools/popup.py` is planned in the architecture (`nimble/tools/` → FR14) — location is correct
- `tests/unit/tools/test_popup.py` follows the mirror structure established in Story 3.1
- The architecture lists `tests/unit/tools/test_popup.py` explicitly — no deviation

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 3.2] — acceptance criteria, FR14, NFR17
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Repository Module Structure] — `nimble/tools/popup.py` placement, `tests/unit/tools/test_popup.py`
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, type annotations, absolute imports, test mirroring rules
- [Source: nimble/notifier.py] — lazy plyer import pattern to follow exactly
- [Source: nimble/tools/__init__.py] — current ToolRegistry structure to extend
- [Source: worker/entrypoint.py] — existing `_build_tools()` function to update
- [Source: docs/bmad_output/implementation-artifacts/3-1-ai-tool-primitive-tools-ai-ask.md#Dev Notes] — ToolRegistry construction pattern, import ordering after sys.path injection, lazy SDK import pattern

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Implemented `PopupTool` in `nimble/tools/popup.py` using lazy plyer import + try/except pattern matching `notifier.py`.
- Added `popup: PopupTool` field to `ToolRegistry` dataclass; updated `worker/entrypoint.py` `_build_tools()` to pass `popup=PopupTool()`.
- No tests directly constructed `ToolRegistry` in existing test suite, so no existing test breakage.
- 4 unit tests added covering: normal call, empty string, plyer runtime failure, plyer import failure.
- All quality gates pass: 139 tests (139 pass), mypy clean (pre-existing test_platform.py errors excluded), black OK, flake8 OK.

### File List

nimble/tools/popup.py
nimble/tools/__init__.py
worker/entrypoint.py
tests/unit/tools/test_popup.py

## Change Log

- 2026-04-25: Implemented PopupTool primitive — created popup.py, extended ToolRegistry with popup field, wired into worker entrypoint, added 4 unit tests; all 139 tests pass, all quality gates green.
