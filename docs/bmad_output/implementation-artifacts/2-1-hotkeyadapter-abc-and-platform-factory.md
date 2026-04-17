# Story 2.1: HotkeyAdapter ABC and Platform Factory

Status: done

## Story

As a developer,
I want a platform factory in `nimble/hotkeys/__init__.py` that selects the correct `HotkeyAdapter` implementation at runtime,
So that the core daemon never contains platform-specific code and tests can always swap in the `FakeHotkeyAdapter`.

> **Note:** The `HotkeyAdapter` ABC (`nimble/hotkeys/base.py`) was already created in Story 1.2. This story's job is the **platform factory** and the **stub adapter classes** that satisfy the ABC, leaving the actual pynput/pywin32 implementations to Stories 2.2 and 2.3.

## Acceptance Criteria

1. **Given** `nimble/hotkeys/base.py` exists with the `HotkeyAdapter` ABC
   **When** mypy checks the full `nimble/` package
   **Then** all hotkeys modules pass `--strict` with zero errors

2. **Given** `nimble/hotkeys/__init__.py` exposes `get_adapter() -> HotkeyAdapter`
   **When** called on Linux (`sys.platform == "linux"`)
   **Then** returns an instance of `X11HotkeyAdapter`
   **When** called on Windows (`sys.platform == "win32"`)
   **Then** returns an instance of `WindowsHotkeyAdapter`
   **When** called on any other platform
   **Then** raises `RuntimeError` with a message identifying the unsupported platform

3. **Given** `FakeHotkeyAdapter` from `tests/unit/hotkeys/fake_adapter.py` is substituted for the real adapter
   **When** `register("ctrl+shift+d", callback)` is called
   **Then** `"ctrl+shift+d"` appears in `fake_adapter.registered` and no real OS API is invoked

## Tasks / Subtasks

- [x] Task 1: Add `get_adapter()` factory to `nimble/hotkeys/__init__.py` (AC: 2)
  - [x] Use lazy imports inside the function body — do NOT import `x11` or `windows` at module level
  - [x] `if sys.platform == "linux":` → lazy import `X11HotkeyAdapter`, return instance
  - [x] `elif sys.platform == "win32":` → lazy import `WindowsHotkeyAdapter`, return instance
  - [x] `else:` → `raise RuntimeError(f"Unsupported platform: {sys.platform}")`
  - [x] Return type annotation: `-> HotkeyAdapter`

- [x] Task 2: Create `nimble/hotkeys/x11.py` — stub `X11HotkeyAdapter` (AC: 1, 2)
  - [x] Import `HotkeyAdapter` from `nimble.hotkeys.base` (absolute import)
  - [x] Import `Callable` from `collections.abc`
  - [x] Implement all three ABC methods with correct annotations
  - [x] Each method body: `raise NotImplementedError("Implemented in Story 2.2")`
  - [x] **Do NOT import pynput** — pynput imports belong in Story 2.2 only

- [x] Task 3: Create `nimble/hotkeys/windows.py` — stub `WindowsHotkeyAdapter` (AC: 1, 2)
  - [x] Same structure as x11.py stub
  - [x] **Do NOT import pywin32 or pynput** — pywin32 imports belong in Story 2.3 only

- [x] Task 4: Write unit tests (AC: 1, 2, 3)
  - [x] `tests/unit/hotkeys/test_factory.py` — factory tests with monkeypatched `sys.platform`
  - [x] `tests/unit/hotkeys/test_base.py` — ABC enforcement test
  - [x] Verify CI still passes: `pytest || [ $? -eq 5 ]` exits 0

- [x] Task 5: Verify all AC locally
  - [x] `mypy nimble/` — exits 0, no issues in any hotkeys module
  - [x] `pytest` — all tests pass (or exits 5 if only new test files with no tests)
  - [x] `black --check nimble/ tests/` — exits 0
  - [x] `flake8 nimble/ tests/` — exits 0

## Dev Notes

### What Already Exists from Story 1.2

Do NOT recreate these:

| File | Content | Status |
|---|---|---|
| `nimble/hotkeys/base.py` | `HotkeyAdapter` ABC with `register`, `start`, `stop` | ✅ Complete |
| `nimble/hotkeys/__init__.py` | Empty — explicitly left empty for this story | ✅ Exists, needs factory added |
| `tests/unit/hotkeys/fake_adapter.py` | `FakeHotkeyAdapter` implementing the ABC | ✅ Complete |
| `tests/unit/hotkeys/__init__.py` | Empty pytest discovery init | ✅ Complete |
| `tests/conftest.py` | `fake_adapter`, `tmp_config`, `fake_notifier` fixtures | ✅ Complete |

