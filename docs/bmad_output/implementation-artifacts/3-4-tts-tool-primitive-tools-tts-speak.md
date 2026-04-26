# Story 3.4: TTS Tool Primitive (`tools.tts.speak`)

Status: done

## Story

As a skill author,
I want to call `tools.tts.speak(text)` to have the system read text aloud,
so that I can build hands-free skills that deliver output via audio.

## Acceptance Criteria

1. **Given** `tools.tts.speak("Processing complete")` is called
   **When** the skill runs on Linux
   **Then** the system TTS engine speaks the text aloud

2. **When** the skill runs on Windows
   **Then** the system TTS engine (SAPI) speaks the text aloud

3. **Given** TTS is unavailable on the system
   **When** `tools.tts.speak()` is called
   **Then** a `RuntimeError` is raised with a clear message — not a silent no-op

## Tasks / Subtasks

- [x] Task 1: Create `nimble/tools/tts.py` with `TtsTool` class (AC: 1, 2, 3)
  - [x] Add `from __future__ import annotations` at top
  - [x] Add `import logging` and `logger = logging.getLogger(__name__)` at module level
  - [x] Define `class TtsTool` with no constructor arguments
  - [x] Implement `speak(self, text: str) -> None`:
    - Lazy import: `from plyer import tts as plyer_tts`
    - Call `plyer_tts.speak(text)`
    - Wrap in `try/except Exception as exc` — on failure re-raise as `RuntimeError(f"TTS is not available: {exc}")` from exc
    - **Critical:** Do NOT swallow the exception — AC3 requires RuntimeError to propagate
  - [x] Full `mypy --strict` compliance — all params and return types annotated

- [x] Task 2: Update `nimble/tools/__init__.py` to add `tts` field to `ToolRegistry` (AC: 1, 2, 3)
  - [x] Add `from nimble.tools.tts import TtsTool` import (after `ClipboardTool` import)
  - [x] Add `tts: TtsTool` field to `ToolRegistry` dataclass (after `clipboard: ClipboardTool`)
  - [x] Do NOT add stub fields for story 3.5 (input) — comes in next story

- [x] Task 3: Update `worker/entrypoint.py` to instantiate `TtsTool` in `_build_tools()` (AC: 1, 2)
  - [x] Add `from nimble.tools.tts import TtsTool` import after existing clipboard import (line 24)
  - [x] Update `_build_tools()` return — wrapped multi-line for black compliance (89-char line split)
  - [x] No other changes to `entrypoint.py`

- [x] Task 4: Add `tests/unit/tools/test_tts.py` (AC: 1, 2, 3)
  - [x] `test_speak_calls_plyer_tts_speak()` — mock plyer.tts, call `speak("hello")`, assert `tts.speak` called with `"hello"`
  - [x] `test_speak_raises_runtime_error_when_tts_fails()` — mock plyer.tts.speak to raise `RuntimeError("espeak not found")`, assert `RuntimeError` propagates and message contains `"TTS is not available"`
  - [x] `test_speak_raises_runtime_error_on_import_failure()` — `patch.dict("sys.modules", {"plyer": None})`, assert calling `speak("x")` raises `RuntimeError`
  - [x] `test_speak_error_message_is_descriptive()` — mock plyer.tts.speak to raise `Exception("espeak not found")`, assert caught `RuntimeError` message starts with `"TTS is not available:"`
  - [x] `test_speak_raises_not_logs_warning()` — confirm that calling `speak()` when TTS fails raises RuntimeError rather than returning silently (distinct from clipboard behaviour)

- [x] Task 5: Verify quality gates (AC: all)
  - [x] `mypy nimble/ tests/ worker/` — exits 0 on new files; 7 pre-existing errors in test_platform.py, watcher.py, manifest/parser.py, tools/ai.py unchanged
  - [x] `python3 -m pytest` — 146 passed (141 pre-existing + 5 new TTS tests); 2 pre-existing collection errors unrelated to this story
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0

## Dev Notes

### Role in the Daemon Architecture

```
hotkey fires
  → runner.py dispatches JSON payload to worker stdin
  → worker/entrypoint.py calls _build_tools()
  → _build_tools() constructs ToolRegistry(ai=..., popup=..., clipboard=..., tts=TtsTool())
  → skill.run(context, tools)
  → tools.tts.speak("text")    ← invokes system TTS engine
```

