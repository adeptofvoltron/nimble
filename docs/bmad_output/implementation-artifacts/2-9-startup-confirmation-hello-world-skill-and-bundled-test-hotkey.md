# Story 2.9: Startup Confirmation, Hello World Skill, and Bundled Test Hotkey

Status: done

## Story

As a first-time user,
I want to see a confirmation notification and fire a test hotkey immediately after `nimble start`,
So that I know the daemon is running and responsive without having to write any skill code first.

## Acceptance Criteria

1. **Given** the daemon starts successfully
   **When** all skills are loaded and hotkeys are registered
   **Then** a system notification fires: title `"Nimble"`, body `"Nimble daemon running."` (FR41)

2. **Given** `skills/hello_world/skill.py` and `skills/hello_world/manifest.yaml` exist in the template
   **When** the template `config.yaml` is used unchanged
   **Then** `ctrl+shift+h` is pre-bound to the `hello_world` skill

3. **Given** the user presses `ctrl+shift+h` after `nimble start`
   **When** the hello_world skill executes
   **Then** a notification appears with title `"Nimble"` and body `"Hello from Nimble! The daemon is working."` — no user configuration required (FR45)

4. **Given** the `skills/` directory is tracked in the user's git fork
   **When** a user commits their skills
   **Then** `skills/hello_world/` is committed alongside any user-written skills (FR42)

## Tasks / Subtasks

- [x] Task 1: Create `skills/hello_world/skill.py` — HelloWorldSkill class (AC: 2, 3, 4)
  - [x] Create `skills/` directory at repo root (not gitignored — committed to fork, FR42)
  - [x] Create `skills/hello_world/` subdirectory
  - [x] Define class `HelloWorldSkill` with `run(self, context: object, tools: object) -> None`
  - [x] Inside `run()`, fire a plyer notification: `notification.notify(title="Nimble", message="Hello from Nimble! The daemon is working.", app_name="Nimble")`
  - [x] Import plyer lazily inside `run()` (same pattern as `nimble/notifier.py`) to prevent import-time failures on headless environments
  - [x] Add `from __future__ import annotations` at top of file
  - [x] No class-level type annotations required — `skills/` is not in the `nimble/` package and not under `mypy --strict`; however, type the method signature for clarity

- [x] Task 2: Create `skills/hello_world/manifest.yaml` — skill metadata (AC: 2, 4)
  - [x] `name: hello_world`
  - [x] `version: "1.0.0"`
  - [x] `api_version: 1`
  - [x] `description: "Bundled test skill — fires a notification to confirm the daemon is working"`
  - [x] `entrypoint: skill.py`
  - [x] `class_name: HelloWorldSkill`
  - [x] `permissions: []`
  - [x] `dependencies: []`
  - [x] `author: "Nimble Template"`

- [x] Task 3: Update `config.yaml` — add hello_world binding (AC: 2, 3)
  - [x] Replace `skills: []\nbindings: []` with a skills list entry for hello_world
  - [x] Required fields: `name: hello_world`, `source: local`, `path: skills/hello_world/skill.py`, `class_name: HelloWorldSkill`, `binding: "ctrl+shift+h"`
  - [x] Keep the file minimal and human-readable — it ships as the template config

- [x] Task 4: Update `nimble/daemon.py` — add startup notification (AC: 1)
  - [x] Add `notifier.send("Nimble", "Nimble daemon running.")` immediately after `write_pid(os.getpid())` and before `watcher = ConfigWatcher(...)` — at the point where adapter is started and all hotkeys are registered
  - [x] No other changes to `daemon.py` — only this one call is added
  - [x] The `Notifier` instance is already available as `notifier` in scope

- [x] Task 5: Create `tests/unit/test_daemon.py` — startup notification test (AC: 1)
  - [x] `test_startup_notification_fires(tmp_path, fake_notifier)`: patch `get_adapter` → `FakeHotkeyAdapter`, patch `load_config` → empty config, patch `validate_skill_paths` → `[]`, patch `SkillRunner.spawn_workers` → no-op, patch `write_pid`/`remove_pid` → no-op, patch `ConfigWatcher` → does not start, call `daemon.run(tmp_path)` in a thread with `stop_event` set immediately; assert `("Nimble", "Nimble daemon running.")` is in `fake_notifier.sent`
  - [x] `test_startup_notification_title_and_body(tmp_path, fake_notifier)`: same setup; assert `fake_notifier.sent[0] == ("Nimble", "Nimble daemon running.")`
  - [x] Use `FakeNotifier` from `tests/conftest.py` — do NOT instantiate a real `Notifier`

