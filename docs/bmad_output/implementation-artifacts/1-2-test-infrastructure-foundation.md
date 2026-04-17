# Story 1.2: Test Infrastructure Foundation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer writing tests,
I want shared test fixtures and a `FakeHotkeyAdapter` available from day one,
So that all unit tests can use the fake adapter and common fixtures without real OS APIs or duplicated setup code.

## Acceptance Criteria

1. **Given** `tests/unit/hotkeys/fake_adapter.py` exists
   **When** a test imports `FakeHotkeyAdapter`
   **Then** it implements the `HotkeyAdapter` ABC with `register(shortcut, callback)`, `start()`, and `stop()` methods and tracks registered shortcuts in a `registered: list[str]` attribute

2. **Given** `tests/conftest.py` exists
   **When** any test module in the `tests/` tree is collected by pytest
   **Then** the `fake_adapter`, `tmp_config`, and `fake_notifier` fixtures are available without any per-module imports

3. **Given** `tmp_config` fixture is used in a test
   **When** the fixture is requested
   **Then** it creates a temporary `config.yaml` at `tmp_path / "config.yaml"` pre-populated with `skills: []\nbindings: []\n`

4. **Given** the `nimble/hotkeys/base.py` module exists
   **When** mypy checks the file
   **Then** `HotkeyAdapter` is defined as an abstract base class with all methods annotated and passing `--strict`

## Tasks / Subtasks

- [x] Task 1: Create `nimble/hotkeys/base.py` — HotkeyAdapter ABC (AC: 4)
  - [x] Import `abc` and `collections.abc.Callable` (not `typing.Callable` — use stdlib directly)
  - [x] Define `HotkeyAdapter(abc.ABC)` with three `@abc.abstractmethod` methods, all annotated
  - [x] `register(self, shortcut: str, callback: Callable[[], None]) -> None`
  - [x] `start(self) -> None`
  - [x] `stop(self) -> None`
  - [x] Verify `mypy nimble/` exits 0

- [x] Task 2: Create `nimble/hotkeys/__init__.py` — empty package init
  - [x] File must be empty (platform factory added in Story 2.1 — do NOT add any factory here)
  - [x] Do NOT import pynput or any OS API here or in base.py

- [x] Task 3: Create `tests/unit/hotkeys/__init__.py` — empty (AC: 1)
  - [x] Enables pytest discovery of the `tests/unit/hotkeys/` directory

- [x] Task 4: Create `tests/unit/hotkeys/fake_adapter.py` — FakeHotkeyAdapter (AC: 1)
  - [x] Import `HotkeyAdapter` from `nimble.hotkeys.base` (absolute import)
  - [x] Implement all three ABC methods with correct annotations
  - [x] `__init__` sets `self.registered: list[str] = []`
  - [x] `register` appends `shortcut` to `self.registered` — no real OS API
  - [x] `start` and `stop` are no-ops (`pass`) — no real OS API

- [x] Task 5: Create `tests/conftest.py` — shared fixtures (AC: 2, 3)
  - [x] `fake_adapter` fixture returns a fresh `FakeHotkeyAdapter` instance
  - [x] `tmp_config` fixture creates `tmp_path / "config.yaml"` with `"skills: []\nbindings: []\n"`
  - [x] `fake_notifier` fixture returns a fresh `FakeNotifier` instance (see Dev Notes)
  - [x] All fixtures annotated with return types (mypy --strict)
  - [x] All imports are absolute

- [x] Task 6: Verify all AC with local commands
  - [x] `mypy nimble/` — exits 0, no issues
  - [x] `pytest` — exits with code 5 (no tests collected) or 0 — zero failures, zero errors
  - [x] `black --check nimble/ tests/` — exits 0
  - [x] `flake8 nimble/ tests/` — exits 0

### Review Findings

- [x] [Review][Patch] Task 4 import target is incorrect in story text (`FakeHotkeyAdapter` is said to come from `nimble.hotkeys.base`, but that module defines `HotkeyAdapter`) [docs/bmad_output/implementation-artifacts/1-2-test-infrastructure-foundation.md:49]

## Dev Notes

### Files This Story Creates

```
nimble/hotkeys/
    __init__.py              ← empty package init (platform factory in Story 2.1)
    base.py                  ← HotkeyAdapter ABC

tests/
    conftest.py              ← fake_adapter, tmp_config, fake_notifier fixtures
    unit/hotkeys/
        __init__.py          ← empty (pytest discovery)
        fake_adapter.py      ← FakeHotkeyAdapter implementation
```

**Not created in this story:**
- `nimble/hotkeys/x11.py` — Story 2.2
- `nimble/hotkeys/windows.py` — Story 2.3
- Any factory in `nimble/hotkeys/__init__.py` — Story 2.1
- `nimble/notifier.py` (real implementation) — Story 4.1

### `nimble/hotkeys/base.py` — Exact Required Content

```python
import abc
from collections.abc import Callable


class HotkeyAdapter(abc.ABC):
    @abc.abstractmethod
    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        """Register a global hotkey that invokes callback when pressed."""

    @abc.abstractmethod
    def start(self) -> None:
        """Start the hotkey listener."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the hotkey listener and clean up resources."""
```

**Critical — import from `collections.abc`, NOT `typing`:**
- Python 3.10+: `collections.abc.Callable` is the canonical location
- `typing.Callable` still works but is deprecated; mypy --strict prefers `collections.abc`
- Do NOT import pynput here; base.py must be importable in any environment, including headless CI

### `tests/unit/hotkeys/fake_adapter.py` — Exact Required Content