`TtsTool` is the fourth tool primitive in the registry. It lives at `nimble/tools/tts.py` (already defined in architecture's repository structure).

### Critical: Error Handling Differs from Clipboard and Popup

This is the key distinction that makes TTS implementation different from prior tools:

| Tool | On failure | Rationale |
|---|---|---|
| `popup.show()` | Swallow, log warning | Popup failure shouldn't crash skill |
| `clipboard.get()` | Swallow, return `""` | Empty string is a valid fallback |
| `clipboard.set()` | Swallow, log warning | Write failure shouldn't crash skill |
| **`tts.speak()`** | **Re-raise as RuntimeError** | AC3 explicitly requires this — skill author must know TTS failed |

The skill author is responsible for checking TTS availability or handling the RuntimeError. A silent no-op would be misleading in hands-free workflows.

### Complete Implementation: `nimble/tools/tts.py`

```python
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class TtsTool:
    def speak(self, text: str) -> None:
        try:
            from plyer import tts as plyer_tts

            plyer_tts.speak(text)
        except Exception as exc:
            raise RuntimeError(f"TTS is not available: {exc}") from exc
```

**Lazy import rationale:** mirrors `popup.py` and `clipboard.py` exactly — plyer is available in author skill workers (use `sys.executable`, the daemon's Python). Community skill workers run in isolated venvs without plyer. The lazy import allows graceful handling in any venv context.

**`plyer.tts.speak()` behaviour:**
- Linux: delegates to `espeak` or `espeak-ng` subprocess — must be installed as a system binary
- Windows: uses SAPI (built-in, always available on Windows)
- macOS: uses `say` subprocess (built-in)
- If the underlying system binary is absent, plyer raises an exception — which we convert to `RuntimeError`

**No logger.warning:** Unlike clipboard, TTS failure re-raises so no warning log is needed — the exception itself is the signal.

### Updated `nimble/tools/__init__.py`

Current state (after Story 3.3):
```python
from __future__ import annotations

from dataclasses import dataclass

from nimble.tools.ai import AiTool
from nimble.tools.clipboard import ClipboardTool
from nimble.tools.popup import PopupTool


@dataclass
class ToolRegistry:
    ai: AiTool
    popup: PopupTool
    clipboard: ClipboardTool
```

Target state (after Story 3.4):
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

### Updated `worker/entrypoint.py` — `_build_tools()`

Add import after line 24 (`from nimble.tools.clipboard import ClipboardTool`):
```python
from nimble.tools.tts import TtsTool  # noqa: E402
```

Change the return statement at lines 91–93:
```python
return ToolRegistry(
    ai=AiTool(ai_config), popup=PopupTool(), clipboard=ClipboardTool(), tts=TtsTool()
)
```

No other changes to `entrypoint.py`.

### ToolRegistry Breakage Check

Before starting, run:
```bash
grep -r "ToolRegistry(" tests/ worker/ nimble/
```

Adding `tts: TtsTool` to the dataclass makes it a required positional arg. Only `worker/entrypoint.py::_build_tools()` constructs `ToolRegistry` directly (confirmed from Story 3.3 notes). Tests mock at module level, not via dataclass construction. Verify the grep result before assuming no other break sites.

### Test Pattern for `tests/unit/tools/test_tts.py`

Use `patch.dict("sys.modules", {"plyer": MagicMock(tts=mock_tts)})` — same pattern as clipboard tests (established because plyer 2.1.0 lacks direct attribute access; patching the module object is more reliable than `patch("plyer.tts.speak")`).

```python
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from nimble.tools.tts import TtsTool


def test_speak_calls_plyer_tts_speak() -> None:
    tool = TtsTool()
    mock_tts = MagicMock()
    with patch.dict("sys.modules", {"plyer": MagicMock(tts=mock_tts)}):
        tool.speak("hello")
    mock_tts.speak.assert_called_once_with("hello")


def test_speak_raises_runtime_error_when_tts_fails() -> None:
    tool = TtsTool()
    mock_tts = MagicMock()
    mock_tts.speak.side_effect = RuntimeError("espeak not found")
    with patch.dict("sys.modules", {"plyer": MagicMock(tts=mock_tts)}):
        with pytest.raises(RuntimeError, match="TTS is not available"):
            tool.speak("hello")


def test_speak_raises_runtime_error_on_import_failure() -> None:
    tool = TtsTool()
    with patch.dict("sys.modules", {"plyer": None}):
        with pytest.raises(RuntimeError):
            tool.speak("hello")


def test_speak_error_message_is_descriptive() -> None:
    tool = TtsTool()
    mock_tts = MagicMock()
    mock_tts.speak.side_effect = Exception("espeak not found")
    with patch.dict("sys.modules", {"plyer": MagicMock(tts=mock_tts)}):
        with pytest.raises(RuntimeError) as exc_info:
            tool.speak("hello")
    assert "TTS is not available:" in str(exc_info.value)


def test_speak_raises_not_returns_silently() -> None:
    # Confirms TTS does NOT swallow failure like clipboard does
    tool = TtsTool()
    mock_tts = MagicMock()
    mock_tts.speak.side_effect = OSError("no tts engine")
    with patch.dict("sys.modules", {"plyer": MagicMock(tts=mock_tts)}):
        with pytest.raises(RuntimeError):
            tool.speak("should fail loudly")
```

### Architecture Compliance

- `nimble/tools/tts.py` defined in architecture (`nimble/tools/` → FR17) — location is correct
- `tests/unit/tools/test_tts.py` follows mirror structure established in Stories 3.1–3.3
- `mypy --strict` across `nimble/`, `tests/`, `worker/`
- Absolute imports: `from nimble.tools.tts import TtsTool` — never relative
- `@dataclass` for `ToolRegistry` — just add `tts: TtsTool` field after `clipboard`
- Lazy import in `tts.py` — consistent with `popup.py` and `clipboard.py` pattern
- No new `pyproject.toml` dependencies — plyer is already a core dep
- `from __future__ import annotations` at top of `tts.py`

### New Files

```
nimble/tools/tts.py                ← TtsTool class
tests/unit/tools/test_tts.py       ← 5 unit tests
```

### Modified Files

```
nimble/tools/__init__.py           ← add TtsTool import + tts field to ToolRegistry
worker/entrypoint.py               ← add TtsTool import; update _build_tools() return value
```

No changes to: `nimble/manifest/parser.py`, `nimble/skills/runner.py`, `nimble/daemon.py`, `config.yaml`, `pyproject.toml`

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 3.4] — acceptance criteria, FR17
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Repository Module Structure] — `nimble/tools/tts.py` placement, `tests/unit/tools/test_tts.py`
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, type annotations, absolute imports, test mirroring rules
- [Source: nimble/tools/popup.py] — lazy import pattern to follow
- [Source: nimble/tools/clipboard.py] — lazy import pattern; note error handling DIFFERS (tts re-raises, clipboard swallows)
- [Source: nimble/tools/__init__.py] — current ToolRegistry structure to extend (add tts after clipboard)
- [Source: worker/entrypoint.py:91–93] — existing `_build_tools()` return statement to update
- [Source: docs/bmad_output/implementation-artifacts/3-3-clipboard-tool-primitives-tools-clipboard-get-tools-clipboard-set.md#Dev Notes] — ToolRegistry extension pattern, `patch.dict` test approach for plyer-based tools

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `_build_tools()` return statement was initially 89 chars (1 over the 88-char limit). Split to multi-line form to satisfy black and flake8.

### Completion Notes List

- Implemented `TtsTool` in `nimble/tools/tts.py` with lazy plyer import and re-raise as `RuntimeError` on failure (distinct from clipboard's swallow-and-log pattern — AC3 requires failure to propagate).
- Added `TtsTool` import and `tts: TtsTool` field to `ToolRegistry` dataclass in `nimble/tools/__init__.py`.
- Updated `worker/entrypoint.py` `_build_tools()` to construct `TtsTool()` and pass it into `ToolRegistry`; split return to multi-line for black compliance.
- Added 5 unit tests in `tests/unit/tools/test_tts.py` using `patch.dict` sys.modules mocking (same pattern as clipboard tests for plyer 2.1.0 compatibility).
- All 146 tests pass; mypy/black/flake8 clean on all changed files; no regressions.

### File List

- nimble/tools/tts.py (new)
- tests/unit/tools/test_tts.py (new)
- nimble/tools/__init__.py (modified)
- worker/entrypoint.py (modified)

## Change Log

- 2026-04-26: Implemented TtsTool with lazy plyer import and RuntimeError propagation on failure; wired into ToolRegistry and worker entrypoint; added 5 unit tests; all quality gates pass (146 tests, mypy/black/flake8 clean).