### `nimble/hotkeys/__init__.py` — Required Content

```python
import sys

from nimble.hotkeys.base import HotkeyAdapter


def get_adapter() -> HotkeyAdapter:
    if sys.platform == "linux":
        from nimble.hotkeys.x11 import X11HotkeyAdapter

        return X11HotkeyAdapter()
    elif sys.platform == "win32":
        from nimble.hotkeys.windows import WindowsHotkeyAdapter

        return WindowsHotkeyAdapter()
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
```

**Why lazy imports:** `x11.py` will import pynput in Story 2.2. If pynput is imported at module level in `__init__.py`, the CI (headless `ubuntu-latest`) will fail when `nimble.hotkeys` is imported by any test. Lazy imports mean pynput is only loaded when `get_adapter()` is actually called on Linux — which never happens in the CI test suite. This pattern is established here and must not be changed in Story 2.2.

**`mypy --strict` note:** mypy accepts imports inside function bodies. No `TYPE_CHECKING` guard needed.

**flake8 note:** Imports inside function bodies do not trigger any flake8 errors. `E402` only applies to module-level imports not at top of file.

### `nimble/hotkeys/x11.py` — Required Content (Stub)

```python
from collections.abc import Callable

from nimble.hotkeys.base import HotkeyAdapter


class X11HotkeyAdapter(HotkeyAdapter):
    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        raise NotImplementedError("Implemented in Story 2.2")

    def start(self) -> None:
        raise NotImplementedError("Implemented in Story 2.2")

    def stop(self) -> None:
        raise NotImplementedError("Implemented in Story 2.2")
```

**Critical:** Do NOT add `import pynput` or any pynput reference. Story 2.2 replaces these method bodies with the actual pynput implementation.

### `nimble/hotkeys/windows.py` — Required Content (Stub)

```python
from collections.abc import Callable

from nimble.hotkeys.base import HotkeyAdapter


class WindowsHotkeyAdapter(HotkeyAdapter):
    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        raise NotImplementedError("Implemented in Story 2.3")

    def start(self) -> None:
        raise NotImplementedError("Implemented in Story 2.3")

    def stop(self) -> None:
        raise NotImplementedError("Implemented in Story 2.3")
```

### `tests/unit/hotkeys/test_factory.py` — Required Content

```python
import sys
from unittest.mock import patch

import pytest

from nimble.hotkeys import get_adapter
from nimble.hotkeys.windows import WindowsHotkeyAdapter
from nimble.hotkeys.x11 import X11HotkeyAdapter


def test_get_adapter_returns_x11_on_linux() -> None:
    with patch.object(sys, "platform", "linux"):
        adapter = get_adapter()
    assert isinstance(adapter, X11HotkeyAdapter)


def test_get_adapter_returns_windows_on_win32() -> None:
    with patch.object(sys, "platform", "win32"):
        adapter = get_adapter()
    assert isinstance(adapter, WindowsHotkeyAdapter)


def test_get_adapter_raises_on_unsupported_platform() -> None:
    with patch.object(sys, "platform", "darwin"):
        with pytest.raises(RuntimeError, match="Unsupported platform: darwin"):
            get_adapter()
```

**Note:** These imports are safe on any platform because the stub files (`x11.py`, `windows.py`) do not import pynput or pywin32. Only `get_adapter()` at runtime (never called in CI tests) would trigger the lazy imports.

### `tests/unit/hotkeys/test_base.py` — Required Content

```python
import pytest

from nimble.hotkeys.base import HotkeyAdapter


def test_hotkeyAdapter_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        HotkeyAdapter()  # type: ignore[abstract]
```

### Architecture Guardrails

| Rule | Enforcement |
|---|---|
| Platform-specific code stays in `x11.py` / `windows.py`, never in `daemon.py` or `__init__.py` | Architecture Boundary 4 |
| `daemon.py` calls only `get_adapter()` — never imports `x11` or `windows` directly | Architecture Boundary 4 |
| Lazy imports in `get_adapter()` — must not be changed to module-level | CI safety for headless Linux |
| `collections.abc.Callable`, not `typing.Callable` | mypy --strict preference (established in 1.2) |
| All parameters and return types annotated | mypy --strict |
| Absolute imports only | flake8 + architecture rule |

### File Structure This Story Creates

