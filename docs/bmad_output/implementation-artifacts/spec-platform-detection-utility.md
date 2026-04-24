---
title: 'Platform Detection Utility'
type: 'refactor'
created: '2026-04-24'
status: 'done'
baseline_commit: '9d44f91d50b64b2e4550bf26a7ea0976922fed20'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `sys.platform` string comparisons are scattered across 4 production modules (`hotkeys/__init__.py`, `context/assembler.py`, `cli/commands.py`, `skills/runner.py`), making platform logic hard to grep, hard to mock in tests, and easy to get wrong (e.g. `"win32"` vs `"windows"`).

**Approach:** Introduce `nimble/platform.py` with three boolean helpers — `is_windows()`, `is_linux()`, `is_mac()` — and replace all production `sys.platform` comparisons with calls to these helpers.

## Boundaries & Constraints

**Always:**
- Functions are pure stateless wrappers over `sys.platform` — no caching, no side effects.
- Module follows existing project conventions: `from __future__ import annotations`, module-level logger, full type annotations, `mypy --strict` clean.
- All existing tests must continue to pass without modification.
- No new runtime dependencies.

**Ask First:**
- If a future caller needs a platform not covered by the three helpers (e.g. `is_mac()`), halt and ask before adding it.

**Never:**
- Do not rename or restructure the `nimble/hotkeys/` factory — only replace the `sys.platform` literals inside it.
- Do not add business logic to `platform.py` (e.g. path helpers, binary name selection). Those stay in their callers.
- Do not modify `tests/unit/skills/test_runner.py` — its `sys.platform` guard is a conditional assertion in test code, not production logic.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output | Error Handling |
|----------|--------------|-----------------|----------------|
| Running on Linux | `sys.platform == "linux"` | `is_linux()=True`, `is_windows()=False`, `is_mac()=False` | N/A |
| Running on Windows | `sys.platform == "win32"` | `is_windows()=True`, `is_linux()=False`, `is_mac()=False` | N/A |
| Running on macOS | `sys.platform == "darwin"` | `is_mac()=True`, `is_linux()=False`, `is_windows()=False` | N/A |

</frozen-after-approval>

## Code Map

- `nimble/platform.py` -- new module: `is_windows()`, `is_linux()`, `is_mac()` helpers
- `nimble/hotkeys/__init__.py` -- `get_adapter()` factory uses `sys.platform` × 3
- `nimble/context/assembler.py` -- `_get_selection/clipboard/active_app` each guard with `sys.platform != "linux"` × 3
- `nimble/cli/commands.py` -- `_terminate_windows` guard, binary name, `close_fds` all use `sys.platform == "win32"` × 3
- `nimble/skills/runner.py` -- `_get_python_executable` uses `sys.platform == "win32"` × 1
- `tests/unit/test_platform.py` -- new: unit tests for the three helpers

## Tasks & Acceptance

**Execution:**
- [x] `nimble/platform.py` -- create with `is_windows()`, `is_linux()`, `is_mac()` each returning a `bool` by comparing `sys.platform`
- [x] `tests/unit/test_platform.py` -- create tests for all three helpers by patching `sys.platform` (6 cases from I/O matrix)
- [x] `nimble/hotkeys/__init__.py` -- replace `sys.platform == "linux"` → `is_linux()`, `sys.platform == "win32"` → `is_windows()`, error message keeps `sys.platform` for diagnostics
- [x] `nimble/context/assembler.py` -- replace `sys.platform != "linux"` → `not is_linux()` in all three guard functions
- [x] `nimble/cli/commands.py` -- replace `sys.platform == "win32"` → `is_windows()` in `_terminate_windows`, `_do_start` binary name, `_do_start` `close_fds`
- [x] `nimble/skills/runner.py` -- replace `sys.platform == "win32"` → `is_windows()` in `_get_python_executable`

**Acceptance Criteria:**
- Given any production module that previously used `sys.platform`, when the module is imported, then `sys.platform` is no longer referenced directly in its source (grep confirms zero hits in changed files, excluding diagnostic strings).
- Given `is_windows()` / `is_linux()` / `is_mac()` are patched in a test, when production code is called, then it branches correctly based on the patched value.
- Given the full test suite is run, when no changes are made to test files other than adding `test_platform.py`, then all tests pass.

## Design Notes

```python
# nimble/platform.py
from __future__ import annotations
import sys

def is_windows() -> bool:
    return sys.platform == "win32"

def is_linux() -> bool:
    return sys.platform == "linux"

def is_mac() -> bool:
    return sys.platform == "darwin"
```

The error diagnostic in `hotkeys/__init__.py` (`raise RuntimeError(f"Unsupported platform: {sys.platform}")`) intentionally keeps the raw `sys.platform` value for human-readable error messages — this is not a platform-branching check and should not be replaced.

## Verification

**Commands:**
- `grep -rn "sys.platform ==" nimble/hotkeys/ nimble/context/ nimble/cli/ nimble/skills/` -- expected: zero matches
- `pytest` -- expected: all tests pass
- `mypy nimble/ tests/ worker/` -- expected: no new errors in changed files
- `black --check nimble/ tests/` -- expected: exits 0
- `flake8 nimble/ tests/` -- expected: exits 0

## Spec Change Log

## Suggested Review Order

**New module — entry point**

- Single source of truth for all platform checks; read this first.
  [`platform.py:1`](../../../nimble/platform.py#L1)

**Callers — highest-risk replacements**

- `get_adapter()` factory: Linux/Windows branches now use helpers; `sys.platform` kept in error message.
  [`hotkeys/__init__.py:4`](../../../nimble/hotkeys/__init__.py#L4)

- Community-skill Python executable path: Windows `Scripts/python.exe` vs Unix `bin/python`.
  [`runner.py:36`](../../../nimble/skills/runner.py#L36)

- `_do_stop` OS dispatch and `_do_start` binary name + `close_fds` flag.
  [`commands.py:40`](../../../nimble/cli/commands.py#L40)

**Context guards**

- Three early-return guards unified under `not is_linux()`; semantics identical to original.
  [`assembler.py:8`](../../../nimble/context/assembler.py#L8)

**Tests**

- Three parametric scenarios patch `platform_module.sys.platform` and verify mutual exclusivity.
  [`test_platform.py:1`](../../../tests/unit/test_platform.py#L1)