- [x] Task 6: Create `tests/unit/skills/test_hello_world.py` — HelloWorldSkill test (AC: 3)
  - [x] `test_hello_world_run_fires_notification(tmp_path)`: patch `plyer.notification.notify` via `unittest.mock.patch`; instantiate `HelloWorldSkill()`; call `skill.run(object(), None)`; assert `plyer.notification.notify` called with `title="Nimble"`, `message="Hello from Nimble! The daemon is working."`
  - [x] `test_hello_world_run_swallows_plyer_exception()`: patch notify to raise `Exception`; assert `skill.run(object(), None)` does not raise
  - [x] Mirror test path: `tests/unit/skills/test_hello_world.py` (file is in `skills/`, tests in `tests/unit/skills/` per architecture test pattern)

- [x] Task 7: Verify quality gates (AC: all)
  - [x] `mypy nimble/ tests/ worker/` — new `test_daemon.py` and `test_hello_world.py` must pass strict; `skills/` is NOT included in mypy scope
  - [x] `pytest` — all existing tests pass plus new tests
  - [x] `black --check nimble/ tests/ worker/` — exits 0
  - [x] `flake8 nimble/ tests/ worker/` — exits 0 (note: `skills/` is excluded from linting scope in this story; do not add it to CI scope)

## Dev Notes

### Role in the Daemon Architecture

Story 2.9 is the finishing touch on Epic 2. The daemon (Story 2.8) is already fully wired — `daemon.py` loads config, spawns workers, registers hotkeys, enters its main loop, and shuts down cleanly. This story adds exactly two observable behaviours:
1. A startup notification (one line added to `daemon.py`)
2. A pre-configured hello_world skill that fires when `ctrl+shift+h` is pressed

No structural changes are needed to `daemon.py`, `runner.py`, `registry.py`, `watcher.py`, or any test infrastructure.

### Critical: `tools = None` in Worker

**`worker/entrypoint.py` line 83:** `tools = None`

The `HelloWorldSkill.run(context, tools)` receives `tools=None`. **Do NOT call `tools.popup.show()` or any `tools.*` method.** The tools primitives (Epic 3) are not implemented yet. The hello_world skill must fire its notification using plyer directly, matching the same pattern as `nimble/notifier.py`.

Correct implementation:
```python
class HelloWorldSkill:
    def run(self, context: object, tools: object) -> None:
        try:
            from plyer import notification
            notification.notify(
                title="Nimble",
                message="Hello from Nimble! The daemon is working.",
                app_name="Nimble",
            )
        except Exception:
            pass
```

plyer is already declared in `pyproject.toml` dependencies and is always available for author skills (which use `sys.executable`).

### Path Resolution: config.yaml → runner.py

The `path` field in `config.yaml` is passed as-is to the worker subprocess:
- `loader.py`: validates `repo_root / config.path` exists at startup
- `runner.py` line 57: passes `config.path` directly as `sys.argv[1]` to `entrypoint.py`
- `entrypoint.py`: uses `importlib.util.spec_from_file_location("skill_module", module_path)` — this resolves relative paths against the current working directory

**Implication:** `nimble start` (and therefore the daemon) must be run from the repo root for `skills/hello_world/skill.py` to resolve correctly. This is the expected developer workflow for v1. It is a known limitation noted in `deferred-work.md`.

Use `path: skills/hello_world/skill.py` in `config.yaml`.

### Exact Position for Startup Notification in daemon.py

Insert the notification call at **exactly** this location (after `write_pid`, before watcher creation):

```python
adapter.start()
write_pid(os.getpid())
started = True

notifier.send("Nimble", "Nimble daemon running.")   # ← ADD THIS LINE (FR41)

def _shutdown_worker(name: str) -> None:            # existing code
```