```
nimble/hotkeys/
    __init__.py      ← add get_adapter() factory (was empty)
    base.py          ← HotkeyAdapter ABC (already exists, do not modify)
    x11.py           ← X11HotkeyAdapter stub (new)
    windows.py       ← WindowsHotkeyAdapter stub (new)

tests/unit/hotkeys/
    __init__.py          ← already exists
    fake_adapter.py      ← FakeHotkeyAdapter (already exists, do not modify)
    test_base.py         ← new — ABC instantiation test
    test_factory.py      ← new — factory platform selection tests
```

### Architecture Doc Inconsistency (Known — Do Not Follow the Diagram)

The architecture doc Module Structure diagram shows `nimble.yaml` at the repo root. Everywhere else (and in the actual codebase from Story 1.1) the file is named `config.yaml`. Use `config.yaml`. This story does not touch config files but future stories in Epic 2 do.

### Cross-Story Context

- **Story 1.2** created `nimble/hotkeys/base.py` and `tests/unit/hotkeys/fake_adapter.py` — those files are complete and must not be modified
- **Story 2.2** replaces `X11HotkeyAdapter` method bodies with real pynput listener implementation — do not pre-empt this
- **Story 2.3** replaces `WindowsHotkeyAdapter` method bodies with real pywin32 implementation — do not pre-empt this
- **Story 2.8** creates `nimble/daemon.py` which calls `get_adapter()` — the factory interface established here is the contract it will use

### CI Note

The existing `pytest || [ $? -eq 5 ]` pattern in `.github/workflows/ci.yml` handles pytest exit code 5 (no tests collected). After this story, real tests exist, so pytest should exit 0. Verify locally before pushing.

### Deferred Concern from Story 1.1 / Retrospective

The pynput headless CI concern is **resolved by the lazy import pattern** in the factory. When CI runs tests, `get_adapter()` is never called (tests use `FakeHotkeyAdapter` via the fixture). Therefore pynput is never imported on headless Linux. Story 2.2's x11.py adds the real pynput implementation but does not affect this guard.

### References

- `HotkeyAdapter` ABC: `nimble/hotkeys/base.py` (Story 1.2)
- `FakeHotkeyAdapter`: `tests/unit/hotkeys/fake_adapter.py` (Story 1.2)
- Factory pattern: `docs/bmad_output/planning-artifacts/architecture.md` § Repository Module Structure
- Lazy import rationale: `docs/bmad_output/implementation-artifacts/deferred-work.md` (pynput headless CI item)
- Architecture Boundary 4: `docs/bmad_output/planning-artifacts/architecture.md` § Architectural Boundaries

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation was straightforward following Dev Notes specifications.

### Completion Notes List

- Implemented `get_adapter()` factory with lazy imports in `nimble/hotkeys/__init__.py`
- Created stub `X11HotkeyAdapter` in `nimble/hotkeys/x11.py` (no pynput imports)
- Created stub `WindowsHotkeyAdapter` in `nimble/hotkeys/windows.py` (no pywin32 imports)
- Added `tests/unit/hotkeys/test_factory.py` with 3 tests (linux/win32/unsupported platform)
- Added `tests/unit/hotkeys/test_base.py` with 1 ABC instantiation enforcement test
- All 4 tests pass; mypy --strict, black, flake8 all clean

### File List

- `nimble/hotkeys/__init__.py` (modified — added `get_adapter()` factory)
- `nimble/hotkeys/x11.py` (new — `X11HotkeyAdapter` stub)
- `nimble/hotkeys/windows.py` (new — `WindowsHotkeyAdapter` stub)
- `tests/unit/hotkeys/test_factory.py` (new — factory platform selection tests)
- `tests/unit/hotkeys/test_base.py` (new — ABC instantiation enforcement test)
- `tests/unit/hotkeys/test_fake_adapter.py` (new — AC3 `FakeHotkeyAdapter.register` records shortcut)

### Review Findings

- [x] [Review][Patch] No unit test covers acceptance criterion 3 (FakeHotkeyAdapter `register` records shortcut, no OS API) — resolved: `tests/unit/hotkeys/test_fake_adapter.py` added in code review follow-up.

## Change Log

- 2026-04-17: Story created by bmad-create-story workflow
- 2026-04-17: Implementation complete by claude-sonnet-4-6 — platform factory and stub adapters created, 4 tests added, all validations pass
- 2026-04-17: Code review — AC3 unit test added (`test_fake_adapter.py`); story marked done