```python
from collections.abc import Callable

from nimble.hotkeys.base import HotkeyAdapter


class FakeHotkeyAdapter(HotkeyAdapter):
    def __init__(self) -> None:
        self.registered: list[str] = []

    def register(self, shortcut: str, callback: Callable[[], None]) -> None:
        self.registered.append(shortcut)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
```

**Notes:**
- `callback` parameter must be accepted but never called — FakeHotkeyAdapter records registrations only
- `start()` and `stop()` are intentional no-ops — no OS API invoked
- Absolute imports only — `from nimble.hotkeys.base import HotkeyAdapter`

### `tests/conftest.py` — Required Content

```python
from pathlib import Path

import pytest

from tests.unit.hotkeys.fake_adapter import FakeHotkeyAdapter


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, title: str, body: str) -> None:
        self.sent.append((title, body))


@pytest.fixture
def fake_adapter() -> FakeHotkeyAdapter:
    return FakeHotkeyAdapter()


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text("skills: []\nbindings: []\n")
    return config


@pytest.fixture
def fake_notifier() -> FakeNotifier:
    return FakeNotifier()
```

**Notes:**
- `FakeNotifier` is defined inline in conftest (not a separate file) — no dedicated path in architecture
- `FakeNotifier.send(title, body)` tracks sent notifications for test assertions
- `fake_notifier` return type annotation `FakeNotifier` requires the class to be visible at module level — define it above the fixtures
- All functions are fully annotated for mypy --strict

### Architecture Guardrails

| Rule | Where enforced |
|---|---|
| `mypy --strict` across all `nimble/` code | Configured in `pyproject.toml [tool.mypy]` |
| Absolute imports only — no relative imports | flake8 + code review |
| snake_case for all Python identifiers | black + flake8 |
| `collections.abc.Callable`, not `typing.Callable` | mypy --strict (deprecation warning) |
| No platform-specific code in `nimble/hotkeys/base.py` | Review — base.py must be CI-safe |
| `FakeHotkeyAdapter` never invokes real OS APIs | Review |

### Why `nimble/hotkeys/__init__.py` Must Stay Empty

Story 2.1 adds the platform factory (`get_adapter() -> HotkeyAdapter`) to `nimble/hotkeys/__init__.py`. Creating anything there now would conflict with Story 2.1. Leave the file empty — its only purpose this story is to make `nimble.hotkeys` a Python package so `from nimble.hotkeys.base import HotkeyAdapter` resolves correctly.

### pytest Exit Code 5 — Expected Behaviour

As noted in Story 1.1 review, pytest exits with code 5 when no tests are collected. This is still the expected outcome after Story 1.2 — no test files (`test_*.py`) are created in this story. The exit code 5 resolves when Story 1.3 and beyond add actual tests.

### Cross-Story Context

- **Story 1.1** created `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py` — these already exist, do NOT recreate
- **Story 2.1** adds `get_adapter()` factory and `nimble/hotkeys/__init__.py` imports — leave `__init__.py` empty here
- **Story 4.1** creates the real `nimble/notifier.py` — `FakeNotifier` in conftest is the test double for that module
- The `FakeHotkeyAdapter` established here is used by every story that tests hotkey-related code (2.1–2.9, 4.x)

### pynput and Headless CI (Deferred Concern)

From Story 1.1 deferred work: `pynput` raises `ImportError` on headless Linux without `DISPLAY`. `nimble/hotkeys/base.py` MUST NOT import pynput — it is a pure ABC with stdlib imports only. The concrete adapters (`x11.py`, `windows.py`) will import pynput; those are guarded by the platform factory in Story 2.1. This story is safe.

### References

- `HotkeyAdapter` ABC spec: [Source: docs/bmad_output/planning-artifacts/epics.md#Story 1.2]
- Test patterns and `FakeHotkeyAdapter` structure: [Source: docs/bmad_output/planning-artifacts/architecture.md#Test Patterns]
- Conftest fixtures pattern: [Source: docs/bmad_output/planning-artifacts/architecture.md#Test Patterns]
- Import rules (absolute only): [Source: docs/bmad_output/planning-artifacts/architecture.md#Import Patterns]
- Full project directory structure: [Source: docs/bmad_output/planning-artifacts/architecture.md#Complete Project Directory Structure]
- pynput headless issue: [Source: docs/bmad_output/implementation-artifacts/deferred-work.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- Created `nimble/hotkeys/base.py` with `HotkeyAdapter` ABC using `collections.abc.Callable` and stdlib `abc` — passes `mypy --strict`.
- Created empty `nimble/hotkeys/__init__.py` to make `nimble.hotkeys` a Python package (factory deferred to Story 2.1).
- Created empty `tests/unit/hotkeys/__init__.py` to enable pytest discovery.
- Created `tests/unit/hotkeys/fake_adapter.py` with `FakeHotkeyAdapter` — records registrations in `self.registered`, no OS API calls.
- Created `tests/conftest.py` with `fake_adapter`, `tmp_config`, and `fake_notifier` fixtures; `FakeNotifier` defined inline.
- All validations pass: `mypy nimble/` exits 0, `pytest` exits 5 (no tests collected — expected), `black --check` exits 0, `flake8` exits 0.

### File List

- nimble/hotkeys/__init__.py
- nimble/hotkeys/base.py
- tests/conftest.py
- tests/unit/hotkeys/__init__.py
- tests/unit/hotkeys/fake_adapter.py

## Change Log

- 2026-04-17: Story 1.2 implemented — created HotkeyAdapter ABC, FakeHotkeyAdapter, and shared pytest fixtures.