The notification must fire after `adapter.start()` because that is the moment hotkeys are live. Firing it earlier (e.g. after `spawn_workers`) would be premature — hotkeys would not yet be registered.

### config.yaml Format

The parser (`nimble/manifest/parser.py`) requires exactly these fields per skill entry: `name`, `source`, `path`, `class_name`, `binding`. `source` must be `"local"` or `"community"`.

Final `config.yaml`:
```yaml
skills:
  - name: hello_world
    source: local
    path: skills/hello_world/skill.py
    class_name: HelloWorldSkill
    binding: "ctrl+shift+h"
```

The `bindings:` key at the top level is no longer needed — the parser uses `skills[].binding` for hotkey registration. Remove it to avoid confusion.

### skills/ Directory Is Committed (FR42)

`skills/` must NOT be in `.gitignore`. Check `.gitignore` to ensure it doesn't exclude `skills/`. If it does, remove the exclusion. The `.nimble/` directory IS in `.gitignore` (community skills) — `skills/` is the author-owned directory that is committed.

### Testing daemon.py Startup Notification

The daemon `run()` function is hard to unit test directly because it blocks on `stop_event.wait()`. The recommended approach is to patch the blocking call:

```python
import threading
from unittest.mock import MagicMock, patch

from tests.conftest import FakeNotifier

def test_startup_notification_fires(tmp_path: Path) -> None:
    fake_notifier = FakeNotifier()

    config_path = tmp_path / "config.yaml"
    config_path.write_text("skills: []\n")

    with (
        patch("nimble.daemon.get_adapter") as mock_adapter_factory,
        patch("nimble.daemon.load_config") as mock_load_config,
        patch("nimble.daemon.validate_skill_paths", return_value=[]),
        patch("nimble.daemon.SkillRunner") as mock_runner_cls,
        patch("nimble.daemon.ConfigWatcher") as mock_watcher_cls,
        patch("nimble.daemon.write_pid"),
        patch("nimble.daemon.remove_pid"),
        patch("nimble.daemon.Notifier", return_value=fake_notifier),
    ):
        stop_event_holder: list[threading.Event] = []

        def fake_wait() -> None:
            pass  # return immediately instead of blocking

        mock_stop_event = MagicMock()
        mock_stop_event.wait.side_effect = fake_wait

        with patch("threading.Event", return_value=mock_stop_event):
            from nimble import daemon
            daemon.run(tmp_path)

    assert ("Nimble", "Nimble daemon running.") in fake_notifier.sent
```

This is a guidance sketch — adjust mock setup to match how `daemon.run()` uses its dependencies. The key assertion is `("Nimble", "Nimble daemon running.") in fake_notifier.sent`.

### mypy Scope

`mypy --strict` is enforced on `nimble/`, `tests/`, and `worker/`. The `skills/` directory is NOT in mypy scope. Do not add type annotations that conflict with mypy strict — the hello_world skill just needs to work, not pass strict type checking.

However, the new test files (`tests/unit/test_daemon.py` and `tests/unit/skills/test_hello_world.py`) ARE in mypy scope — annotate them fully.

### Patterns Carried Forward from Story 2.8

- `from __future__ import annotations` at top of every new `nimble/` or `tests/` module
- Absolute imports only: `from nimble.daemon import run`, never relative
- Module-level `logger = logging.getLogger(__name__)` in every new `nimble/` module
- `FakeNotifier` from `tests/conftest.py` — do not define a new one in test files
- Lazy plyer import inside method body (same pattern as `nimble/notifier.py`) — prevents import failures in headless CI

### Cross-Story Dependencies

- **Stories 2.1–2.8** (ALL DONE): Entire daemon stack is functional. This story adds the finishing touches.
- **Story 4.2** (later): Replaces `logging.basicConfig` with `RotatingFileHandler`. No changes to this story's code needed.
- **Story 5.1** (later): Adds `state.json`. No changes to this story's code needed.
- **Epic 3** (later): Implements `tools.*` primitives. The hello_world skill will then be updatable to use `tools.popup.show()` instead of plyer directly — but that's a future enhancement, not required here.

### New Files

```
skills/hello_world/skill.py           ← new
skills/hello_world/manifest.yaml      ← new
tests/unit/test_daemon.py             ← new
tests/unit/skills/test_hello_world.py ← new
```

### Modified Files

```
config.yaml          ← add hello_world skill entry + ctrl+shift+h binding
nimble/daemon.py     ← one line added: notifier.send("Nimble", "Nimble daemon running.")
```

### Do NOT Modify

```
nimble/notifier.py         (Notifier class — already correct)
nimble/manifest/parser.py  (off-limits per Story 2.8 constraint; unchanged in this story)
nimble/skills/runner.py    (no changes needed)
nimble/skills/loader.py    (no changes needed)
worker/entrypoint.py       (no changes needed)
tests/conftest.py          (FakeNotifier already defined here)
```

### Deferred

- Using `tools.popup.show()` in hello_world — deferred to Epic 3 when tools primitives are implemented
- Adding `skills/` to mypy/flake8/black scope — deferred; skills are user-authored code with relaxed quality gates
- macOS hotkey adapter — deferred to Story 2.10

### References

- [Source: docs/bmad_output/planning-artifacts/epics.md#Story 2.9] — acceptance criteria, FR41, FR42, FR45
- [Source: docs/bmad_output/planning-artifacts/architecture.md#Repository Module Structure] — `skills/hello_world/` location, `config.yaml` at repo root
- [Source: docs/bmad_output/planning-artifacts/architecture.md#All AI Agents MUST] — naming, import, type annotation, test rules
- [Source: docs/bmad_output/planning-artifacts/epics.md#Additional Requirements] — hello_world ships with template pre-bound to ctrl+shift+h
- [Source: docs/bmad_output/implementation-artifacts/2-8-daemon-main-loop-and-cli-start-stop-restart.md#Dev Notes] — `Notifier` usage, patterns carried forward, `tools=None` note
- [Source: nimble/notifier.py] — lazy plyer import pattern, `Notifier.send()` signature
- [Source: nimble/manifest/parser.py] — required config.yaml skill fields: name, source, path, class_name, binding
- [Source: nimble/daemon.py] — exact insertion point for startup notification (after write_pid, before ConfigWatcher)
- [Source: worker/entrypoint.py#83] — `tools = None` — hello_world cannot use tools.*

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- All 7 tasks completed in a single execution pass with no blockers.
- `skills/hello_world/skill.py`: `HelloWorldSkill.run()` uses lazy plyer import inside method body, matching `nimble/notifier.py` pattern. Exception is silently swallowed to protect daemon stability.
- `nimble/daemon.py`: Single line `notifier.send("Nimble", "Nimble daemon running.")` inserted after `write_pid(os.getpid())` and before `_shutdown_worker` definition, exactly per FR41 spec.
- `config.yaml`: Replaced `skills: []\nbindings: []` with hello_world skill entry bound to `ctrl+shift+h`. `bindings:` top-level key removed as it's unused by parser.
- `tests/unit/test_daemon.py`: Patches `threading.Event` to return a mock that returns immediately from `wait()`, allowing `daemon.run()` to be called synchronously in tests. `FakeNotifier` from `tests/conftest.py` injected via `patch("nimble.daemon.Notifier", return_value=fake_notifier)`.
- `tests/unit/skills/test_hello_world.py`: Uses `importlib.util.spec_from_file_location` to load `HelloWorldSkill` from `skills/` directory (which is outside the Python package), matching how `worker/entrypoint.py` loads skills in production.
- Pre-existing `test_platform.py` mypy errors (`nimble.platform.sys` attr-defined) confirmed pre-date this story — not introduced here.
- 104 tests pass, 0 regressions.

### File List

- `skills/hello_world/skill.py` (new)
- `skills/hello_world/manifest.yaml` (new)
- `tests/unit/test_daemon.py` (new)
- `tests/unit/skills/test_hello_world.py` (new)
- `config.yaml` (modified)
- `nimble/daemon.py` (modified)
- `docs/bmad_output/implementation-artifacts/sprint-status.yaml` (modified)

## Change Log

- 2026-04-24: Implemented Story 2.9 — added `skills/hello_world/` bundled skill, updated `config.yaml` with `ctrl+shift+h` binding, added startup notification to `nimble/daemon.py`, created 4 new test files. 104 tests pass.
